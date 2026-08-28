#requires -Version 5
# Windows behavior harness for the five hook pairs in hooks/: runs each hooks/*.ps1 against the
# shared case table tools/hook-cases.tsv, the same table tools/test-hooks.sh runs the .sh hooks
# against, so a behavior divergence between the two implementations shows up as one platform's CI
# job failing while the other passes. Written for Windows PowerShell 5.1, the interpreter the
# install snippets in hooks/README.md register.
#
# Layers: the bash harness owns syntax, pattern-guard, and threshold-sync (plain text checks that
# run on every platform); this harness owns Windows behavior only. Assertions mirror
# test-hooks.sh: deny rows expect exit 0 and a stdout JSON object whose
# hookSpecificOutput.permissionDecision is 'deny' with the row's signature inside the reason;
# allow/silent rows expect exit 0 and empty stdout/stderr; warn rows expect exit 2, empty stdout,
# and the signature on stderr. Signatures are matched as ordinal literals, never as patterns.
# Payloads stay inert: they reach a hook only as bytes on stdin (a BOM-less temp file redirected
# via Start-Process), never through Invoke-Expression or a shell-parsed command line.
#
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\test-hooks.ps1
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\test-hooks.ps1 -HooksDir "$env:USERPROFILE\.claude\hooks"
#
# With -HooksDir, the hooks in that directory are graded against this checkout's case table, so an
# installed copy that drifted behind repo policy fails.
# Exit codes: 0 all cases green, 1 case failures, 2 harness/setup error.

