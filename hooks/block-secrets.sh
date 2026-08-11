#!/usr/bin/env bash
# PreToolUse hook for the Bash and PowerShell tools: block commands that READ or COPY a file that
# looks like a secret (.env, appsettings.json, secrets.*, credentials.*, *.key/*.pem, master.key,
# .htpasswd, ...). POSIX port of block-secrets.ps1 (Windows uses the .ps1). JSON in/out is handled
# by Perl with JSON::PP, a core module present on stock macOS and Ubuntu, so there is nothing to
# install. Companion to route-to-text-tools (shell probing) and guard-file-targets (native Glob/Grep/
# Read); the three hooks are independent and all run on PreToolUse. This one is shell-only: it sees
# Bash|PowerShell, not the native tools, and it blocks reading or copying a secret, not merely locating one.
#
# Fails OPEN: missing Perl/JSON::PP, a parse error, or any fault exits 0 so a legitimate command is
# never broken. Self-test:  bash block-secrets.sh --command "cat .env"
# See skills/brain/hooks/README.md for install and tuning.

DENY_MSG="$(cat <<'MSG'
Blocked: this command reads or copies a file matching a secret-file pattern (.env, appsettings.json, secrets.*, credentials.*, *.key, *.pem, *.pfx, *.p12, *.jks, *.keystore, master.key, private_key, .htpasswd), which would pull secret material into context. If the target is genuinely non-secret, read it another way or point at its .example/.template/.sample. For legitimate file reads prefer the text-search MCP, which withholds secret-shaped content on its own. Locating or enumerating secret files is equally off-limits, not only reading them; the ban is on seeking a secret, and the native Glob/Grep/Read tools are covered by the guard-file-targets hook. See brain/knowledge/text-search-operations.md.
MSG
)"

# A file that looks like a secret. BSD-grep-safe (no \b/\w): word end is (non-word-char | end-of-line).
SECRET='(\.env([^A-Za-z0-9_]|$)|appsettings\.json|appsettings\.[A-Za-z0-9_]+\.json|secrets\.(json|yaml|yml)|credentials\.(json|yaml)|\.key([^A-Za-z0-9_]|$)|\.pem([^A-Za-z0-9_]|$)|\.pfx([^A-Za-z0-9_]|$)|\.p12([^A-Za-z0-9_]|$)|\.jks([^A-Za-z0-9_]|$)|\.keystore([^A-Za-z0-9_]|$)|master\.key|private_key|\.htpasswd)'
# A non-secret sample that matches a pattern above but is safe to read.
SAFE='\.(example|template|sample)([^A-Za-z0-9_]|$)'
# The command reads file content, copies it, redirects it, or exfiltrates it.
READEXFIL='((cat|head|tail|less|more|type|Get-Content|bat|sed|awk|source)[[:space:]]|(^|[[:space:]])\.[[:space:]]|cp[[:space:]]|copy[[:space:]]|>|curl.*-d.*@|xargs)'

classify() {
    local command="$1"
    printf '%s' "$command" | grep -qiE "$SECRET" || return
    printf '%s' "$command" | grep -qiE "$SAFE" && return
    printf '%s' "$command" | grep -qiE "$READEXFIL" && { echo secret; return; }
}

emit_deny() {
    MSG="$1" perl -MJSON::PP -e 'print encode_json({hookSpecificOutput=>{hookEventName=>"PreToolUse",permissionDecision=>"deny",permissionDecisionReason=>$ENV{MSG}}});' 2>/dev/null
}

# --- main ---
if [ "$1" = "--command" ]; then
    v="$(classify "$2")"
    printf '%s\n' "${v:-allow}"
    exit 0
fi

cmd="$(perl -MJSON::PP -0777 -ne 'my $d=eval{decode_json($_)}; exit unless $d; my $c=$d->{tool_input}{command}; print $c if defined $c;' 2>/dev/null)"
[ -n "$cmd" ] || exit 0

[ "$(classify "$cmd")" = secret ] && emit_deny "$DENY_MSG"
exit 0
