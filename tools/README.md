# Tools

## lint-repo (`lint-repo.ps1` / `lint-repo.sh`)

Static checks over every markdown file in the repo. Two implementations with identical behavior:
the `.ps1` for Windows, the `.sh` for macOS/Linux and CI. Keep them in sync when tuning either.

### Why this exists

This repo is a rulebase, and prose rots in one specific way: pointers go stale and text drifts from
the rules it states. An audit (August 2026) found all of these live at once: the hooks folder had
moved and its README links were dead, a workflow file referenced a `verify` skill that never
existed, a routing table referenced a long-renamed review skill, and the README described eight
always-on files while listing ten. None of it was caught, because nothing checked. Each lint check
below corresponds to a class of bug found that day. Knowledge rules and agent skills can't be the
enforcement layer for their own repo (a rule outside the context window checks nothing), so this
runs as a script, and CI runs it on every push and pull request (`.github/workflows/repo-lint.yml`).
CI runs **both implementations**, the `.sh` on ubuntu and the `.ps1` on Windows PowerShell 5.1:
they are kept in sync by hand, so an OS quirk or a drifted edit surfaces as one job failing while
the other passes, instead of silently diverging.

### The checks

| Tag         | Check                                                                                                                                                                             | Catches                                                                                              |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| `[link]`    | Relative markdown link targets exist (external URLs and anchors skipped)                                                                                                          | dead links after a file moves                                                                        |
| `[ref]`     | Backticked, slash-containing `*.md` paths resolve; tried against the repo root, `skills/<path>` (the `brain/...` shorthand used inside skills), and the referencing file's folder | dead cross-references between knowledge files and skills, including the ten files CLAUDE.md mandates |
| `[style]`   | No em-dash character anywhere                                                                                                                                                     | the single most-banned writing-style tell sneaking back in                                           |
| `[privacy]` | No machine-identifying path shapes (`Users/<name>`, the AppData local temp folder)                                                                                                | machine details leaking into durable prose (`machine-privacy.md`)                                    |

