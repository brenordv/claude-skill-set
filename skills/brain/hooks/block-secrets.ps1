#requires -Version 5
# PreToolUse hook for the Bash and PowerShell tools: block commands that READ or COPY a file that
# looks like a secret (.env, appsettings.json, secrets.*, credentials.*, *.key/*.pem, master.key,
# .htpasswd, ...). Windows implementation; macOS/Linux use block-secrets.sh. Companion to
# route-to-text-tools; the two hooks are independent and both run on PreToolUse.
#
# Fails OPEN: any parse error or unexpected fault exits 0 so a legitimate command is never broken.
# See skills/brain/hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $command = [string]($raw | ConvertFrom-Json).tool_input.command
    if ([string]::IsNullOrWhiteSpace($command)) { exit 0 }
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

# A file that looks like a secret.
$secret = '\.env\b|appsettings\.json|appsettings\.\w+\.json|secrets\.(json|yaml|yml)|credentials\.(json|yaml)|\.key\b|\.pem\b|\.pfx\b|\.p12\b|\.jks\b|\.keystore\b|master\.key|private_key|\.htpasswd'
# A non-secret sample that matches a pattern above but is safe to read.
$safe = '\.(example|template|sample)\b'
# The command reads file content, copies it, redirects it, or exfiltrates it.
$readExfil = '(cat|head|tail|less|more|type|Get-Content|bat|sed|awk|source)\s|(^|\s)\.\s|cp\s|copy\s|>|curl.*-d.*@|xargs'

$msg = @'
Blocked: this command reads or copies a file matching a secret-file pattern (.env, appsettings.json, secrets.*, credentials.*, *.key, *.pem, *.pfx, *.p12, *.jks, *.keystore, master.key, private_key, .htpasswd), which would pull secret material into context. If the target is genuinely non-secret, read it another way or point at its .example/.template/.sample. For legitimate file reads prefer the text-search MCP, which withholds secret-shaped content on its own. See brain/knowledge/text-search-operations.md.
'@

if (($command -imatch $secret) -and ($command -notmatch $safe) -and ($command -imatch $readExfil)) {
    Deny $msg
}

exit 0
