#requires -Version 5
# PreToolUse hook for the Bash and PowerShell tools: block VCS state changes the agent must never
# make. Two families: git writes the user owns (commit, add, stash except list/show), and every
# `gh stack` subcommand other than `view` (stack creation/mutation is the user's responsibility).
# Windows implementation; macOS/Linux use block-vcs-writes.sh.
#
# Unlike route-to-text-tools, which routes read-only git to the git-ops MCP and deliberately allows
# all git writes, this hook encodes a policy choice: the user manages git, the agent never stages,
# commits, or stashes. Don't install it if you want the agent making commits. Other git writes
# (push, checkout, merge, ...) are untouched; those happen on explicit request and still pass the
# permission prompt.
#
# Fails OPEN: any parse error or unexpected fault exits 0 so a legitimate command is never broken.
# See hooks/README.md for install and tuning.

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

$gitMsg = @'
Blocked: this command runs a git write the user owns (commit, add, or stash). Standing rule of this skill set: never stage, never commit, never stash; leave the working tree exactly as your file edits made it and let the user drive git. Read-only inspection goes through the git-ops MCP. See brain/knowledge/coding-general.md, Version Control Hygiene.
'@

$stackMsg = @'
Blocked: every gh stack subcommand except 'view' creates, restructures, or submits PR stacks, and stack management is the user's responsibility. The only permitted call is 'gh stack view' (stack detection). See brain/knowledge/github-pr-stacks.md, Hard Rules.
'@

# git global options that consume a following value token.
$gitValueOpts = @('-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path')

# Split into statements and pipeline stages; a write anywhere in the command is a write.
$fragments = $command -split '(&&|\|\||;|\||\r?\n)'
foreach ($frag in $fragments) {
    $f = $frag.Trim()
    if (-not $f) { continue }
    $tokens = @($f -split '\s+' | Where-Object { $_ })
    if ($tokens.Count -eq 0) { continue }
    $lead = ($tokens[0] -replace '^.*[\\/]', '') -replace '\.exe$', ''

    if ($lead -ieq 'git') {
        $i = 1
        while ($i -lt $tokens.Count) {
            if ($tokens[$i] -in $gitValueOpts) { $i += 2; continue }
            if ($tokens[$i] -like '-*') { $i += 1; continue }
            break
        }
        if ($i -lt $tokens.Count) {
            $sub = $tokens[$i].ToLowerInvariant()
            if ($sub -eq 'commit' -or $sub -eq 'add') { Deny $gitMsg }
            if ($sub -eq 'stash') {
                $next = ''
                if ($i + 1 -lt $tokens.Count) { $next = $tokens[$i + 1].ToLowerInvariant() }
                if ($next -ne 'list' -and $next -ne 'show') { Deny $gitMsg }
            }
        }
    }
    elseif ($lead -ieq 'gh') {
        $i = 1
        while ($i -lt $tokens.Count -and $tokens[$i] -like '-*') { $i += 1 }
        if ($i -lt $tokens.Count -and $tokens[$i] -ieq 'stack') {
            $j = $i + 1
            while ($j -lt $tokens.Count -and $tokens[$j] -like '-*') { $j += 1 }
            if ($j -lt $tokens.Count -and $tokens[$j].ToLowerInvariant() -ne 'view') { Deny $stackMsg }
        }
    }
}

exit 0
