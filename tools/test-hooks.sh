#!/usr/bin/env bash
# Test harness for the five hook pairs in hooks/ (.sh side; tools/test-hooks.ps1 runs the .ps1 side
# against the same case table, so a behavior divergence between the two implementations shows up as
# one platform's CI job failing while the other passes). Nothing else in the pipeline ever parses or
# runs these scripts: lint-repo checks markdown prose, and the hooks only execute on an installed
# machine. A heredoc built inside command substitution (VAR="$(cat <<'MSG' ... MSG )") parses on
# bash >= 5.2 but mis-lexes an apostrophe in the body on the bash 3.2 that ships with macOS, so a
# hook could fail to parse on the OS it targets while every CI runner stayed green. This harness
# closes that gap, and its siblings, with four layers:
#
#   1. syntax    -- "$BASH" -n over hooks/*.sh and tools/*.sh.
#   2. pattern   -- fail if a command-substitution-wrapped heredoc reappears in any hooks/*.sh, so
#                   the incident class is blocked even on a bash new enough to parse it cleanly.
#   3. threshold -- the file-size warn thresholds and size constants live in five scripts (both
#                   warn-file-size hooks and the three quality gates); extract and cross-compare
#                   them so a hand-sync miss goes red instead of drifting silently.
#   4. behavior  -- feed the JSON payloads from tools/hook-cases.tsv to each hook on stdin (the
#                   production path) and assert the verdict, exit status, and (on deny/warn) that
#                   the real message came back intact.
#
# Every bash invocation uses "$BASH", the interpreter running this harness, not bare `bash` or the
# hooks' shebang: that is what lets the macOS CI job run this under /bin/bash 3.2 as a true reproducer.
# Bodies stay inert: payloads reach a hook only as bytes on stdin, never through eval or a field
# spliced into command position. Written to run on bash 3.2 and Git Bash (no mapfile, associative
# arrays, ${var,,}, [[ =~ ]], or globstar).
#
#   bash tools/test-hooks.sh                       # check the repo's hooks/
#   bash tools/test-hooks.sh --hooks-dir ~/.claude/hooks   # check an installed copy
#
# With --hooks-dir, the behavior and threshold layers grade the hooks in that directory against this
# checkout's case table and gate scripts, so an installed copy that drifted behind repo policy fails.
# JSON in/out uses Perl with JSON::PP, the same core module the hooks require; if it is missing the
# hooks fail open (emit nothing) and every deny row here fails loudly rather than being skipped.
# Exit codes: 0 all layers green, 1 case or layer failures, 2 harness/setup error.

: "${BASH:?test-hooks: must run under bash (BASH is unset)}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || { printf 'test-hooks: cannot cd to repo root %s\n' "$REPO_ROOT" >&2; exit 2; }

HOOKS_DIR="hooks"
while [ $# -gt 0 ]; do
    case "$1" in
        --hooks-dir)   [ $# -ge 2 ] || { printf 'test-hooks: --hooks-dir needs a value\n' >&2; exit 2; }
                       HOOKS_DIR="$2"; shift 2 ;;
        --hooks-dir=*) HOOKS_DIR="${1#--hooks-dir=}"; shift ;;
        -h|--help)     printf 'usage: %s [--hooks-dir DIR]\n' "$0"; exit 0 ;;
        *)             printf 'test-hooks: unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
[ -d "$HOOKS_DIR" ] || { printf 'test-hooks: hooks dir not found: %s\n' "$HOOKS_DIR" >&2; exit 2; }

FAILCOUNT=0
report() { FAILCOUNT=$((FAILCOUNT + 1)); printf '%s\n' "$1"; }

