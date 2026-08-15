---
name: ticket-description
description: >-
  Draft a ticket/issue title and description, either reverse-engineered from
  the current branch's changes or worked out through a short Q&A with the user.
  Retrieves similar past tickets for consistency and archives the result in the
  vault. Use when opening a ticket/issue or when asked to write one up.
---

# Ticket Description

> **Shared Knowledge**: This skill builds on `brain/knowledge/writing-style.md` (a ticket is prose a human
> reads; apply it in full) and `brain/knowledge/vault-operations.md` §"Artifact archives (pinned vault
> projects)". Stack detection comes from `brain/knowledge/github-pr-stacks.md`; on a stacked branch,
> Mode A scopes its inputs per that file (see Step 2).

Produce a **title and a description** for a ticket/issue. A ticket describes the *need and the outcome*,
not a changelog. Write it as a specification of the work, even in retroactive mode.

## When to Use This Skill

- Opening a ticket/issue for work about to be done
- Writing a ticket after the fact for work already on a branch
- Asked to "make a ticket / issue for this"

## Step 1: Pick the Mode

- **Mode A: Retroactive (from the branch).** Work already exists as a diff and needs a ticket to describe
  it. Trigger: there are branch/working changes and the user says "make a ticket for this."
- **Mode B: Interactive (from intent).** The user has work in mind but no clear spec yet. Trigger: the
  user describes something they want done that isn't built.

If it's ambiguous which applies, ask one question to settle it before proceeding.

## Step 2: Gather

**Mode A:**
1. **Stack check first.** Run `gh stack view --json` per `brain/knowledge/github-pr-stacks.md`. Exit 2,
   or `gh`/the stack extension missing, means no stack; any other outcome follows that file's detection
   table. Never run any `gh stack` command other than `view`.
2. `git_diff` with `fromRef` = base branch, `toRef` = `HEAD`; `git_log` with `ref: "<base>..HEAD"`.
   On a stacked branch, the ticket describes the feature the whole stack delivers, so diff and log from
   the trunk to the top layer (`fromRef: "<trunk>...<top-layer-branch>"`) instead; produce a per-layer
   ticket only when the user asks for one, scoped to that layer's diff.
3. Infer the *problem the change solves* and the *outcome it delivers*. Describe those, not the file-level
   edits and not the stack's layer structure (that's implementation detail; at most, one Notes line
   saying the work lands as a PR stack). If the intent behind the diff is genuinely unclear, ask rather
   than guess.

**Mode B:**
Run one focused round of questions (batch them, don't drip). Cover only what you actually need:
- What problem or need is this solving, and who feels it?
- What's the desired outcome / definition of done?
- What's in scope, and what's explicitly out?
- Any constraints, dependencies, or hard requirements?

Ask a second round only if the answers leave a real gap. Don't over-interrogate a small ticket.

## Step 3: Retrieve Similar Past Tickets

`vault_list` with `project: "ticket-descriptions"` (pass it explicitly) and a `query`/`tags` from the
topic. `vault_get` the closest matches and mirror their structure and phrasing so tickets stay consistent.
Treat them as precedent for *form*, not facts about this work.

## Step 4: Write the Title and Description

**Title:** one line, names the outcome or the problem. Concrete, no filler. Prefer an imperative ("Add
retry/backoff to the payment webhook") or a clear noun phrase ("Duplicate points on replayed transfer
events").

**Description format:**

```
## Summary
<1–2 sentences: the problem and the desired outcome>

## Context
<why this matters, who's affected, any background a reader needs>

## Scope
<what's included>

## Out of scope
<what's explicitly excluded; omit this heading if nothing applies>

## Acceptance criteria
- [ ] <testable, observable condition>
- [ ] <...>

## Notes
<links, dependencies, open questions (optional)>
```

**Rules:**
- Acceptance criteria must be observable and testable ("Returns `409` on a replayed event"), not vague
  ("handle duplicates properly").
- Keep it tight. A small ticket doesn't need every heading; drop the ones with nothing to say.
- Follow `brain/knowledge/writing-style.md`: no em-dashes, no throat-clearing, no "..., ensuring..."
  clauses, none of the AI vocabulary set. Write like an engineer filing an issue for a teammate.
- Run the `brain/knowledge/machine-privacy.md` self-check before outputting: no absolute local paths,
  OS usernames, or hostnames; paths go repo-relative.

## Step 5: Archive in the Vault

After the ticket is settled, archive it: `vault_save` with `project: "ticket-descriptions"` passed
explicitly, the title and description as the body. Run the machine-privacy self-check once more before
saving. Name, summary, and tags follow `brain/knowledge/vault-operations.md` §"Artifact archives
(pinned vault projects)".
