# Hooks

Enforcement hooks that back the always-on rules in `../knowledge/`. A rule in a knowledge file is
probabilistic: it only fires if the model recalls it at the moment a reflex fires, and the reflex is
strongest exactly where recall is weakest (fresh chat, long context, deep in a task). A hook does not
depend on recall. It intercepts the tool call after the model emits it and before it runs, and its
denial message lands in context at the one moment it steers the next attempt.

This folder holds two independent `PreToolUse` hooks (matcher `Bash|PowerShell`), each shipped as a
Windows `.ps1` and a POSIX `.sh` with identical behavior, each failing open:
- **route-to-text-tools** routes file-probing, in-place-edit, and read-only-git shell commands to the
  `text-search`, `text-edit`, and `git-ops` MCPs.
- **block-secrets** hard-blocks shell commands that read or copy secret-looking files.

> [!IMPORTANT]
> It is crucial to know that those hooks are not a foolproof, be-all, end-all security solution. 
> Pretty much nothing will be with generative AI. It will nudge the agents in the right direction,
> but they could still decide to circumvent the blocks presented in the hooks. A more comprehensive
> security solution would include a containerized solution that runs in a separate process and
> enforces the blocks at a filesystem permission level.
> So, is this useless? Not at all, just don't look at it as the final solution.

## route-to-text-tools

A `PreToolUse` hook for the **Bash** and **PowerShell** tools, shipped as two interchangeable
implementations with identical logic and behavior: **`route-to-text-tools.ps1`** (Windows PowerShell
5.1) and **`route-to-text-tools.sh`** (POSIX bash, for macOS/Linux). It denies shell commands
whose purpose is to read, search, or list files (routing the agent to the `text-search` MCP), to
rewrite file content in place (routing to the `text-edit` MCP), or to inspect a repo read-only through
shell `git` (routing to the `git-ops` MCP), and lets everything else through. It is the enforcement
layer for
[`../knowledge/text-search-operations.md`](../knowledge/text-search-operations.md),
[`../knowledge/text-edit-operations.md`](../knowledge/text-edit-operations.md), and
[`../knowledge/git-readonly-operations.md`](../knowledge/git-readonly-operations.md).

The motivating incident: on a fresh chat in a new repo the reflex fired before any rule was salient,
and `grep`/`cat` read files a `.gitignore` should have hidden. `text-search` would have withheld those
structurally (ignore tiers plus the secret denylist and content scan); the shell tools have no such
rail. The hook removes the dependency on the rule being remembered.

### What it blocks, and what it does not

| Command shape                                                                                                          | Verdict   | Routed to                              |
|------------------------------------------------------------------------------------------------------------------------|-----------|----------------------------------------|
| `grep`/`rg`/`egrep`/`ack` leading a command                                                                            | deny      | `search_text`                          |
| `cat`/`tac`/`head`/`tail` reading a file                                                                               | deny      | `read_lines`                           |
| `find`/`fd`, `ls -R`, `dir /s`, `Get-ChildItem -Recurse`                                                               | deny      | `find_files`                           |
| `sed`/`awk` reading a file (leading position)                                                                          | deny      | `search_text` / `read_lines`           |
| `Select-String`, `Get-Content`                                                                                         | deny      | `search_text` / `read_lines`           |
| `sed -i`, `perl -pi -e`, `Set-Content`/`Add-Content`/`Out-File`                                                        | deny      | `replace_text` / `normalize_files`     |
| `git grep`/`log`/`diff`/`show`/`status`/`blame`/`ls-files`, `git branch` (list), `git reflog`, `git stash list`/`show` | deny      | `git-ops` (`git_grep`, `git_log`, ...) |
| `git commit`/`add`/`push`/`checkout`/`reset`/`merge`, `git branch -d`, `git stash pop`, `git tag <name>`               | **allow** | shell git is fine for writes           |
| `dotnet test \| tail -20` (downstream of a pipe)                                                                       | **allow** | output trimming, not probing           |
| `cat > file <<EOF` (redirect/heredoc), `find ... -delete`/`-exec`                                                      | **allow** | authoring / acting, not reading        |
| `ls -r` (reverse sort, not `-R`), plain `ls`/`dir`/`Get-ChildItem`                                                     | **allow** | not a recursive walk                   |

The one nuance worth understanding: only a command **leading** a pipeline stage is treated as reading
files. A read filter downstream of a `|` is consuming another command's stdout (output trimming), which
the knowledge files explicitly exempt. Statements are split on `&&`, `||`, `;`, and newlines first, so
`build && grep TODO src` still denies the `grep` even though it is not the first word overall.