# --- layer 1: syntax ---
for f in "$HOOKS_DIR"/*.sh tools/*.sh; do
    [ -e "$f" ] || continue
    errout="$("$BASH" -n "$f" 2>&1)" || report "$f: [syntax]: ${errout:-parse failed}"
done

# --- layer 2: pattern guard ---
# A '$(' or backtick that opens a command substitution followed on the same line by a heredoc opener
# is the exact shape that mis-parses on bash 3.2. Scans hooks/*.sh only, which keeps this harness's own
# pattern literal out of scope. Message-body backticks never sit on a line that also carries '<<'.
GUARD_RE='(\$\(|`).*<<'
for f in "$HOOKS_DIR"/*.sh; do
    [ -e "$f" ] || continue
    hits="$(grep -nE "$GUARD_RE" "$f" 2>/dev/null)"
    [ -n "$hits" ] || continue
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        report "$f: [pattern] command-substitution heredoc: $line"
    done <<PATTERN_HITS
$hits
PATTERN_HITS
done

# --- layer 3: threshold sync ---
# The warn thresholds and size constants are declared independently in five scripts and kept equal
# by hand. Extraction is deliberately strict: a constant must match its anchored pattern on exactly
# one line, and the value must be a plain integer after stripping '_' separators and any CR; zero
# matches, multiple matches, or a non-integer are each a failure, never a silent skip. The values
# are only cross-compared, never checked against literals baked in here, so a deliberate retune
# that updates all five scripts together stays green without touching this harness.
ts_extract() {
    # $1 = file, $2 = anchored ERE for the count check, $3 = unanchored ERE with one capture group
    # for the value, $4 = label. Sets TS_VALUE to the extracted integer, or to '' after reporting.
    # Called as a plain command, never inside $(...): report must run in this shell so the failure
    # line prints and FAILCOUNT moves.
    TS_VALUE=""
    ts_file="$1"; ts_grep="$2"; ts_cap="$3"; ts_label="$4"
    if [ ! -f "$ts_file" ]; then
        report "$ts_file: [threshold] $ts_label: file not found"
        return 1
    fi
    ts_hits="$(grep -cE "$ts_grep" "$ts_file" 2>/dev/null)"
    if [ "$ts_hits" != "1" ]; then
        report "$ts_file: [threshold] $ts_label: expected exactly 1 matching line, found ${ts_hits:-0}"
        return 1
    fi
    ts_value="$(grep -E "$ts_grep" "$ts_file" | sed -E "s/^.*$ts_cap.*\$/\1/" | tr -d '_\r')"
    case "$ts_value" in
        '' | *[!0-9]*)
            report "$ts_file: [threshold] $ts_label: extracted value is not a plain integer: \"$ts_value\""
            return 1
            ;;
    esac
    TS_VALUE="$ts_value"
}

ts_agree() {
    # $1 = constant label; then repeated pairs: description, value. An empty value means its
    # extraction already reported; skip it here.
    ts_l="$1"; shift
    ts_ref=""; ts_refdesc=""
    while [ $# -ge 2 ]; do
        ts_d="$1"; ts_v="$2"; shift 2
        [ -n "$ts_v" ] || continue
        if [ -z "$ts_ref" ]; then
            ts_ref="$ts_v"; ts_refdesc="$ts_d"
            continue
        fi
        if [ "$ts_v" != "$ts_ref" ]; then
            report "$ts_d: [threshold] $ts_l: $ts_v != $ts_ref ($ts_refdesc)"
        fi
    done
}

WFS="$HOOKS_DIR/warn-file-size.sh"
WFP="$HOOKS_DIR/warn-file-size.ps1"
GATE_PY="skills/python/scripts/python_quality_gate.py"
GATE_CS="skills/csharp/scripts/csharp_quality_gate.py"
GATE_RS="skills/rust/scripts/rust_quality_gate.py"

ts_extract "$WFS" '^WARN_PY=[0-9]+' 'WARN_PY=([0-9]+)' 'WARN_PY';              t_sh_py="$TS_VALUE"
ts_extract "$WFS" '^WARN_CS=[0-9]+' 'WARN_CS=([0-9]+)' 'WARN_CS';              t_sh_cs="$TS_VALUE"
ts_extract "$WFS" '^WARN_RS=[0-9]+' 'WARN_RS=([0-9]+)' 'WARN_RS';              t_sh_rs="$TS_VALUE"
ts_extract "$WFS" '^BYTE_CAP=[0-9]+' 'BYTE_CAP=([0-9]+)' 'BYTE_CAP';           t_sh_cap="$TS_VALUE"
ts_extract "$WFP" "'\.py' *= *[0-9]+" "'\.py' *= *([0-9]+)" '.py warn';        t_ps_py="$TS_VALUE"
ts_extract "$WFP" "'\.cs' *= *[0-9]+" "'\.cs' *= *([0-9]+)" '.cs warn';        t_ps_cs="$TS_VALUE"
ts_extract "$WFP" "'\.rs' *= *[0-9]+" "'\.rs' *= *([0-9]+)" '.rs warn';        t_ps_rs="$TS_VALUE"
ts_extract "$WFP" '^.byteCap *= *[0-9]+' 'byteCap *= *([0-9]+)' 'byteCap';     t_ps_cap="$TS_VALUE"
ts_extract "$GATE_PY" '^SIZE_WARN_THRESHOLD = [0-9_]+' 'SIZE_WARN_THRESHOLD = ([0-9_]+)' 'SIZE_WARN_THRESHOLD'; t_g1_warn="$TS_VALUE"
ts_extract "$GATE_CS" '^SIZE_WARN_THRESHOLD = [0-9_]+' 'SIZE_WARN_THRESHOLD = ([0-9_]+)' 'SIZE_WARN_THRESHOLD'; t_g2_warn="$TS_VALUE"
ts_extract "$GATE_RS" '^SIZE_WARN_THRESHOLD = [0-9_]+' 'SIZE_WARN_THRESHOLD = ([0-9_]+)' 'SIZE_WARN_THRESHOLD'; t_g3_warn="$TS_VALUE"
ts_extract "$GATE_PY" '^SIZE_FAIL_CAP = [0-9_]+' 'SIZE_FAIL_CAP = ([0-9_]+)' 'SIZE_FAIL_CAP';                   t_g1_cap="$TS_VALUE"
ts_extract "$GATE_CS" '^SIZE_FAIL_CAP = [0-9_]+' 'SIZE_FAIL_CAP = ([0-9_]+)' 'SIZE_FAIL_CAP';                   t_g2_cap="$TS_VALUE"
ts_extract "$GATE_RS" '^SIZE_FAIL_CAP = [0-9_]+' 'SIZE_FAIL_CAP = ([0-9_]+)' 'SIZE_FAIL_CAP';                   t_g3_cap="$TS_VALUE"
ts_extract "$GATE_PY" '^SIZE_GROWTH_ALLOWANCE = [0-9_]+' 'SIZE_GROWTH_ALLOWANCE = ([0-9_]+)' 'SIZE_GROWTH_ALLOWANCE'; t_g1_allow="$TS_VALUE"
ts_extract "$GATE_CS" '^SIZE_GROWTH_ALLOWANCE = [0-9_]+' 'SIZE_GROWTH_ALLOWANCE = ([0-9_]+)' 'SIZE_GROWTH_ALLOWANCE'; t_g2_allow="$TS_VALUE"
ts_extract "$GATE_RS" '^SIZE_GROWTH_ALLOWANCE = [0-9_]+' 'SIZE_GROWTH_ALLOWANCE = ([0-9_]+)' 'SIZE_GROWTH_ALLOWANCE'; t_g3_allow="$TS_VALUE"
ts_extract "$GATE_PY" '^SIZE_READ_BYTE_CAP = [0-9_]+' 'SIZE_READ_BYTE_CAP = ([0-9_]+)' 'SIZE_READ_BYTE_CAP';    t_g1_bytes="$TS_VALUE"
ts_extract "$GATE_CS" '^SIZE_READ_BYTE_CAP = [0-9_]+' 'SIZE_READ_BYTE_CAP = ([0-9_]+)' 'SIZE_READ_BYTE_CAP';    t_g2_bytes="$TS_VALUE"
ts_extract "$GATE_RS" '^SIZE_READ_BYTE_CAP = [0-9_]+' 'SIZE_READ_BYTE_CAP = ([0-9_]+)' 'SIZE_READ_BYTE_CAP';    t_g3_bytes="$TS_VALUE"

ts_agree ".py warn tier" \
    "$WFS WARN_PY" "$t_sh_py" "$WFP '.py'" "$t_ps_py" "$GATE_PY SIZE_WARN_THRESHOLD" "$t_g1_warn"
ts_agree ".cs warn tier" \
    "$WFS WARN_CS" "$t_sh_cs" "$WFP '.cs'" "$t_ps_cs" "$GATE_CS SIZE_WARN_THRESHOLD" "$t_g2_warn"
ts_agree ".rs warn tier" \
    "$WFS WARN_RS" "$t_sh_rs" "$WFP '.rs'" "$t_ps_rs" "$GATE_RS SIZE_WARN_THRESHOLD" "$t_g3_warn"
ts_agree "fail cap" \
    "$GATE_PY SIZE_FAIL_CAP" "$t_g1_cap" "$GATE_CS SIZE_FAIL_CAP" "$t_g2_cap" \
    "$GATE_RS SIZE_FAIL_CAP" "$t_g3_cap"
ts_agree "growth allowance" \
    "$GATE_PY SIZE_GROWTH_ALLOWANCE" "$t_g1_allow" "$GATE_CS SIZE_GROWTH_ALLOWANCE" "$t_g2_allow" \
    "$GATE_RS SIZE_GROWTH_ALLOWANCE" "$t_g3_allow"
ts_agree "read byte cap" \
    "$WFS BYTE_CAP" "$t_sh_cap" "$WFP byteCap" "$t_ps_cap" \
    "$GATE_PY SIZE_READ_BYTE_CAP" "$t_g1_bytes" "$GATE_CS SIZE_READ_BYTE_CAP" "$t_g2_bytes" \
    "$GATE_RS SIZE_READ_BYTE_CAP" "$t_g3_bytes"

# --- layer 4: behavior ---
# Parallel-array case table, loaded from tools/hook-cases.tsv (shared with test-hooks.ps1). Deny
# signatures pick a phrase unique to the emitted message, and include an apostrophe wherever the
# message has one, so a body mangled by the 3.2 lexer bug cannot pass.
C_SCRIPT=(); C_TOOL=(); C_INPUT=(); C_EXPECT=(); C_SIG=(); C_ROW=()
add_case() {
    if [ "$#" -ne 6 ]; then
        printf 'test-hooks: malformed case row (need 6 fields, got %s): %s\n' "$#" "$*" >&2
        exit 2
    fi
    C_SCRIPT[${#C_SCRIPT[@]}]="$1"
    C_TOOL[${#C_TOOL[@]}]="$2"
    C_INPUT[${#C_INPUT[@]}]="$3"
    C_EXPECT[${#C_EXPECT[@]}]="$4"
    C_SIG[${#C_SIG[@]}]="$5"
    C_ROW[${#C_ROW[@]}]="$6"
}

# warn-file-size reads the file named in the payload, so its rows need real fixtures. The fixture
# set is declared here and again in test-hooks.ps1 on purpose: six stable lines whose drift fails
# loudly as wrong verdicts beat a fixture-description format with parsers in two languages.
WF_FIXDIR="$(mktemp -d 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}/test-hooks-fix.$$")"
mkdir -p "$WF_FIXDIR/cfg.sample" 2>/dev/null
[ -d "$WF_FIXDIR/cfg.sample" ] || { printf 'test-hooks: cannot create fixture dir %s\n' "$WF_FIXDIR" >&2; exit 2; }

ERRFILE="$(mktemp 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}/test-hooks.$$")"
trap 'rm -f "$ERRFILE"; [ -n "$WF_FIXDIR" ] && rm -rf "$WF_FIXDIR"' EXIT

gen_lines() {  # $1 = line count, $2 = destination file; verifies the count landed
    _n=1
    while [ "$_n" -le "$1" ]; do printf 'x = %s\n' "$_n"; _n=$((_n + 1)); done > "$2"
    _got="$(wc -l < "$2" 2>/dev/null | tr -d ' \t\r')"
    case "$_got" in '' | *[!0-9]*) _got="unreadable" ;; esac
    if [ "$_got" != "$1" ]; then
        printf 'test-hooks: fixture %s: expected %s lines, found %s\n' "$2" "$1" "$_got" >&2
        exit 2
    fi
}
gen_lines 801 "$WF_FIXDIR/big.py"
gen_lines 5 "$WF_FIXDIR/small.py"
gen_lines 750 "$WF_FIXDIR/big.rs"
gen_lines 900 "$WF_FIXDIR/notes.md"
gen_lines 801 "$WF_FIXDIR/cfg.sample/secrets.py"
gen_lines 801 "$WF_FIXDIR/secrets.example.py"

# Load the table. Validation is strict because the runner's deny branch is the fallback and an
# empty signature would make grep -Fq match anything: exactly five fields, none empty, a known
# verdict, '-' only on allow/silent rows (normalized to empty), a shape-checked hook name, no
# unsubstituted placeholder, and a payload that still parses as JSON after substitution.
CASES_FILE="$SCRIPT_DIR/hook-cases.tsv"
[ -f "$CASES_FILE" ] || { printf 'test-hooks: case table not found: %s\n' "$CASES_FILE" >&2; exit 2; }
TAB="$(printf '\t')"
CR="$(printf '\r')"
declared_cases=""
tsv_row=0
while IFS= read -r line || [ -n "$line" ]; do
    tsv_row=$((tsv_row + 1))
    line="${line%$CR}"
    case "$line" in
        '') continue ;;
        "# cases: "*) declared_cases="${line#"# cases: "}"; continue ;;
        '#'*) continue ;;
    esac
    f1=""; f2=""; f3=""; f4=""; f5=""
    IFS="$TAB" read -r f1 f2 f3 f4 f5 <<ROW
$line
ROW
    bad=""
    if [ -z "$f1" ] || [ -z "$f2" ] || [ -z "$f3" ] || [ -z "$f4" ] || [ -z "$f5" ]; then
        bad="fewer than 5 fields, or an empty field"
    else
        case "$f5" in *"$TAB"*) bad="more than 5 fields" ;; esac
    fi
    if [ -z "$bad" ]; then
        case "$f1" in
            *[!a-z0-9-]*) bad="hook name must be [a-z0-9-] only: \"$f1\"" ;;
        esac
    fi
    if [ -z "$bad" ]; then
        case "$f4" in
            deny | warn)
                [ "$f5" != "-" ] || bad="deny/warn rows need a real signature, got '-'"
                ;;
            allow | silent)
                if [ "$f5" = "-" ]; then f5=""; else bad="allow/silent rows take '-' as the signature"; fi
                ;;
            *) bad="unknown verdict \"$f4\"" ;;
        esac
    fi
    if [ -n "$bad" ]; then
        printf 'test-hooks: hook-cases.tsv row %s: %s\n' "$tsv_row" "$bad" >&2
        exit 2
    fi
    input="${f3//@WF_FIXDIR@/$WF_FIXDIR}"
    input="${input//@REPO_ROOT@/$REPO_ROOT}"
    if printf '%s' "$input" | grep -Eq '@[A-Z_]+@'; then
        printf 'test-hooks: hook-cases.tsv row %s: unsubstituted placeholder in payload\n' "$tsv_row" >&2
        exit 2
    fi
    if ! printf '%s' "$input" | perl -MJSON::PP -0777 -ne 'exit(eval { decode_json($_); 1 } ? 0 : 1)' 2>/dev/null; then
        printf 'test-hooks: hook-cases.tsv row %s: tool_input is not valid JSON after substitution (or perl JSON::PP is unavailable)\n' "$tsv_row" >&2
        exit 2
    fi
    add_case "$f1.sh" "$f2" "$input" "$f4" "$f5" "$tsv_row"
done < "$CASES_FILE"

declared="${#C_SCRIPT[@]}"
case "$declared_cases" in
    '') printf 'test-hooks: hook-cases.tsv has no "# cases: N" header\n' >&2; exit 2 ;;
    *[!0-9]*) printf 'test-hooks: hook-cases.tsv "# cases" header is not a number: %s\n' "$declared_cases" >&2; exit 2 ;;
esac
if [ "$declared" -ne "$declared_cases" ]; then
    printf 'test-hooks: hook-cases.tsv declares %s cases but %s rows parsed\n' "$declared_cases" "$declared" >&2
    exit 2
fi

decode_field() {
    # $1 = raw hook stdout, $2 = "permissionDecision" | "permissionDecisionReason".
    # The field name goes through the environment, never @ARGV: under -n an @ARGV entry would be read
    # as an input filename and stdin would never be consumed.
    printf '%s' "$1" | FIELD="$2" perl -MJSON::PP -0777 -ne '
        my $d = eval { decode_json($_) }; exit unless $d;
        print $d->{hookSpecificOutput}{$ENV{FIELD}} // "";
    ' 2>/dev/null
}

executed=0
i=0
while [ "$i" -lt "$declared" ]; do
    script="${C_SCRIPT[$i]}"; tool="${C_TOOL[$i]}"; input="${C_INPUT[$i]}"
    expect="${C_EXPECT[$i]}"; sig="${C_SIG[$i]}"; row="${C_ROW[$i]}"
    i=$((i + 1))
    disp="$HOOKS_DIR/$script"
    name="row $row: $tool $input"
    scriptpath="$HOOKS_DIR/$script"
    if [ ! -f "$scriptpath" ]; then
        report "$disp: [behavior] case \"$name\": script not found at $scriptpath"
        continue
    fi
    payload="$(printf '{"tool_name":"%s","tool_input":%s}' "$tool" "$input")"
    : > "$ERRFILE"
    out="$(printf '%s' "$payload" | "$BASH" "$scriptpath" 2>"$ERRFILE")"
    rc=$?
    executed=$((executed + 1))
    stderr_shown="$(tr '\n' ' ' < "$ERRFILE")"
    out_oneline="$(printf '%s' "$out" | tr '\n' ' ')"

    case "$expect" in
    allow | silent)
        problem=""
        if [ -n "$out" ]; then
            problem="expected empty stdout, got output"
        elif [ "$rc" -ne 0 ]; then
            problem="expected exit 0, got $rc"
        elif [ -s "$ERRFILE" ]; then
            problem="expected empty stderr, got stderr output"
        fi
        if [ -n "$problem" ]; then
            report "$disp: [behavior] case \"$name\": expected $expect, $problem"
            printf '    stdout: %s\n' "$out_oneline"
            printf '    stderr: %s\n' "$stderr_shown"
            printf '    exit:   %s\n' "$rc"
        fi
        ;;
    warn)
        problem=""
        if [ "$rc" -ne 2 ]; then
            problem="expected exit 2, got $rc"
        elif [ -n "$out" ]; then
            problem="expected empty stdout, got output"
        elif ! grep -Fq -- "$sig" "$ERRFILE"; then
            problem="expected stderr to contain \"$sig\""
        fi
        if [ -n "$problem" ]; then
            report "$disp: [behavior] case \"$name\": $problem"
            printf '    stdout: %s\n' "$out_oneline"
            printf '    stderr: %s\n' "$stderr_shown"
            printf '    exit:   %s\n' "$rc"
        fi
        ;;
    deny)
        decision="$(decode_field "$out" permissionDecision)"
        reason="$(decode_field "$out" permissionDecisionReason)"
        problem=""
        if [ "$rc" -ne 0 ]; then
            problem="expected exit 0, got $rc"
        elif [ "$decision" != deny ]; then
            problem="expected permissionDecision=deny, got \"${decision:-<none>}\""
        elif ! printf '%s' "$reason" | grep -Fq -- "$sig"; then
            problem="expected reason to contain \"$sig\", got \"$(printf '%s' "$reason" | tr '\n' ' ')\""
        fi
        if [ -n "$problem" ]; then
            report "$disp: [behavior] case \"$name\": $problem"
            printf '    stdout: %s\n' "$out_oneline"
            printf '    stderr: %s\n' "$stderr_shown"
            printf '    exit:   %s\n' "$rc"
        fi
        ;;
    esac
done

if [ "$executed" -eq 0 ]; then
    printf 'test-hooks: no behavior cases executed (table has %s rows)\n' "$declared" >&2
    exit 2
fi
if [ "$executed" -ne "$declared" ]; then
    report "test-hooks: [table] executed $executed of $declared declared rows"
fi

printf 'test-hooks: %s cases, %s failed\n' "$executed" "$FAILCOUNT"
[ "$FAILCOUNT" -eq 0 ] || exit 1
exit 0
