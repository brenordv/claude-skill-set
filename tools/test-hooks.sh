#!/usr/bin/env bash
# Test harness for the four PreToolUse hook scripts in hooks/*.sh. Nothing else in the pipeline ever
# parses or runs those scripts: lint-repo checks markdown prose, and the hooks only execute on an
# installed machine. A heredoc built inside command substitution (VAR="$(cat <<'MSG' ... MSG )")
# parses on bash >= 5.2 but mis-lexes an apostrophe in the body on the bash 3.2 that ships with macOS,
# so a hook could fail to parse on the OS it targets while every CI runner stayed green. This harness
# closes that gap with three layers:
#
#   1. syntax   -- "$BASH" -n over hooks/*.sh and tools/*.sh.
#   2. pattern  -- fail if a command-substitution-wrapped heredoc reappears in any hooks/*.sh, so the
#                  incident class is blocked even on a bash new enough to parse it cleanly.
#   3. behavior -- feed JSON payloads to each hook on stdin (the production path) and assert the
#                  verdict, exit status, and (on deny) that the real message came back intact.
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
# JSON in/out uses Perl with JSON::PP, the same core module the hooks require; if it is missing the
# hooks fail open (emit nothing) and every deny row here fails loudly rather than being skipped.

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

# --- layer 3: behavior ---
# Parallel-array case table. Each row: script, tool_name, tool_input JSON, expected verdict
# (deny|allow), reason signature (a substring the deny message must contain; empty for allow rows).
# Deny signatures pick a phrase unique to the emitted message, and include an apostrophe wherever the
# message has one, so a body mangled by the 3.2 lexer bug cannot pass.
C_SCRIPT=(); C_TOOL=(); C_INPUT=(); C_EXPECT=(); C_SIG=()
add_case() {
    if [ "$#" -ne 5 ]; then
        printf 'test-hooks: malformed case row (need 5 fields, got %s): %s\n' "$#" "$*" >&2
        exit 2
    fi
    C_SCRIPT[${#C_SCRIPT[@]}]="$1"
    C_TOOL[${#C_TOOL[@]}]="$2"
    C_INPUT[${#C_INPUT[@]}]="$3"
    C_EXPECT[${#C_EXPECT[@]}]="$4"
    C_SIG[${#C_SIG[@]}]="$5"
}

RT="route-to-text-tools.sh"
RT_SEARCH="command's OWN output"
RT_EDIT="the repo's absolute path. For one hand-shaped edit"
RT_GIT="Use these with cwd = the repo's absolute path"
add_case "$RT" Bash '{"command":"grep -r foo ."}'        deny  "$RT_SEARCH"
add_case "$RT" Bash '{"command":"dotnet test | tail -20"}' allow ''
add_case "$RT" Bash '{"command":"sed -i s/a/b/ f"}'      deny  "$RT_EDIT"
add_case "$RT" Bash '{"command":"git log --oneline"}'    deny  "$RT_GIT"
add_case "$RT" Bash '{"command":"git commit -m x"}'      allow ''
add_case "$RT" Bash '{"command":"ls -R"}'                deny  "$RT_SEARCH"
add_case "$RT" Bash '{"command":"ls -r"}'                allow ''
add_case "$RT" Bash '{"command":"build && grep TODO src"}' deny "$RT_SEARCH"
add_case "$RT" Bash '{"command":"git branch"}'           deny  "$RT_GIT"
add_case "$RT" Bash '{"command":"git branch -d x"}'      allow ''

BS="block-secrets.sh"
BS_SIG="reads or copies a file matching a secret-file pattern"
add_case "$BS" Bash '{"command":"cat .env"}'                       deny  "$BS_SIG"
add_case "$BS" Bash '{"command":"cat .env.example"}'               allow ''
add_case "$BS" Bash '{"command":"grep FOO .env"}'                  allow ''
add_case "$BS" Bash '{"command":"cp secrets.json out"}'            deny  "$BS_SIG"
add_case "$BS" Bash '{"command":"head master.key"}'                deny  "$BS_SIG"
add_case "$BS" Bash '{"command":"cat appsettings.Production.json"}' deny "$BS_SIG"
add_case "$BS" Bash '{"command":"cat .env > out"}'                 deny  "$BS_SIG"

GF="guard-file-targets.sh"
GF_SIG="targets a secret-looking file"
add_case "$GF" Glob '{"pattern":"**/.env*"}'              deny  "$GF_SIG"
add_case "$GF" Read '{"file_path":".env"}'                deny  "$GF_SIG"
add_case "$GF" Read '{"file_path":".env.example"}'        allow ''
add_case "$GF" Grep '{"pattern":".env"}'                  allow ''
add_case "$GF" Read '{"file_path":"docs/environment.md"}' allow ''
add_case "$GF" Grep '{"glob":"**/*.pem"}'                 deny  "$GF_SIG"
add_case "$GF" Read '{"file_path":"config/secrets.yaml"}' deny  "$GF_SIG"

BV="block-vcs-writes.sh"
BV_GIT="never stage, never commit, never stash"
BV_STACK="stack management is the user's responsibility"
add_case "$BV" Bash '{"command":"git commit -m x"}'      deny  "$BV_GIT"
add_case "$BV" Bash '{"command":"git add ."}'            deny  "$BV_GIT"
add_case "$BV" Bash '{"command":"git stash pop"}'        deny  "$BV_GIT"
add_case "$BV" Bash '{"command":"git stash"}'            deny  "$BV_GIT"
add_case "$BV" Bash '{"command":"git stash list"}'       allow ''
add_case "$BV" Bash '{"command":"git -C sub commit -m x"}' deny "$BV_GIT"
add_case "$BV" Bash '{"command":"echo hi && git add -A"}' deny "$BV_GIT"
add_case "$BV" Bash '{"command":"gh stack submit"}'      deny  "$BV_STACK"
add_case "$BV" Bash '{"command":"gh stack view --json"}' allow ''
add_case "$BV" Bash '{"command":"git push"}'             allow ''

decode_field() {
    # $1 = raw hook stdout, $2 = "permissionDecision" | "permissionDecisionReason".
    # The field name goes through the environment, never @ARGV: under -n an @ARGV entry would be read
    # as an input filename and stdin would never be consumed.
    printf '%s' "$1" | FIELD="$2" perl -MJSON::PP -0777 -ne '
        my $d = eval { decode_json($_) }; exit unless $d;
        print $d->{hookSpecificOutput}{$ENV{FIELD}} // "";
    ' 2>/dev/null
}

ERRFILE="$(mktemp 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}/test-hooks.$$")"
trap 'rm -f "$ERRFILE"' EXIT

declared="${#C_SCRIPT[@]}"
executed=0
i=0
while [ "$i" -lt "$declared" ]; do
    script="${C_SCRIPT[$i]}"; tool="${C_TOOL[$i]}"; input="${C_INPUT[$i]}"
    expect="${C_EXPECT[$i]}"; sig="${C_SIG[$i]}"
    i=$((i + 1))
    disp="$HOOKS_DIR/$script"
    name="$tool $input"
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

    if [ "$expect" = allow ]; then
        problem=""
        if [ -n "$out" ]; then
            problem="expected empty stdout, got output"
        elif [ "$rc" -ne 0 ]; then
            problem="expected exit 0, got $rc"
        elif [ -s "$ERRFILE" ]; then
            problem="expected empty stderr, got stderr output"
        fi
        if [ -n "$problem" ]; then
            report "$disp: [behavior] case \"$name\": expected allow, $problem"
            printf '    stdout: %s\n' "$out_oneline"
            printf '    stderr: %s\n' "$stderr_shown"
            printf '    exit:   %s\n' "$rc"
        fi
    else
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
    fi
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