Fenced code blocks are exempt from `[link]`/`[ref]` (code samples aren't prose links) but still
scanned by `[style]`/`[privacy]`, since config examples are exactly where paths leak. Two deliberate
skips: bare filenames without a slash (`CONTRIBUTING.md` in a skill refers to the *target* repo, not
this one), and `writing-style.md` for the em-dash check, since it quotes the character to ban it.
The `[privacy]` patterns are case-sensitive on purpose: lowercase `/users/123` is an API route, not
a Windows profile, and placeholder forms like `Users\<you>` don't match.

### Running it

```shell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lint-repo.ps1

# macOS / Linux / Git Bash
bash tools/lint-repo.sh
```

Exit 0 means clean; exit 1 prints one `file:line: [tag] message` per finding. Agents editing
markdown in this repo run it before handing off (wired in `.claude/rules/markdown-lint.md`); CI is the backstop for
hand edits.

### Tuning

Exemptions are deliberate and minimal; add one only when a check is structurally wrong for a file
(a file that *quotes* a banned pattern), never because a finding is inconvenient. Apply every change
to both scripts.

## test-hooks (`test-hooks.sh` / `test-hooks.ps1` / `hook-cases.tsv`)

Parses and exercises the five hook pairs in `../hooks/` (four `PreToolUse`, plus the `PostToolUse`
`warn-file-size`). Each side runs the way it ships: the `.sh` harness runs the `.sh` hooks under
bash, the `.ps1` harness runs the `.ps1` hooks under Windows PowerShell 5.1, and both grade against
the same case table, `hook-cases.tsv`, so a behavior divergence inside a hook pair surfaces as one
platform's CI job failing while the other passes.

### Why this exists

The hooks ship to macOS, Linux, and Windows and only ever execute on an installed machine; for a
long time nothing in the pipeline parsed or ran them. That let a real bug hide. Each `.sh` built its
deny messages with a heredoc inside command substitution (`VAR="$(cat <<'MSG' ... MSG )"`). Bash 5.2
rewrote its command-substitution parser to recurse into that body, but the bash 3.2 that ships with
macOS scans for the closing delimiter instead, so an apostrophe in the body mis-lexes as an opening
quote and the parse runs past the terminator. Three of the four hooks failed to load on macOS while
every Linux CI runner (bash 5.2) parsed the same source without complaint. The bash harness runs the
hooks under the interpreter that ships, so that class of failure surfaces before it reaches a
machine.

The Windows side earned its harness the same way. In August 2026 `warn-file-size.ps1` shipped with
an unanchored sample-form regex that made the hook open secret-named files under a sample-named
parent directory. It parsed clean, so the CI parse check stayed green, and the `.sh` twin carried
the anchored form, so the bash harness stayed green too. A behavior divergence inside one hook pair
is invisible to every check that looks at only one side; the shared case table closes that gap.

### The layers

| Layer         | Where          | Check                                                                                                                                                                                                                                                  | Catches                                                                             |
|---------------|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| `[syntax]`    | `.sh` harness  | `bash -n` over the hook scripts and `tools/*.sh`                                                                                                                                                                                                       | a script that does not parse                                                        |
| `[pattern]`   | `.sh` harness  | no command-substitution-wrapped heredoc remains in the hook scripts                                                                                                                                                                                    | the incident class reappearing on a bash new enough to parse it silently            |
| `[threshold]` | `.sh` harness  | the file-size warn thresholds and size constants declared in five scripts (both `warn-file-size` hooks and the three `*_quality_gate.py` gates) are extracted and cross-compared, with zero matches, multiple matches, or a non-integer each a failure | a hand-sync miss drifting the write-time nudge apart from the diff-scoped gate      |
| `[behavior]`  | both harnesses | the `hook-cases.tsv` payloads fed to each hook on stdin, asserting verdict, exit status, and (on deny/warn) that the real message came back intact                                                                                                     | a routing or verdict regression, a mangled message, and `.sh`/`.ps1` behavior drift |

The threshold layer lives in the bash harness only (it is plain text comparison and runs on the
ubuntu and macOS jobs; a PowerShell duplicate would recreate the sync problem it solves). It
compares the sources against each other, never against numbers baked into the harness, so a
deliberate retune that updates all five scripts together stays green.

The case table is five tab-separated fields per row (hook, tool, tool_input JSON, verdict,
signature) with a `# cases: N` header both readers verify, so a dropped or malformed row is a hard
error rather than silently shrunk coverage. Payload rows for `warn-file-size` name fixture files the
harnesses generate, including two regression rows that pin the secret-skip anchoring the August 2026
incident regressed. Every interpreter call in the `.sh` harness uses `$BASH`, the bash running the
harness, so the macOS CI job runs the hooks under `/bin/bash` 3.2 as a true reproducer. In both
harnesses, case payloads reach a hook only as bytes on stdin, never through `eval`,
`Invoke-Expression`, or a field spliced into command position, and signatures are matched as
literal strings, never as patterns.

### Running it

```shell
# from the repo root: macOS / Linux / Git Bash
bash tools/test-hooks.sh

# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test-hooks.ps1

# point either at an installed copy, after copying the hooks or after an OS update
bash tools/test-hooks.sh --hooks-dir ~/.claude/hooks
powershell -NoProfile -ExecutionPolicy Bypass -File tools/test-hooks.ps1 -HooksDir "$env:USERPROFILE\.claude\hooks"
```

With a custom hooks directory, the hooks in that directory are graded against this checkout's case
table and gate scripts, so an installed copy that drifted behind repo policy fails. Exit 0 means
clean; exit 1 prints one `<script>: [layer] case "row <n>: ...": expected X, got Y` per failure with
the raw stdout, stderr, and exit code beneath, ending with a `test-hooks: N cases, M failed` tally;
exit 2 is a harness or setup error. CI runs the bash harness on Ubuntu (bash 5.2, fast signal on
verdict regressions) and on macOS (bash 3.2, the shipping interpreter that catches the parse-failure
class), and the PowerShell harness on the Windows job alongside the `.ps1` parse check. The `.sh`
side uses Perl with `JSON::PP` for JSON in and out, the same core module the hooks require; the
`.ps1` side uses `ConvertFrom-Json`, same as the hooks it runs.
