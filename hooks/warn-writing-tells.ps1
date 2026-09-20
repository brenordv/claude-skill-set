#requires -Version 5
# PostToolUse hook for the Write and Edit tools: warn when the text just written ADDS a hard-banned
# writing tell: an em-dash (U+2014) or a curly quote/apostrophe (U+2018, U+2019, U+201C, U+201D).
# See skills/brain/knowledge/writing-style.md, hard bans. Windows implementation; macOS/Linux use
# warn-writing-tells.sh. It scans only the payload the tool wrote (tool_input.content for Write,
# tool_input.new_string for Edit), never the file on disk, so tells already present in an edited
# file never nag. It reports counts only, never content.
#
# PostToolUse cannot block; the tool already ran. A warning is exit 2 with a short message on
# stderr, which Claude Code surfaces to the model. Fails OPEN: any parse error or unexpected fault
# exits 0 and warns nothing.
# See hooks/README.md for install and tuning.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Files allowed to carry the banned characters because they quote or test them (this repo's style
# guide, the lint scripts, the hook case table, and this hook pair).
$skip = '(^|[\\/])(writing-style\.md|lint-repo\.(sh|ps1)|hook-cases\.tsv|warn-writing-tells\.(sh|ps1))$'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $ti = ($raw | ConvertFrom-Json).tool_input
    if ($null -eq $ti) { exit 0 }
    $text = $null
    if ($ti.PSObject.Properties['content']) { $text = [string]$ti.content }
    elseif ($ti.PSObject.Properties['new_string']) { $text = [string]$ti.new_string }
    if ([string]::IsNullOrEmpty($text)) { exit 0 }
    $path = ''
    if ($ti.PSObject.Properties['file_path']) { $path = [string]$ti.file_path }
} catch {
    exit 0
}

try {
    if (($path -ne '') -and ($path -imatch $skip)) { exit 0 }
    $emDash = [string][char]0x2014
    $curly = '[' + [string][char]0x2018 + [string][char]0x2019 + [string][char]0x201C + [string][char]0x201D + ']'
    $em = ([regex]::Matches($text, $emDash)).Count
    $cq = ([regex]::Matches($text, $curly)).Count
    if (($em + $cq) -eq 0) { exit 0 }
    [Console]::Error.WriteLine("[warn-writing-tells] The text just written adds $em em-dash(es) and $cq curly quote(s)/apostrophe(s).")
    [Console]::Error.WriteLine('[warn-writing-tells] Both are hard-banned tells (writing-style.md): use a period, comma, colon, or parentheses instead of an em-dash, and straight quotes/apostrophes. Fix the text you just wrote; leave pre-existing prose alone.')
    exit 2
} catch {
    exit 0
}
