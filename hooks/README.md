# Hooks

Enforcement hooks that back the always-on rules in `../skills/brain/knowledge/`. A rule in a knowledge file is
probabilistic: it only fires if the model recalls it at the moment a reflex fires, and the reflex is
strongest exactly where recall is weakest (fresh chat, long context, deep in a task). A hook does not
depend on recall. It intercepts the tool call after the model emits it and before it runs, and its
denial message lands in context at the one moment it steers the next attempt.

This folder holds five independent hooks, each shipped as a Windows `.ps1` and a POSIX `.sh` with
identical behavior, each failing open. Four are `PreToolUse`: three match the shell tools
(`Bash|PowerShell`), one matches the native file tools (`Glob|Grep|Read`). The fifth is
`PostToolUse`, matching the write tools (`Write|Edit`):
- **route-to-text-tools** routes file-probing, in-place-edit, and read-only-git shell commands to the
  `text-search`, `text-edit`, and `git-ops` MCPs.
- **block-secrets** hard-blocks shell commands that read or copy secret-looking files.
- **guard-file-targets** hard-blocks native `Glob`/`Grep`/`Read` calls that target a secret-looking
  file, so a secret cannot be located or read by stepping around the shell hooks.
- **block-vcs-writes** hard-blocks the git writes the user owns (`commit`, `add`, `stash`) and every
  `gh stack` subcommand except `view`.
- **warn-file-size** (PostToolUse) warns when a newly created `.py`/`.cs`/`.rs` file is written past
  its language's "worth reviewing" line tier. It never blocks and stays silent for files already
  tracked in git.

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
[`../skills/brain/knowledge/text-search-operations.md`](../skills/brain/knowledge/text-search-operations.md),
[`../skills/brain/knowledge/text-edit-operations.md`](../skills/brain/knowledge/text-edit-operations.md), and
[`../skills/brain/knowledge/git-readonly-operations.md`](../skills/brain/knowledge/git-readonly-operations.md).

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
| `jq '.key' file` leading a stage, `jq . < file`, `jq -n` with `--slurpfile`/`--argfile`/`-f`/`inputs`                  | deny      | `read_json`                            |
| `python -c`/`node -e` one-liners that open a file (`open(`, `read_text`, `readFile*`)                                  | deny      | `read_json` / `read_lines`             |
| `sed -i`, `perl -pi -e`, `Set-Content`/`Add-Content`/`Out-File`                                                        | deny      | `replace_text` / `normalize_files`     |
| `git grep`/`log`/`diff`/`show`/`status`/`blame`/`ls-files`, `git branch` (list), `git reflog`, `git stash list`/`show` | deny      | `git-ops` (`git_grep`, `git_log`, ...) |
| `git commit`/`add`/`push`/`checkout`/`reset`/`merge`, `git branch -d`, `git stash pop`, `git tag <name>`               | **allow** | shell git is fine for writes           |
| `dotnet test \| tail -20`, `curl ... \| jq '.x'` (downstream of a pipe)                                                | **allow** | output trimming, not probing           |
| `jq -n '{...}'` (null input, no file flags), `python3 -c "print(1+2)"` (no file-open token)                            | **allow** | constructs JSON / computes, no read    |
| `cat > file <<EOF` (redirect/heredoc), `find ... -delete`/`-exec`                                                      | **allow** | authoring / acting, not reading        |
| `ls -r` (reverse sort, not `-R`), plain `ls`/`dir`/`Get-ChildItem`                                                     | **allow** | not a recursive walk                   |

The one nuance worth understanding: only a command **leading** a pipeline stage is treated as reading
files. A read filter downstream of a `|` is consuming another command's stdout (output trimming), which
the knowledge files explicitly exempt. Statements are split on `&&`, `||`, `;`, and newlines first, so
`build && grep TODO src` still denies the `grep` even though it is not the first word overall.

Interpreter one-liners are the one probe matched against the whole command instead of a pipeline
stage: quotes hide `;` from that statement splitter, so `python3 -c "import json; ..."` would
otherwise be cut mid-payload. Two signals must both hit before a deny: an eval flag (`-c`, `-e`,
`--eval`) after a `python`/`py`/`node` word, and a file-open token (`open(`, `read_text`,
`readFile*`) anywhere in the command. That keeps compute one-liners and `json.load(sys.stdin)`
pipe filters out of it.

