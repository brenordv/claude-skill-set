#!/usr/bin/env python3
"""New-code quality gate for C# projects.

Answers two questions about the lines a branch adds, over the merge-base to
working-tree diff:

* Are they tested?  ``dotnet test`` with the coverlet collector produces lcov
  output; this script intersects it with the added lines and enforces a
  new-line coverage threshold.
* Do the tests mean anything?  Stryker.NET (``dotnet stryker --since``)
  mutates only the changed code and fails when any scoped mutant survives the
  suite.

Standard library only, so it runs anywhere a Python 3 interpreter, the .NET
SDK, and dotnet-stryker are present. The parsing and intersection logic is
factored into pure functions that the co-located test file imports directly;
the phases that shell out to git and dotnet live in the orchestration half.
The language-agnostic core (diff parsing, lcov parsing, path normalization,
threshold check) is deliberately duplicated in the sibling gates
``skills/rust/scripts/rust_quality_gate.py`` and
``skills/python/scripts/python_quality_gate.py`` because each skill folder is
a self-contained distribution unit; a bug fix in that core belongs in all
three. See ``skills/csharp/testing-guidelines.md`` for the two-gate model,
install commands, and the trust boundary.
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
EXIT_USAGE = 64
EXIT_TOOL_FAILED = 70
EXIT_ENV_NOT_READY = 78

DEFAULT_COV_THRESHOLD = 90

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_C_ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11}
_CS_TYPE_DECL_RE = re.compile(
    r"\b(class|struct|record|interface|enum|delegate)\s+[A-Za-z_@]"
)
_BODYLESS_KEYWORDS = frozenset({"interface", "enum", "delegate"})


# --------------------------------------------------------------------------
# Pure functions: diff parsing, lcov parsing, path normalization, gating.
# These take strings and return data; the test file drives them directly.
# --------------------------------------------------------------------------


def parse_added_lines(diff_text: str) -> dict[str, set[int]]:
    """Extract added line numbers per file from a unified diff.

    Reads the destination path from each ``+++`` header and the new-file line
    numbers from each hunk, counting hunk-body lines against the declared
    counts so an added source line that itself begins with ``+++`` or ``@@`` is
    never mistaken for a header.

    Args:
        diff_text: Output of ``git diff`` (any ``-U`` context; ``-U0`` is what
            the gate feeds it).

    Returns:
        Map of repo-relative POSIX path to the set of 1-based line numbers the
        diff adds in the new version of that file. Deletions (``+++
        /dev/null``) contribute nothing.
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
    return path.removeprefix("b/")


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
                while (
                    len(digits) < 3
                    and index + 1 < length
                    and token[index + 1] in "01234567"
                ):
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
    """Parse ``SF:``/``DA:`` records into per-file line hit counts.

    Duplicate ``SF:`` blocks for one file merge by summing their ``DA:``
    counts, which is legal lcov and common in multi-producer output (one
    coverlet attachment per test project, for instance). The optional checksum
    third field of a ``DA:`` record is ignored.

    Args:
        lcov_text: Contents of one or more concatenated lcov ``.info`` files.
        repo_root: Absolute repo root (POSIX or native), used to make absolute
            ``SF:`` paths repo-relative.

    Returns:
        Map of repo-relative POSIX path to a map of 1-based line number to hit
        count.
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
    when the path is absolute (coverlet's ``SF:`` shape is undocumented and
    varies by platform). A relative path is returned as-is.
    """
    path = sf_path.replace("\\", "/")
    root = repo_root.replace("\\", "/").rstrip("/")
    if root and _is_absolute_posix(path):
        if path.lower() == root.lower():
            return ""
        prefix = root + "/"
        if path.lower().startswith(prefix.lower()):
            return path[len(prefix) :]
    return path


def _is_absolute_posix(path: str) -> bool:
    """True for a POSIX-rooted path or a Windows drive path (``C:/...``)."""
    return path.startswith("/") or bool(re.match(r"^[A-Za-z]:/", path))


