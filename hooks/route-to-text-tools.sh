#!/usr/bin/env bash
# PreToolUse hook for the Bash and PowerShell tools (POSIX / macOS / Linux port of
# route-to-text-tools.ps1; Windows uses the .ps1). JSON in/out is handled by Perl with JSON::PP, a
# core module present on stock macOS and Ubuntu, so there is nothing to install.
#
# Deny shell commands whose purpose is to read/search files on disk (route to the text-search MCP),
# rewrite file content in place (route to text-edit), or inspect a repo read-only through shell git
# (route to git-ops). Everything else passes. A read filter that only consumes ANOTHER command's
# piped output (`dotnet test | tail -20`) is output trimming, not probing, and is allowed: only a
# command LEADING a pipeline stage is treated as reading files.
#
# Fails OPEN: missing Perl/JSON::PP, a parse error, or any fault exits 0 so a legitimate command is
# never broken. Self-test without Perl or Claude Code:  bash route-to-text-tools.sh --command "grep -r foo ."
# See hooks/README.md for install and tuning.

IFS= read -r -d '' SEARCH_MSG <<'MSG'
Blocked: this shell command reads or searches files on disk, which bypasses the .gitignore and secret guards (this is exactly what leaked a gitignored file before). Use the text-search MCP instead (blanket-approved, read-only, ignore- and secret-aware), scoped with cwd = the repo's absolute path:
  grep / rg            -> search_text
  cat / head / tail    -> read_lines
  find / ls -R / dir /s -> find_files
  file / encoding      -> inspect_files
For paths the native Read / Grep / Glob tools reach, those are fine too. See brain/knowledge/text-search-operations.md.
Exempt (NOT blocked): piping a command's OWN output through grep/head/tail, e.g. `dotnet test | tail -20`. If that was the intent, re-run it in that shape.
MSG
SEARCH_MSG=${SEARCH_MSG%$'\n'}

IFS= read -r -d '' EDIT_MSG <<'MSG'
Blocked: this rewrites file content through the shell, which is banned. For a pattern edit across files use the text-edit MCP: replace_text (dry_run: true first, then the real run gated with expected_match_count) or normalize_files, scoped with cwd = the repo's absolute path. For one hand-shaped edit use the native Edit tool; for a brand-new file use the native Write tool. See brain/knowledge/text-edit-operations.md.
MSG
EDIT_MSG=${EDIT_MSG%$'\n'}

IFS= read -r -d '' GIT_MSG <<'MSG'
Blocked: read-only git inspection goes through the git-ops MCP, not the shell (a shell `git log` / `git grep` is exactly the case the rule targets). Use these with cwd = the repo's absolute path:
  git grep -> git_grep (fixedString:false for regex)    git log -> git_log
  git diff -> git_diff    git show -> git_show    git status -> git_status    git blame -> git_blame
  git ls-files -> git_ls_files    git branch -> git_branch_list    git reflog -> git_reflog
  git stash list/show -> git_stash_list / git_stash_show
Shell git stays fine for WRITES (commit, add, push, checkout, reset, merge, rebase, tag, fetch, pull). See brain/knowledge/git-readonly-operations.md.
MSG
GIT_MSG=${GIT_MSG%$'\n'}

# The bare command word leading one pipeline stage.
lead_word() {
    local s="$1" tok
    s="${s#"${s%%[![:space:]]*}"}"
    while printf '%s' "$s" | grep -qE '^(sudo|env|command|time|nice|nohup)[[:space:]]'; do
        s="$(printf '%s' "$s" | sed -E 's/^(sudo|env|command|time|nice|nohup)[[:space:]]+//')"
    done
    s="$(printf '%s' "$s" | sed -E 's/^[({!]+//')"
    s="${s#"${s%%[![:space:]]*}"}"
    while printf '%s' "$s" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]'; do
        s="$(printf '%s' "$s" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+//')"
    done
    tok="${s%%[[:space:]]*}"
    tok="${tok%\"}"; tok="${tok#\"}"; tok="${tok%\'}"; tok="${tok#\'}"
    tok="${tok##*/}"; tok="${tok##*\\}"
    tok="$(printf '%s' "$tok" | sed -E 's/\.[Ee][Xx][Ee]$//')"
    printf '%s' "$tok" | tr '[:upper:]' '[:lower:]'
}