On a deny the model receives a `permissionDecision: "deny"` with a message naming the exact replacement
tool and a concrete call; see the `$searchMsg`/`$editMsg`/`$gitMsg` strings (`SEARCH_MSG`/`EDIT_MSG`/
`GIT_MSG` in the `.sh`).

### Install (per machine, not committed)

The scripts live in the repo; the wiring is local machine config. Pick the script for your OS, copy it
somewhere stable, and register it in your **user** settings so it applies to every project.

1. Copy the script for your OS to `~/.claude/hooks/` (any stable path works): `route-to-text-tools.ps1`
   on Windows, `route-to-text-tools.sh` on macOS/Linux.

2. Add a hook group to `~/.claude/settings.json` under `hooks.PreToolUse`. **Append** to the array; do
   not replace it, other `PreToolUse` hooks (a secrets guard, for example) coexist here.

   **Windows** (exec-form: spawned directly with no shell, so there is no quoting to get wrong and the
   hook JSON is piped to the script's stdin; the `-File` path is not shell-expanded, so give an
   absolute path):

   ```jsonc
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash|PowerShell",
           "hooks": [
             {
               "type": "command",
               "command": "powershell.exe",
               "args": [
                 "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", "C:\\Users\\<you>\\.claude\\hooks\\route-to-text-tools.ps1"
               ],
               "timeout": 10
             }
           ]
         }
       ]
     }
   }
   ```

   **macOS / Linux** (the default hook shell is bash, so `$HOME` expands):

   ```jsonc
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash|PowerShell",
           "hooks": [
             { "type": "command", "command": "bash \"$HOME/.claude/hooks/route-to-text-tools.sh\"", "timeout": 10 }
           ]
         }
       ]
     }
   }
   ```

3. Reload: open `/hooks` once (it reloads config) or restart Claude Code. The settings watcher only
   watches directories that had a settings file when the session started, so an edit to
   `~/.claude/settings.json` mid-session is not picked up until then.

**Requirements.** Windows: `powershell.exe` (Windows PowerShell 5.1, always present). macOS/Linux:
`bash` and `perl` with `JSON::PP` (a core module), both present on stock macOS and Ubuntu, so nothing
to install. `JSON::PP` handles the JSON in and out; if Perl or the module is somehow absent the `.sh`
fails open (exits 0 and enforces nothing). The matcher covers both the `Bash` and `PowerShell` tools,
so `grep` and `Get-Content` reflexes are both caught. Both scripts carry identical logic and the same
52-case behavior; keep them in sync when you tune one.

### Verify

**PowerShell** (pipe a synthesized payload straight into the script, no Claude Code needed):

```powershell
$s = "$HOME\.claude\hooks\route-to-text-tools.ps1"
'{"tool_name":"Bash","tool_input":{"command":"grep -r foo ."}}'      | & powershell.exe -NoProfile -File $s  # -> deny (search)
'{"tool_name":"Bash","tool_input":{"command":"dotnet test | tail"}}' | & powershell.exe -NoProfile -File $s  # -> (no output = allow)
'{"tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ f"}}'    | & powershell.exe -NoProfile -File $s  # -> deny (edit)
'{"tool_name":"Bash","tool_input":{"command":"git log --oneline"}}'  | & powershell.exe -NoProfile -File $s  # -> deny (git-ops)
'{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'    | & powershell.exe -NoProfile -File $s  # -> (no output = allow, write)
```

**bash** (the `.sh` has a `--command` self-test that needs neither Perl nor Claude Code):

```bash
s=~/.claude/hooks/route-to-text-tools.sh
bash "$s" --command 'grep -r foo .'          # -> search
bash "$s" --command 'dotnet test | tail -20' # -> allow
bash "$s" --command 'git log --oneline'      # -> git
bash "$s" --command 'git commit -m x'        # -> allow
```

Empty stdout (PowerShell) or `allow` (bash `--command`) means allowed; a deny prints the JSON object
with `"permissionDecision":"deny"` (or, in `--command` mode, the verdict word `search`/`edit`/`git`).

### Tuning

Everything is in the scripts; tune in place, and apply the same change to both so they stay in sync.
The PowerShell identifiers below mirror the bash ones: `$probeLeading` is the probe `case` list, the
`elseif ($lead -eq 'git')` block is the `git_readonly` function, and `$searchMsg`/`$editMsg`/`$gitMsg`
are `SEARCH_MSG`/`EDIT_MSG`/`GIT_MSG`.

