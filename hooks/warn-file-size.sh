#!/usr/bin/env bash
# PostToolUse hook for the Write and Edit tools: warn once when a NEWLY CREATED source file
# (.py/.cs/.rs) exceeds its language's "worth reviewing" line threshold (coding-general.md section 3).
# Silent for any file tracked at HEAD (checked with git ls-files), so it never nags edits to
# pre-existing files. POSIX port of warn-file-size.ps1 (Windows uses the .ps1). This is the only
# content-reading hook: it opens the written file to count lines, under a byte cap, and echoes NO
# file content, only the count. JSON in is parsed with Perl JSON::PP (a core module).
#
# PostToolUse cannot block; the tool already ran. A warning is exit 2 with a short message on stderr,
# which Claude Code surfaces to the model. Fails OPEN: a missing tool, parse error, unreadable file,
# or any fault exits 0 and warns nothing.
# Self-test:  bash warn-file-size.sh --check path/to/file.py   (prints warn|silent)
# See hooks/README.md for install and tuning.

# Warn thresholds: the start of the "worth reviewing" tier per coding-general.md section 3. Keep in
# sync with SIZE_WARN_THRESHOLD in each skill's scripts/*_quality_gate.py.
WARN_PY=800
WARN_CS=700
WARN_RS=700
# Stop reading past this many bytes: a source file larger than this is over any threshold anyway.
BYTE_CAP=2000000
# Secret-looking basenames: never open one, even with a gated extension (secrets.py, credentials.py).
SECRET='(^|/)secrets\.|(^|/)credentials\.|(^|/)\.env|(^|/)private_key|(^|/)master\.key'
# The .example/.template/.sample sample forms are never secret.
SAFE='\.(example|template|sample)([^/]*)$'

# Print "<threshold> <lang>" for a gated path's extension, or nothing.
threshold_for() {
    case "$1" in
        *.py) printf '%s Python\n' "$WARN_PY" ;;
        *.cs) printf '%s C#\n' "$WARN_CS" ;;
        *.rs) printf '%s Rust\n' "$WARN_RS" ;;
    esac
}

# classify PATH: on a qualifying oversized new file, emit the warning to stderr and return 2;
# otherwise return 0. Never echoes file content.
classify() {
    path="$1"
    tw="$(threshold_for "$path")"
    [ -n "$tw" ] || return 0
    threshold="${tw%% *}"
    lang="${tw#* }"
    if printf '%s' "$path" | grep -qiE "$SECRET" && ! printf '%s' "$path" | grep -qiE "$SAFE"; then
        return 0
    fi
    [ -f "$path" ] || return 0
    [ -L "$path" ] && return 0
    command -v git >/dev/null 2>&1 || return 0
    dir="$(dirname "$path")"
    if git -C "$dir" ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
        return 0
    fi
    count="$(head -c "$BYTE_CAP" "$path" 2>/dev/null | awk 'END{print NR}')"
    case "$count" in '' | *[!0-9]*) return 0 ;; esac
    [ "$count" -ge "$threshold" ] || return 0
    printf '[warn-file-size] New %s file: %s lines, at or over the %s-line "worth reviewing" tier.\n' \
        "$lang" "$count" "$threshold" >&2
    printf '[warn-file-size] Split new code into a new cohesive module; never mass-refactor an existing file for size (coding-general.md section 3).\n' >&2
    if [ "${path##*.}" = "rs" ]; then
        printf '[warn-file-size] The new-code size gate subtracts the trailing #[cfg(test)] module, so the effective production count may be below this raw count.\n' >&2
    fi
    return 2
}

# --- main ---
if [ "$1" = "--check" ]; then
    classify "$2" 2>/dev/null
    if [ $? -eq 2 ]; then printf 'warn\n'; else printf 'silent\n'; fi
    exit 0
fi

path="$(perl -MJSON::PP -0777 -ne 'my $d=eval{decode_json($_)}; exit unless $d; my $p=$d->{tool_input}{file_path}; print $p if defined $p;' 2>/dev/null)"
[ -n "$path" ] || exit 0
classify "$path"
exit $?
