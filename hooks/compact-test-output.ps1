#requires -Version 5
# PostToolUse hook for the Bash and PowerShell tools: compact noisy test-runner output before the
# model reads it. Windows implementation; macOS/Linux use compact-test-output.sh, and the two carry
# identical behavior. A passing run collapses to its summary line(s); a run whose output carries
# failure indicators keeps every unrecognized line verbatim and drops only positively identified
# noise (per-test pass lines, restore/build chatter). The replacement is emitted as
# hookSpecificOutput.updatedToolOutput, an object mirroring the tool_response shape with only
# stdout/stderr rewritten; Claude Code validates that shape and falls back to the original output
# on any mismatch.
#
# PostToolUse fires only for commands that exited 0; a nonzero exit routes to PostToolUseFailure,
# which cannot rewrite output, so plain failing runs pass through untouched by design.
#
# Fails OPEN: any parse error, unexpected tool_response shape, regex timeout, or unexpected fault
# exits 0 and emits nothing, so the model sees the original output. Stdin is decoded and stdout
# encoded as BOM-less UTF-8 explicitly: this hook re-emits payload text, and the 5.1 console code
# page would mojibake non-ASCII on the plain streams.
# See hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Tunables; keep in sync with compact-test-output.sh. The replacement is never larger than the
# original (a subset of its lines plus one header line), so Claude Code's own Bash output window
# is the only size limit in play and nothing here caps the output.
# minChars: below this many output characters nothing is rewritten (not worth a rewrite).
# byteCap:  stdin payloads longer than this many characters pass through unparsed (the .sh twin
#           counts bytes; the two agree on ASCII output).
$minChars = 1500
$byteCap = 2000000

# Patterns compile with a match timeout so a pathological line degrades to in-hook fail-open
# instead of burning the outer hook timeout. All matching is case-sensitive for parity with the
# perl twin; .NET regexes are case-sensitive by default, and nothing below uses -match/-imatch.
$rxTimeout = [TimeSpan]::FromSeconds(1)
function New-Rx([string]$pattern) {
    New-Object System.Text.RegularExpressions.Regex(
        $pattern, [System.Text.RegularExpressions.RegexOptions]::None, $rxTimeout)
}

# Non-ASCII glyphs the jest patterns need, spelled as code points: 5.1 reads a BOM-less UTF-8
# script as ANSI, so literals would mojibake.
$ckCheck = [string][char]0x2713   # check mark
$ckRoot = [string][char]0x221A    # square root, the Windows-console check variant
$ckCross = [string][char]0x2715   # multiplication x
$ckTimes = [string][char]0x00D7   # multiplication sign
$ckBullet = [string][char]0x25CF  # black circle, jest failure block marker
$ckPointer = [string][char]0x276F # heavy right-pointing angle, vitest failed-file marker