Accepted residue, on purpose: ruby/php/perl one-liners, python heredoc scripts (`python <<EOF`),
`node -e "require('./cfg.json')"`, and `jq '.' file --args -n` flag-lookalikes still pass; on the
false-positive side, `python -c "open('f','w')..."` authoring and a `-n` jq filter containing `<`
deny. The hook is a nudge, not a wall (see the note at the top of this file); `block-secrets`,
`guard-file-targets`, and text-search's own denylist and content scan hold independently.

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
so `grep` and `Get-Content` reflexes are both caught. Both scripts carry identical logic and
behavior; keep them in sync when you tune one.

### Verify

All five hooks run together from the repo root with `bash tools/test-hooks.sh`: it parses every
script, guards against the command-substitution heredoc that broke them on macOS bash 3.2, checks the
file-size thresholds stay in sync across hooks and gates, and checks every verdict in the tables
above. On Windows, `tools\test-hooks.ps1` runs the `.ps1` hooks against the same case table (see
`../tools/README.md`). The hand checks below exercise just this hook.

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
bash "$s" --command 'jq .version package.json' # -> search
bash "$s" --command 'jq -n {}'               # -> allow
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
- **Interpreter one-liners:** the python/node branch sits with the whole-command pre-checks
  (next to `sed -i`/`perl -i`), not in the stage loop, because quotes hide `;` from the statement
  splitter. Tune the interpreter names, eval flags, or file-open tokens there, in both scripts.
  The jq null-input carve-out and its file-flag kill list live in the stage loop beside the
  `cat`/`find` carve-outs.
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
while this one hard-blocks the shell commands that would read or exfiltrate a secret file directly. It is
shell-only (matcher `Bash|PowerShell`) and blocks reading or copying, not merely locating; the native
`Glob`/`Grep`/`Read` tools and pure enumeration are covered by `guard-file-targets` below.

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

The full harness for all five hooks runs from the repo root with `bash tools/test-hooks.sh` (on
Windows, `tools\test-hooks.ps1` runs the `.ps1` side against the same case table); the hand checks
below exercise just this one.

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

## guard-file-targets

The third `PreToolUse` hook, and the only one that matches the **native** tools rather than the shell:
its matcher is `Glob|Grep|Read`. It denies a call whose **target** is a secret-looking file (`.env`,
`appsettings.json`, `secrets.*`, `credentials.*`, `*.key`, `*.pem`, `*.pfx`, `*.p12`, `*.jks`,
`*.keystore`, `master.key`, `private_key`, `.htpasswd`) and lets everything else through.

The motivating incident: on a fresh chat in a monorepo the model reached for `Glob("**/.env*")` to find
where a shared `.env` lived, telling itself "I won't read the contents, only find the file." Both shell
hooks missed it, they match `Bash|PowerShell` and the model never shelled out, and `block-secrets` would
not have caught it even on the shell path: it blocks reading or copying a secret, not locating one. This
hook closes both gaps. It watches the native tools the shell hooks cannot see, and because it keys on the
**target** rather than on a read construct, it denies pure enumeration too. It also codifies the
principle the model rationalized around: seeking a secret is off-limits, not only reading it.

### What it blocks, and what it does not

It inspects only the fields that name a **file target**, per tool, and denies when that target matches a
secret-file pattern and is not the `.example`/`.template`/`.sample` form.

| Tool   | Fields inspected  | Deliberately ignored                     |
|--------|-------------------|------------------------------------------|
| `Glob` | `pattern`, `path` | (none)                                   |
| `Grep` | `glob`, `path`    | `pattern` (a content regex, not a path)  |
| `Read` | `file_path`       | (none)                                   |

| Call                                                                                     | Verdict   |
|------------------------------------------------------------------------------------------|-----------|
| `Glob("**/.env*")`, `Read(".env")`, `Read("config/secrets.yaml")`, `Grep(glob:"**/*.pem")` | deny (secret target) |
| `Read(".env.example")`, `Glob("*.sample.json")`                                          | **allow** (sample/template) |
| `Grep(pattern:"DATABASE_URL", path:"src")`                                               | **allow** (searching code for a string, no secret target) |
| `Read("docs/environment.md")`, `Glob("**/*.ts")`                                         | **allow** (not a secret target) |

The nuance worth understanding: `Grep`'s `pattern` is what you search *for*, a content regex, not a file
you point *at*, so it is deliberately ignored. Grepping the codebase for the string `DATABASE_URL` is
fine; globbing for `**/.env` is not. Only `Grep`'s `glob`/`path` name a target.

### Install

