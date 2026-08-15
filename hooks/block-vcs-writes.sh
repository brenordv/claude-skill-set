#!/usr/bin/env bash
# PreToolUse hook for the Bash and PowerShell tools: block VCS state changes the agent must never
# make. Two families: git writes the user owns (commit, add, stash except list/show), and every
# `gh stack` subcommand other than `view` (stack creation/mutation is the user's responsibility).
# POSIX port of block-vcs-writes.ps1 (Windows uses the .ps1). JSON in/out is handled by Perl with
# JSON::PP, a core module present on stock macOS and Ubuntu, so there is nothing to install.
#
# Unlike route-to-text-tools, which routes read-only git to the git-ops MCP and deliberately allows
# all git writes, this hook encodes a policy choice: the user manages git, the agent never stages,
# commits, or stashes. Don't install it if you want the agent making commits. Other git writes
# (push, checkout, merge, ...) are untouched; those happen on explicit request and still pass the
# permission prompt.
#
# Fails OPEN: missing Perl/JSON::PP, a parse error, or any fault exits 0 so a legitimate command is
# never broken. Self-test:  bash block-vcs-writes.sh --command "git commit -m x"
# See hooks/README.md for install and tuning.

set -f  # no glob expansion while tokenizing untrusted command text

GIT_MSG="$(cat <<'MSG'
Blocked: this command runs a git write the user owns (commit, add, or stash). Standing rule of this skill set: never stage, never commit, never stash; leave the working tree exactly as your file edits made it and let the user drive git. Read-only inspection goes through the git-ops MCP. See brain/knowledge/coding-general.md, Version Control Hygiene.
MSG
)"

STACK_MSG="$(cat <<'MSG'
Blocked: every gh stack subcommand except 'view' creates, restructures, or submits PR stacks, and stack management is the user's responsibility. The only permitted call is 'gh stack view' (stack detection). See brain/knowledge/github-pr-stacks.md, Hard Rules.
MSG
)"

lower() { printf '%s' "$1" | tr 'A-Z' 'a-z'; }

# Prints "git", "stack", or nothing. A write anywhere in the command (any statement or pipeline
# stage) counts.
classify() {
    local command="$1" frags frag lead sub next i
    frags="${command//&&/$'\n'}"
    frags="${frags//||/$'\n'}"
    frags="${frags//;/$'\n'}"
    frags="${frags//|/$'\n'}"
    while IFS= read -r frag; do
        # shellcheck disable=SC2086
        set -- $frag
        [ $# -ge 1 ] || continue
        lead="${1##*/}"; lead="${lead%.exe}"; lead="$(lower "$lead")"
        if [ "$lead" = git ]; then
            shift
            while [ $# -ge 1 ]; do
                case "$1" in
                    -C|-c|--git-dir|--work-tree|--namespace|--exec-path)
                        if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
                    -*) shift ;;
                    *) break ;;
                esac
            done
            [ $# -ge 1 ] || continue
            sub="$(lower "$1")"
            case "$sub" in
                commit|add) echo git; return ;;
                stash)
                    next=""; [ $# -ge 2 ] && next="$(lower "$2")"
                    case "$next" in
                        list|show) ;;
                        *) echo git; return ;;
                    esac ;;
            esac
        elif [ "$lead" = gh ]; then
            shift
            while [ $# -ge 1 ]; do case "$1" in -*) shift ;; *) break ;; esac; done
            if [ $# -ge 1 ] && [ "$(lower "$1")" = stack ]; then
                shift
                while [ $# -ge 1 ]; do case "$1" in -*) shift ;; *) break ;; esac; done
                if [ $# -ge 1 ] && [ "$(lower "$1")" != view ]; then
                    echo stack; return
                fi
            fi
        fi
    done <<EOF
$frags
EOF
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
    git)   emit_deny "$GIT_MSG" ;;
    stack) emit_deny "$STACK_MSG" ;;
esac
exit 0