def looks_like_lcov(text: str) -> bool:
    """Grammar sniff: whether a file's text is lcov data.

    Coverlet's lcov file name is not documented, so candidates found under the
    test-results attachment folders are identified by grammar instead of by
    name: the text must contain at least one line starting with ``SF:`` and at
    least one ``end_of_record`` line. Both markers must start their line, so
    an attachment that merely mentions ``SF:`` mid-line is rejected.
    """
    has_sf = False
    has_end = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("SF:"):
            has_sf = True
        elif line == "end_of_record":
            has_end = True
        if has_sf and has_end:
            return True
    return False


def is_excluded(path: str, extra_globs: list[str]) -> bool:
    """Whether a repo-relative POSIX path is excluded from the denominator.

    The default set follows the skill's test-project conventions,
    case-insensitively: any path segment named ``test`` or ``tests`` or ending
    ``.Tests``, plus basenames ending ``Tests.cs`` or ``.Designer.cs``. User
    globs match against the full path and the basename.
    """
    parts = path.split("/")
    for part in parts[:-1]:
        low = part.lower()
        if low in ("test", "tests") or low.endswith(".tests"):
            return True
    base = parts[-1]
    low_base = base.lower()
    if low_base.endswith(("tests.cs", ".designer.cs")):
        return True
    for pattern in extra_globs:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(base, pattern):
            return True
    return False


