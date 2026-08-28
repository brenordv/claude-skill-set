#!/usr/bin/env python3
"""New-code quality gate for Rust projects.

Grades the lines a branch adds, over the merge-base to working-tree diff:

* Coverage: ``cargo-llvm-cov`` per-line coverage intersected with the added
  lines against a new-line threshold.
* Mutation: ``cargo-mutants --in-diff`` mutates only the added code and fails
  when a mutant survives the suite.
* File size: new and cap-crossing production files graded against per-language
  line tiers, subtracting the trailing ``#[cfg(test)]`` module so co-located
  tests never inflate the count. Needs only git and the filesystem, so it runs
  first and reports even where cargo is absent.

Standard library only. The pure functions (diff/lcov parsing, path
normalization, threshold check) are the language-agnostic core, deliberately
duplicated in the sibling ``python`` and ``csharp`` gates because each skill
folder is a self-contained distribution unit; a fix there belongs in all three.
See ``skills/rust/testing-guidelines.md`` for the two-gate model, install
commands, and the trust boundary.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

EXIT_OK = 0
EXIT_COVERAGE_FAILED = 2
EXIT_MUTATION_FAILED = 3
EXIT_SIZE_FAILED = 4
EXIT_USAGE = 64
EXIT_TOOL_FAILED = 70
EXIT_ENV_NOT_READY = 78

DEFAULT_COV_THRESHOLD = 80

SIZE_WARN_THRESHOLD = 700
SIZE_FAIL_CAP = 1500
SIZE_GROWTH_ALLOWANCE = 50
SIZE_READ_BYTE_CAP = 2_000_000

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_MOD_RE = re.compile(r"^\s*(?:pub\s+)?mod\s+\w+")
_SIZE_MOD_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+\w+")
_SIZE_MOD_SEMI_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+\w+\s*;\s*$")
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_C_ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11}


# --------------------------------------------------------------------------
# Pure functions: diff/lcov parsing, path normalization, gating.
# Strings in, data out; the co-located test file drives them directly.
# --------------------------------------------------------------------------


def parse_added_lines(diff_text: str) -> dict[str, set[int]]:
    """Map each file's repo-relative POSIX path to the 1-based line numbers the
    diff adds in its new version (deletions contribute nothing).

    Counts hunk-body lines against the declared counts, so an added source line
    that itself begins with ``+++`` or ``@@`` is never mistaken for a header.
    """
    added: dict[str, set[int]] = {}
    current_path: str | None = None
    new_line = 0
    old_remaining = 0
    new_remaining = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if in_hunk:
            marker = raw[:1]
            if marker == "+":
                if current_path is not None:
                    added.setdefault(current_path, set()).add(new_line)
                new_line += 1
                new_remaining -= 1
            elif marker == "-":
                old_remaining -= 1
            elif marker == "\\":
                pass  # "\ No newline at end of file"; counts against neither side
            else:
                new_line += 1
                new_remaining -= 1
                old_remaining -= 1
            if new_remaining <= 0 and old_remaining <= 0:
                in_hunk = False
            continue
        if raw.startswith("@@"):
            match = HUNK_RE.match(raw)
            if match is None:
                continue
            new_line = int(match.group(3))
            old_remaining = int(match.group(2)) if match.group(2) is not None else 1
            new_remaining = int(match.group(4)) if match.group(4) is not None else 1
            in_hunk = new_remaining > 0 or old_remaining > 0
        elif raw.startswith("+++ "):
            current_path = _diff_new_path(raw[4:])
        elif raw.startswith("diff --git"):
            current_path = None
    return added


def _diff_new_path(token: str) -> str | None:
    """Turn the text after ``+++ `` into a repo-relative path, or None."""
    path = _unquote_diff_path(token)
    if path == "/dev/null":
        return None
    if path.startswith("b/"):
        path = path[2:]
    return path


def _unquote_diff_path(token: str) -> str:
    """Decode one diff header path token, C-quoted or bare."""
    token = token.rstrip("\r\n")
    if token.startswith('"'):
        return _c_unquote(token)
    if "\t" in token:  # a bare path never contains a tab; it delimits metadata
        token = token.split("\t", 1)[0]
    return token


def _c_unquote(token: str) -> str:
    """Decode a git C-style quoted path (surrounding quotes, ``\\`` escapes)."""
    out = bytearray()
    index = 1  # skip the opening quote
    length = len(token)
    while index < length:
        char = token[index]
        if char == '"':
            break
        if char == "\\" and index + 1 < length:
            index += 1
            esc = token[index]
            if esc in _C_ESCAPES:
                out.append(_C_ESCAPES[esc])
            elif esc == "\\":
                out.append(0x5C)
            elif esc == '"':
                out.append(0x22)
            elif esc in "01234567":
                digits = esc
                while len(digits) < 3 and index + 1 < length and token[index + 1] in "01234567":
                    index += 1
                    digits += token[index]
                out.append(int(digits, 8) & 0xFF)
            else:
                out.extend(esc.encode("utf-8"))
        else:
            out.extend(char.encode("utf-8"))
        index += 1
    return out.decode("utf-8", errors="replace")


def parse_lcov(lcov_text: str, repo_root: str) -> dict[str, dict[int, int]]:
    """Parse ``SF:``/``DA:`` records into ``{repo-relative path: {line: hits}}``.

    Duplicate ``SF:`` blocks for one file merge by summing their ``DA:`` counts,
    which is legal lcov and common in multi-producer output; the optional
    ``DA:`` checksum field is ignored. ``repo_root`` makes absolute ``SF:``
    paths repo-relative.
    """
    result: dict[str, dict[int, int]] = {}
    current: dict[int, int] | None = None
    for line in lcov_text.splitlines():
        line = line.strip()
        if line.startswith("SF:"):
            path = normalize_sf_path(line[3:], repo_root)
            current = result.setdefault(path, {})
        elif line.startswith("DA:"):
            if current is None:
                continue
            parts = line[3:].split(",")
            if len(parts) < 2:
                continue
            try:
                lineno = int(parts[0])
                count = int(parts[1])
            except ValueError:
                continue
            current[lineno] = current.get(lineno, 0) + count
        elif line == "end_of_record":
            current = None
    return result


def normalize_sf_path(sf_path: str, repo_root: str) -> str:
    """Normalize an lcov ``SF:`` path to a repo-relative POSIX path.

    Converts backslashes, and strips the repo-root prefix case-insensitively
    when the path is absolute (cargo-llvm-cov's shape is undocumented and
    varies by platform). A relative path is returned as-is.
    """
    path = sf_path.replace("\\", "/")
    root = repo_root.replace("\\", "/").rstrip("/")
    if root and _is_absolute_posix(path):
        if path.lower() == root.lower():
            return ""
        prefix = root + "/"
        if path.lower().startswith(prefix.lower()):
            return path[len(prefix):]
    return path


def _is_absolute_posix(path: str) -> bool:
    """True for a POSIX-rooted path or a Windows drive path (``C:/...``)."""
    return path.startswith("/") or bool(re.match(r"^[A-Za-z]:/", path))


def strip_cfg_test_regions(content: str) -> int | None:
    """The 1-based line where a trailing ``#[cfg(test)]`` module begins (its
    ``#[cfg(test)]`` attribute), or None when no qualifying module is found.

    Locates the last ``#[cfg(test)]`` attribute followed by a ``mod``
    declaration, then requires a brace balance over attribute-to-EOF that first
    returns to zero exactly at the file's last non-blank line. Any other shape
    fails open (returns None) so in-file test code can only ever be dropped from
    the coverage denominator, never production code. Because the strip range is
    always attribute-to-EOF, a brace miscount from a brace inside a string, char
    literal, or comment can only break the balance check and fail open.
    """
    lines = content.splitlines()
    attr_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() != "#[cfg(test)]":
            continue
        probe = i + 1
        while probe < len(lines):
            stripped = lines[probe].strip()
            if stripped == "" or stripped.startswith("#["):
                probe += 1
                continue
            break
        if probe < len(lines) and _MOD_RE.match(lines[probe]):
            attr_idx = i
    if attr_idx is None:
        return None

    last_nonblank: int | None = None
    for k in range(len(lines) - 1, -1, -1):
        if lines[k].strip():
            last_nonblank = k
            break
    if last_nonblank is None or last_nonblank < attr_idx:
        return None

    depth = 0
    opened = False
    for k in range(attr_idx, len(lines)):
        depth += lines[k].count("{") - lines[k].count("}")
        if depth < 0:
            return None
        if depth > 0:
            opened = True
        elif opened and depth == 0 and k < last_nonblank:
            return None
    if not opened or depth != 0:
        return None
    return attr_idx + 1


def drop_test_module_lines(added: set[int], strip_from: int | None) -> set[int]:
    """Remove added line numbers that fall inside a trailing test module."""
    if strip_from is None:
        return set(added)
    return {line for line in added if line < strip_from}


def is_excluded(path: str, extra_globs: list[str]) -> bool:
    """Whether a repo-relative POSIX path is excluded from the denominator.

    The default set is a superset of cargo-llvm-cov's own report exclusions so a
    file it drops is never counted uncovered: any path with a ``tests/``
    segment, plus the ``tests.rs`` / ``*_tests.rs`` / ``*-tests.rs`` /
    ``*_test.rs`` basenames. User globs match against the full path and the
    basename.
    """
    parts = path.split("/")
    if "tests" in parts:
        return True
    base = parts[-1]
    if base == "tests.rs" or base.endswith(("_tests.rs", "-tests.rs", "_test.rs")):
        return True
    for pattern in extra_globs:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(base, pattern):
            return True
    return False


def parse_diff_file_status(diff_text: str) -> dict[str, tuple[bool, str | None]]:
    """Map each new-path in a diff to ``(is_new, old_path)``.

    Reads ``new file mode`` and rename headers, so a rename is scored against
    its old blob; ``old_path`` is the rename source, else the path itself.
    """
    status: dict[str, tuple[bool, str | None]] = {}
    new_path: str | None = None
    old_path: str | None = None
    is_new = False

    def commit() -> None:
        if new_path is not None:
            status[new_path] = (is_new, old_path if old_path is not None else new_path)

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            commit()
            new_path, old_path, is_new = None, None, False
        elif raw.startswith("new file mode"):
            is_new = True
        elif raw.startswith("rename from "):
            old_path = _unquote_diff_path(raw[len("rename from "):])
        elif raw.startswith("rename to "):
            renamed = _unquote_diff_path(raw[len("rename to "):])
            if new_path is None:
                new_path = renamed
        elif raw.startswith("+++ "):
            candidate = _diff_new_path(raw[4:])
            if candidate is not None:
                new_path = candidate
    commit()
    return status


def is_size_test_file(path: str) -> bool:
    """Whether a repo-relative POSIX path is test code for the size gate.

    Test code is warn-only at the cap, never a hard failure: any path with a
    ``tests`` segment, plus the ``tests.rs`` / ``*_tests.rs`` / ``*-tests.rs`` /
    ``*_test.rs`` basenames.
    """
    parts = path.split("/")
    if "tests" in parts:
        return True
    base = parts[-1]
    return base == "tests.rs" or base.endswith(("_tests.rs", "-tests.rs", "_test.rs"))


def is_size_skipped(path: str, extra_globs: list[str]) -> bool:
    """Whether a path is excluded from the size gate entirely.

    Only the user ``--exclude`` globs skip a file here (matched against the full
    path and the basename). Test files are not skipped; they are evaluated
    warn-only via ``is_size_test_file``.
    """
    base = path.split("/")[-1]
    for pattern in extra_globs:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(base, pattern):
            return True
    return False


def size_verdict(
    counted: int,
    is_new: bool,
    base: int | None,
    is_test: bool,
    warn: int,
    cap: int,
    allowance: int,
) -> str:
    """Grade one file's line count: ``"FAIL"``, ``"WARN"``, or ``"OK"``.

    New files fail at the cap and warn at the warn tier; pre-existing files fail
    only on a change that crosses the cap (never once already over), and warn on
    growth past the allowance into the warn tier. Test code never fails; ``>=``.
    """
    if is_new or base is None:
        if counted >= cap:
            verdict = "FAIL"
        elif counted >= warn:
            verdict = "WARN"
        else:
            verdict = "OK"
    elif base < cap:
        if counted >= cap:
            verdict = "FAIL"
        elif counted - base > allowance and counted >= warn:
            verdict = "WARN"
        else:
            verdict = "OK"
    else:
        verdict = "WARN" if counted - base > allowance else "OK"
    if verdict == "FAIL" and is_test:
        return "WARN"
    return verdict


def size_trailing_test_start(content: str) -> int | None:
    """1-based line where the trailing run of ``#[cfg(test)]`` modules begins,
    or None when the file does not end in a test module.

    Walks backward from the last real line (blanks and ``//`` comments skipped)
    through consecutive ``#[cfg(test)] mod`` blocks, so a file ending in one or
    more test modules yields the start of the earliest one in that trailing run:
    a stacked ``mod tests`` then ``mod proptests`` are all subtracted. Returns
    None when the file does not end in a test module: a mid-file test block, an
    attribute on a non-``mod`` item, ``#[cfg(all(test, ...))]`` / ``cfg_attr``
    (deliberately not recognized), production code after the tests, or any brace
    imbalance leaves the count untouched. Attribute and ``mod`` matching is on
    whole trimmed lines, so a ``mod`` token inside a string is not an anchor.
    Everything from the returned line to EOF is production-excluded, so a little
    trailing production after the tests is leniently over-subtracted.
    """
    lines = content.splitlines()
    end: int | None = None
    for k in range(len(lines) - 1, -1, -1):
        stripped = lines[k].strip()
        if stripped == "" or stripped.startswith("//"):
            continue
        end = k
        break
    if end is None:
        return None
    anchor: int | None = None
    while end is not None and end >= 0:
        start = _cfg_test_block_start(lines, end)
        if start is None:
            break
        anchor = start
        probe = start - 1
        while probe >= 0 and (
            lines[probe].strip() == "" or lines[probe].strip().startswith("//")
        ):
            probe -= 1
        end = probe
    return anchor + 1 if anchor is not None else None


def _cfg_test_block_start(lines: list[str], end: int) -> int | None:
    """0-based start of a ``#[cfg(test)]`` module whose last line is ``end``.

    Handles the brace form (``mod tests { ... }``) via backward brace balance
    and the semicolon form (``mod tests;``). Returns None unless the block is
    directly attributed with a whole-line ``#[cfg(test)]`` (other attributes and
    doc comments between the attribute and ``mod`` are tolerated).
    """
    if end < 0 or end >= len(lines):
        return None
    line = lines[end]
    if _SIZE_MOD_SEMI_RE.match(line):
        mod_idx = end
    elif "}" in line:
        depth = 0
        opened = False
        k = end
        while k >= 0:
            depth += lines[k].count("}") - lines[k].count("{")
            if depth < 0:
                return None
            if depth > 0:
                opened = True
            if depth == 0 and opened:
                break
            k -= 1
        if k < 0 or depth != 0 or not opened:
            return None
        if not _SIZE_MOD_RE.match(lines[k]):
            return None
        mod_idx = k
    else:
        return None
    cfg_idx: int | None = None
    probe = mod_idx - 1
    while probe >= 0:
        stripped = lines[probe].strip()
        if stripped == "":
            probe -= 1
            continue
        if stripped == "#[cfg(test)]":
            cfg_idx = probe
            probe -= 1
            continue
        if stripped.startswith("#[") or stripped.startswith("//"):
            probe -= 1
            continue
        break
    return cfg_idx


@dataclass
class SizeFinding:
    """One file's size-gate result."""

    path: str
    verdict: str
    is_new: bool
    is_test: bool
    counted: int
    total: int
    base: int | None
    truncated: bool


