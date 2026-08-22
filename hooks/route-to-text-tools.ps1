#requires -Version 5
# PreToolUse hook for the Bash and PowerShell tools.
#
# Deny shell commands whose purpose is to read/search files on disk (route the agent to the
# text-search MCP) or to rewrite file content in place (route to the text-edit MCP). Everything
# else passes. The one nuance the repo rules call out: a read filter that only consumes ANOTHER
# command's piped output (e.g. `dotnet test | tail -20`) is output trimming, not file probing,
# and is allowed. Only a command LEADING a pipeline stage is treated as reading files.
#
# Any unexpected error fails OPEN (exit 0): a hook must never break a legitimate command.
# See hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $payload = $raw | ConvertFrom-Json
    $command = [string]$payload.tool_input.command
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

# The bare command word leading one pipeline stage: drop leading whitespace and grouping
# punctuation, benign prefixes (sudo/env/command/time/nice/nohup), and env-assignments
# (FOO=bar cmd), then take the first token and reduce a path or .exe to its bare name.
function Get-LeadWord([string]$stage) {
    $s = $stage.Trim()
    while ($s -match '^(sudo|env|command|time|nice|nohup)\s+') {
        $s = ($s -replace '^(sudo|env|command|time|nice|nohup)\s+', '').Trim()
    }
    $s = $s -replace '^[\(\{\!\s]+', ''
    while ($s -match '^[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+') {
        $s = ($s -replace '^[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+', '').Trim()
    }
    if ($s.Length -eq 0) { return '' }
    $token = ($s -split '\s+')[0]
    $token = $token.Trim('"').Trim("'")
    $token = $token -replace '.*[\\/]', ''
    $token = $token -replace '\.exe$', ''
    return $token.ToLowerInvariant()
}

# For a stage whose leading word is `git`, return @{ sub = <subcommand>; rest = <args> } by
# walking past git's global options (-C <path> and -c <kv> each consume the next token), or $null.
function Get-GitParts([string]$stage) {
    $s = $stage.Trim()
    while ($s -match '^(sudo|env|command|time|nice|nohup)\s+') {
        $s = ($s -replace '^(sudo|env|command|time|nice|nohup)\s+', '').Trim()
    }
    $s = $s -replace '^[\(\{\!\s]+', ''
    while ($s -match '^[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+') {
        $s = ($s -replace '^[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+', '').Trim()
    }
    $tokens = @($s -split '\s+')
    if ($tokens.Count -eq 0) { return $null }
    $first = (($tokens[0].Trim('"').Trim("'")) -replace '.*[\\/]', '' -replace '\.exe$', '').ToLowerInvariant()
    if ($first -ne 'git') { return $null }
    $idx = 1
    while ($idx -lt $tokens.Count -and $tokens[$idx] -like '-*') {
        if ($tokens[$idx] -eq '-C' -or $tokens[$idx] -eq '-c') { $idx += 2 } else { $idx += 1 }
    }
    if ($idx -ge $tokens.Count) { return $null }
    $sub = $tokens[$idx].ToLowerInvariant()
    $rest = ''
    if ($idx + 1 -lt $tokens.Count) { $rest = ($tokens[($idx + 1)..($tokens.Count - 1)] -join ' ') }
    return @{ sub = $sub; rest = $rest }
}

$searchMsg = @'
Blocked: this shell command reads or searches files on disk, which bypasses the .gitignore and secret guards (this is exactly what leaked a gitignored file before). Use the text-search MCP instead (blanket-approved, read-only, ignore- and secret-aware), scoped with cwd = the repo's absolute path:
  grep / rg            -> search_text
  cat / head / tail    -> read_lines
  find / ls -R / dir /s -> find_files
  file / encoding      -> inspect_files
  jq / JSON plucking   -> read_json
For paths the native Read / Grep / Glob tools reach, those are fine too. See brain/knowledge/text-search-operations.md.
Exempt (NOT blocked): piping a command's OWN output through grep/head/tail, e.g. `dotnet test | tail -20`. If that was the intent, re-run it in that shape.
'@

$editMsg = @'
Blocked: this rewrites file content through the shell, which is banned. For a pattern edit across files use the text-edit MCP: replace_text (dry_run: true first, then the real run gated with expected_match_count) or normalize_files, scoped with cwd = the repo's absolute path. For one hand-shaped edit use the native Edit tool; for a brand-new file use the native Write tool. See brain/knowledge/text-edit-operations.md.
'@

$gitMsg = @'
Blocked: read-only git inspection goes through the git-ops MCP, not the shell (a shell `git log` / `git grep` is exactly the case the rule targets). Use these with cwd = the repo's absolute path:
  git grep -> git_grep (fixedString:false for regex)    git log -> git_log
  git diff -> git_diff    git show -> git_show    git status -> git_status    git blame -> git_blame
  git ls-files -> git_ls_files    git branch -> git_branch_list    git reflog -> git_reflog
  git stash list/show -> git_stash_list / git_stash_show
Shell git stays fine for WRITES (commit, add, push, checkout, reset, merge, rebase, tag, fetch, pull). See brain/knowledge/git-readonly-operations.md.
'@

