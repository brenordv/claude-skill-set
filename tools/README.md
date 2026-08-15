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
markdown in this repo run it before handing off (wired in `CLAUDE.md`); CI is the backstop for
hand edits.

### Tuning

Exemptions are deliberate and minimal; add one only when a check is structurally wrong for a file
(a file that *quotes* a banned pattern), never because a finding is inconvenient. Apply every change
to both scripts.
