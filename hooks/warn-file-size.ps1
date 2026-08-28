#requires -Version 5
# PostToolUse hook for the Write and Edit tools: warn once when a NEWLY CREATED source file
# (.py/.cs/.rs) exceeds its language's "worth reviewing" line threshold (coding-general.md section 3).
# Windows implementation; macOS/Linux use warn-file-size.sh. Silent for any file tracked at HEAD
# (checked with git ls-files), so it never nags edits to pre-existing files. This is the only
# content-reading hook: it opens the written file to count lines, under a byte cap, and echoes NO
# file content, only the count.
#
# PostToolUse cannot block; the tool already ran. A warning is exit 2 with a short message on stderr,
# which Claude Code surfaces to the model. Fails OPEN: any parse error, missing tool, unreadable file,
# or unexpected fault exits 0 and warns nothing.
# See hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Warn thresholds: the start of the "worth reviewing" tier per coding-general.md section 3. Keep in
# sync with SIZE_WARN_THRESHOLD in each skill's scripts/*_quality_gate.py.
$warn = @{ '.py' = 800; '.cs' = 700; '.rs' = 700 }
$lang = @{ '.py' = 'Python'; '.cs' = 'C#'; '.rs' = 'Rust' }
# Stop reading past this many bytes: a source file larger than this is over any threshold anyway.
$byteCap = 2000000
# Secret-looking basenames: never open one, even with a gated extension (secrets.py, credentials.py).
$secret = '(^|[\\/])secrets\.|(^|[\\/])credentials\.|(^|[\\/])\.env|(^|[\\/])private_key|(^|[\\/])master\.key'
# The .example/.template/.sample sample forms are never secret. Anchored to the final path segment so
# a parent directory named like a sample form cannot exempt a secret basename.
$safe = '\.(example|template|sample)[^\\/]*$'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $path = [string]([string]($raw | ConvertFrom-Json).tool_input.file_path)
    if ([string]::IsNullOrWhiteSpace($path)) { exit 0 }
} catch {
    exit 0
}

try {
    $ext = [System.IO.Path]::GetExtension($path).ToLowerInvariant()
    if (-not $warn.ContainsKey($ext)) { exit 0 }
    $threshold = $warn[$ext]

    if (($path -imatch $secret) -and ($path -notmatch $safe)) { exit 0 }

    $item = Get-Item -LiteralPath $path -ErrorAction Stop
    if ($item.PSIsContainer) { exit 0 }
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { exit 0 }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { exit 0 }
    $dir = [System.IO.Path]::GetDirectoryName($path)
    if ([string]::IsNullOrEmpty($dir)) { $dir = '.' }
    # git writes to stderr when the target is not in a repo; under $ErrorActionPreference='Stop'
    # Windows PowerShell 5.1 turns that into a terminating error, so relax it around the native call
    # and read the exit code instead.
    $tracked = $false
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & git -C $dir ls-files --error-unmatch -- $path 2>&1 | Out-Null
        $tracked = ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = 'Stop'
    }
    if ($tracked) { exit 0 }

    $stream = [System.IO.File]::OpenRead($path)
    try {
        $bufSize = [int][Math]::Min([int64]$byteCap, $stream.Length)
        $buffer = New-Object byte[] $bufSize
        $read = $stream.Read($buffer, 0, $buffer.Length)
    } finally {
        $stream.Close()
    }
    $count = 0
    for ($i = 0; $i -lt $read; $i++) {
        if ($buffer[$i] -eq 10) { $count++ }
    }
    if (($read -gt 0) -and ($buffer[$read - 1] -ne 10)) { $count++ }

    if ($count -lt $threshold) { exit 0 }

    [Console]::Error.WriteLine("[warn-file-size] New $($lang[$ext]) file: $count lines, at or over the $threshold-line ""worth reviewing"" tier.")
    [Console]::Error.WriteLine('[warn-file-size] Split new code into a new cohesive module; never mass-refactor an existing file for size (coding-general.md section 3).')
    if ($ext -eq '.rs') {
        [Console]::Error.WriteLine('[warn-file-size] The new-code size gate subtracts the trailing #[cfg(test)] module, so the effective production count may be below this raw count.')
    }
    exit 2
} catch {
    exit 0
}