@dataclass
class CoverageReport:
    """Intersection of added lines with coverage data."""

    per_file: list[tuple[str, int, int]] = field(default_factory=list)
    uncovered: list[tuple[str, int]] = field(default_factory=list)
    not_instrumented: list[str] = field(default_factory=list)
    total_covered: int = 0
    total_coverable: int = 0


def intersect(
    added_by_file: dict[str, set[int]],
    coverage_by_file: dict[str, dict[int, int]],
    extra_globs: list[str],
) -> CoverageReport:
    """Intersect added ``.rs`` lines (already stripped of trailing test-module
    lines) with lcov data into a ``CoverageReport``.

    An added line is *coverable* only when lcov emitted a ``DA:`` record for it
    (blank lines, comments, and other non-executable additions carry none and
    stay out of the denominator). A changed ``.rs`` file with no ``SF:`` record
    at all is reported as not instrumented and excluded from the ratio rather
    than counted uncovered.
    """
    report = CoverageReport()
    for path in sorted(added_by_file):
        if not path.endswith(".rs"):
            continue
        if is_excluded(path, extra_globs):
            continue
        added = added_by_file[path]
        if not added:
            continue
        line_hits = coverage_by_file.get(path)
        if line_hits is None:
            report.not_instrumented.append(path)
            continue
        coverable = sorted(line for line in added if line in line_hits)
        if not coverable:
            continue
        covered = 0
        for line in coverable:
            if line_hits[line] > 0:
                covered += 1
            else:
                report.uncovered.append((path, line))
        report.per_file.append((path, covered, len(coverable)))
        report.total_covered += covered
        report.total_coverable += len(coverable)
    return report


