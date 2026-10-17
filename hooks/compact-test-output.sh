#!/usr/bin/env bash
# PostToolUse hook for the Bash and PowerShell tools: compact noisy test-runner output before the
# model reads it (POSIX port of compact-test-output.ps1; Windows uses the .ps1). A passing run
# collapses to its summary line(s); a run whose output carries failure indicators keeps every
# unrecognized line verbatim and drops only positively identified noise (per-test pass lines,
# restore/build chatter). The replacement is emitted as hookSpecificOutput.updatedToolOutput, an
# object mirroring the Bash tool_response shape with only stdout/stderr rewritten; Claude Code
# validates that shape and falls back to the original output on any mismatch.
#
# PostToolUse fires only for commands that exited 0; a nonzero exit routes to PostToolUseFailure,
# which cannot rewrite output, so plain failing runs pass through untouched by design. The
# failure-shaped content this hook does filter arrives when a compound command masks the exit
# (`dotnet test; echo done`) or a build warning rides a passing run.
#
# JSON in/out is handled by Perl with JSON::PP (core on stock macOS and Ubuntu). Fails OPEN:
# missing Perl, a parse error, an unexpected tool_response shape, or any fault exits 0 and emits
# nothing, so the model sees the original output.
# Self-test without Claude Code:  bash compact-test-output.sh --filter 'dotnet test' < raw-output
# (prints skip:<reason>, passthrough:<reason>, or the replacement text).
# See hooks/README.md for install and tuning.

# Tunables, read by the embedded perl program through the environment. The replacement is never
# larger than the original (a subset of its lines plus one header line), so Claude Code's own Bash
# output window is the only size limit in play and nothing here caps the output.
# CTO_MIN_CHARS: below this many output characters nothing is rewritten (not worth a rewrite).
# CTO_BYTE_CAP:  stdin payloads larger than this many bytes pass through unparsed (the .ps1 twin
#                counts characters; the two agree on ASCII output).
CTO_MIN_CHARS=1500
CTO_BYTE_CAP=2000000
export CTO_MIN_CHARS CTO_BYTE_CAP

IFS= read -r -d '' PROG <<'PERL'
use strict;
use warnings;
use JSON::PP;

my $MIN  = $ENV{CTO_MIN_CHARS} || 1500;
my $BCAP = $ENV{CTO_BYTE_CAP}  || 2000000;
my $MODE = $ENV{CTO_MODE}      || 'hook';

