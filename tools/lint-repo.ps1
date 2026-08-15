#requires -Version 5
# Repo lint: keeps the prose rulebase healthy. Why each check exists is documented in
# tools/README.md; the short version is that this repo's regression class is dead pointers and
# prose that violates its own style rules, and every check below has caught a real instance.
#
# Checks over every .md file (excluding .git):
#   [link]    relative markdown link targets resolve
#   [ref]     backticked, slash-containing *.md path references resolve (tried against the repo
#             root, skills/<path> for the brain/... convention, and the referencing file's folder;
#             bare filenames without a slash are skipped as unresolvable by convention)
#   [style]   no em-dash character (exemption: writing-style.md, which quotes it to ban it)
#   [privacy] no machine-identifying path shapes (Users/<name>, AppData/Local/Temp)
#
# Exit 0 = clean, 1 = findings. Windows implementation of lint-repo.sh; keep both in sync.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script:fail = $false

function Report([string]$msg) {
    Write-Output $msg
    $script:fail = $true
}

$emDash = [string][char]0x2014

$mdFiles = Get-ChildItem -Path $root -Recurse -Filter '*.md' -File |
    Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' }

foreach ($file in $mdFiles) {
    $dir = $file.DirectoryName
    $rel = $file.FullName.Substring($root.Length + 1) -replace '\\', '/'
    $isWritingStyle = $rel -eq 'skills/brain/knowledge/writing-style.md'
    $lines = @(Get-Content -Path $file.FullName -Encoding UTF8)

    $inFence = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        $n = $i + 1

        # Fenced code blocks are exempt from the link/ref checks: code samples (a regex like
        # `](Users|home)`) would otherwise parse as links. Style/privacy checks still apply.
        if ($line -match '^\s*```') { $inFence = -not $inFence }
        $proseLine = if ($inFence -or $line -match '^\s*```') { '' } else { $line }

        foreach ($m in [regex]::Matches($proseLine, '\]\(([^)]+)\)')) {
            $target = $m.Groups[1].Value
            if ($target -match '^(https?://|mailto:|#)') { continue }
            $t = ($target -split '#')[0]
            if (-not $t) { continue }
            if (-not (Test-Path (Join-Path $dir $t))) {
                Report "${rel}:${n}: [link] relative link target not found: $target"
            }
        }

        foreach ($m in [regex]::Matches($proseLine, '`([A-Za-z0-9._/-]+\.md)`')) {
            $p = $m.Groups[1].Value
            if ($p -notmatch '/') { continue }
            $ok = (Test-Path (Join-Path $root $p)) -or
                  (Test-Path (Join-Path $root (Join-Path 'skills' $p))) -or
                  (Test-Path (Join-Path $dir $p))
            if (-not $ok) { Report "${rel}:${n}: [ref] backticked path not found: $p" }
        }

        if (-not $isWritingStyle -and $line.Contains($emDash)) {
            Report "${rel}:${n}: [style] em-dash found"
        }

        if ($line -cmatch '[/\\]Users[/\\][A-Za-z0-9._-]+' -or $line -cmatch 'AppData[/\\]+Local[/\\]+Te?mp') {
            Report "${rel}:${n}: [privacy] machine-identifying path shape"
        }
    }
}

if ($script:fail) {
    Write-Output 'lint-repo: findings above'
    exit 1
}
Write-Output 'lint-repo: clean'
exit 0