def coverage_passes(
    total_covered: int, total_coverable: int, threshold: int
) -> bool | None:
    """Integer threshold check.

    Returns None when there is nothing to check (no new coverable lines), which
    is informational and neither a pass of substance nor a failure. Otherwise
    passes when ``covered * 100 >= threshold * coverable`` (exactly the
    threshold passes).
    """
    if total_coverable == 0:
        return None
    return total_covered * 100 >= threshold * total_coverable


def strip_control(text: str) -> str:
    """Strip ANSI escape sequences and control characters from echoed source."""
    text = _ANSI_RE.sub("", text)
    return "".join(ch for ch in text if ch == "\t" or ch >= " ")


# --------------------------------------------------------------------------
# Orchestration: preflight, the size/coverage/mutation phases, reporting.
# Shells out to git and cargo; never run by the unit tests.
# --------------------------------------------------------------------------


class GateError(Exception):
    """A controlled failure carrying the process exit code to return."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _ArgParser(argparse.ArgumentParser):
    """argparse parser that exits 64 on usage errors, not the default 2."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def _threshold_percent(value: str) -> int:
    """argparse type for ``--cov-threshold``: an integer in [0, 100]."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from exc
    if not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 100")
    return number


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = _ArgParser(
        prog="rust_quality_gate.py",
        description=(
            "New-code quality gate: diff coverage (cargo-llvm-cov) and "
            "mutation testing (cargo-mutants --in-diff)."
        ),
        epilog=(
            "Exit codes: 0 pass; 2 coverage gate failed (all phases report before "
            "exiting); 3 mutation gate failed; 4 file-size gate failed; 64 usage "
            "error; 70 an underlying tool ran and failed; 78 environment not ready. "
            "Precedence when several fail: 2 > 3 > 4."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="base ref to diff against (default: origin/HEAD, then main, then master)",
    )
    parser.add_argument(
        "--lcov-file",
        metavar="PATH",
        help="consume a pre-generated lcov file instead of running cargo llvm-cov",
    )
    parser.add_argument(
        "--cov-threshold",
        type=_threshold_percent,
        default=DEFAULT_COV_THRESHOLD,
        metavar="PCT",
        help="minimum %% of new coverable lines that must be covered (default: 80)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="GLOB",
        default=[],
        help="extra glob (matched against repo-relative path and basename) to "
        "exclude from the coverage denominator and the file-size gate; repeatable",
    )
    parser.add_argument(
        "--skip-mutants",
        action="store_true",
        help="run only the coverage gate",
    )
    return parser.parse_args(argv)


def _log(message: str) -> None:
    """Write a progress line to stderr, ordered after any pending stdout."""
    sys.stdout.flush()
    print(message, file=sys.stderr, flush=True)


def _log_command(cmd: list[str]) -> None:
    """Echo a subprocess command line to stderr so any phase is reproducible."""
    _log("+ " + " ".join(shlex.quote(part) for part in cmd))


def run_capture(cmd: list[str], cwd: str | None = None) -> "subprocess.CompletedProcess[str]":
    """Run a command capturing stdout/stderr as decoded text."""
    _log_command(cmd)
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )


def run_streaming(cmd: list[str], cwd: str | None = None) -> int:
    """Run a command with its output streamed live to stderr; return the code."""
    _log_command(cmd)
    sys.stdout.flush()
    sys.stderr.flush()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        stdout=sys.stderr.fileno(),
        stderr=sys.stderr.fileno(),
    )
    return completed.returncode


def _resolve_tool(name: str) -> str | None:
    """Resolve a tool to its absolute real path via PATH."""
    found = shutil.which(name)
    if found is None:
        return None
    return os.path.realpath(found)


def _is_within(path: str, root: str) -> bool:
    """Whether ``path`` resolves to a location inside ``root``."""
    try:
        resolved = os.path.realpath(path)
        base = os.path.realpath(root)
        return os.path.commonpath([resolved, base]) == base
    except ValueError:
        return False  # different drives on Windows


def _refuse_repo_local_tools(tools: tuple[tuple[str, str], ...], root: str) -> None:
    """Refuse any tool that resolved to a path inside ``root``.

    Windows resolves executables from the process working directory ahead of
    PATH on Python versions before 3.12, so a binary committed to the target
    repo could shadow the real tool. Nothing inside the tree being checked may
    run as a tool, and the refusal must come before the tool is ever invoked.
    """
    for name, tool_path in tools:
        if _is_within(tool_path, root):
            raise GateError(
                EXIT_ENV_NOT_READY,
                f"{name} resolved to a path inside the target repo; refusing to run "
                "a repo-local binary",
            )


def _tool_version(cmd: list[str], cwd: str, tool_name: str, install_cmd: str) -> str:
    """Confirm a cargo subcommand responds to --version; return its version line."""
    try:
        result = run_capture(cmd, cwd=cwd)
    except OSError:
        result = None
    if result is None or result.returncode != 0:
        raise GateError(
            EXIT_ENV_NOT_READY,
            f"{tool_name} is not available; install it with: {install_cmd}",
        )
    text = result.stdout.strip()
    return text.splitlines()[0] if text else tool_name


def _resolve_base_ref(git: str, cwd: str, explicit: str | None) -> tuple[str, str]:
    """Resolve the base ref to (name, commit sha), trying the fallback chain."""
    candidates = [explicit] if explicit else ["origin/HEAD", "main", "master"]
    for ref in candidates:
        if ref is None:
            continue
        if ref.startswith("-"):
            raise GateError(EXIT_ENV_NOT_READY, f"invalid base ref (leading dash): {ref}")
        result = run_capture(
            [git, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"],
            cwd=cwd,
        )
        if result.returncode == 0:
            return ref, result.stdout.strip()
    if explicit:
        raise GateError(EXIT_ENV_NOT_READY, f"base ref not found: {explicit}")
    raise GateError(
        EXIT_ENV_NOT_READY,
        "no base ref found (tried origin/HEAD, main, master); pass --base <ref>",
    )


def _git_diff(git: str, cwd: str, merge_base: str, context: bool) -> str:
    """Produce a merge-base-to-working-tree diff with a forced, stable shape."""
    cmd = [
        git,
        "--no-pager",
        "-c",
        "diff.noprefix=false",
        "diff",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--src-prefix=a/",
        "--dst-prefix=b/",
    ]
    if not context:
        cmd.append("-U0")
    cmd += [merge_base, "--"]
    result = run_capture(cmd, cwd=cwd)
    if result.returncode != 0:
        raise GateError(EXIT_TOOL_FAILED, f"git diff failed: {result.stderr.strip()}")
    return result.stdout


def _untracked_rs(git: str, cwd: str) -> list[str]:
    """List untracked, non-ignored ``.rs`` files (invisible to git diff)."""
    result = run_capture([git, "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.endswith(".rs")]


def _read_worktree_file(repo_root: str, rel_path: str) -> str | None:
    """Read a repo file's working-tree text, or None if unreadable."""
    try:
        return (Path(repo_root) / rel_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _read_line(repo_root: str, rel_path: str, lineno: int) -> str:
    """Read one 1-based line of a repo file, trimmed; empty if out of range."""
    content = _read_worktree_file(repo_root, rel_path)
    if content is None:
        return ""
    lines = content.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def _file_nonempty(path: str) -> bool:
    """Whether a file exists and has nonzero size."""
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False


def _size_counted_lines(text: str) -> tuple[int, int]:
    """Return (counted, total) line counts.

    ``total`` is every physical line; ``counted`` subtracts the trailing
    ``#[cfg(test)]`` module so co-located unit tests never inflate the
    production tier.
    """
    total = len(text.splitlines())
    start = size_trailing_test_start(text)
    counted = start - 1 if start is not None else total
    return counted, total


def _merge_base_content(git: str, cwd: str, merge_base: str, path: str) -> str | None:
    """The working blob text of ``path`` at the merge base, or None if absent."""
    result = run_capture([git, "show", f"{merge_base}:{path}"], cwd=cwd)
    if result.returncode != 0:
        return None
    return result.stdout


def _read_source_for_size(repo_root: str, rel_path: str) -> tuple[str | None, bool]:
    """Read a regular source file for counting, capped at a byte ceiling.

    Returns ``(text, truncated)``; a symlink, directory, missing file, or read
    error yields ``(None, False)`` so the size gate fails open on read errors.
    """
    path = Path(repo_root) / rel_path
    try:
        if path.is_symlink() or not path.is_file():
            return None, False
        with open(path, "rb") as handle:
            data = handle.read(SIZE_READ_BYTE_CAP + 1)
    except OSError:
        return None, False
    truncated = len(data) > SIZE_READ_BYTE_CAP
    return data[:SIZE_READ_BYTE_CAP].decode("utf-8", errors="replace"), truncated


def _evaluate_sizes(
    added_by_file: dict[str, set[int]],
    file_status: dict[str, tuple[bool, str | None]],
    untracked: list[str],
    git: str,
    repo_cwd: str,
    repo_root: str,
    merge_base: str,
    extra_globs: list[str],
) -> list[SizeFinding]:
    """Grade every added or new ``.rs`` file against the size policy; untracked
    ``.rs`` files fold in as new (invisible to the diff, so the other gates miss
    them, but exactly what the size gate is here to catch).
    """
    candidates: dict[str, tuple[bool, str | None]] = {}
    for path, lines in added_by_file.items():
        if lines and path.endswith(".rs"):
            candidates[path] = file_status.get(path, (False, path))
    for path in untracked:
        if path.endswith(".rs") and path not in candidates:
            candidates[path] = (True, None)

    findings: list[SizeFinding] = []
    for path in sorted(candidates):
        if is_size_skipped(path, extra_globs):
            continue
        is_new, old_path = candidates[path]
        text, truncated = _read_source_for_size(repo_root, path)
        if text is None:
            continue
        counted, total = _size_counted_lines(text)
        if is_new:
            base: int | None = None
        else:
            base_text = _merge_base_content(git, repo_cwd, merge_base, old_path or path)
            base = _size_counted_lines(base_text)[0] if base_text is not None else counted
        is_test = is_size_test_file(path)
        verdict = size_verdict(
            counted,
            is_new,
            base,
            is_test,
            SIZE_WARN_THRESHOLD,
            SIZE_FAIL_CAP,
            SIZE_GROWTH_ALLOWANCE,
        )
        findings.append(
            SizeFinding(path, verdict, is_new, is_test, counted, total, base, truncated)
        )
    return findings


def _size_finding_line(finding: SizeFinding) -> str:
    """One report line: classification, line counts, verdict, and next action."""
    if finding.is_new:
        classification = "new"
    elif finding.base is not None and finding.counted - finding.base > SIZE_GROWTH_ALLOWANCE:
        classification = f"pre-existing, grew {finding.counted - finding.base:+d} net lines"
    elif finding.base is not None and finding.base >= SIZE_FAIL_CAP:
        classification = "pre-existing, already over cap"
    else:
        classification = "pre-existing"
    if finding.total != finding.counted:
        size = f"{finding.counted} production lines ({finding.total} total, tests subtracted)"
    else:
        size = f"{finding.counted} lines"
    if finding.truncated:
        size += ", exceeds the read cap"
    action = ""
    if finding.verdict == "FAIL":
        action = "; split the new code into a new module (or --exclude a generated file)"
    elif finding.verdict == "WARN" and finding.is_test:
        action = " (test file, warn-only)"
    elif finding.verdict == "WARN" and finding.base is not None and finding.base >= SIZE_FAIL_CAP:
        action = "; route new code into a new module, do not refactor this file for size"
    elif finding.verdict == "WARN":
        action = "; approaching the cap, plan to split new code into a new module"
    return f"{finding.path}: {classification}, {size} -> {finding.verdict}{action}"


def _print_size_report(findings: list[SizeFinding], elapsed: float) -> None:
    """Print the file-size gate section to stdout."""
    print("-- file-size gate (new code, vs merge-base) --")
    print(
        f"  policy: warn >= {SIZE_WARN_THRESHOLD}, fail >= {SIZE_FAIL_CAP} (new and cap-crossing "
        f"production); allowance {SIZE_GROWTH_ALLOWANCE}; #[cfg(test)] subtracted; tests warn-only"
    )
    if not findings:
        print("  no added or newly created .rs files to check")
    for finding in findings:
        print(f"  {_size_finding_line(finding)}")
    print(f"  file-size phase: {elapsed:.1f}s")
    print()


def _default_exclusion_desc() -> str:
    """One-line description of the default coverage exclusions."""
    return (
        "paths under any tests/ segment; basenames tests.rs, *_tests.rs, "
        "*-tests.rs, *_test.rs"
    )


def _print_header(
    args: argparse.Namespace,
    base_ref: str,
    base_sha: str,
    merge_base: str,
    llvm_ver: str | None,
    mutants_ver: str | None,
) -> None:
    """Print the reproducibility header to stdout."""
    print("== Rust new-code quality gate ==")
    print(f"base ref:    {base_ref} ({base_sha[:12]})")
    print(f"merge-base:  {merge_base[:12]}")
    if llvm_ver:
        print(f"cargo-llvm-cov: {llvm_ver}")
    elif args.lcov_file:
        print(f"coverage source: pre-generated lcov ({args.lcov_file})")
    if mutants_ver:
        print(f"cargo-mutants:  {mutants_ver}")
    elif args.skip_mutants:
        print("mutation gate:  skipped (--skip-mutants)")
    print(f"coverage threshold: {args.cov_threshold}% of new coverable lines")
    print(f"exclusions: {_default_exclusion_desc()}")
    if args.exclude:
        print(f"  + user globs: {', '.join(args.exclude)}")
    print()


def _print_coverage_report(
    report: CoverageReport,
    verdict: bool | None,
    threshold: int,
    repo_root: str,
    elapsed: float,
) -> None:
    """Print the coverage gate result to stdout."""
    print("-- coverage gate (new-line quantity) --")
    for path, covered, coverable in report.per_file:
        pct = covered * 100 / coverable
        print(f"  {path}: {covered}/{coverable} ({pct:.0f}%)")
    for path in report.not_instrumented:
        print(f"  {path}: not instrumented (no coverage data; excluded from ratio)")
    if report.uncovered:
        print("  uncovered new lines:")
        for path, line in report.uncovered:
            print(f"    {path}:{line}: {strip_control(_read_line(repo_root, path, line))}")
    if report.total_coverable == 0:
        print("  nothing to check (no new coverable lines)")
    else:
        total_pct = report.total_covered * 100 / report.total_coverable
        status = "PASS" if verdict else "FAIL"
        print(
            f"  total: {report.total_covered}/{report.total_coverable} "
            f"({total_pct:.1f}%), threshold {threshold}% -> {status}"
        )
    print(f"  coverage phase: {elapsed:.1f}s")
    print()


def _print_missed(missed_path: str) -> None:
    """Print the mutants ``missed.txt`` if present."""
    if _file_nonempty(missed_path):
        print("-- mutation gate: missed mutants --")
        print(Path(missed_path).read_text(encoding="utf-8", errors="replace"))
    else:
        print("-- mutation gate: FAILED (missed mutants; see tool output above) --")


def _obtain_lcov(args: argparse.Namespace, cargo: str, cwd: str, tmpdir: str) -> str:
    """Return lcov text, either from --lcov-file or by running cargo llvm-cov."""
    if args.lcov_file:
        if not os.path.isfile(args.lcov_file):
            raise GateError(EXIT_ENV_NOT_READY, f"--lcov-file not found: {args.lcov_file}")
        return Path(args.lcov_file).read_text(encoding="utf-8", errors="replace")
    out = os.path.join(tmpdir, "lcov.info")
    code = run_streaming(
        [cargo, "llvm-cov", "--workspace", "--lcov", "--output-path", out],
        cwd=cwd,
    )
    if code != 0:
        raise GateError(EXIT_TOOL_FAILED, f"cargo llvm-cov exited {code}")
    if not os.path.isfile(out):
        raise GateError(EXIT_TOOL_FAILED, "cargo llvm-cov produced no lcov output")
    return Path(out).read_text(encoding="utf-8", errors="replace")


def _run_mutation_gate(cargo: str, cwd: str, diff_path: str, tmpdir: str) -> bool:
    """Run cargo-mutants over the diff; return True when the gate fails."""
    out_dir = os.path.join(tmpdir, "mutants")
    code = run_streaming(
        [cargo, "mutants", "--workspace", "--in-diff", diff_path, "--output", out_dir],
        cwd=cwd,
    )
    missed = os.path.join(out_dir, "mutants.out", "missed.txt")
    if code == 0:
        print("-- mutation gate: all mutants caught --")
        return False
    if code == 2:
        _print_missed(missed)
        return True
    if code == 3:
        if _file_nonempty(missed):
            _print_missed(missed)
            return True
        print("-- mutation gate: timeouts occurred, no missed mutants; pass (warning) --")
        return False
    raise GateError(
        EXIT_TOOL_FAILED,
        f"cargo mutants exited {code} (build or tree failure, not a gate verdict)",
    )


def _run_gate(args: argparse.Namespace, tmpdir: str) -> int:
    """Run preflight and both gates; return the process exit code."""
    started = time.monotonic()

    git = _resolve_tool("git")
    if git is None:
        raise GateError(EXIT_ENV_NOT_READY, "git not found on PATH")
    _refuse_repo_local_tools((("git", git),), os.getcwd())

    toplevel = run_capture([git, "rev-parse", "--show-toplevel"])
    if toplevel.returncode != 0:
        raise GateError(EXIT_ENV_NOT_READY, "not inside a git repository")
    repo_root = toplevel.stdout.strip()
    repo_cwd = os.path.normpath(repo_root)

    _refuse_repo_local_tools((("git", git),), repo_root)

    base_ref, base_sha = _resolve_base_ref(git, repo_cwd, args.base)

    merge = run_capture([git, "merge-base", base_sha, "HEAD"], cwd=repo_cwd)
    if merge.returncode != 0:
        raise GateError(
            EXIT_ENV_NOT_READY, f"could not compute merge-base of {base_ref} and HEAD"
        )
    merge_base = merge.stdout.strip()

    zero_diff = _git_diff(git, repo_cwd, merge_base, context=False)
    added_raw = parse_added_lines(zero_diff)
    file_status = parse_diff_file_status(zero_diff)

    added_by_file: dict[str, set[int]] = {}
    for path, lines in added_raw.items():
        if not path.endswith(".rs"):
            added_by_file[path] = lines
            continue
        content = _read_worktree_file(repo_root, path)
        if content is None:
            added_by_file[path] = lines
            continue
        added_by_file[path] = drop_test_module_lines(lines, strip_cfg_test_regions(content))

    untracked = _untracked_rs(git, repo_cwd)
    if untracked:
        _log(
            "warning: untracked .rs files are invisible to git diff; coverage and "
            "mutation miss them, though the file-size gate checks them as new:"
        )
        for name in untracked:
            _log(f"  {name}")
        _log(
            "  a git write makes them visible to every gate (a commit, or "
            "`git add -N <file>`); git writes are the user's, so ask them first."
        )

    # File-size gate runs first, on git and the filesystem alone, so it reports
    # even where cargo is absent. It grades the raw added set; its own counter
    # subtracts the trailing test module.
    size_start = time.monotonic()
    size_findings = _evaluate_sizes(
        added_raw,
        file_status,
        untracked,
        git,
        repo_cwd,
        repo_root,
        merge_base,
        args.exclude,
    )
    _print_size_report(size_findings, time.monotonic() - size_start)
    size_failed = any(finding.verdict == "FAIL" for finding in size_findings)

    coverage_failed = False
    mutation_failed = False
    try:
        cargo = _resolve_tool("cargo")
        if cargo is None:
            raise GateError(
                EXIT_ENV_NOT_READY,
                "cargo not found on PATH; install Rust from https://rustup.rs",
            )
        _refuse_repo_local_tools((("cargo", cargo),), os.getcwd())
        _refuse_repo_local_tools((("cargo", cargo),), repo_root)

        llvm_ver = None
        if not args.lcov_file:
            llvm_ver = _tool_version(
                [cargo, "llvm-cov", "--version"],
                repo_cwd,
                "cargo-llvm-cov",
                "cargo +stable install cargo-llvm-cov --locked",
            )
        mutants_ver = None
        if not args.skip_mutants:
            mutants_ver = _tool_version(
                [cargo, "mutants", "--version"],
                repo_cwd,
                "cargo-mutants",
                "cargo install --locked cargo-mutants",
            )

        _print_header(args, base_ref, base_sha, merge_base, llvm_ver, mutants_ver)

        cov_start = time.monotonic()
        lcov_text = _obtain_lcov(args, cargo, repo_cwd, tmpdir)
        coverage_by_file = parse_lcov(lcov_text, repo_root)
        report = intersect(added_by_file, coverage_by_file, args.exclude)
        verdict = coverage_passes(
            report.total_covered, report.total_coverable, args.cov_threshold
        )
        _print_coverage_report(
            report, verdict, args.cov_threshold, repo_root, time.monotonic() - cov_start
        )
        coverage_failed = verdict is False

        if args.skip_mutants:
            print("-- mutation gate: skipped (--skip-mutants) --\n")
        else:
            full_diff = _git_diff(git, repo_cwd, merge_base, context=True)
            diff_path = os.path.join(tmpdir, "changes.diff")
            with open(diff_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(full_diff)
            mut_start = time.monotonic()
            mutation_failed = _run_mutation_gate(cargo, repo_cwd, diff_path, tmpdir)
            print(f"  mutation phase: {time.monotonic() - mut_start:.1f}s\n")
    except GateError as err:
        if size_failed and err.code == EXIT_ENV_NOT_READY:
            _log(f"note: coverage and mutation phases not run: {err.message}")
        else:
            raise

    _log(f"quality gate finished in {time.monotonic() - started:.1f}s")
    if coverage_failed:
        return EXIT_COVERAGE_FAILED
    if mutation_failed:
        return EXIT_MUTATION_FAILED
    if size_failed:
        return EXIT_SIZE_FAILED
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Entry point: run the gate and clean up the temp dir on success."""
    args = parse_args(argv)
    tmpdir = tempfile.mkdtemp(prefix="rust-quality-gate-")
    retain = False
    try:
        code = _run_gate(args, tmpdir)
        retain = code in (EXIT_COVERAGE_FAILED, EXIT_MUTATION_FAILED)
        return code
    except GateError as err:
        _log(f"error: {err.message}")
        retain = err.code == EXIT_TOOL_FAILED
        return err.code
    finally:
        if retain:
            _log(f"artifacts retained for inspection in: {tmpdir}")
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