# Runner table. Keep every pattern line-anchored and free of nested quantifiers; keep it in sync
# with $runners in compact-test-output.ps1. Shapes are empirical (pinned by tools/hook-cases.tsv):
# a drifted pattern degrades to pass-through, never to dropped errors.
#   match: the statement that invokes the runner.    spos/sneg: a line proving a zero-failure run.
#   keep:  summary lines retained by a collapse.     noise: lines dropped by noise-drop mode.
#   fail:  failure indicators; any hit blocks a collapse (the lines themselves are always kept).
my @RUNNERS = (
  {
    key   => 'dotnet test',
    match => qr/^dotnet[ \t]+test\b/,
    spos  => qr/^Passed![ \t]+-[ \t]+Failed:[ \t]+0,|^Test summary: total: ?\d+, failed: ?0\b/,
    keep  => qr/^Passed!|^Test summary:/,
    noise => qr/^[ \t]+Passed[ \t]|^[ \t]*Determining projects to restore|^[ \t]+Restored[ \t]|^.*[ \t]->[ \t].*\.(?:dll|exe)[ \t]*$|^Test run for[ \t]|^Microsoft \(R\) Test Execution Command Line Tool|^Copyright \(c\) Microsoft Corporation|^Starting test execution, please wait|^A total of \d+ test files? matched|^[ \t]*\[xUnit\.net [0-9:.]+\][ \t]+(?:Discovering|Discovered|Starting|Finished):/,
    fail  => qr/^[ \t]+Failed[ \t]|^Failed!|^[ \t]+Error Message:|^[ \t]+Stack Trace:|(?:^|: )(?:error|warning) [A-Za-z0-9]+:|^Test summary:.*\bfailed: ?[1-9]/,
  },
  {
    key   => 'pytest',
    match => qr/^(?:pytest|py\.test)\b|^python[0-9.]*[ \t]+-m[ \t]+pytest\b/,
    spos  => qr/^=+ \d+ passed\b[^\n]* =+$|^\d+ passed\b[^\n]*$/,
    sneg  => qr/\bfailed\b|\berrors?\b/,
    keep  => qr/^=+ \d+ passed\b[^\n]* =+$|^\d+ passed\b[^\n]*$/,
    noise => qr/^\S+::[^\n]* PASSED(?: +\[ *\d+%\])?$|^[.sx]+(?: +\[ *\d+%\])?$|^platform \S+ -- Python|^rootdir: |^plugins: |^cachedir: |^configfile: |^collected \d+ items?\b/,
    fail  => qr/\bFAILED\b|\bERRORS?\b|^=+ (?:FAILURES|ERRORS) =+$/,
  },
  {
    key   => 'cargo test',
    match => qr/^cargo[ \t]+(?:test\b|nextest[ \t]+run\b)/,
    spos  => qr/^test result: ok\. \d+ passed; 0 failed;/,
    keep  => qr/^test result: /,
    noise => qr/^test \S+ \.\.\. ok$|^[ \t]*(?:Compiling|Finished|Running|Doc-tests)\b|^running \d+ tests?$/,
    fail  => qr/^test \S+ \.\.\. FAILED$|^---- \S+ stdout ----$|panicked at|^test result: FAILED|^error(?:\[E[0-9]+\])?:|^warning:/,
  },
  {
    key   => 'jest/vitest',
    match => qr/^npx[ \t]+(?:jest|vitest)\b|^(?:jest|vitest)\b|^npm[ \t]+(?:test\b|run[ \t]+test)|^yarn[ \t]+test\b|^pnpm[ \t]+(?:run[ \t]+)?test\b/,
    spos  => qr/^Tests:[ \t]+\d+ passed, \d+ total[ \t]*$|^[ \t]*Tests[ \t]+\d+ passed(?: \| \d+ skipped)?(?: \| \d+ todo)?[ \t]+\(\d+\)[ \t]*$/,
    sneg  => qr/\bfailed\b/,
    keep  => qr/^(?:Test Suites|Tests|Snapshots|Time):|^Ran all test suites|^[ \t]*(?:Test Files|Tests|Start at|Duration)[ \t]+\S/,
    noise => qr/^PASS [^\n]*$|^[ \t]*[\x{2713}\x{221A}][ \t]|^[ \t]*RUN[ \t]+v\d+\.\d+/,
    fail  => qr/^[ \t]*FAIL[ \t]|[\x{2715}\x{00D7}\x{276F}]|^[ \t]*\x{25CF} |^Tests:[^\n]*\bfailed\b|^[ \t]*(?:Test Files|Tests)[ \t]+\d+ failed\b|^[ \t]*Errors[ \t]+\d+ error/,
  },
);

# Print a self-test reason (filter mode) or stay silent (hook mode), then stop.
sub bail {
    my ($reason) = @_;
    if ($MODE eq 'filter') { binmode(STDOUT, ':encoding(UTF-8)'); print "$reason\n"; }
    exit 0;
}

# Classify the command: the runner it invokes, and whether other significant statements ride along.
sub classify_cmd {
    my ($cmd) = @_;
    bail('skip:keep-output') if index($cmd, '#keep-output') >= 0;
    my ($runner, $rstmt, $extra);
    for my $s (split /&&|\|\||;|\n/, $cmd) {
        my $t = $s;
        $t =~ s/^[ \t]+//;
        $t =~ s/^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]+// while $t =~ /^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]/;
        next if $t eq '' || $t =~ /^cd\b/ || $t =~ /^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*$/;
        my $m;
        for my $r (@RUNNERS) { if ($t =~ $r->{match}) { $m = $r; last; } }
        if ($m && !defined $runner) { $runner = $m; $rstmt = $t; next; }
        $extra = 1;
    }
    bail('skip:no-runner') unless $runner;
    bail('skip:piped') if index($rstmt, '|') >= 0;
    return ($runner, $extra ? 1 : 0);
}

sub line_matches {
    my ($re, @streams) = @_;
    for my $text (@streams) {
        for my $line (split /\n/, $text) {
            $line =~ s/\r$//;
            return 1 if $line =~ $re;
        }
    }
    return 0;
}