def _strip_cs_noncode(content: str) -> str:
    """Blank out comments, string literals, and char literals in C# source.

    Each skipped region collapses to a single space so keyword scanning never
    matches text inside a comment or a literal, and adjacent tokens never fuse.
    """
    out: list[str] = []
    i = 0
    n = len(content)
    while i < n:
        char = content[i]
        nxt = content[i + 1] if i + 1 < n else ""
        if char == "/" and nxt == "/":
            while i < n and content[i] != "\n":
                i += 1
        elif char == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (content[i] == "*" and content[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
        elif char == "@" and nxt == '"':
            i += 2
            while i < n:
                if content[i] == '"':
                    if i + 1 < n and content[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
        elif char == '"':
            i += 1
            while i < n and content[i] != '"':
                if content[i] == "\\":
                    i += 1
                i += 1
            i += 1
        elif char == "'":
            i += 1
            while i < n and content[i] != "'":
                if content[i] == "\\":
                    i += 1
                i += 1
            i += 1
        else:
            out.append(char)
            i += 1
            continue
        out.append(" ")
    return "".join(out)


def is_bodyless_cs(content: str) -> bool:
    """Whether a ``.cs`` file declares only interfaces, enums, or delegates.

    Such files compile to no method bodies, so the coverlet collector has no
    sequence points to instrument and emits no ``SF:`` record for them; the
    coverage gate reports them as non-coverable instead of counting their
    added lines as uncovered. A file declaring any class, struct, or record
    stays coverable, and so does a file with no type declaration at all
    (top-level statements are code). Detection requires an identifier after
    the keyword, so a ``where T : class`` constraint is not a declaration,
    and comments and string literals are blanked out before scanning.
    """
    stripped = _strip_cs_noncode(content)
    found = set(_CS_TYPE_DECL_RE.findall(stripped))
    if not found:
        return False
    return found <= _BODYLESS_KEYWORDS


def map_changed_projects(
    paths: list[str], csproj_paths: list[str]
) -> tuple[set[str], list[str]]:
    """Map changed files to production projects by nearest ``.csproj`` ancestor.

    A Stryker run from one test project directory mutates only the production
    projects that test project references, so a branch whose changes resolve
    to more than one project needs the solution-mode run; this mapping feeds
    that warning.

    Args:
        paths: Repo-relative POSIX paths of the in-scope changed ``.cs`` files.
        csproj_paths: Repo-relative POSIX paths of every ``.csproj`` in the
            repo (a directory listing snapshot).

    Returns:
        The set of project directories the changed files resolve to (the repo
        root is ``""``), and the list of files with no ``.csproj`` ancestor.
    """
    project_dirs = {
        csproj.rsplit("/", 1)[0] if "/" in csproj else "" for csproj in csproj_paths
    }
    projects: set[str] = set()
    unmapped: list[str] = []
    for path in paths:
        parts = path.split("/")[:-1]
        found: str | None = None
        for depth in range(len(parts), -1, -1):
            candidate = "/".join(parts[:depth])
            if candidate in project_dirs:
                found = candidate
                break
        if found is None:
            unmapped.append(path)
        else:
            projects.add(found)
    return projects, unmapped


def mutation_scope_empty(
    added_by_file: dict[str, set[int]], extra_globs: list[str]
) -> tuple[bool, bool]:
    """Whether the mutation scope is empty, and whether user globs emptied it.

    The scope is the same set the coverage gate counts: added lines in
    non-excluded ``.cs`` files. On an empty scope the gate never invokes the
    mutation tool. The second flag is True only when the scope is empty with
    the user globs applied but non-empty without them, so the report can name
    ``--exclude`` as the cause.
    """

    def has_scope(globs: list[str]) -> bool:
        return any(
            lines and path.endswith(".cs") and not is_excluded(path, globs)
            for path, lines in added_by_file.items()
        )

    if has_scope(extra_globs):
        return False, False
    return True, bool(extra_globs) and has_scope([])


@dataclass
class CoverageReport:
    """Intersection of added lines with coverage data."""

    per_file: list[tuple[str, int, int]] = field(default_factory=list)
    uncovered: list[tuple[str, int]] = field(default_factory=list)
    not_instrumented: list[tuple[str, int]] = field(default_factory=list)
    non_coverable: list[str] = field(default_factory=list)
    total_covered: int = 0
    total_coverable: int = 0


def intersect(
    added_by_file: dict[str, set[int]],
    coverage_by_file: dict[str, dict[int, int]],
    extra_globs: list[str],
    bodyless_paths: set[str],
) -> CoverageReport:
    """Intersect added ``.cs`` lines with lcov data into a coverage report.

    An added line in an instrumented file is *coverable* only when lcov
    emitted a ``DA:`` record for it (blank lines, comments, and other
    non-executable additions carry none and stay out of the denominator). A
    changed ``.cs`` file with no ``SF:`` record at all is an everyday .NET
    layout mistake, usually a project no test project references, so every
    one of its added lines counts as coverable and uncovered, dragging the
    total through the threshold check instead of silently dropping out of it.
    The one carve-out is ``bodyless_paths``: files whose type declarations are
    all interfaces, enums, or delegates compile to no method bodies, so they
    are reported as non-coverable and excluded from the ratio.

    Args:
        added_by_file: Added lines per file, from ``parse_added_lines``.
        coverage_by_file: Per-file line hit counts from ``parse_lcov``.
        extra_globs: User exclusion globs.
        bodyless_paths: Not-instrumented files the content classifier marked
            as interface/enum/delegate-only.

    Returns:
        A ``CoverageReport`` with per-file and total covered/coverable counts.
    """
    report = CoverageReport()
    for path in sorted(added_by_file):
        if not path.endswith(".cs"):
            continue
        if is_excluded(path, extra_globs):
            continue
        added = added_by_file[path]
        if not added:
            continue
        line_hits = coverage_by_file.get(path)
        if line_hits is None:
            if path in bodyless_paths:
                report.non_coverable.append(path)
                continue
            report.not_instrumented.append((path, len(added)))
            report.total_coverable += len(added)
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
# Orchestration: preflight, the two gates, reporting. Shells out to git and
# dotnet; never exercised by the unit tests.
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


def _path_value(value: str) -> str:
    """argparse type for path flags: rejects a value that looks like a flag.

    Every path flag splices its value into a tool command line, so a value
    with a leading dash could smuggle in an option; it is a usage error.
    """
    if value.startswith("-"):
        raise argparse.ArgumentTypeError(
            f"path value must not start with '-': {value!r}"
        )
    return value


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = _ArgParser(
        prog="csharp_quality_gate.py",
        description=(
            "New-code quality gate: diff coverage (dotnet test with the "
            "coverlet collector) and mutation testing (Stryker.NET --since)."
        ),
        epilog=(
            "Exit codes: 0 pass; 2 coverage gate failed (both gates report even "
            "when both fail); 3 mutation gate failed; 64 usage error; 70 an "
            "underlying tool ran and failed; 78 environment not ready."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="base ref to diff against (default: origin/HEAD, then main, then master)",
    )
    parser.add_argument(
        "--lcov-file",
        type=_path_value,
        metavar="PATH",
        help="consume a pre-generated lcov file instead of running dotnet test",
    )
    parser.add_argument(
        "--cov-threshold",
        type=_threshold_percent,
        default=DEFAULT_COV_THRESHOLD,
        metavar="PCT",
        help="minimum %% of new coverable lines that must be covered (default: 90)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="GLOB",
        default=[],
        help="extra glob (matched against repo-relative path and basename) to "
        "exclude from the coverage denominator; repeatable",
    )
    parser.add_argument(
        "--skip-mutants",
        action="store_true",
        help="run only the coverage gate",
    )
    parser.add_argument(
        "--test-target",
        type=_path_value,
        default=".",
        metavar="PATH",
        help="project, solution, or directory argument for dotnet test (default: .)",
    )
    parser.add_argument(
        "--stryker-dir",
        type=_path_value,
        metavar="PATH",
        help="directory to run dotnet stryker from; Stryker requires the test "
        "project directory (default: the current directory)",
    )
    parser.add_argument(
        "--stryker-solution",
        type=_path_value,
        metavar="PATH",
        help="solution file for full-solution mutation scope; Stryker runs from "
        "the solution file's directory (cannot be combined with --stryker-dir)",
    )
    args = parser.parse_args(argv)
    if args.stryker_dir is not None and args.stryker_solution is not None:
        parser.error("--stryker-solution cannot be combined with --stryker-dir")
    return args


def _log(message: str) -> None:
    """Write a progress line to stderr, ordered after any pending stdout."""
    sys.stdout.flush()
    print(message, file=sys.stderr, flush=True)


def _log_command(cmd: list[str]) -> None:
    """Echo a subprocess command line to stderr so any phase is reproducible."""
    _log("+ " + " ".join(shlex.quote(part) for part in cmd))


def run_capture(
    cmd: list[str], cwd: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command capturing stdout/stderr as decoded text."""
    _log_command(cmd)
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
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
    """Confirm a tool answers its probe command; return its first output line."""
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
            raise GateError(
                EXIT_ENV_NOT_READY, f"invalid base ref (leading dash): {ref}"
            )
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


def _git_diff(git: str, cwd: str, merge_base: str) -> str:
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
        "-U0",
        merge_base,
        "--",
    ]
    result = run_capture(cmd, cwd=cwd)
    if result.returncode != 0:
        raise GateError(EXIT_TOOL_FAILED, f"git diff failed: {result.stderr.strip()}")
    return result.stdout


def _tracked_dirty(git: str, cwd: str) -> bool:
    """Whether the working tree has uncommitted changes to tracked files."""
    result = run_capture([git, "status", "--porcelain"], cwd=cwd)
    if result.returncode != 0:
        raise GateError(EXIT_TOOL_FAILED, f"git status failed: {result.stderr.strip()}")
    return any(
        line and not line.startswith("??") for line in result.stdout.splitlines()
    )


def _untracked_cs(git: str, cwd: str) -> list[str]:
    """List untracked, non-ignored ``.cs`` files (invisible to git diff)."""
    result = run_capture([git, "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.endswith(".cs")]


def _list_csprojs(git: str, cwd: str) -> list[str]:
    """List tracked and untracked ``.csproj`` paths, repo-relative POSIX."""
    result = run_capture(
        [
            git,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.csproj",
        ],
        cwd=cwd,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _read_worktree_file(repo_root: str, rel_path: str) -> str | None:
    """Read a repo file's working-tree text, or None if unreadable."""
    try:
        return (Path(repo_root) / rel_path).read_text(
            encoding="utf-8", errors="replace"
        )
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


def _default_exclusion_desc() -> str:
    """One-line description of the default coverage exclusions."""
    return (
        "path segments test/, tests/, *.Tests/; basenames *Tests.cs, "
        "*.Designer.cs (all case-insensitive)"
    )


def _print_header(
    args: argparse.Namespace,
    base_ref: str,
    base_sha: str,
    merge_base: str,
    dotnet_ver: str,
    stryker_ver: str | None,
    mutation_line: str,
) -> None:
    """Print the reproducibility header to stdout."""
    print("== C# new-code quality gate ==")
    print(f"base ref:    {base_ref} ({base_sha[:12]})")
    print(f"merge-base:  {merge_base[:12]}")
    print(f"dotnet:      {dotnet_ver}")
    if stryker_ver:
        print(f"dotnet-stryker: {stryker_ver}")
    if args.lcov_file:
        print(f"coverage source: pre-generated lcov ({args.lcov_file})")
    print(mutation_line)
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
    for path in report.non_coverable:
        print(
            f"  {path}: non-coverable (interface, enum, or delegate declarations "
            "only; excluded from ratio)"
        )
    for path, count in report.not_instrumented:
        print(
            f"  {path}: not instrumented (counted uncovered, {count} added lines; "
            "likely no test project references its project, so the collector "
            "never saw it)"
        )
    if report.uncovered:
        print("  uncovered new lines:")
        for path, line in report.uncovered:
            print(
                f"    {path}:{line}: {strip_control(_read_line(repo_root, path, line))}"
            )
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


def _collect_lcov_texts(results_dir: str) -> list[str]:
    """Gather lcov texts from the per-run attachment subfolders.

    Coverlet writes each attachment into a per-run subdirectory of the VSTest
    results directory, and the lcov file name it uses is undocumented, so
    candidates are identified by grammar (``looks_like_lcov``). Files sitting
    directly in the results root (test logs, trx files) are never sniffed.
    """
    texts: list[str] = []
    root_norm = os.path.normpath(results_dir)
    for walk_root, _dirs, files in sorted(os.walk(results_dir)):
        if os.path.normpath(walk_root) == root_norm:
            continue
        for name in sorted(files):
            try:
                text = Path(walk_root, name).read_text(
                    encoding="utf-8", errors="replace"
                )
            except OSError:
                continue
            if looks_like_lcov(text):
                texts.append(text)
    return texts


def _obtain_lcov(args: argparse.Namespace, dotnet: str, cwd: str, tmpdir: str) -> str:
    """Return lcov text, either from --lcov-file or by running dotnet test."""
    if args.lcov_file:
        if not os.path.isfile(args.lcov_file):
            raise GateError(
                EXIT_ENV_NOT_READY, f"--lcov-file not found: {args.lcov_file}"
            )
        return Path(args.lcov_file).read_text(encoding="utf-8", errors="replace")
    results_dir = os.path.join(tmpdir, "testresults")
    code = run_streaming(
        [
            dotnet,
            "test",
            args.test_target,
            "--collect:XPlat Code Coverage;Format=lcov",
            "--results-directory",
            results_dir,
        ],
        cwd=cwd,
    )
    if code != 0:
        raise GateError(EXIT_TOOL_FAILED, f"dotnet test exited {code}")
    texts = _collect_lcov_texts(results_dir)
    if not texts:
        raise GateError(
            EXIT_TOOL_FAILED,
            "dotnet test produced no lcov output under the results directory",
        )
    return "\n".join(texts)


def _find_json_report(out_dir: str) -> bool:
    """Whether the Stryker json reporter left a report under the output tree.

    This is an existence signal only: no report content is ever parsed. A
    present report means the run completed and scored below 100; an absent
    one means the run never completed. Stryker 4.16 writes the report to
    ``reports/mutation-report.json`` under the ``--output`` directory, so the
    check scans the ``reports`` subtree for any ``.json`` file rather than
    pinning the file name.
    """
    reports_dir = os.path.join(out_dir, "reports")
    for _walk_root, _dirs, files in os.walk(reports_dir):
        if any(name.endswith(".json") for name in files):
            return True
    return False


def _run_mutation_gate(
    dotnet: str,
    workdir: str,
    merge_base: str,
    solution_path: str | None,
    tmpdir: str,
) -> bool:
    """Run Stryker over the changed scope; return True when the gate fails."""
    out_dir = os.path.join(tmpdir, "stryker")
    cmd = [
        dotnet,
        "stryker",
        f"--since:{merge_base}",
        "--threshold-high",
        "100",
        "--threshold-low",
        "100",
        "--break-at",
        "100",
        "--output",
        out_dir,
        "--reporter",
        "json",
        "--reporter",
        "cleartext",
    ]
    if solution_path is not None:
        cmd += ["--solution", solution_path]
    code = run_streaming(cmd, cwd=workdir)
    if code == 0:
        print("-- mutation gate: all scoped mutants caught --")
        return False
    if _find_json_report(out_dir):
        print(
            "-- mutation gate: FAILED (mutation score below 100 in the changed "
            "scope; survivors are in the Stryker output above) --"
        )
        return True
    raise GateError(
        EXIT_TOOL_FAILED,
        f"dotnet stryker exited {code} without a completed report "
        "(tool failure, not a gate verdict)",
    )


def _run_gate(args: argparse.Namespace, tmpdir: str) -> int:
    """Run preflight and both gates; return the process exit code."""
    started = time.monotonic()

    git = _resolve_tool("git")
    if git is None:
        raise GateError(EXIT_ENV_NOT_READY, "git not found on PATH")
    dotnet = _resolve_tool("dotnet")
    if dotnet is None:
        raise GateError(
            EXIT_ENV_NOT_READY,
            "dotnet not found on PATH; install the .NET SDK from "
            "https://dotnet.microsoft.com",
        )

    tools = (("git", git), ("dotnet", dotnet))
    _refuse_repo_local_tools(tools, os.getcwd())

    toplevel = run_capture([git, "rev-parse", "--show-toplevel"])
    if toplevel.returncode != 0:
        raise GateError(EXIT_ENV_NOT_READY, "not inside a git repository")
    repo_root = toplevel.stdout.strip()
    repo_cwd = os.path.normpath(repo_root)

    _refuse_repo_local_tools(tools, repo_root)

    if not args.skip_mutants and _tracked_dirty(git, repo_cwd):
        _log(
            "warning: uncommitted tracked changes present; whether Stryker's "
            "--since scope covers working-tree-only changes is unverified, so "
            "uncommitted lines may not be mutation-gated. The verdict is only "
            "trustworthy once the changes are committed; committing is the "
            "user's action, so ask them, or run --skip-mutants."
        )

    base_ref, base_sha = _resolve_base_ref(git, repo_cwd, args.base)

    merge = run_capture([git, "merge-base", base_sha, "HEAD"], cwd=repo_cwd)
    if merge.returncode != 0:
        raise GateError(
            EXIT_ENV_NOT_READY, f"could not compute merge-base of {base_ref} and HEAD"
        )
    merge_base = merge.stdout.strip()

    zero_diff = _git_diff(git, repo_cwd, merge_base)
    added_by_file = parse_added_lines(zero_diff)

    scope_empty, emptied_by_globs = mutation_scope_empty(added_by_file, args.exclude)
    mutation_will_run = not args.skip_mutants and not scope_empty

    stryker_workdir = ""
    solution_path: str | None = None
    if mutation_will_run:
        if args.stryker_solution:
            solution_path = os.path.abspath(args.stryker_solution)
            if not os.path.isfile(solution_path):
                raise GateError(
                    EXIT_ENV_NOT_READY,
                    f"--stryker-solution not found: {args.stryker_solution}",
                )
            stryker_workdir = os.path.dirname(solution_path)
        else:
            stryker_workdir = os.path.abspath(args.stryker_dir or ".")
            if not os.path.isdir(stryker_workdir):
                raise GateError(
                    EXIT_ENV_NOT_READY, f"--stryker-dir not found: {args.stryker_dir}"
                )

    dotnet_ver = _tool_version(
        [dotnet, "--version"],
        repo_cwd,
        "dotnet",
        "install the .NET SDK from https://dotnet.microsoft.com",
    )
    stryker_ver = None
    if mutation_will_run:
        # Stryker has no --version flag (--version is a dashboard option that
        # takes a value); --help exits 0 when the tool is installed.
        stryker_ver = _tool_version(
            [dotnet, "stryker", "--help"],
            stryker_workdir,
            "dotnet-stryker",
            "dotnet tool install -g dotnet-stryker",
        )

    untracked = _untracked_cs(git, repo_cwd)
    if untracked:
        _log(
            "warning: untracked .cs files are invisible to git diff and to both gates:"
        )
        for name in untracked:
            _log(f"  {name}")
        _log(
            "  a git write makes them visible (a commit, or `git add -N <file>`); "
            "git writes are the user's, so ask them first."
        )

    if mutation_will_run and solution_path is None:
        scoped = [
            path
            for path, lines in added_by_file.items()
            if lines and path.endswith(".cs") and not is_excluded(path, args.exclude)
        ]
        projects, unmapped = map_changed_projects(scoped, _list_csprojs(git, repo_cwd))
        if len(projects) > 1:
            listed = ", ".join(sorted(name or "<repo root>" for name in projects))
            _log(
                f"warning: the changed files span {len(projects)} projects "
                f"({listed}); a single-project Stryker run mutates only the "
                "production projects its test project references, so this run "
                "may not cover all changed projects. Pass --stryker-solution "
                "for full-solution scope."
            )
        if unmapped:
            _log(
                "warning: no .csproj ancestor found for: " + ", ".join(sorted(unmapped))
            )

    if args.skip_mutants:
        mutation_line = "mutation gate: skipped (--skip-mutants)"
    elif scope_empty:
        mutation_line = "mutation gate: no added in-scope lines (tool not invoked)"
    else:
        mutation_line = (
            f"mutation scope: --since:{merge_base[:12]} (the resolved merge-base, "
            "passed to dotnet stryker)"
        )

    _print_header(
        args, base_ref, base_sha, merge_base, dotnet_ver, stryker_ver, mutation_line
    )

    cov_start = time.monotonic()
    lcov_text = _obtain_lcov(args, dotnet, repo_cwd, tmpdir)
    coverage_by_file = parse_lcov(lcov_text, repo_root)
    bodyless: set[str] = set()
    for path, lines in added_by_file.items():
        if not lines or not path.endswith(".cs") or is_excluded(path, args.exclude):
            continue
        if path in coverage_by_file:
            continue
        content = _read_worktree_file(repo_root, path)
        if content is not None and is_bodyless_cs(content):
            bodyless.add(path)
    report = intersect(added_by_file, coverage_by_file, args.exclude, bodyless)
    verdict = coverage_passes(
        report.total_covered, report.total_coverable, args.cov_threshold
    )
    _print_coverage_report(
        report, verdict, args.cov_threshold, repo_root, time.monotonic() - cov_start
    )
    coverage_failed = verdict is False

    mutation_failed = False
    if args.skip_mutants:
        print("-- mutation gate: skipped (--skip-mutants) --\n")
    elif scope_empty:
        note = " (user --exclude globs emptied the scope)" if emptied_by_globs else ""
        print(
            f"-- mutation gate: nothing to check (no added in-scope lines){note} --\n"
        )
    else:
        mut_start = time.monotonic()
        mutation_failed = _run_mutation_gate(
            dotnet, stryker_workdir, merge_base, solution_path, tmpdir
        )
        print(f"  mutation phase: {time.monotonic() - mut_start:.1f}s\n")

    _log(f"quality gate finished in {time.monotonic() - started:.1f}s")
    if coverage_failed:
        return EXIT_COVERAGE_FAILED
    if mutation_failed:
        return EXIT_MUTATION_FAILED
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Entry point: run the gate and clean up the temp dir on success."""
    args = parse_args(argv)
    tmpdir = tempfile.mkdtemp(prefix="csharp-quality-gate-")
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