- **Add/remove a probed command:** edit the `$probeLeading` array (PS) / the probe `case` list (bash).
- **Narrow the git redirect:** the `elseif ($lead -eq 'git')` block maps read-only subcommands to
  git-ops. To cover only `git grep`/`git log`, cut the always-redirect list to `@('grep','log')` and
  drop the `reflog`/`stash`/`branch` branches. It is deliberately biased toward **allow**: a git write
  (`commit`, `branch -d`, `stash pop`, ...) is never blocked, and ambiguous read forms like
  `git branch --contains X` pass rather than risk blocking a write.
- **Add a false-positive escape hatch:** the `find -exec`/`-delete` and `cat >`/heredoc carve-outs show
  the pattern, add your own `continue` guard in the same loop.
- **Loosen the write side:** if routing every `Out-File`/`Set-Content` to `text-edit` is too aggressive
  for your workflow, drop that line from the in-place block.
- **Reword a redirect message:** edit `$searchMsg` / `$editMsg` / `$gitMsg`. Keep them concrete (name the
  tool and a call); the message is the whole point of the hook.

The hook fails **open**: any parse error, missing Perl/`JSON::PP` (bash), or an unexpected fault exits
0 so a legitimate command is never broken. It runs the interpreter once per shell call
(`powershell.exe`, or `bash` + `perl`), a small startup cost; the `if` filter field cannot express
"command contains grep", so there is no cheaper pre-filter.

## block-secrets

A second `PreToolUse` hook: it denies a command that would **read or copy a file that looks like a
secret** (`.env`, `appsettings.json`, `secrets.*`, `credentials.*`, `*.key`, `*.pem`, `*.pfx`, `*.p12`,
`*.jks`, `*.keystore`, `master.key`, `private_key`, `.htpasswd`). This is defense-in-depth next to
`route-to-text-tools`: that hook routes reads to `text-search` (which withholds secret-shaped content),
while this one hard-blocks the shell commands that would read or exfiltrate a secret file directly.

### What it blocks, and what it does not

A command is denied only when all three hold: it names a secret-file pattern, it is **not** the
`.example`/`.template`/`.sample` form, and it uses a content-reading or copying construct.

| Command | Verdict |
|---|---|
| `cat .env`, `Get-Content secrets.yaml`, `sed -n 1p .env`, `head master.key` | deny (reads a secret) |
| `cp secrets.json ...`, `cat .env > out`, `curl -d @credentials.json`, `. ./secrets.env` | deny (copy / redirect / source / exfil) |
| `cat .env.example`, `cat config.sample.json` | **allow** (sample/template) |
| `grep FOO .env`, `git status`, `cat application.json`, `ls` | **allow** (not a content read of a secret) |

`grep .env` passes this hook (grep is not a content-read here); the routing hook handles `grep`
separately, and `text-search` itself withholds secret content.

### Install

Same mechanics as `route-to-text-tools` above: copy the script for your OS (`block-secrets.ps1` on
Windows, `block-secrets.sh` on macOS/Linux) to `~/.claude/hooks/`, and add a **second** hook group
under `hooks.PreToolUse` with matcher `Bash|PowerShell` pointing at it (exec-form `powershell.exe` +
`-File` on Windows; `bash "$HOME/.claude/hooks/block-secrets.sh"` on POSIX). The two hooks are separate
groups and both run; if either denies, the command is blocked. Requirements are identical (Windows
`powershell.exe`; macOS/Linux `bash` + `perl` with `JSON::PP` core, nothing to install), and it fails
open.

> The original in-use version of this hook depended on `jq`, which is not installed by default on
> macOS/Ubuntu (nor in this machine's Git Bash). When `jq` is absent that version silently allows
> everything. This repo version parses with Perl instead, so it enforces with nothing to install.

### Verify

```bash
s=~/.claude/hooks/block-secrets.sh
bash "$s" --command 'cat .env'          # -> secret
bash "$s" --command 'cat .env.example'  # -> allow
bash "$s" --command 'grep FOO .env'     # -> allow
```

PowerShell: pipe a `{"tool_name":"Bash","tool_input":{"command":"cat .env"}}` payload into
`powershell.exe -File block-secrets.ps1`; a deny prints the JSON, allow prints nothing.

### Tuning

Edit the `SECRET` / `SAFE` / `READEXFIL` regexes (`.sh`) or `$secret` / `$safe` / `$readExfil` (`.ps1`)
to add file patterns or reader commands; keep both scripts in sync. The `.sh` uses BSD-grep-safe
character classes (no `\b`/`\w`) so it runs on macOS; the `.ps1` uses .NET `\b`/`\w`.
