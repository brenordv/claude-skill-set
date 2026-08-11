#requires -Version 5
# PreToolUse hook for the NATIVE Glob/Grep/Read tools: deny when the target of a file search, listing,
# or read is a secret-looking file (.env, appsettings.json, secrets.*, credentials.*, *.key/*.pem,
# master.key, .htpasswd, ...). Windows implementation; macOS/Linux use guard-file-targets.sh.
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
# Fails OPEN: any parse error or unexpected fault exits 0 so a legitimate call is never broken.
# See hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $payload = $raw | ConvertFrom-Json
    $tool = [string]$payload.tool_name
    $in = $payload.tool_input
} catch {
    exit 0
}

function Deny([string]$reason) {
    $out = [pscustomobject]@{
        hookSpecificOutput = [pscustomobject]@{
            hookEventName            = 'PreToolUse'
            permissionDecision       = 'deny'
            permissionDecisionReason = $reason
        }
    }
    $out | ConvertTo-Json -Depth 5 -Compress
    exit 0
}

$fields = switch ($tool) {
    'Glob' { @($in.pattern, $in.path) }
    'Grep' { @($in.glob, $in.path) }
    'Read' { @($in.file_path) }
    default { @() }
}
$candidate = ($fields | Where-Object { $_ }) -join ' '
if ([string]::IsNullOrWhiteSpace($candidate)) { exit 0 }

# A file that looks like a secret.
$secret = '\.env\b|appsettings\.json|appsettings\.\w+\.json|secrets\.(json|yaml|yml)|credentials\.(json|yaml)|\.key\b|\.pem\b|\.pfx\b|\.p12\b|\.jks\b|\.keystore\b|master\.key|private_key|\.htpasswd'
# A non-secret sample that matches a pattern above but is safe to target.
$safe = '\.(example|template|sample)\b'

$msg = @'
Blocked: this Glob/Grep/Read targets a secret-looking file (.env, appsettings.json, secrets.*, credentials.*, *.key, *.pem, *.pfx, *.p12, *.jks, *.keystore, master.key, private_key, .htpasswd). Seeking a secret file is off-limits, not only reading one: its existence and location are not yours to map, and opening it pulls secret material into context. If you need a non-secret sample, target its .example/.template/.sample instead. Legitimate reads of non-secret files are unaffected. See brain/knowledge/text-search-operations.md.
'@

if (($candidate -imatch $secret) -and ($candidate -notmatch $safe)) {
    Deny $msg
}

exit 0
