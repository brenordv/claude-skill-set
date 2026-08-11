#!/usr/bin/env bash
# PreToolUse hook for the NATIVE Glob/Grep/Read tools: deny when the target of a file search, listing,
# or read is a secret-looking file (.env, appsettings.json, secrets.*, credentials.*, *.key/*.pem,
# master.key, .htpasswd, ...). POSIX port of guard-file-targets.ps1 (Windows uses the .ps1). JSON in/out
# is handled by Perl with JSON::PP, a core module present on stock macOS and Ubuntu, nothing to install.
#
# This is the native-tool companion to block-secrets and route-to-text-tools, which only match the
# Bash|PowerShell tools. The model can enumerate or open a secret with Glob("**/.env*") or Read(".env")
# without ever shelling out, and no shell hook watches those calls. This hook closes that seam. Unlike
# block-secrets it blocks LOCATING a secret file, not only reading it: the existence and location of a
# secret are not ours to map. It keys on the target field, so pure enumeration is denied too.
#
# Field selection per tool: Glob -> pattern + path; Grep -> glob + path (NOT pattern, which is a content
# regex, not a path); Read -> file_path. Keep the secret/safe regexes in sync with block-secrets.
#
# Fails OPEN: missing Perl/JSON::PP, a parse error, or any fault exits 0 so a legitimate call is never
# broken. Self-test:  bash guard-file-targets.sh --candidate "**/.env"
# See hooks/README.md for install and tuning.

DENY_MSG="$(cat <<'MSG'
Blocked: this Glob/Grep/Read targets a secret-looking file (.env, appsettings.json, secrets.*, credentials.*, *.key, *.pem, *.pfx, *.p12, *.jks, *.keystore, master.key, private_key, .htpasswd). Seeking a secret file is off-limits, not only reading one: its existence and location are not yours to map, and opening it pulls secret material into context. If you need a non-secret sample, target its .example/.template/.sample instead. Legitimate reads of non-secret files are unaffected. See brain/knowledge/text-search-operations.md.
MSG
)"

# A file that looks like a secret. BSD-grep-safe (no \b/\w): word end is (non-word-char | end-of-line).
SECRET='(\.env([^A-Za-z0-9_]|$)|appsettings\.json|appsettings\.[A-Za-z0-9_]+\.json|secrets\.(json|yaml|yml)|credentials\.(json|yaml)|\.key([^A-Za-z0-9_]|$)|\.pem([^A-Za-z0-9_]|$)|\.pfx([^A-Za-z0-9_]|$)|\.p12([^A-Za-z0-9_]|$)|\.jks([^A-Za-z0-9_]|$)|\.keystore([^A-Za-z0-9_]|$)|master\.key|private_key|\.htpasswd)'
# A non-secret sample that matches a pattern above but is safe to target.
SAFE='\.(example|template|sample)([^A-Za-z0-9_]|$)'

classify() {
    local candidate="$1"
    [ -n "$candidate" ] || return
    printf '%s' "$candidate" | grep -qiE "$SECRET" || return
    printf '%s' "$candidate" | grep -qiE "$SAFE" && return
    echo secret
}

emit_deny() {
    MSG="$1" perl -MJSON::PP -e 'print encode_json({hookSpecificOutput=>{hookEventName=>"PreToolUse",permissionDecision=>"deny",permissionDecisionReason=>$ENV{MSG}}});' 2>/dev/null
}

# --- main ---
if [ "$1" = "--candidate" ]; then
    v="$(classify "$2")"
    printf '%s\n' "${v:-allow}"
    exit 0
fi

# Extract only the target fields per tool. Grep's `pattern` is a content regex, not a path, so it is
# excluded; Grep's `glob`/`path` do name targets.
candidate="$(perl -MJSON::PP -0777 -ne '
    my $d = eval { decode_json($_) }; exit unless $d;
    my $t = $d->{tool_name} // "";
    my $in = $d->{tool_input} // {};
    my @f;
    if    ($t eq "Glob") { @f = ($in->{pattern}, $in->{path}); }
    elsif ($t eq "Grep") { @f = ($in->{glob}, $in->{path}); }
    elsif ($t eq "Read") { @f = ($in->{file_path}); }
    print join(" ", grep { defined && length } @f);
' 2>/dev/null)"
[ -n "$candidate" ] || exit 0

[ "$(classify "$candidate")" = secret ] && emit_deny "$DENY_MSG"
exit 0