# Keep only the lines a predicate accepts. Trailing CRs are trimmed from matching and from the
# kept lines, so a CRLF input yields the same LF replacement on both implementations.
sub sieve {
    my ($text, $want) = @_;
    my (@kept, $dropped);
    $dropped = 0;
    for my $line (split /\n/, $text) {
        (my $probe = $line) =~ s/\r$//;
        if ($want->($probe)) { push @kept, $probe; } else { $dropped++; }
    }
    return (join("\n", @kept), $dropped);
}

sub count_lines { my ($t) = @_; return 0 if $t eq ''; my @l = split /\n/, $t; return scalar @l; }

# --- read the input ---
my ($cmd, $stdout, $stderr, $resp);
if ($MODE eq 'filter') {
    $cmd = $ENV{CTO_CMD};
    defined $cmd or exit 0;
    my $raw = do { local $/; <STDIN> };
    $raw = '' unless defined $raw;
    bail('passthrough:byte-cap') if length($raw) > $BCAP;
    utf8::decode($raw);
    ($stdout, $stderr) = ($raw, '');
} else {
    my $raw = do { local $/; <STDIN> };
    exit 0 unless defined $raw;
    exit 0 if length($raw) > $BCAP;
    my $d = eval { decode_json($raw) };
    exit 0 unless ref($d) eq 'HASH' && ref($d->{tool_input}) eq 'HASH';
    $cmd = $d->{tool_input}{command};
    exit 0 unless defined $cmd && !ref $cmd;
    my $tr = $d->{tool_response};
    exit 0 unless ref($tr) eq 'HASH';
    exit 0 if $tr->{interrupted};
    exit 0 unless defined $tr->{stdout} && !ref $tr->{stdout};
    $stdout = $tr->{stdout};
    $stderr = (defined $tr->{stderr} && !ref $tr->{stderr}) ? $tr->{stderr} : '';
    $resp = $tr;
}

my ($r, $extra) = classify_cmd($cmd);
bail('passthrough:short') if length($stdout) + length($stderr) < $MIN;

my $has_fail = line_matches($r->{fail}, $stdout, $stderr);
my $has_success = 0;
if (!$has_fail) {
    for my $text ($stdout, $stderr) {
        for my $line (split /\n/, $text) {
            $line =~ s/\r$//;
            next unless $line =~ $r->{spos};
            next if defined $r->{sneg} && $line =~ $r->{sneg};
            $has_success = 1;
            last;
        }
        last if $has_success;
    }
}

my $total = count_lines($stdout) + count_lines($stderr);
my ($new_out, $new_err, $header);
if (!$extra && $has_success && !$has_fail) {
    my ($ko) = sieve($stdout, sub { $_[0] =~ $r->{keep} });
    my ($ke) = sieve($stderr, sub { $_[0] =~ $r->{keep} });
    my $kept = count_lines($ko) + count_lines($ke);
    $header = sprintf('[compact-test-output] %s passed; %d of %d output lines elided (append #keep-output to a re-run for the full output).',
        $r->{key}, $total - $kept, $total);
    ($new_out, $new_err) = ($ko, $ke);
} else {
    my ($ko, $do) = sieve($stdout, sub { $_[0] !~ $r->{noise} });
    my ($ke, $de) = sieve($stderr, sub { $_[0] !~ $r->{noise} });
    my $dropped = $do + $de;
    bail('passthrough:nothing-dropped') if $dropped == 0;
    $header = sprintf('[compact-test-output] %s: dropped %d of %d known-noise lines, everything unrecognized kept verbatim (append #keep-output to a re-run for the full output).',
        $r->{key}, $dropped, $total);
    ($new_out, $new_err) = ($ko, $ke);
}

$new_out = $new_out eq '' ? $header : "$header\n$new_out";

if ($MODE eq 'filter') {
    binmode(STDOUT, ':encoding(UTF-8)');
    print $new_out, "\n";
    print "--- stderr ---\n$new_err\n" if $new_err ne '';
    exit 0;
}

my %copy = %$resp;
$copy{stdout} = $new_out;
$copy{stderr} = $new_err;
print encode_json({ hookSpecificOutput => {
    hookEventName     => 'PostToolUse',
    updatedToolOutput => \%copy,
} });
exit 0;
PERL

if [ "$1" = "--filter" ]; then
    if [ -z "$2" ]; then
        printf 'usage: %s --filter "<command>" < raw-test-output\n' "$0" >&2
        exit 2
    fi
    CTO_MODE=filter CTO_CMD="$2" perl -e "$PROG" 2>/dev/null
    exit 0
fi

perl -e "$PROG" 2>/dev/null
exit 0
