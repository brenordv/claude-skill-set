#!/usr/bin/env bash
# Repo lint: keeps the prose rulebase healthy. Why each check exists is documented in
# tools/README.md; the short version is that this repo's regression class is dead pointers and
# prose that violates its own style rules, and every check below has caught a real instance.
#
# Checks over every .md file (excluding .git):
#   [link]    relative markdown link targets resolve
#   [ref]     backticked, slash-containing *.md path references resolve (tried against the repo
#             root, skills/<path> for the brain/... convention, and the referencing file's folder;
#             bare filenames without a slash are skipped as unresolvable by convention)
#   [style]   no em-dash character (exemption: writing-style.md, which quotes it to ban it)
#   [privacy] no machine-identifying path shapes (Users/<name>, AppData/Local/Temp)
#
# Exit 0 = clean, 1 = findings. POSIX port of lint-repo.ps1; keep both in sync.

set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

report() { printf '%s\n' "$1"; fail=1; }

blank_fences() {
    # Reproduces the file with fenced code blocks blanked, preserving line numbers, so the link
    # and ref checks don't parse code samples (a regex like `](Users|home)` reads as a link).
    awk 'BEGIN{fence=0} /^[[:space:]]*```/{fence=!fence; print ""; next} fence{print ""; next} {print}' "$1" 2>/dev/null
}

while IFS= read -r -d '' f; do
    dir="$(dirname "$f")"
    rel="${f#"$root"/}"

    # [link] relative markdown link targets resolve
    while IFS=: read -r ln target; do
        [ -n "$target" ] || continue
        case "$target" in
            http://*|https://*|mailto:*|'#'*) continue ;;
        esac
        t="${target%%#*}"
        [ -n "$t" ] || continue
        [ -e "$dir/$t" ] || report "$rel:$ln: [link] relative link target not found: $target"
    done < <(blank_fences "$f" | grep -noE '\]\([^)]+\)' | sed -E 's/^([0-9]+):\]\((.*)\)$/\1:\2/')

    # [ref] backticked slash-containing .md paths resolve
    while IFS=: read -r ln p; do
        [ -n "$p" ] || continue
        case "$p" in
            */*) ;;
            *) continue ;;
        esac
        if [ ! -e "$root/$p" ] && [ ! -e "$root/skills/$p" ] && [ ! -e "$dir/$p" ]; then
            report "$rel:$ln: [ref] backticked path not found: $p"
        fi
    done < <(blank_fences "$f" | grep -noE '`[A-Za-z0-9._/-]+\.md`' | sed -E 's/^([0-9]+):`(.*)`$/\1:\2/')

    # [style] em-dash ban (writing-style.md quotes the character to ban it)
    if [ "$rel" != "skills/brain/knowledge/writing-style.md" ]; then
        while IFS= read -r hit; do
            report "$rel:${hit%%:*}: [style] em-dash found"
        done < <(grep -n -- '—' "$f" 2>/dev/null)
    fi

    # [privacy] machine-identifying path shapes
    while IFS= read -r hit; do
        report "$rel:${hit%%:*}: [privacy] machine-identifying path shape"
    done < <(grep -nE '[/\\]Users[/\\][A-Za-z0-9._-]+|AppData[/\\]+Local[/\\]+Te?mp' "$f" 2>/dev/null)

done < <(find "$root" -name '*.md' -not -path '*/.git/*' -print0)

if [ "$fail" -eq 0 ]; then
    echo "lint-repo: clean"
else
    echo "lint-repo: findings above"
fi
exit "$fail"