# Runner table; keep in sync with @RUNNERS in compact-test-output.sh. Shapes are empirical (pinned
# by tools/hook-cases.tsv): a drifted pattern degrades to pass-through, never to dropped errors.
#   Match: the statement that invokes the runner.   SPos/SNeg: a line proving a zero-failure run.
#   Keep:  summary lines retained by a collapse.    Noise: lines dropped by noise-drop mode.
#   Fail:  failure indicators; any hit blocks a collapse (the lines themselves are always kept).
$runners = @(
    @{
        Key   = 'dotnet test'
        Match = New-Rx '^dotnet[ \t]+test\b'
        SPos  = New-Rx '^Passed![ \t]+-[ \t]+Failed:[ \t]+0,|^Test summary: total: ?\d+, failed: ?0\b'
        SNeg  = $null
        Keep  = New-Rx '^Passed!|^Test summary:'
        Noise = New-Rx ('^[ \t]+Passed[ \t]|^[ \t]*Determining projects to restore|^[ \t]+Restored[ \t]|^.*[ \t]->[ \t].*\.(?:dll|exe)[ \t]*$|^Test run for[ \t]|^Microsoft \(R\) Test Execution Command Line Tool|^Copyright \(c\) Microsoft Corporation|^Starting test execution, please wait|^A total of \d+ test files? matched|^[ \t]*\[xUnit\.net [0-9:.]+\][ \t]+(?:Discovering|Discovered|Starting|Finished):')
        Fail  = New-Rx ('^[ \t]+Failed[ \t]|^Failed!|^[ \t]+Error Message:|^[ \t]+Stack Trace:|(?:^|: )(?:error|warning) [A-Za-z0-9]+:|^Test summary:.*\bfailed: ?[1-9]')
    }
    @{
        Key   = 'pytest'
        Match = New-Rx '^(?:pytest|py\.test)\b|^python[0-9.]*[ \t]+-m[ \t]+pytest\b'
        SPos  = New-Rx '^=+ \d+ passed\b[^\n]* =+$|^\d+ passed\b[^\n]*$'
        SNeg  = New-Rx '\bfailed\b|\berrors?\b'
        Keep  = New-Rx '^=+ \d+ passed\b[^\n]* =+$|^\d+ passed\b[^\n]*$'
        Noise = New-Rx ('^\S+::[^\n]* PASSED(?: +\[ *\d+%\])?$|^[.sx]+(?: +\[ *\d+%\])?$|^platform \S+ -- Python|^rootdir: |^plugins: |^cachedir: |^configfile: |^collected \d+ items?\b')
        Fail  = New-Rx '\bFAILED\b|\bERRORS?\b|^=+ (?:FAILURES|ERRORS) =+$'
    }
    @{
        Key   = 'cargo test'
        Match = New-Rx '^cargo[ \t]+(?:test\b|nextest[ \t]+run\b)'
        SPos  = New-Rx '^test result: ok\. \d+ passed; 0 failed;'
        SNeg  = $null
        Keep  = New-Rx '^test result: '
        Noise = New-Rx ('^test \S+ \.\.\. ok$|^[ \t]*(?:Compiling|Finished|Running|Doc-tests)\b|^running \d+ tests?$')
        Fail  = New-Rx ('^test \S+ \.\.\. FAILED$|^---- \S+ stdout ----$|panicked at|^test result: FAILED|^error(?:\[E[0-9]+\])?:|^warning:')
    }
    @{
        Key   = 'jest/vitest'
        Match = New-Rx '^npx[ \t]+(?:jest|vitest)\b|^(?:jest|vitest)\b|^npm[ \t]+(?:test\b|run[ \t]+test)|^yarn[ \t]+test\b|^pnpm[ \t]+(?:run[ \t]+)?test\b'
        SPos  = New-Rx '^Tests:[ \t]+\d+ passed, \d+ total[ \t]*$|^[ \t]*Tests[ \t]+\d+ passed(?: \| \d+ skipped)?(?: \| \d+ todo)?[ \t]+\(\d+\)[ \t]*$'
        SNeg  = New-Rx '\bfailed\b'
        Keep  = New-Rx '^(?:Test Suites|Tests|Snapshots|Time):|^Ran all test suites|^[ \t]*(?:Test Files|Tests|Start at|Duration)[ \t]+\S'
        Noise = New-Rx ('^PASS [^\n]*$|^[ \t]*[' + $ckCheck + $ckRoot + '][ \t]|^[ \t]*RUN[ \t]+v\d+\.\d+')
        Fail  = New-Rx ('^[ \t]*FAIL[ \t]|[' + $ckCross + $ckTimes + $ckPointer + ']|^[ \t]*' + $ckBullet + ' |^Tests:[^\n]*\bfailed\b|^[ \t]*(?:Test Files|Tests)[ \t]+\d+ failed\b|^[ \t]*Errors[ \t]+\d+ error')
    }
)

function Get-Prop($obj, [string]$name) {
    if ($null -eq $obj) { return $null }
    if (-not ($obj -is [System.Management.Automation.PSCustomObject])) { return $null }
    $p = $obj.PSObject.Properties[$name]
    if ($null -eq $p) { return $null }
    return $p.Value
}

function Split-TextLines([string]$text) {
    if ($text -eq '') { return @() }
    return [regex]::Split($text, "\r?\n")
}

# Keep only the lines a predicate accepts; trailing CRs are already consumed by the split, so a
# CRLF input yields the same LF replacement as the .sh twin.
function Invoke-Sieve([string]$text, [System.Text.RegularExpressions.Regex]$rx, [bool]$keepMatching) {
    $kept = New-Object System.Collections.Generic.List[string]
    $dropped = 0
    foreach ($line in (Split-TextLines $text)) {
        $hit = $rx.IsMatch($line)
        if ($hit -eq $keepMatching) { [void]$kept.Add($line) } else { $dropped++ }
    }
    return @(($kept -join "`n"), $dropped)
}

function Measure-TextLines([string]$text) {
    if ($text -eq '') { return 0 }
    return @(Split-TextLines $text).Count
}