param(
    [string]$HooksDir = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail-Setup([string]$message) {
    [Console]::Error.WriteLine("test-hooks: $message")
    exit 2
}

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir
$hooksDirGiven = -not [string]::IsNullOrEmpty($HooksDir)
if (-not $hooksDirGiven) { $HooksDir = Join-Path $repoRoot 'hooks' }
if (-not (Test-Path -LiteralPath $HooksDir -PathType Container)) { Fail-Setup "hooks dir not found: $HooksDir" }
if ($null -eq (Get-Command powershell.exe -ErrorAction SilentlyContinue)) { Fail-Setup 'powershell.exe not found on PATH' }

$script:failCount = 0
function Report([string]$line) {
    $script:failCount++
    [Console]::Out.WriteLine($line)
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$newlineChars = [char[]]"`r`n"

# warn-file-size reads the file named in the payload, so its rows need real fixtures. This fixture
# set is declared here and again in test-hooks.sh on purpose: six stable lines whose drift fails
# loudly as wrong verdicts beat a fixture-description format with parsers in two languages.
$fixDir = Join-Path ([System.IO.Path]::GetTempPath()) ('test-hooks-fix-' + [Guid]::NewGuid().ToString('N'))

function New-Fixture([int]$count, [string]$path) {
    $builder = New-Object System.Text.StringBuilder
    for ($n = 1; $n -le $count; $n++) { [void]$builder.Append("x = $n`n") }
    [System.IO.File]::WriteAllText($path, $builder.ToString(), $utf8NoBom)
    $got = ([regex]::Matches([System.IO.File]::ReadAllText($path), "`n")).Count
    if ($got -ne $count) { Fail-Setup "fixture ${path}: expected $count lines, found $got" }
}

try {
    [void](New-Item -ItemType Directory -Path (Join-Path $fixDir 'cfg.sample') -Force)
    foreach ($p in @($HooksDir, $fixDir, $repoRoot)) {
        if ($p.Contains('"')) { Fail-Setup "path contains a double quote, refusing: $p" }
    }
    New-Fixture 801 (Join-Path $fixDir 'big.py')
    New-Fixture 5 (Join-Path $fixDir 'small.py')
    New-Fixture 750 (Join-Path $fixDir 'big.rs')
    New-Fixture 900 (Join-Path $fixDir 'notes.md')
    New-Fixture 801 (Join-Path $fixDir 'cfg.sample\secrets.py')
    New-Fixture 801 (Join-Path $fixDir 'secrets.example.py')
    $fixFwd = $fixDir.Replace('\', '/')
    $repoFwd = $repoRoot.Replace('\', '/')

    # Load the table. Validation is strict and mirrors test-hooks.sh: exactly five fields, none
    # empty, a known verdict, '-' only on allow/silent rows (normalized to empty), a shape-checked
    # hook name, no unsubstituted placeholder, and a payload that still parses as JSON after
    # substitution.
    $casesFile = Join-Path $scriptDir 'hook-cases.tsv'
    if (-not (Test-Path -LiteralPath $casesFile)) { Fail-Setup "case table not found: $casesFile" }
    $cases = New-Object System.Collections.ArrayList
    $declaredHeader = ''
    $rowNum = 0
    foreach ($rawLine in [System.IO.File]::ReadAllLines($casesFile)) {
        $rowNum++
        $line = $rawLine.TrimEnd([char]"`r")
        if ($line -eq '') { continue }
        if ($line.StartsWith('# cases: ')) { $declaredHeader = $line.Substring('# cases: '.Length); continue }
        if ($line.StartsWith('#')) { continue }
        $fields = $line.Split("`t")
        if ($fields.Count -ne 5) { Fail-Setup "hook-cases.tsv row ${rowNum}: expected 5 fields, found $($fields.Count)" }
        foreach ($f in $fields) {
            if ($f -eq '') { Fail-Setup "hook-cases.tsv row ${rowNum}: empty field" }
        }
        $hookName = $fields[0]
        $verdict = $fields[3]
        $sig = $fields[4]
        if ($hookName -cnotmatch '^[a-z0-9-]+$') { Fail-Setup "hook-cases.tsv row ${rowNum}: hook name must be [a-z0-9-] only: `"$hookName`"" }
        if ($verdict -eq 'deny' -or $verdict -eq 'warn') {
            if ($sig -eq '-') { Fail-Setup "hook-cases.tsv row ${rowNum}: deny/warn rows need a real signature, got '-'" }
        } elseif ($verdict -eq 'allow' -or $verdict -eq 'silent') {
            if ($sig -ne '-') { Fail-Setup "hook-cases.tsv row ${rowNum}: allow/silent rows take '-' as the signature" }
            $sig = ''
        } else {
            Fail-Setup "hook-cases.tsv row ${rowNum}: unknown verdict `"$verdict`""
        }
        $inputJson = $fields[2].Replace('@WF_FIXDIR@', $fixFwd).Replace('@REPO_ROOT@', $repoFwd)
        if ($inputJson -cmatch '@[A-Z_]+@') { Fail-Setup "hook-cases.tsv row ${rowNum}: unsubstituted placeholder in payload" }
        try { $null = ConvertFrom-Json -InputObject $inputJson } catch {
            Fail-Setup "hook-cases.tsv row ${rowNum}: tool_input is not valid JSON after substitution"
        }
        [void]$cases.Add(@{
            Row = $rowNum; Hook = $hookName; Tool = $fields[1]
            Input = $inputJson; Expect = $verdict; Sig = $sig
        })
    }
    if ($declaredHeader -eq '') { Fail-Setup 'hook-cases.tsv has no "# cases: N" header' }
    if ($declaredHeader -cnotmatch '^[0-9]+$') { Fail-Setup "hook-cases.tsv `"# cases`" header is not a number: $declaredHeader" }
    if ($cases.Count -ne [int]$declaredHeader) { Fail-Setup "hook-cases.tsv declares $declaredHeader cases but $($cases.Count) rows parsed" }

    $inFile = Join-Path $fixDir 'stdin.txt'
    $outFile = Join-Path $fixDir 'stdout.txt'
    $errFile = Join-Path $fixDir 'stderr.txt'
    $dispBase = if ($hooksDirGiven) { $HooksDir } else { 'hooks' }
    $executed = 0

    foreach ($case in $cases) {
        $scriptName = $case['Hook'] + '.ps1'
        $scriptPath = Join-Path $HooksDir $scriptName
        $disp = "$dispBase/$scriptName"
        $name = "row $($case['Row']): $($case['Tool']) $($case['Input'])"
        if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
            Report "${disp}: [behavior] case `"$name`": script not found at $scriptPath"
            continue
        }
        $rc = -1
        $out = ''
        $err = ''
        try {
            $payload = '{"tool_name":"' + $case['Tool'] + '","tool_input":' + $case['Input'] + '}'
            [System.IO.File]::WriteAllText($inFile, $payload, $utf8NoBom)
            [System.IO.File]::WriteAllText($outFile, '', $utf8NoBom)
            [System.IO.File]::WriteAllText($errFile, '', $utf8NoBom)
            $argList = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $scriptPath))
            $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList `
                -RedirectStandardInput $inFile -RedirectStandardOutput $outFile -RedirectStandardError $errFile `
                -NoNewWindow -PassThru -Wait
            $rc = $proc.ExitCode
            $executed++
            $out = [System.IO.File]::ReadAllText($outFile)
            $err = [System.IO.File]::ReadAllText($errFile)
        } catch {
            Report "${disp}: [behavior] case `"$name`": harness fault: $($_.Exception.Message)"
            continue
        }
        $outTrim = $out.TrimEnd($newlineChars)
        $outOneline = ($out -replace "[`r`n]+", ' ')
        $errOneline = ($err -replace "[`r`n]+", ' ')
        $problem = ''
        if ($case['Expect'] -eq 'allow' -or $case['Expect'] -eq 'silent') {
            if ($outTrim -ne '') { $problem = "expected $($case['Expect']), expected empty stdout, got output" }
            elseif ($rc -ne 0) { $problem = "expected $($case['Expect']), expected exit 0, got $rc" }
            elseif ($err.Length -gt 0) { $problem = "expected $($case['Expect']), expected empty stderr, got stderr output" }
        } elseif ($case['Expect'] -eq 'warn') {
            if ($rc -ne 2) { $problem = "expected exit 2, got $rc" }
            elseif ($outTrim -ne '') { $problem = 'expected empty stdout, got output' }
            elseif ($err.IndexOf($case['Sig'], [StringComparison]::Ordinal) -lt 0) { $problem = 'expected stderr to contain "' + $case['Sig'] + '"' }
        } else {
            # deny: any parse or member-access throw below means the hook's stdout was not the
            # expected JSON; that is a case failure, never a harness abort.
            $decision = ''
            $reason = ''
            try {
                $json = ConvertFrom-Json -InputObject $out
                $decision = [string]$json.hookSpecificOutput.permissionDecision
                $reason = [string]$json.hookSpecificOutput.permissionDecisionReason
            } catch {
                $decision = ''
                $reason = ''
            }
            if ($rc -ne 0) { $problem = "expected exit 0, got $rc" }
            elseif (-not ($decision -ceq 'deny')) {
                $shown = if ($decision -eq '') { '<none>' } else { $decision }
                $problem = 'expected permissionDecision=deny, got "' + $shown + '"'
            }
            elseif ($reason.IndexOf($case['Sig'], [StringComparison]::Ordinal) -lt 0) {
                $problem = 'expected reason to contain "' + $case['Sig'] + '", got "' + ($reason -replace "[`r`n]+", ' ') + '"'
            }
        }
        if ($problem -ne '') {
            Report "${disp}: [behavior] case `"$name`": $problem"
            [Console]::Out.WriteLine("    stdout: $outOneline")
            [Console]::Out.WriteLine("    stderr: $errOneline")
            [Console]::Out.WriteLine("    exit:   $rc")
        }
    }

    if ($executed -eq 0) { Fail-Setup "no behavior cases executed (table has $($cases.Count) rows)" }
    if ($executed -ne $cases.Count) {
        Report "test-hooks: [table] executed $executed of $($cases.Count) declared rows"
    }
    [Console]::Out.WriteLine("test-hooks: $executed cases, $($script:failCount) failed")
    if ($script:failCount -gt 0) { exit 1 }
    exit 0
} finally {
    if (Test-Path -LiteralPath $fixDir) {
        Remove-Item -LiteralPath $fixDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