# For a stage led by `git`, return 0 if it is a read-only subcommand to redirect, 1 otherwise.
# Biased toward allow: a git write is never redirected.
git_readonly() {
    local s="$1" first sub rest idx tk hasPos hasWrite
    s="${s#"${s%%[![:space:]]*}"}"
    while printf '%s' "$s" | grep -qE '^(sudo|env|command|time|nice|nohup)[[:space:]]'; do
        s="$(printf '%s' "$s" | sed -E 's/^(sudo|env|command|time|nice|nohup)[[:space:]]+//')"
    done
    s="$(printf '%s' "$s" | sed -E 's/^[({!]+//')"
    s="${s#"${s%%[![:space:]]*}"}"
    while printf '%s' "$s" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]'; do
        s="$(printf '%s' "$s" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+//')"
    done
    local W; read -ra W <<< "$s"
    [ "${#W[@]}" -ge 1 ] || return 1
    first="${W[0]##*/}"; first="${first##*\\}"
    first="$(printf '%s' "$first" | sed -E 's/\.[Ee][Xx][Ee]$//' | tr '[:upper:]' '[:lower:]')"
    [ "$first" = git ] || return 1
    idx=1
    while [ "$idx" -lt "${#W[@]}" ]; do
        case "${W[$idx]}" in
            -C|-c) idx=$((idx + 2)) ;;
            -*)    idx=$((idx + 1)) ;;
            *)     break ;;
        esac
    done
    [ "$idx" -lt "${#W[@]}" ] || return 1
    sub="$(printf '%s' "${W[$idx]}" | tr '[:upper:]' '[:lower:]')"
    rest="${W[*]:$((idx + 1))}"
    case "$sub" in
        grep|log|status|diff|show|blame|ls-files) return 0 ;;
        reflog)
            printf '%s' "$rest" | grep -qiE '^[[:space:]]*(expire|delete)([^A-Za-z]|$)' && return 1
            return 0 ;;
        stash)
            printf '%s' "$rest" | grep -qiE '^[[:space:]]*(list|show)([^A-Za-z]|$)' && return 0
            return 1 ;;
        branch)
            hasPos=0
            for tk in $rest; do case "$tk" in -*) ;; *) hasPos=1; break ;; esac; done
            hasWrite=0
            printf '%s' " $rest " | grep -qE '[[:space:]](-d|-D|--delete|-m|-M|--move|-c|-C|--copy|--set-upstream-to|--unset-upstream|--edit-description|-f|--force|-u|--set-upstream|--track|--no-track)([[:space:]]|=|$)' && hasWrite=1
            [ "$hasPos" -eq 0 ] && [ "$hasWrite" -eq 0 ] && return 0
            return 1 ;;
        *) return 1 ;;
    esac
}

# Classify a command: echoes search|edit|git, or nothing for allow.
classify() {
    local command="$1" sentinel stmt stage0 lw tk
    # In-place / content-write (any position) -> edit.
    printf '%s' "$command" | grep -qiE '(^|[^A-Za-z0-9_])sed([^|;&]*)[[:space:]]-i'          && { echo edit; return; }
    printf '%s' "$command" | grep -qE  '(^|[^A-Za-z0-9_])perl[[:space:]]+-[a-z]*i'            && { echo edit; return; }
    printf '%s' "$command" | grep -qiE '(^|[^A-Za-z0-9_])(Set-Content|Add-Content|Out-File)([^A-Za-z0-9_]|$)' && { echo edit; return; }
    # Recursive directory listings -> search.
    printf '%s' "$command" | grep -qE  '(^|[^A-Za-z0-9_])ls([^|;&]*)[[:space:]]-[A-Za-z]*R'   && { echo search; return; }   # ls -R (not ls -r)
    printf '%s' "$command" | grep -qiE '(^|[^A-Za-z0-9_])dir([^|;&]*)[[:space:]]/s([^A-Za-z0-9_]|$)' && { echo search; return; }
    printf '%s' "$command" | grep -qiE '(^|[^A-Za-z0-9_])(Get-ChildItem|gci)([^|;&]*)[[:space:]]-r' && { echo search; return; }
    printf '%s' "$command" | grep -qiE '(^|[^A-Za-z0-9_])ls([^|;&]*)[[:space:]]-recurse([^A-Za-z0-9_]|$)' && { echo search; return; }

    # Split into statements on && || ; and newlines, keeping only each statement's first pipeline
    # stage (the producer); a read filter downstream of a pipe is output trimming, allowed.
    sentinel=$'\x01'
    local tmp="$command"
    tmp="${tmp//&&/$sentinel}"
    tmp="${tmp//||/$sentinel}"
    tmp="${tmp//;/$sentinel}"
    tmp="${tmp//$'\n'/$sentinel}"
    local STMTS; IFS="$sentinel" read -ra STMTS <<< "$tmp"
    for stmt in "${STMTS[@]}"; do
        stage0="${stmt%%|*}"
        lw="$(lead_word "$stage0")"
        [ -n "$lw" ] || continue
        case " grep egrep fgrep rg ripgrep ag ack cat tac head tail find fd sed awk gawk select-string sls get-content gc " in
            *" $lw "*)
                if { [ "$lw" = cat ] || [ "$lw" = tac ]; } && printf '%s' "$stage0" | grep -qE '(>|>>|<<)'; then continue; fi
                if [ "$lw" = find ] && printf '%s' "$stage0" | grep -qE '[[:space:]]-(exec|execdir|delete|ok)([^A-Za-z]|$)'; then continue; fi
                echo search; return ;;
            *)
                if [ "$lw" = git ] && git_readonly "$stage0"; then echo git; return; fi ;;
        esac
    done
}

emit_deny() {
    MSG="$1" perl -MJSON::PP -e 'print encode_json({hookSpecificOutput=>{hookEventName=>"PreToolUse",permissionDecision=>"deny",permissionDecisionReason=>$ENV{MSG}}});' 2>/dev/null
}

# --- main ---
if [ "$1" = "--command" ]; then
    v="$(classify "$2")"
    printf '%s\n' "${v:-allow}"
    exit 0
fi

cmd="$(perl -MJSON::PP -0777 -ne 'my $d=eval{decode_json($_)}; exit unless $d; my $c=$d->{tool_input}{command}; print $c if defined $c;' 2>/dev/null)"
[ -n "$cmd" ] || exit 0

case "$(classify "$cmd")" in
    search) emit_deny "$SEARCH_MSG" ;;
    edit)   emit_deny "$EDIT_MSG" ;;
    git)    emit_deny "$GIT_MSG" ;;
esac
exit 0