try {
    $reader = New-Object System.IO.StreamReader(
        [Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
    $raw = $reader.ReadToEnd()
    if ([string]::IsNullOrEmpty($raw)) { exit 0 }
    if ($raw.Length -gt $byteCap) { exit 0 }

    $d = ConvertFrom-Json -InputObject $raw
    $cmd = Get-Prop (Get-Prop $d 'tool_input') 'command'
    if (-not ($cmd -is [string]) -or $cmd -eq '') { exit 0 }
    $tr = Get-Prop $d 'tool_response'
    if ($null -eq $tr) { exit 0 }
    if ((Get-Prop $tr 'interrupted') -eq $true) { exit 0 }
    $outText = Get-Prop $tr 'stdout'
    if (-not ($outText -is [string])) { exit 0 }
    $errText = Get-Prop $tr 'stderr'
    if (-not ($errText -is [string])) { $errText = '' }

    if ($cmd.Contains('#keep-output')) { exit 0 }

    # Classify the command: the runner it invokes, and whether other significant statements ride
    # along. Statements split on && || ; and newlines; a single | surviving inside the runner's own
    # statement means its output is already being piped (trimmed) and the hook stays out of it.
    $runner = $null
    $runnerStmt = ''
    $extra = $false
    foreach ($stmt in [regex]::Split($cmd, '&&|\|\||;|\r?\n')) {
        $t = $stmt -creplace '^[ \t]+', ''
        while ($t -cmatch '^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]') {
            $t = $t -creplace '^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]+', ''
        }
        if ($t -eq '' -or $t -cmatch '^cd\b' -or $t -cmatch '^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*$') { continue }
        $m = $null
        foreach ($r in $runners) { if ($r['Match'].IsMatch($t)) { $m = $r; break } }
        if (($null -ne $m) -and ($null -eq $runner)) { $runner = $m; $runnerStmt = $t; continue }
        $extra = $true
    }
    if ($null -eq $runner) { exit 0 }
    if ($runnerStmt.Contains('|')) { exit 0 }
    if (($outText.Length + $errText.Length) -lt $minChars) { exit 0 }

    $hasFail = $false
    foreach ($text in @($outText, $errText)) {
        foreach ($line in (Split-TextLines $text)) {
            if ($runner['Fail'].IsMatch($line)) { $hasFail = $true; break }
        }
        if ($hasFail) { break }
    }
    $hasSuccess = $false
    if (-not $hasFail) {
        foreach ($text in @($outText, $errText)) {
            foreach ($line in (Split-TextLines $text)) {
                if (-not $runner['SPos'].IsMatch($line)) { continue }
                if (($null -ne $runner['SNeg']) -and $runner['SNeg'].IsMatch($line)) { continue }
                $hasSuccess = $true; break
            }
            if ($hasSuccess) { break }
        }
    }

    $total = (Measure-TextLines $outText) + (Measure-TextLines $errText)
    if ((-not $extra) -and $hasSuccess) {
        $so = Invoke-Sieve $outText $runner['Keep'] $true
        $se = Invoke-Sieve $errText $runner['Keep'] $true
        $newOut = [string]$so[0]
        $newErr = [string]$se[0]
        $kept = (Measure-TextLines $newOut) + (Measure-TextLines $newErr)
        $header = '[compact-test-output] {0} passed; {1} of {2} output lines elided (append #keep-output to a re-run for the full output).' -f $runner['Key'], ($total - $kept), $total
    } else {
        $so = Invoke-Sieve $outText $runner['Noise'] $false
        $se = Invoke-Sieve $errText $runner['Noise'] $false
        $newOut = [string]$so[0]
        $newErr = [string]$se[0]
        $dropped = [int]$so[1] + [int]$se[1]
        if ($dropped -eq 0) { exit 0 }
        $header = '[compact-test-output] {0}: dropped {1} of {2} known-noise lines, everything unrecognized kept verbatim (append #keep-output to a re-run for the full output).' -f $runner['Key'], $dropped, $total
    }

    if ($newOut -eq '') { $newOut = $header } else { $newOut = $header + "`n" + $newOut }

    $copy = [ordered]@{}
    foreach ($p in $tr.PSObject.Properties) { $copy[$p.Name] = $p.Value }
    $copy['stdout'] = $newOut
    $copy['stderr'] = $newErr
    $payload = @{ hookSpecificOutput = @{ hookEventName = 'PostToolUse'; updatedToolOutput = $copy } }
    $json = ConvertTo-Json -InputObject $payload -Depth 6 -Compress

    $writer = New-Object System.IO.StreamWriter(
        [Console]::OpenStandardOutput(), (New-Object System.Text.UTF8Encoding($false)))
    $writer.Write($json)
    $writer.Flush()
    exit 0
} catch {
    exit 0
}
