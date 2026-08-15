# Security hardening for the global config

Here we show a suggestion of how to set up a hardened Claude Code global config (`~/.claude/settings.json`) from scratch,
in a way that will work with this skill set.

Feel free to adjust the settings to your needs, or ignore it completely, if you want to. 
I bet you know what you're doing, and you'll be fine.

In any case, here's my suggestion...

## The one thing to know first

Claude Code's `settings.json` **silently ignores unknown top-level keys**. A block named `fileAccess`,
`blockedCommands`, `secretDetection`, `environment`, or `network` looks protective but does nothing,
because those key names are not in the settings schema. The root object accepts unknown keys and drops them.

> [!NOTE]
> This is true for personal settings. Enterprise settings are validated against the schema.
> More information about the schema can be found [here](https://code.claude.com/docs/en/settings).

Security has to go through the mechanisms Claude Code actually reads:
- **`permissions`** (`allow` / `deny` / `ask`), matched per tool: `Read(...)`, `Bash(...)`, `Edit(...)`, `WebFetch(...)`.
- **`hooks`** (`PreToolUse`), which inspect a tool call and can deny it. The sturdiest option, because a hook sees the whole command.
- **`sandbox`**, for OS-level filesystem / network / env-var isolation (a larger, behavior-changing switch).

Two coverage facts that drive everything below:

- A `Read(**/.env)` deny gates the **Read tool only**. It does **not** stop `cat .env` in Bash. The Bash path needs a hook.
- The `text-search` MCP server has its own non-overridable secret denylist and content scan, so agent reads 
*through text-search* are already protected regardless of this file.

## 1. Permissions: MCP allow list and secret deny list

`permissions` is the core of the config. `allow` auto-approves the read-only tools you trust so you are
not prompted constantly; `deny` blocks the **Read tool** from opening secret files. A complete block for
a clean install (settings.json is strict JSON, so no comments in the real file):

```json
{
  "permissions": {
    "allow": [
      "mcp__git-ops",
      "mcp__vault",
      "mcp__text-search",
      "mcp__os-doctor",
      "Read(~/.claude/skills/**)"
    ],
    "deny": [
      "Read(**/.env)",
      "Read(**/.env.local)",
      "Read(**/.env.*.local)",
      "Read(**/appsettings.json)",
      "Read(**/appsettings.*.json)",
      "Read(**/secrets.json)",
      "Read(**/secrets.yaml)",
      "Read(**/secrets.yml)",
      "Read(**/credentials.json)",
      "Read(**/credentials.yaml)",
      "Read(**/credentials.yml)",
      "Read(**/service-account*.json)",
      "Read(**/master.key)",
      "Read(**/*.key)",
      "Read(**/*.pem)",
      "Read(**/*.pfx)",
      "Read(**/*.p12)",
      "Read(**/*.p8)",
      "Read(**/*.pkcs12)",
      "Read(**/*.jks)",
      "Read(**/*.keystore)",
      "Read(**/*.ppk)",
      "Read(**/*-key.json)",
      "Read(**/id_rsa*)",
      "Read(**/id_ed25519*)",
      "Read(**/id_ecdsa*)",
      "Read(**/id_dsa*)",
      "Read(**/.ssh/**)",
      "Read(**/.aws/**)",
      "Read(**/.kube/**)",
      "Read(**/.gnupg/**)",
      "Read(**/.azure/**)",
      "Read(**/.config/gcloud/**)",
      "Read(**/.netrc)",
      "Read(**/.git-credentials)",
      "Read(**/.npmrc)",
      "Read(**/.pypirc)",
      "Read(**/.htpasswd)",
      "Read(**/.pgpass)",
      "Read(**/.cargo/credentials*)",
      "Read(**/*.tfstate)",
      "Read(**/*.tfstate.backup)",
      "Read(**/*.tfvars)",
      "Read(**/*.ovpn)",
      "Read(**/.bash_history)",
      "Read(**/.zsh_history)",
      "Read(**/.python_history)",
      "Read(**/.psql_history)",
      "Read(**/.mysql_history)",
      "Bash(sudo *)",
      "Bash(su *)",
      "Bash(rm -rf *)",
      "Bash(rm -fr *)",
      "Bash(dd *)",
      "Bash(mkfs *)",
      "Bash(shutdown *)",
      "Bash(reboot *)"
    ]
  }
}
```

Notes:
- `text-edit` is deliberately absent from `allow`; keep write tools on prompt.
- Drop any `allow` entry for an MCP server you do not run (an unused entry is harmless but pointless).
- The deny list targets secret variants (`.env`, `.env.local`) rather than a blanket `.env.*`, so a
  non-secret `.env.example` stays readable. Add `Read(**/.env.*)` if you want the stricter, coarser block.
- These are read defaults, not a wall: they gate the Read tool, so a `*.key` or `.npmrc` you legitimately
  need to read is blocked too. Loosen a specific pattern if it gets in your way. The Bash path is
  covered separately in the next section.

## 2. Install the enforcement hooks (covers the Bash path)

`permissions` cannot stop `cat .env` in Bash; a hook can. `hooks/` (at the repo root) ships four
`PreToolUse` hooks (`hooks/README.md` documents the scripts and per-OS install, including
`guard-file-targets` for the native file tools and `block-vcs-writes` for git/`gh stack` writes).
Copy the script for your OS into `~/.claude/hooks/`, then add one group per hook under
`hooks.PreToolUse`; the two shell groups below show the pattern:

Windows (exec-form, absolute `-File` path):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "powershell.exe",
            "args": ["-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File","C:\\Users\\<you>\\.claude\\hooks\\block-secrets.ps1"],
            "timeout": 10 }
        ]
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command", "command": "powershell.exe",
            "args": ["-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File","C:\\Users\\<you>\\.claude\\hooks\\route-to-text-tools.ps1"],
            "timeout": 10 }
        ]
      }
    ]
  }
}
```

macOS / Linux: use `bash` instead, one hook per group:

```json
{ "type": "command", "command": "bash \"$HOME/.claude/hooks/block-secrets.sh\"", "timeout": 10 }
{ "type": "command", "command": "bash \"$HOME/.claude/hooks/route-to-text-tools.sh\"", "timeout": 10 }
```

- **block-secrets** hard-blocks commands that read or copy secret files (the Bash counterpart to the
  Read deny list above).
- **route-to-text-tools** redirects file reads/searches, in-place edits, and read-only `git` to the
  `text-search`, `text-edit`, and `git-ops` MCPs.
- The `.sh` versions parse JSON with Perl (present by default on macOS/Ubuntu), so there is nothing to
  install.
- If you already keep other `PreToolUse` hooks, append to the array rather than replacing it.

## 3. Discourage dangerous Bash commands

There is no `blockedCommands` key. To restrict commands you either add `Bash(...)` deny rules or use a
hook. Deny rules are prefix-matched and **bypassable** (`bash -c "sudo ..."`, `env sudo`, a wrapper
script), so treat them as a speed bump, not a wall. A practical baseline, added to `permissions.deny`:

```json
"Bash(sudo *)", "Bash(su *)", "Bash(rm -rf *)", "Bash(rm -fr *)",
"Bash(dd *)", "Bash(mkfs *)", "Bash(shutdown *)", "Bash(reboot *)"
```

For real enforcement of a command class, model it as a `PreToolUse` hook the way `route-to-text-tools`
does: inspect the full command string and deny with a reason. A hook sees the whole command, so a
`bash -c` wrapper does not slip past it, and one hook with matcher `Bash|PowerShell` covers both shell
tools.

## 4. (Optional, advanced) Sandbox for env vars, network, and filesystem

Env-var hiding, network egress limits, and OS-level filesystem isolation exist only under the real
`sandbox` key, and turning it on changes how commands run. If you want any of that, express it here and
test against your normal workflow first:

```json
"sandbox": {
  "enabled": true,
  "network": { "allowedDomains": ["github.com", "crates.io", "pypi.org", "nuget.org"] },
  "filesystem": { "denyRead": ["~/.ssh/**", "~/.aws/**", "~/.gnupg/**", "~/.config/gcloud/**"] },
  "credentials": {
    "envVars": [
      { "name": "AWS_SECRET_ACCESS_KEY", "mode": "deny" },
      { "name": "AWS_ACCESS_KEY_ID", "mode": "deny" },
      { "name": "ANTHROPIC_API_KEY", "mode": "deny" }
    ]
  }
}
```
> [!IMPORTANT]
> When allowing a domain, remember that a legitimate domain can contain poisoned/malicious code instructions. 
Especially GitHub, so be careful!


## 5. Keys that look like security but do nothing

Configs shared online often set keys like these, expecting them to lock things down. Claude Code ignores
unknown top-level keys in personal settings, so they provide **no** protection. Do not add them and
count on them; use the mechanisms above instead:

`allowedCommands`, `blockedCommands`, `fileAccess`, `environment`, `network` (the real one is
`sandbox.network`), `codeExecution`, `platformSpecific`, `logging`, `notifications`, `secretDetection`,
`projectSettings`, `developerMode`.

I'm adding this here because some times we might copy/paste things from online configs, and even Claude Code can suggest
and/or add those to the settings when you ask to make things more secure.

## Putting it together

A hardened clean-install `settings.json` is just the `permissions` block (section 1, plus the optional
`Bash(...)` rules from section 3), the `hooks` block (section 2), and your normal preferences (`model`,
`effortLevel`, `enabledPlugins`, and so on) as siblings in one JSON object. The `sandbox` block
(section 4) is optional.

## Verify

The settings watcher does not pick up mid-session edits to `~/.claude/settings.json`, so open `/hooks`
once or restart Claude Code. Then spot-check:

- `cat .env` in Bash is denied (secrets hook).
- `grep -r foo .` is redirected to text-search (routing hook).
- Reading `~/.ssh/id_rsa` with the Read tool is denied (permission rule).

If a check does not fire, the config likely has not reloaded yet; reopen `/hooks` or restart.
