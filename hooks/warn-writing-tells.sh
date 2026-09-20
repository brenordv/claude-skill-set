#!/usr/bin/env bash
# PostToolUse hook for the Write and Edit tools: warn when the text just written ADDS a hard-banned
# writing tell: an em-dash (U+2014) or a curly quote/apostrophe (U+2018, U+2019, U+201C, U+201D).
# See skills/brain/knowledge/writing-style.md, hard bans. It scans only the payload the tool wrote
# (tool_input.content for Write, tool_input.new_string for Edit), never the file on disk, so tells
# already present in an edited file never nag. POSIX port of warn-writing-tells.ps1 (Windows uses
# the .ps1). JSON in is parsed with Perl JSON::PP (a core module); the scan runs in the same Perl
# pass and reports counts only, never content.
#
# PostToolUse cannot block; the tool already ran. A warning is exit 2 with a short message on
# stderr, which Claude Code surfaces to the model. Fails OPEN: missing Perl/JSON::PP, a parse
# error, or any fault exits 0 and warns nothing.
# Self-test:  bash warn-writing-tells.sh --text 'some text'   (prints warn|silent)
# See hooks/README.md for install and tuning.

# Files allowed to carry the banned characters because they quote or test them (this repo's style
# guide, the lint scripts, the hook case table, and this hook pair). Matched against the payload's
# file_path with backslashes normalized to slashes.
SKIP='(^|/)(writing-style\.md|lint-repo\.(sh|ps1)|hook-cases\.tsv|warn-writing-tells\.(sh|ps1))$'

# --- self-test: classify a raw text argument without JSON or Claude Code ---
if [ "$1" = "--text" ]; then
    c="$(printf '%s' "$2" | perl -CS -0777 -ne 'my $c = () = /[\x{2014}\x{2018}\x{2019}\x{201C}\x{201D}]/g; print $c;' 2>/dev/null)"
    case "$c" in '' | *[!0-9]*) c=0 ;; esac
    if [ "$c" -gt 0 ]; then printf 'warn\n'; else printf 'silent\n'; fi
    exit 0
fi

# --- main: parse, skip-check, and count in one Perl pass; only counts come back ---
res="$(SKIP="$SKIP" perl -MJSON::PP -0777 -ne '
    my $d = eval { decode_json($_) }; exit unless $d;
    my $t = $d->{tool_input}{content};
    $t = $d->{tool_input}{new_string} unless defined $t;
    exit unless defined $t;
    my $p = $d->{tool_input}{file_path} // "";
    $p =~ tr{\\}{/};
    exit if length($ENV{SKIP}) && $p =~ /$ENV{SKIP}/i;
    my $em = () = $t =~ /\x{2014}/g;
    my $cq = () = $t =~ /[\x{2018}\x{2019}\x{201C}\x{201D}]/g;
    exit unless $em + $cq;
    print "$em $cq";
' 2>/dev/null)"
[ -n "$res" ] || exit 0
em="${res%% *}"
cq="${res#* }"
case "$em" in '' | *[!0-9]*) exit 0 ;; esac
case "$cq" in '' | *[!0-9]*) exit 0 ;; esac
printf '[warn-writing-tells] The text just written adds %s em-dash(es) and %s curly quote(s)/apostrophe(s).\n' "$em" "$cq" >&2
printf '[warn-writing-tells] Both are hard-banned tells (writing-style.md): use a period, comma, colon, or parentheses instead of an em-dash, and straight quotes/apostrophes. Fix the text you just wrote; leave pre-existing prose alone.\n' >&2
exit 2