Same mechanics as the other two, but the matcher differs. Copy the script for your OS
(`guard-file-targets.ps1` on Windows, `guard-file-targets.sh` on macOS/Linux) to `~/.claude/hooks/`, and
add a **third** hook group under `hooks.PreToolUse` with matcher **`Glob|Grep|Read`** (not
`Bash|PowerShell`) pointing at it (exec-form `powershell.exe` + `-File` on Windows;
`bash "$HOME/.claude/hooks/guard-file-targets.sh"` on POSIX). Requirements are identical (Windows
`powershell.exe`; macOS/Linux `bash` + `perl` with `JSON::PP` core, nothing to install), and it fails
open.

### Verify

The full harness for all five hooks runs from the repo root with `bash tools/test-hooks.sh` (on
Windows, `tools\test-hooks.ps1` runs the `.ps1` side against the same case table); the hand checks
below exercise just this one.

The `.sh` has a `--candidate` self-test that classifies a raw target string (`secret`/`allow`) with
neither Perl nor Claude Code; the JSON stdin path needs Perl:

```bash
s=~/.claude/hooks/guard-file-targets.sh
bash "$s" --candidate '**/.env*'      # -> secret
bash "$s" --candidate '.env.example'  # -> allow
bash "$s" --candidate 'src/main.py'   # -> allow
echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' | bash "$s"  # -> deny JSON
echo '{"tool_name":"Grep","tool_input":{"pattern":".env"}}'   | bash "$s"  # -> (no output = allow)
```

PowerShell: pipe a `{"tool_name":"Glob","tool_input":{"pattern":"**/.env*"}}` payload into
`powershell.exe -File guard-file-targets.ps1`; a deny prints the JSON, allow prints nothing.

### Tuning

The `SECRET`/`SAFE` regexes (`.sh`) and `$secret`/`$safe` (`.ps1`) are the same shape as `block-secrets`;
keep all four in sync when you add a file pattern. To cover another native tool, add its name to the
matcher and a branch to the field selector (the `switch ($tool)` in `.ps1`, the `if`/`elsif` in the Perl
extractor in `.sh`) naming that tool's target field. Do **not** add `Grep`'s `pattern` to the selector:
it is a content regex, and inspecting it would deny legitimate code searches for strings like
`SECRET_KEY`.

## block-vcs-writes

The fourth `PreToolUse` hook, shell-matched (`Bash|PowerShell`) like the first two:
**`block-vcs-writes.ps1`** / **`block-vcs-writes.sh`**. It denies VCS state changes the agent must
never make, in two families:

- **git writes the user owns**: `commit`, `add`, and `stash` (except `stash list` / `stash show`).
  Where `route-to-text-tools` is deliberately biased toward allowing git writes, this hook encodes a
  policy: the user manages git, the agent never stages, commits, or stashes
  (`../skills/brain/knowledge/coding-general.md`, Version Control Hygiene). Don't install it if you
  want an agent that commits.
- **`gh stack` mutations**: every subcommand except `view`. Stacks are created, restructured, and
  submitted by the user; `view` is the one read the detection protocol needs
  (`../skills/brain/knowledge/github-pr-stacks.md`).

Statements are split on `&&`, `||`, `;`, `|`, and newlines, and a write anywhere in the command is
denied, so `build && git add -A` is caught. git global flags are tolerated (`git -C path commit`,
`git -c k=v commit`). Push, checkout, merge, and the other git writes stay allowed: those happen on
explicit request and still pass the permission prompt.

### What it blocks, and what it does not

| Command                                                                      | Verdict   |
|------------------------------------------------------------------------------|-----------|
| `git commit -m x`, `git add .`, `git stash`, `git stash pop`, `git -C sub commit` | deny (git write the user owns) |
| `gh stack submit`, `gh stack sync`, `gh stack modify`, `gh stack init`       | deny (stack mutation)          |
| `git stash list`, `git stash show stash@{0}`                                 | **allow** (read-only stash forms) |
| `git push`, `git checkout -b x`, `git merge`                                 | **allow** (user-requested writes; the permission prompt still applies) |
| `gh stack view --json`, bare `gh stack`, `gh pr create`                      | **allow** |

### Install

Same mechanics as the other shell hooks: copy the script for your OS to `~/.claude/hooks/` and add
another hook group under `hooks.PreToolUse` with matcher `Bash|PowerShell` pointing at it.
Requirements are identical (Windows `powershell.exe`; macOS/Linux `bash` + `perl` with `JSON::PP`
core), and it fails open. **Append** the group to the existing array; don't replace the other hooks.

