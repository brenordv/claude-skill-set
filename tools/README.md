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

| Tag | Check | Catches |
|-----|-------|---------|
| `[link]` | Relative markdown link targets exist (external URLs and anchors skipped) | dead links after a file moves |
| `[ref]` | Backticked, slash-containing `*.md` paths resolve; tried against the repo root, `skills/<path>` (the `brain/...` shorthand used inside skills), and the referencing file's folder | dead cross-references between knowledge files and skills, including the ten files CLAUDE.md mandates |
| `[style]` | No em-dash character anywhere | the single most-banned writing-style tell sneaking back in |
| `[privacy]` | No machine-identifying path shapes (`Users/<name>`, the AppData local temp folder) | machine details leaking into durable prose (`machine-privacy.md`) |

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

## test-hooks (`test-hooks.sh`)

Parses and exercises the four `PreToolUse` hook scripts in `../hooks/`. Bash only: it runs the `.sh`
hooks the way they ship, and the `.ps1` hooks get a separate parse check in CI
(`../.github/workflows/repo-lint.yml`).

### Why this exists

The hooks ship to macOS and Linux and only ever execute on an installed machine; nothing in the
pipeline parsed or ran them. That let a real bug hide. Each `.sh` built its deny messages with a
heredoc inside command substitution (`VAR="$(cat <<'MSG' ... MSG )"`). Bash 5.2 rewrote its
command-substitution parser to recurse into that body, but the bash 3.2 that ships with macOS scans
for the closing delimiter instead, so an apostrophe in the body mis-lexes as an opening quote and the
parse runs past the terminator. Three of the four hooks failed to load on macOS while every Linux CI
runner (bash 5.2) parsed the same source without complaint. This harness runs the hooks under the
interpreter that ships, so that class of failure surfaces before it reaches a machine.

### The layers

| Layer | Check | Catches |
|-------|-------|---------|
| `[syntax]` | `bash -n` over the hook scripts and `tools/*.sh` | a script that does not parse |
| `[pattern]` | no command-substitution-wrapped heredoc remains in the hook scripts | the incident class reappearing on a bash new enough to parse it silently |
| `[behavior]` | JSON payloads piped to each hook on stdin, asserting verdict, exit status, and (on deny) that the real message came back intact | a routing or verdict regression, and a message mangled by the parse bug |

Every interpreter call uses `$BASH`, the bash running the harness, so the macOS CI job runs the hooks
under `/bin/bash` 3.2 as a true reproducer rather than whatever bash sits on `PATH`. Case payloads
reach a hook only as bytes on stdin, never through `eval` or a field spliced into command position.

### Running it

```shell
# from the repo root: macOS / Linux / Git Bash
bash tools/test-hooks.sh

# point it at an installed copy, after copying the hooks to ~/.claude/hooks or after an OS update
bash tools/test-hooks.sh --hooks-dir ~/.claude/hooks
```

Exit 0 means clean; exit 1 prints one `hooks/<script>: [layer] case "<name>": expected X, got Y` per
failure with the raw stdout and exit code beneath, ending with a `test-hooks: N cases, M failed`
tally. CI runs it on Ubuntu (bash 5.2, fast signal on verdict regressions) and on macOS (bash 3.2,
the shipping interpreter that catches the parse-failure class); the `.ps1` hooks get their parse check
on the Windows job. JSON in and out uses Perl with `JSON::PP`, the same core module the hooks require.
