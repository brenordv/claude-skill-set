# Machine privacy: keep host details out of everything durable

The machine the agent runs on is not part of the work product. Its paths, usernames, and layout must
never appear in anything persisted or shipped.

## ⛔ Hard Rules

1. **Never write machine-identifying details into a durable artifact.** That covers absolute local
   paths, drive letters, UNC shares, OS usernames, hostnames, and directory layouts outside the repo.
2. **"Durable artifact" means anything persisted or shipped**: source code, comments, tests and
   fixtures, docs, READMEs, commit messages, PR and ticket descriptions, vault notes of every kind
   (reviews that quote diff hunks, lessons, gap tickets, progress checkpoints), auto-memory files,
   config samples, error-message examples, quoted stack traces, log excerpts, and tool output quoted
   anywhere durable.
3. **The rule binds at the moment of persistence**, wherever the text came from. "It was already in
   the chat" or "the subagent report included it" is not permission; scrub before saving.
4. **Absolute paths live only in tool-call parameters** that address the machine (`file_path`, `cwd`,
   and the like). Content being persisted never carries them.
5. **Precedence**: existing files that contain real paths don't authorize adding more. Flag them
   instead of imitating them.

## Write instead

- Repo-relative paths: `skills/brain/knowledge/testing.md`.
- Placeholders when an absolute shape is genuinely needed: `<repo-root>`, `<user-home>`, `~`.
- Environment variables in config samples.

## Not a violation

- Chat replies to the user about their own machine. They can see their own paths.
- Paths fixed by the product or OS rather than by this machine (`/etc/nginx/`, standard install
  directories). Those are content.
- Security-assessment deliverables naming an assessed target's hosts and paths. The target is the
  subject of the deliverable; the ban covers the agent's own host.

## Self-check (run before finalizing any artifact)

Triggers: file writes destined for the repo, `vault_save` of any kind, PR/ticket text, commit-message
text, memory writes. Images too: the scan below can't see pixels, so visually verify screenshots or
crop machine-identifying regions before embedding one.

Search the artifact text for these case-insensitive regexes. When the artifact is a file, use the
runtime's native search tool or text-search `search_text` with `is_regex: true`; never shell
`rg`/`grep` (`text-search-operations.md` ⛔ Hard Rules). When the text isn't on disk yet (a commit
message, a vault body being composed), check the draft against the same patterns before sending it:

```
(^|[^A-Za-z0-9])[A-Za-z]:[\\/]
[\\/](Users|home)[\\/]
\\\\[\w.-]+\\
AppData[\\/]Local[\\/]Te?mp
[\\/]te?mp[\\/]
```

The first pattern's left boundary keeps URL schemes (`https://`, `res://`) and SSH remotes from
matching while still catching drive-letter paths in raw, JSON-escaped, and `file:///` forms. The
bounded temp patterns avoid false hits on words like Template. Also scan for the actual username and
hostname: `$env:USERNAME` and `$env:COMPUTERNAME` on Windows, `whoami` / `hostname` / the basename of
`$HOME` on Unix. A hit is a candidate, not an automatic violation; judge it against "Not a violation"
above before rewriting.

## Dispatch restatement (copy verbatim into every subagent prompt)

> Never put machine-identifying details (absolute local paths, drive letters, OS usernames,
> hostnames) into anything you persist: code, comments, docs, reports, vault notes. Use repo-relative
> paths or placeholders like `<repo-root>`; full rules in `brain/knowledge/machine-privacy.md`.