**Windows** (exec-form, absolute `-File` path):

```jsonc
{
  "hooks": {
    "PreToolUse": [
      // ...existing hook groups stay as they are...
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\block-vcs-writes.ps1"
            ],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**macOS / Linux**:

```jsonc
{
  "hooks": {
    "PreToolUse": [
      // ...existing hook groups stay as they are...
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/block-vcs-writes.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
```

Reload afterwards: open `/hooks` once or restart Claude Code (a mid-session settings edit is not
picked up until then).

### Verify

The full harness for all five hooks runs from the repo root with `bash tools/test-hooks.sh` (on
Windows, `tools\test-hooks.ps1` runs the `.ps1` side against the same case table); the hand checks
below exercise just this one.

```bash
s=~/.claude/hooks/block-vcs-writes.sh
bash "$s" --command 'git commit -m x'       # -> git
bash "$s" --command 'git stash list'        # -> allow
bash "$s" --command 'gh stack submit'       # -> stack
bash "$s" --command 'gh stack view --json'  # -> allow
```

PowerShell: pipe a `{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}` payload into
`powershell.exe -File block-vcs-writes.ps1`; a deny prints the JSON, allow prints nothing.

### Tuning

The write lists live in the fragment loop: the `commit|add` pair, the `stash` branch (its
`list`/`show` carve-out), and the `gh stack` allowlist of one (`view`). To permit stashing, drop the
`stash` branch; to permit stack submission, you are better off uninstalling the hook. Keep both
scripts in sync.

## warn-file-size

The fifth hook, and the only `PostToolUse` one: its matcher is `Write|Edit`. The write has already
landed (a `PostToolUse` hook cannot block), so this one warns rather than denies: when a **newly
created** `.py`/`.cs`/`.rs` file exceeds its language's "worth reviewing" line tier (Python 800, C#
700, Rust 700; the tiers live in `coding-general.md` section 3), it prints a two-to-three line message
prefixed `[warn-file-size]` to stderr and exits 2, which Claude Code surfaces to the model. It is the
write-time nudge for `coding-general.md` Hard Rule 4, ahead of the diff-scoped size check each
language skill's `scripts` quality gate runs before handoff.

It is the only hook that reads file content: to count lines it opens the written file, under a byte
cap, and echoes back the count only, never any content. It stays silent for any file tracked at HEAD
(checked with `git ls-files`), so it warns on freshly created files and never nags edits to
pre-existing ones.

### What it warns on, and what it does not

A write is flagged only when all of these hold: the target has a `.py`/`.cs`/`.rs` extension, it is a
regular file (not a symlink or directory), its basename is not secret-looking (`secrets.*`,
`credentials.*`, `.env*`, `private_key*`, `master.key`), it is not tracked in git, and its line count
is at or over the language's tier.

| Write                                                                       | Verdict   |
|-----------------------------------------------------------------------------|-----------|
| a new 900-line `service.py`, 800-line `Parser.cs`, or 750-line `engine.rs`  | warn (exit 2, `[warn-file-size]` on stderr) |
| a new 200-line `service.py`; any `.md` / `.txt` / `.json` write             | **silent** (under tier, or not a gated extension) |
| an edit to a tracked 2,000-line file                                        | **silent** (tracked at HEAD, never newly created) |
| a new `secrets.py`, a `.env` write, or a missing/unreadable path            | **silent** (secret-skip, or fail-open) |

The `.rs` message adds a note that the diff-scoped gate subtracts the trailing `#[cfg(test)]` module,
so the raw count the hook reports can overstate the effective production size.

### Install

Same mechanics as the other hooks, but it registers under `hooks.PostToolUse` (not `PreToolUse`) with
matcher **`Write|Edit`**. Copy the script for your OS (`warn-file-size.ps1` on Windows,
`warn-file-size.sh` on macOS/Linux) to `~/.claude/hooks/` and add a hook group under
`hooks.PostToolUse`:

**Windows**:

```jsonc
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\warn-file-size.ps1"
            ],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**macOS / Linux**:

```jsonc
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/warn-file-size.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
```

Requirements match the other hooks (Windows `powershell.exe`; macOS/Linux `bash` + `perl` with
`JSON::PP`), plus `git` on PATH; without git the hook fails open and warns nothing. The `.sh` also
uses `awk`, `head`, and `dirname`, all POSIX.

### Threshold sync

The three warn thresholds are named constants at the top of the scripts (`WARN_PY` / `WARN_CS` /
`WARN_RS` in the `.sh`, `$warn` in the `.ps1`). They mirror `SIZE_WARN_THRESHOLD` in each language
skill's `scripts` quality gate and the tiers in `coding-general.md` section 3. Retuning a tier means
changing it in all three places, so the write-time nudge and the diff-scoped gate agree. The sync is
also enforced: `tools/test-hooks.sh` extracts these constants from both hook scripts and the three
gates and cross-compares them, so a missed spot fails the harness instead of drifting silently.

### Verify

`bash tools/test-hooks.sh` covers this hook alongside the four `PreToolUse` ones, and on Windows
`tools\test-hooks.ps1` runs the `.ps1` against the same case table. The cases build real oversized
and small fixture files, since the hook grades the file it reads, and two of them pin the
secret-skip anchoring: a secret basename under a sample-named parent directory stays skipped, while
the in-basename sample form is counted. The `.sh` has a `--check`
self-test that classifies a path without JSON stdin or Claude Code:

```bash
s=~/.claude/hooks/warn-file-size.sh
bash "$s" --check new_big_module.py   # -> warn (untracked, gated extension, over tier)
bash "$s" --check small.py            # -> silent
```

Piping a `{"tool_name":"Write","tool_input":{"file_path":"..."}}` payload into the script warns with
exit 2 and a `[warn-file-size]` line on stderr, or exits 0 silently.

### Tuning

- **Thresholds:** `WARN_PY` / `WARN_CS` / `WARN_RS` (`.sh`) or `$warn` (`.ps1`); keep them in sync
  with the gates (see Threshold sync).
- **Gated extensions:** the `threshold_for` `case` (`.sh`) or the `$warn` keys (`.ps1`).
- **Byte cap:** `BYTE_CAP` / `$byteCap`, the most bytes read before counting stops.
- **Secret skip:** the `SECRET` / `SAFE` regexes (`.sh`) or `$secret` / `$safe` (`.ps1`); keep both
  scripts in sync.

The hook fails **open**: a missing `git`/`perl`, an unreadable file, a parse error, or any fault exits
0 and warns nothing, so it never interferes with a write.

## Protected MCP stores (guard-file-targets + block-secrets)

`guard-file-targets` and `block-secrets` each carry a `PROTECTED_STORES` tunable (`$protectedStores`
in the `.ps1`s): a regex matching the on-disk backing stores owned by MCP servers (the vault's
storage, the text-edit journal). It is empty by default, a no-op until configured, because store
locations are machine config. When set, `guard-file-targets` denies any native `Glob`/`Grep`/`Read`
whose target matches, and `block-secrets` denies any shell command naming a match, read construct or
not: the stores are tool-only (`../skills/brain/knowledge/vault-operations.md`, Hard Rules), so a
shell command naming one has no legitimate use. Set the same regex in all four scripts. This is the
portable enforcement; for a hard wall, put the store under filesystem permissions the agent's
process cannot read.

## Full install: all five hooks at once

For a fresh machine, copy the five scripts for your OS into `~/.claude/hooks/`, then paste the
whole `hooks` block below into `~/.claude/settings.json` (merge it if the file already has other
keys). Each hook is its own group; every group runs on each matching tool call, a deny from any
`PreToolUse` group blocks the call, and the `PostToolUse` `warn-file-size` group only warns after the
write. Reload with `/hooks` or a restart when done.

**Windows**:

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
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\block-secrets.ps1"
            ],
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\block-vcs-writes.ps1"
            ],
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Glob|Grep|Read",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\guard-file-targets.ps1"
            ],
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": [
              "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
              "-File", "C:\\Users\\<you>\\.claude\\hooks\\warn-file-size.ps1"
            ],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**macOS / Linux**:

```jsonc
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/route-to-text-tools.sh\"", "timeout": 10 }
        ]
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/block-secrets.sh\"", "timeout": 10 }
        ]
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/block-vcs-writes.sh\"", "timeout": 10 }
        ]
      },
      {
        "matcher": "Glob|Grep|Read",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/guard-file-targets.sh\"", "timeout": 10 }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.claude/hooks/warn-file-size.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
```

After copying (and again after an OS or bash upgrade that changes `/bin/bash`), point the test harness
at the installed copies to confirm they still parse and behave, using the directory you copied them
into: `bash tools/test-hooks.sh --hooks-dir ~/.claude/hooks`.

Skipping a hook is fine (each is independent); just drop its group. If you use `block-vcs-writes`
but want the agent able to commit on some machine, leave that one group out there rather than
tuning the script.
