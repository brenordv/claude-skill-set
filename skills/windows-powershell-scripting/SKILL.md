---
name: windows-powershell-scripting
description: >-
  Windows PowerShell scripting patterns and pitfalls: operator syntax, strict
  mode, null handling, error handling, arrays, JSON, and encoding rules for
  production scripts on Windows PowerShell 5.1 and PowerShell 7+.
---

# Windows PowerShell Scripting

> **Shared Knowledge**: This skill builds on `brain/knowledge/devops-operations.md` and
> `brain/knowledge/coding-general.md`. Scripts are deliverables, so paths inside them follow
> `brain/knowledge/machine-privacy.md`: no user-profile literals, use `$env:` variables.

## Purpose

Patterns and pitfalls for writing production PowerShell scripts on Windows. Targets Windows
PowerShell 5.1 first, since it is present on every Windows box; notes where PowerShell 7+ behaves
differently. The pitfalls below are the ones that pass a quick glance and then break at runtime.

## 1. Operator syntax

Each cmdlet call inside a condition gets its own parentheses when combined with logical operators:

```powershell
# Correct
if ((Test-Path $a) -or (Test-Path $b)) { ... }

# Wrong: parses -or as a parameter of Test-Path and dies with "parameter 'or'"
if (Test-Path $a -or Test-Path $b) { ... }
```

## 2. Encoding and character set

ASCII only in `.ps1` files. Windows PowerShell 5.1 reads a BOM-less UTF-8 script as ANSI, so emoji
and box-drawing characters mojibake or kill parsing with "Unexpected token". Status markers are
plain ASCII: `[OK]`, `[X]`, `[WARN]`, `[INFO]`, `[...]`. When a non-ASCII literal is genuinely
unavoidable, save the file as UTF-8 **with BOM**; PowerShell 7+ defaults to BOM-less UTF-8 and
reads both.

## 3. Strict mode and null handling

Start every script with strict mode; it turns silent null-property access and typo'd variables
into errors at the fault site:

```powershell
Set-StrictMode -Version Latest
```

Under strict mode, guard before touching members:

```powershell
if ($items -and $items.Count -gt 0) { ... }
if (-not [string]::IsNullOrWhiteSpace($text)) { ... }
```

A pipeline that returns a single object yields a scalar, not an array. Wrap in `@(...)` when the
code needs `.Count` regardless of how many results came back: `@(Get-ChildItem $dir).Count`.

## 4. String interpolation

Keep `$( ... )` subexpressions trivial. A chained property lookup inside a string is easy to get
wrong and hard to read; hoist it into a variable first:

```powershell
$value = $obj.Prop.Sub
Write-Output "Value: $value"
```

## 5. Error handling

- Default to `$ErrorActionPreference = 'Stop'` plus `try`/`catch`. A production script set to
  `Continue` keeps running half-broken and fails somewhere far from the cause; fail at the fault.
- Use `-ErrorAction SilentlyContinue` per call, only where failure is expected and handled (a
  probe like `Get-Command foo`), never as the script-wide preference.
- Don't `return` from inside `try`; compute in the block, clean up in `finally`, return after.
- Native executables don't throw on failure; check `$LASTEXITCODE` after calling one.

## 6. Paths

- Build paths with `Join-Path`, never string concatenation with `\`.
- `$PSScriptRoot` is the script's own directory (PS 3.0+); don't reconstruct it from
  `$MyInvocation`.
- No user-profile or machine-specific literals in scripts: `Join-Path $env:USERPROFILE 'file.txt'`,
  `$env:TEMP`, `$env:ProgramData`.

## 7. Arrays and collections

- `$array += $item` copies the whole array on every call, O(n^2). Harmless for a handful of items,
  wrong inside loops.
- In loops, collect pipeline output directly (`$results = foreach ($x in $set) { ... }`) or use
  `[System.Collections.Generic.List[object]]::new()` with `.Add($item)`.
- `ArrayList` is legacy; prefer `List[T]` when an explicit growable collection is needed.

## 8. JSON

- Always pass `-Depth` to `ConvertTo-Json`; the default of 2 silently flattens nested objects into
  their `ToString()` forms: `$data | ConvertTo-Json -Depth 10`.
- Read with `-Raw`: `Get-Content $path -Raw | ConvertFrom-Json`. Without it the JSON arrives line
  by line.
- Write with `... | Out-File $path -Encoding UTF8` (on 5.1 this includes a BOM, which PowerShell
  reads back fine).

## 9. Common errors

| Error message | Cause | Fix |
|---------------|-------|-----|
| `parameter 'or'` | Cmdlet call not parenthesized before a logical operator | Wrap each cmdlet call in `( )` (§1) |
| `Unexpected token` | Non-ASCII character in a 5.1 script | ASCII only, or save UTF-8 with BOM (§2) |
| `The property 'X' cannot be found` | Member access on `$null` under strict mode | Guard first (§3) |
| `Cannot convert value` | Type mismatch in a comparison or parameter | Cast explicitly or call `.ToString()` |

## 10. Script template

```powershell
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
    # logic here; $PSScriptRoot is this script's directory
    Write-Output '[OK] Done'
    exit 0
}
catch {
    Write-Error "Failed: $_"
    exit 1
}
```

## When to Use This Skill

- Writing or reviewing PowerShell scripts for Windows automation, CI steps, or admin tasks
- Debugging script behavior differences between Windows PowerShell 5.1 and PowerShell 7+
- Any deliverable `.ps1` / `.psm1` where production quality is expected
