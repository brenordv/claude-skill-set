# New-code quality gates

Three of the language skills ship a quality gate: a script that checks the lines a branch adds,
diffing the merge base against the working tree so uncommitted work is checked too. Each gate
answers two questions about that new code:

- Is it tested? The gate runs the language's coverage tool, intersects the per-line coverage data
  with the added lines, and enforces a threshold on new coverable lines.
- Do the tests mean anything? The gate runs the language's mutation tool over the changed code and
  fails when a mutant survives, meaning the code could be broken without any test noticing.

The threshold is a detection signal, not a target to pad. A failing gate means "look at what is
untested and decide", never "add tests until the number moves".

Each gate also runs a file-size phase before the tool-backed halves: new and cap-crossing production
files are graded against the per-language tiers in `skills/brain/knowledge/coding-general.md` §3
(warn at 800 lines for Python, 700 for C# and Rust; fail at the 1,500 cap). It needs only git and
the filesystem, so it reports even where the language toolchain is absent. Test files are warn-only,
and an already-oversized file warns with a message to route new code into a new module rather than
mass-refactor the old one.

| Gate | Coverage producer | Mutation tool | Default threshold |
|------|-------------------|---------------|-------------------|
| C# | `dotnet test` + coverlet collector (lcov) | Stryker.NET, scoped with `--since` | 90% |
| Python | pytest + pytest-cov (lcov) | Cosmic Ray, scoped with its git filter | 80% |
| Rust | cargo-llvm-cov (lcov) | cargo-mutants `--in-diff` | 80% |

## Running a gate

The scripts are Python 3, standard library only; any Python 3 interpreter runs them. From anywhere
inside the target repo:

```bash
python <skill-set>/skills/csharp/scripts/csharp_quality_gate.py
python <skill-set>/skills/python/scripts/python_quality_gate.py
python <skill-set>/skills/rust/scripts/rust_quality_gate.py
```

Shared flags: `--base <ref>` overrides the base (default chain: `origin/HEAD`, `main`, `master`),
`--cov-threshold <pct>` and the repeatable `--exclude <glob>` adjust the coverage policy (`--exclude`
also drops a file from the file-size gate), `--skip-mutants` runs only the coverage half for quick
iteration (the file-size phase always runs), and `--lcov-file <path>`
consumes a pre-generated lcov file when a repo's coverage needs a different producer invocation.
Language-specific flags, caveats, and each gate's trust boundary are documented in the skill's
testing guidelines (linked below).

All three gates share one exit-code contract:

| Code | Meaning |
|------|---------|
| 0 | all gates pass |
| 2 | coverage gate failed |
| 3 | mutation gate failed |
| 4 | file-size gate failed (a new or cap-crossing production file hit the 1,500-line cap) |
| 64 | usage error |
| 70 | an underlying tool ran and failed: broken build, red test run, missing output |
| 78 | environment not ready: tool missing, not a git repo, base ref unresolvable |

All phases run and report before the process exits; when several fail the precedence is 2
(coverage) > 3 (mutation) > 4 (file size). Codes 2, 3, and 4 mean the new code is undertested or
oversized; 70 means the build or suite is broken. A CI consumer should keep those remediation
paths separate.

## What to install

The gate scripts themselves need nothing installed. The language toolchains do the real work.

### C#

- The .NET SDK on `PATH`. Stryker additionally needs the .NET 10 runtime or newer.
- Every test project must reference `coverlet.collector` and `Microsoft.NET.Test.Sdk`. The csharp
  skill already mandates both on all test projects, so a compliant repo needs nothing new.
- Stryker, once per machine: `dotnet tool install -g dotnet-stryker` (a repo-local tool manifest
  works too).

### Python

- Run the gate with the target project's own interpreter (the venv's `python`); the gate reuses
  that interpreter to run pytest.
- In that environment: `pip install pytest-cov cosmic-ray`. Floors: pytest-cov 4.0+ and
  coverage.py 6.3+ (lcov output), Python 3.9+ (Cosmic Ray). Cosmic Ray does not support Windows; prefer WSL on a Windows machine, if possible.
- Coverage sources belong in the repo's coverage config (the gate runs bare `--cov`); a repo whose
  producer differs uses `--lcov-file` instead.

### Rust

```bash
cargo +stable install cargo-llvm-cov --locked
cargo install --locked cargo-mutants
```

## The mutation phase is opt-in

The coverage half runs anytime, dirty tree included; it is the half to run while iterating and at
handoff (`--skip-mutants`). The mutation half is a separate, optional stage with two
preconditions: the user wants it, and the work is committed. An agent never commits, stages, or
stashes; git writes belong to the user. So the protocol is: once the coverage half passes, ask
the user whether they want the mutation phase and, if so, to commit the changes themselves, and
only then run the gate without `--skip-mutants`.

The committed-tree precondition is not ceremony. The C# gate warns up front on uncommitted
tracked changes, because whether Stryker's `--since` covers them is unverified. The Python gate
refuses outright (exit 78): Cosmic Ray mutates source files on disk, and an interrupted run would
leave a mutant indistinguishable from real uncommitted work.

## Which skills are wired to them

Each gate belongs to one language skill. The skill's instructions tell an agent to run the
coverage half before handing off work and to treat the mutation half as the user's opt-in, and
the skill's testing guidelines carry the full documentation:

| Skill | Wiring | Full documentation |
|-------|--------|--------------------|
| `csharp` | testing section and quality-validation checklist in [skills/csharp/SKILL.md](skills/csharp/SKILL.md) | [skills/csharp/testing-guidelines.md](skills/csharp/testing-guidelines.md), section "New-code quality gate" |
| `python` | testing section and completion checklist in [skills/python/SKILL.md](skills/python/SKILL.md) | [skills/python/testing-guidelines.md](skills/python/testing-guidelines.md), section "New-code quality gate" |
| `rust` | testing section in [skills/rust/SKILL.md](skills/rust/SKILL.md) | [skills/rust/testing-guidelines.md](skills/rust/testing-guidelines.md), section "New-code quality gate" |

Each script keeps its unit tests beside it (`test_*_quality_gate.py` in the same `scripts/`
folder), and CI runs all three suites on every push and pull request
(`.github/workflows/repo-lint.yml`, the `gate-tests` job).