# --- In-place / content-write detection (any position) -> route to text-edit ---
if ($command -match '\bsed\b[^|;&]*\s-i') { Deny $editMsg }
if ($command -cmatch '\bperl\s+-[a-z]*i') { Deny $editMsg }
if ($command -match '\b(Set-Content|Add-Content|Out-File)\b') { Deny $editMsg }

# --- Interpreter one-liners that open a file -> search ---
# Matched against the whole command: the statement split below is quote-blind, so an embedded ';'
# would cut a -c/-e payload in two. -cmatch keeps the flag letters case-sensitive (python -E and
# node -C are not eval flags); the interpreter names alone are case-insensitive via (?i:...).
if ($command -cmatch '(^|[^A-Za-z0-9_.])(?i:python[0-9.]*|py|node)\s+([^|;&\r\n]*\s)?(-[A-Za-z]*[ce]|--eval)([^A-Za-z0-9]|$)' -and
    $command -match 'open[(]|read_text|readfile') { Deny $searchMsg }

# --- Recursive directory listings -> find_files ---
if ($command -cmatch '\bls\b[^|;&]*\s-[A-Za-z]*R') { Deny $searchMsg }          # ls -R (not ls -r)
if ($command -match '\bdir\b[^|;&]*\s/s\b') { Deny $searchMsg }                 # dir /s
if ($command -match '\b(Get-ChildItem|gci)\b[^|;&]*\s-r') { Deny $searchMsg }   # gci -r / -Recurse
if ($command -match '\bls\b[^|;&]*\s-recurse\b') { Deny $searchMsg }            # PS: ls (GCI alias) -Recurse

# --- Read/probe detection: the LEADING command of a pipeline stage reads files ---
# Statements are independent commands (&& || ; newline); only a '|' pipe grants the
# output-trimming exemption, so we split statements first, then pipeline stages.
$probeLeading = @(
    'grep','egrep','fgrep','rg','ripgrep','ag','ack',
    'cat','tac','head','tail',
    'find','fd','jq',
    'sed','awk','gawk',
    'select-string','sls','get-content','gc'
)

$statements = [regex]::Split($command, '(&&|\|\||;|\r?\n)')
foreach ($stmt in $statements) {
    if ($stmt -match '^\s*(&&|\|\||;)?\s*$') { continue }
    $stages = $stmt -split '\|'
    for ($i = 0; $i -lt $stages.Count; $i++) {
        if ($i -gt 0) { continue }   # downstream of a pipe = output trimming, allowed
        $lead = Get-LeadWord $stages[$i]
        if ([string]::IsNullOrEmpty($lead)) { continue }
        if ($probeLeading -contains $lead) {
            # cat/tac writing via redirect or heredoc is authoring, not probing.
            if (($lead -eq 'cat' -or $lead -eq 'tac') -and $stages[$i] -match '(>|>>|<<)') { continue }
            # find used to act on matches (-exec/-delete/-ok) is not a read.
            if ($lead -eq 'find' -and $stages[$i] -match '\s-(exec|execdir|delete|ok)\b') { continue }
            # jq under a null-input flag constructs JSON without reading files; any '<' redirect,
            # file-reading flag, or input-family filter word voids the carve-out.
            if ($lead -eq 'jq' -and
                $stages[$i] -cmatch '(^|\s)-[A-Za-z]*n[A-Za-z]*([^A-Za-z0-9]|$)|--null-input' -and
                $stages[$i] -notmatch '<' -and
                $stages[$i] -cnotmatch '--(slurpfile|rawfile|from-file|argfile)|(^|\s)-[A-Za-z]*[fL]([^A-Za-z0-9]|$)|(^|[^A-Za-z0-9_-])(inputs?|import|include)([^A-Za-z0-9_-]|$)') { continue }
            Deny $searchMsg
        }
        elseif ($lead -eq 'git') {
            # Read-only git inspection -> git-ops MCP. Shell git for WRITES stays allowed, so bias
            # toward allow: only redirect subcommands that are read-only in the form given.
            $gp = Get-GitParts $stages[$i]
            if ($gp) {
                $sub = $gp.sub; $rest = $gp.rest; $redirect = $false
                if (@('grep', 'log', 'status', 'diff', 'show', 'blame', 'ls-files') -contains $sub) { $redirect = $true }
                elseif ($sub -eq 'reflog') { if ($rest -notmatch '^\s*(expire|delete)\b') { $redirect = $true } }
                elseif ($sub -eq 'stash') { if ($rest -match '^\s*(list|show)\b') { $redirect = $true } }
                elseif ($sub -eq 'branch') {
                    # list form only: no branch name and no create/delete/move/force flag.
                    $hasPositional = $false
                    foreach ($tk in @($rest -split '\s+')) { if ($tk -and ($tk -notlike '-*')) { $hasPositional = $true; break } }
                    $hasWriteFlag = $rest -match '(^|\s)(-d|-D|--delete|-m|-M|--move|-c|-C|--copy|--set-upstream-to|--unset-upstream|--edit-description|-f|--force|-u|--set-upstream|--track|--no-track)(\s|=|$)'
                    if (-not $hasPositional -and -not $hasWriteFlag) { $redirect = $true }
                }
                if ($redirect) { Deny $gitMsg }
            }
        }
    }
}

exit 0
