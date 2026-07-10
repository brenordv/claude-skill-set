---
name: pr-description
description: >-
  Generate a pull-request description in the house format from a diff and commit
  history. Retrieves similar past PRs for consistency and archives the result in
  the vault. Use when opening a PR, or when asked to write or update a PR
  description.
---

# PR Description

> **Shared Knowledge**: This skill builds on `brain/knowledge/writing-style.md` (apply it in full; a PR
> description is exactly the kind of prose that must not read as AI-generated) and
> `brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault projects)".

You are writing a pull-request description for a change just made (by the user or an agent on their behalf).
Use the diff, commit messages, and any context provided. **Output only the description in the exact format
below. No preamble, no closing remarks.**

## When to Use This Skill

- Opening a PR (e.g. before `gh pr create`)
- Asked to write, rewrite, or update a PR description
- Summarising a completed branch for review

## Step 1: Gather Inputs

1. `git_diff` with `fromRef` = base branch and `toRef` = `HEAD` (or `statOnly` first to see the shape).
2. `git_log` with `ref: "<base>..HEAD"` for the commit narrative.
3. Fold in any extra context the user gave you.

## Step 2: Retrieve Similar Past PRs

`vault_list` with `project: "pr-descriptions"` (pass it explicitly) and a `query`/`tags` from the change.
`vault_get` the closest matches and mirror their structure and phrasing so descriptions stay consistent
across the team. Treat them as precedent for *form*, not as facts about the current change.

## Step 3: Write the Description

### Format

```
> [!TIP]
> TL;DR: <one-sentence summary>

# Changes

1. **<Category>**:  <Short title>
    - <1–3 sentence explanation>

2. **<Category>**:  <Short title>
    - <1–3 sentence explanation>

...

# Caveats
...

# Test evidence

```

### Rules

1. **TL;DR.** One sentence. Lead with the user- or system-visible outcome ("Adds a new X endpoint..."),
   then briefly mention key supporting work if it's load-bearing. No marketing tone.

2. **Categories.** Each numbered item begins with a bolded category, then a colon, then two spaces, then a
   short title. Use these categories:
   - `Main Change`: the core functionality being delivered (the feature, fix, or new endpoint the PR
     exists for).
   - `Improved code reusability`: refactors that extract shared abstractions or remove duplication.
   - `Improved robustness`: error handling, cancellation, retries, validation, reliability.
   - `Extensibility`: scaffolding or new models that enable future work without using it yet.
   - If a change genuinely fits none of these, invent a short category in the same style. Prefer the
     canonical ones.

3. **Sub-bullet.** Each numbered item has exactly one nested bullet (`    - ...`) with the explanation. Be
   concrete: name the function, class, type, file, or endpoint involved (in backticks). Include enough
   detail that a reviewer understands the change without reading the diff, but stay tight. Usually 1 to 3
   sentences.

4. **Ordering.** `Main Change` items first (in logical or dependency order), then improvements and
   refactors.

5. **Formatting details.**
   - Exactly two spaces after the colon following the bold category.
   - Backticks around identifiers, types, paths, endpoints, HTTP verb plus path.
   - Full sentences with terminal periods in the sub-bullets.
   - No emoji, no images, no tables unless asked.

6. **Caveats and Test evidence.** Leave these for the user to fill in. Output `Caveats` with a literal
   `...` placeholder on the next line. Output `Test evidence` with nothing after the header. Do not invent
   caveats or test results.

### Writing Style

Follow `brain/knowledge/writing-style.md` in full. The hard bans matter most here: **no em-dashes**, no
"not just X but Y," no throat-clearing transitions, no trailing "..., ensuring/allowing/making it..."
clauses, no closing summary (the list is the summary), and none of the AI vocabulary set. Write like an
engineer describing the change to a teammate. Prefer concrete over abstract ("Returns `0` when the member
has no transfers" beats "gracefully handles the empty case"). Vary bullet openings.

## Step 4: Archive in the Vault

After the description is settled, archive it: `vault_save` with `project: "pr-descriptions"` passed
explicitly, the full description as the body. Name, summary, and tags follow `vault-operations.md`
§"Artifact archives (pinned vault projects)".

## Example Output

> [!TIP]
> TL;DR: Adds a new campaign balance endpoint that returns how many entries (or points/cash) a member has earned in a campaign, backed by scroll-paginated point transfer fetching and a shared paginated result abstraction.

# Changes

1. **Main Change**:  New `GET /campaign/{campaignId}/balance/{walletType}` endpoint
    - Exposes the member's balance for a given wallet type within a campaign. Supports `entries`, `points`, and `cash`, mapped to their internal OpenLoyalty wallet codes. Returns `0` if the member has no transfers.

2. **Improved robustness**:  `CancellationToken` propagation
    - `GetMemberBalanceAsync` and related interfaces now accept and forward a `CancellationToken`, so callers can cancel in-flight requests.

# Caveats
...

# Test evidence
