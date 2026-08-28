#!/usr/bin/env python3
"""New-code quality gate for Python projects.

Grades the lines a branch adds, over the merge-base to working-tree diff:

* Coverage: pytest-cov lcov intersected with the added lines against a new-line
  threshold.
* Mutation: Cosmic Ray scoped to the changed lines with ``cr-filter-git``,
  failing when a mutant survives the suite.
* File size: new and cap-crossing production files graded against per-language
  line tiers. Needs only git and the filesystem, so it runs first and reports
  even where pytest and cosmic-ray are absent.

Standard library only. The pure functions (diff/lcov parsing, path
normalization, threshold check) are the language-agnostic core, deliberately
duplicated in the sibling ``rust`` and ``csharp`` gates because each skill
folder is a self-contained distribution unit; a fix to that core belongs in all
three. See ``skills/python/testing-guidelines.md`` for the two-gate model,
install commands, and the trust boundary.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import platform
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
DEFAULT_TIMEOUT_SECONDS = 300.0

SIZE_WARN_THRESHOLD = 800
SIZE_FAIL_CAP = 1500
SIZE_GROWTH_ALLOWANCE = 50
SIZE_READ_BYTE_CAP = 2_000_000
SIZE_DEFAULT_EXCLUDE_GLOBS = ("skills/*/scripts/*_quality_gate.py",)

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_C_ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11}
_BARE_RATE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_RATE_CONTEXT_RE = re.compile(
    r"\b(?:rate|surviv\w*)\b\D*(\d+(?:\.\d+)?)", re.IGNORECASE
)


# --------------------------------------------------------------------------
# Pure functions: diff/lcov parsing, path normalization, config, gating.
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
    when the path is absolute (coverage.py usually writes relative paths, but
    the shape depends on its configuration). A relative path is returned
    as-is.
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


def is_excluded(path: str, extra_globs: list[str]) -> bool:
    """Whether a repo-relative POSIX path is excluded from the denominator.

    The default set follows the skill's separate-``tests/``-tree convention:
    any path with a ``tests`` segment, plus the ``test_*.py``, ``*_test.py``,
    and ``conftest.py`` basenames. User globs match against the full path and
    the basename.
    """
    parts = path.split("/")
    if "tests" in parts:
        return True
    base = parts[-1]
    if base == "conftest.py":
        return True
    if base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py")):
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
            old_path = _unquote_diff_path(raw[len("rename from ") :])
        elif raw.startswith("rename to "):
            renamed = _unquote_diff_path(raw[len("rename to ") :])
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
    ``tests`` segment, plus the ``test_*.py``, ``*_test.py``, and
    ``conftest.py`` basenames.
    """
    parts = path.split("/")
    if "tests" in parts:
        return True
    base = parts[-1]
    if base == "conftest.py":
        return True
    return base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))


def is_size_skipped(path: str, extra_globs: list[str]) -> bool:
    """Whether a path is excluded from the size gate entirely.

    The gate's own scripts are skipped by default: they are large single-file
    distribution units by design (the core is duplicated across the three
    language gates), so the gate never flags its own tooling. User ``--exclude``
    globs skip further files, matched against the full path and the basename.
    Test files are not skipped; they are evaluated warn-only via
    ``is_size_test_file``.
    """
    base = path.split("/")[-1]
    for pattern in (*SIZE_DEFAULT_EXCLUDE_GLOBS, *extra_globs):
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


def mutation_scope_empty(
    added_by_file: dict[str, set[int]], extra_globs: list[str]
) -> tuple[bool, bool]:
    """Whether the mutation scope is empty, and whether user globs emptied it.

    The scope is the same set the coverage gate counts: added lines in
    non-excluded ``.py`` files. On an empty scope the gate never invokes
    Cosmic Ray. The second flag is True only when the scope is empty with the
    user globs applied but non-empty without them, so the report can name
    ``--exclude`` as the cause.
    """

    def has_scope(globs: list[str]) -> bool:
        return any(
            lines and path.endswith(".py") and not is_excluded(path, globs)
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
    total_covered: int = 0
    total_coverable: int = 0


def intersect(
    added_by_file: dict[str, set[int]],
    coverage_by_file: dict[str, dict[int, int]],
    extra_globs: list[str],
) -> CoverageReport:
    """Intersect added ``.py`` lines with lcov data into a ``CoverageReport``.

    An added line in an instrumented file is *coverable* only when lcov emitted
    a ``DA:`` record for it (blank lines, comments, and other non-executable
    additions carry none and stay out of the denominator). A changed ``.py``
    file with no ``SF:`` record at all is an everyday layout mistake, a module
    the suite never imports or one the coverage sources do not include, so every
    added line counts as coverable and uncovered, dragging the total through the
    threshold check instead of silently dropping out of it.
    """
    report = CoverageReport()
    for path in sorted(added_by_file):
        if not path.endswith(".py"):
            continue
        if is_excluded(path, extra_globs):
            continue
        added = added_by_file[path]
        if not added:
            continue
        line_hits = coverage_by_file.get(path)
        if line_hits is None:
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


class GateError(Exception):
    """A controlled failure carrying the process exit code to return."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def toml_basic_string(value: str) -> str:
    """Encode a string as a TOML basic string, escaping ``\\`` and ``"``.

    Control characters, newlines included, are rejected as a usage error
    (``GateError``) rather than escaped: none of the values the gate
    interpolates (a module path, a test command, a git ref) legitimately
    contains one, and accepting them would let a crafted value smuggle extra
    TOML lines into the generated config.
    """
    for char in value:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            raise GateError(
                EXIT_USAGE,
                f"control character not allowed in a configuration value: {value!r}",
            )
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_cosmic_ray_config(
    module_path: str, test_command: str, timeout: float, scope_ref: str
) -> str:
    """Generate the Cosmic Ray TOML configuration for one gate run.

    The config uses the local distributor and the git filter, so a following
    ``cr-filter-git`` pass skips every mutation outside the lines changed since
    ``scope_ref``. All interpolated strings go through ``toml_basic_string``,
    which raises ``GateError`` on a control character.
    """
    return (
        "[cosmic-ray]\n"
        f"module-path = {toml_basic_string(module_path)}\n"
        f"timeout = {float(timeout)}\n"
        "excluded-modules = []\n"
        f"test-command = {toml_basic_string(test_command)}\n"
        "\n"
        "[cosmic-ray.distributor]\n"
        'name = "local"\n'
        "\n"
        "[cosmic-ray.filters.git-filter]\n"
        f"branch = {toml_basic_string(scope_ref)}\n"
    )


def parse_survival_rate(text: str) -> float | None:
    """Extract a survival percentage from ``cr-rate`` output, or None.

    Separates a verdict from a crash: parseable output carries the survival
    rate the gate judges, while unparseable output (a traceback, for one) is a
    tool failure. cosmic-ray 8.7.0 prints exactly one bare ``{rate:.2f}`` line
    (``50.00``), so a line that is nothing but a number is the primary match;
    a percent-marked number and a number after the word ``rate`` or
    ``surviv...`` are fallbacks for other versions.
    """
    for line in text.splitlines():
        match = _BARE_RATE_RE.match(line)
        if match:
            return float(match.group(1))
    for line in text.splitlines():
        match = _PERCENT_RE.search(line)
        if match:
            return float(match.group(1))
    for line in text.splitlines():
        match = _RATE_CONTEXT_RE.search(line)
        if match:
            return float(match.group(1))
    return None


def files_outside_module_path(paths: list[str], module_path: str) -> list[str]:
    """The subset of in-scope changed files not equal to and not under the
    mutation ``module_path`` (all repo-relative POSIX).

    Cosmic Ray only generates mutants for files under ``module-path``, and its
    git filter marks a skipped mutant as killed, so a mutation scope made
    entirely of files outside the module path produces an all-skipped session
    that ``cr-rate`` scores as 0.00 survival: a silent false pass. The gate
    refuses that shape and warns about partial mismatches.
    """
    root = module_path.replace("\\", "/").rstrip("/")
    if root in ("", "."):
        return []
    prefix = root + "/"
    return [path for path in paths if path != root and not path.startswith(prefix)]


# --------------------------------------------------------------------------
# Orchestration: preflight, the size/coverage/mutation phases, reporting.
# Shells out to git, pytest, and cosmic-ray; never run by the unit tests.
# --------------------------------------------------------------------------


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


def _positive_seconds(value: str) -> float:
    """argparse type for ``--timeout``: a positive number of seconds."""
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid number: {value!r}") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("timeout must be positive")
    return number


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = _ArgParser(
        prog="python_quality_gate.py",
        description=(
            "New-code quality gate: diff coverage (pytest-cov lcov) and "
            "mutation testing (Cosmic Ray with cr-filter-git)."
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
        type=_path_value,
        metavar="PATH",
        help="consume a pre-generated lcov file instead of running pytest",
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
        "exclude from the coverage denominator and the file-size gate; repeatable "
        "(the gate's own *_quality_gate.py scripts are already size-exempt)",
    )
    parser.add_argument(
        "--skip-mutants",
        action="store_true",
        help="run only the coverage gate",
    )
    parser.add_argument(
        "--module-path",
        type=_path_value,
        default="src",
        metavar="PATH",
        help="package directory or module Cosmic Ray mutates (default: src)",
    )
    parser.add_argument(
        "--test-command",
        default=f"{sys.executable} -m pytest",
        metavar="CMD",
        help="test command Cosmic Ray runs against each mutant "
        "(default: the launching interpreter with -m pytest)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_seconds,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help="per-mutant test timeout for the Cosmic Ray config (default: 300)",
    )
    return parser.parse_args(argv)


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


def _venv_roots() -> list[str]:
    """Verified virtual-environment roots eligible for the tool exemption."""
    roots: list[str] = []
    if sys.prefix != sys.base_prefix:
        roots.append(sys.prefix)
    declared = os.environ.get("VIRTUAL_ENV")
    if declared and os.path.isfile(os.path.join(declared, "pyvenv.cfg")):
        roots.append(declared)
    return roots


def _is_venv_exempt(tool_path: str, venv_roots: list[str]) -> bool:
    """Whether a tool lives inside a verified virtual environment.

    A tool is exempt when it sits under the running interpreter's own venv,
    under a ``VIRTUAL_ENV`` root that actually holds a ``pyvenv.cfg``, or in a
    scripts directory whose parent holds a ``pyvenv.cfg``. A stale or mis-set
    ``VIRTUAL_ENV`` pointing at a directory with no ``pyvenv.cfg`` exempts
    nothing.
    """
    for root in venv_roots:
        if _is_within(tool_path, root):
            return True
    parent = os.path.dirname(os.path.dirname(os.path.realpath(tool_path)))
    return os.path.isfile(os.path.join(parent, "pyvenv.cfg"))


def _refuse_repo_local_tools(tools: tuple[tuple[str, str], ...], root: str) -> None:
    """Refuse any tool that resolved to a path inside ``root``.

    Windows resolves executables from the process working directory ahead of
    PATH on Python versions before 3.12, so a binary committed to the target
    repo could shadow the real tool. Nothing inside the tree being checked may
    run as a tool, with one carve-out: an executable inside a verified virtual
    environment, because this skill's recommended layout puts ``.venv`` inside
    the repo and the gate must test with the interpreter that carries the
    project's dependencies.
    """
    venv_roots = _venv_roots()
    for name, tool_path in tools:
        if _is_within(tool_path, root) and not _is_venv_exempt(tool_path, venv_roots):
            raise GateError(
                EXIT_ENV_NOT_READY,
                f"{name} resolved to a path inside the target repo; refusing to run "
                "a repo-local binary",
            )


def _tool_version(cmd: list[str], cwd: str, tool_name: str, install_cmd: str) -> str:
    """Confirm a tool responds to --version; return its version line."""
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


def _untracked_py(git: str, cwd: str) -> list[str]:
    """List untracked, non-ignored ``.py`` files (invisible to git diff)."""
    result = run_capture([git, "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.endswith(".py")]


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


def _size_counted_lines(text: str) -> tuple[int, int]:
    """Return (counted, total) line counts. For Python the two are equal."""
    total = len(text.splitlines())
    return total, total


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
    """Grade every added or new ``.py`` file against the size policy; untracked
    ``.py`` files fold in as new (invisible to the diff, so the other gates miss
    them, but exactly what the size gate is here to catch).
    """
    candidates: dict[str, tuple[bool, str | None]] = {}
    for path, lines in added_by_file.items():
        if lines and path.endswith(".py"):
            candidates[path] = file_status.get(path, (False, path))
    for path in untracked:
        if path.endswith(".py") and path not in candidates:
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
        size = f"{finding.counted} production lines ({finding.total} total)"
    else:
        size = f"{finding.counted} lines"
    if finding.truncated:
        size += ", exceeds the read cap"
    action = ""
    if finding.verdict == "FAIL":
        action = "; split the new code into a new cohesive module (or --exclude a generated file)"
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
        f"production); net-growth allowance {SIZE_GROWTH_ALLOWANCE}; test files warn-only"
    )
    if not findings:
        print("  no added or newly created .py files to check")
    for finding in findings:
        print(f"  {_size_finding_line(finding)}")
    print(f"  file-size phase: {elapsed:.1f}s")
    print()


def _default_exclusion_desc() -> str:
    """One-line description of the default coverage exclusions."""
    return "paths under any tests/ segment; basenames test_*.py, *_test.py, conftest.py"


def _print_header(
    args: argparse.Namespace,
    base_ref: str,
    base_sha: str,
    merge_base: str,
    pytest_ver: str | None,
    pytest_cov_ver: str | None,
    cosmic_ray_ver: str | None,
    mutation_line: str,
) -> None:
    """Print the reproducibility header to stdout."""
    print("== Python new-code quality gate ==")
    print(f"base ref:    {base_ref} ({base_sha[:12]})")
    print(f"merge-base:  {merge_base[:12]}")
    print(f"python:      {platform.python_version()}")
    if pytest_ver:
        print(f"pytest:      {pytest_ver}")
    elif args.lcov_file:
        print(f"coverage source: pre-generated lcov ({args.lcov_file})")
    if pytest_cov_ver:
        print(f"pytest-cov:  {pytest_cov_ver}")
    if cosmic_ray_ver:
        print(f"cosmic-ray:  {cosmic_ray_ver}")
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
    for path, count in report.not_instrumented:
        print(
            f"  {path}: not instrumented (counted uncovered, {count} added lines; "
            "likely the suite never imports it, or the coverage sources do not "
            "include it)"
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


def _obtain_lcov(args: argparse.Namespace, cwd: str, tmpdir: str) -> str:
    """Return lcov text, either from --lcov-file or by running pytest."""
    if args.lcov_file:
        if not os.path.isfile(args.lcov_file):
            raise GateError(
                EXIT_ENV_NOT_READY, f"--lcov-file not found: {args.lcov_file}"
            )
        return Path(args.lcov_file).read_text(encoding="utf-8", errors="replace")
    out = os.path.join(tmpdir, "lcov.info")
    code = run_streaming(
        [sys.executable, "-m", "pytest", "--cov", f"--cov-report=lcov:{out}"],
        cwd=cwd,
    )
    if code != 0:
        raise GateError(EXIT_TOOL_FAILED, f"pytest exited {code}")
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        raise GateError(EXIT_TOOL_FAILED, "pytest produced no lcov output")
    return Path(out).read_text(encoding="utf-8", errors="replace")


def _run_mutation_gate(
    config_text: str,
    cr_tools: dict[str, str],
    cwd: str,
    tmpdir: str,
) -> bool:
    """Run the Cosmic Ray pipeline; return True when the gate fails.

    Every step is fail-closed: a non-zero exit from init, the git filter, the
    baseline run, exec, or the report aborts with the tool-failure code and
    the step's name. The git filter gets ``--config`` explicitly because
    without it the filter falls back to diffing against a branch named
    ``master``. The verdict comes from parsing the survival rate ``cr-rate``
    prints: cosmic-ray 8.7.0 treats ``--fail-over 0`` as unset (a falsy-zero
    check in the tool), so its exit code cannot carry the any-survivor
    verdict; the flag is still passed for versions that honor it. An
    unparseable rate is a tool failure, never a pass.
    """
    config_path = os.path.join(tmpdir, "cosmic-ray.toml")
    session_path = os.path.join(tmpdir, "session.sqlite")
    with open(config_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(config_text)
    steps = [
        (
            "cosmic-ray init",
            [cr_tools["cosmic-ray"], "init", config_path, session_path],
        ),
        (
            "cr-filter-git",
            [cr_tools["cr-filter-git"], "--config", config_path, session_path],
        ),
        ("cosmic-ray baseline", [cr_tools["cosmic-ray"], "baseline", config_path]),
        (
            "cosmic-ray exec",
            [cr_tools["cosmic-ray"], "exec", config_path, session_path],
        ),
        ("cr-report", [cr_tools["cr-report"], session_path]),
    ]
    for step_name, cmd in steps:
        code = run_streaming(cmd, cwd=cwd)
        if code != 0:
            raise GateError(
                EXIT_TOOL_FAILED,
                f"{step_name} exited {code} (tool failure, not a gate verdict)",
            )
    result = run_capture(
        [cr_tools["cr-rate"], "--fail-over", "0", session_path], cwd=cwd
    )
    output = (result.stdout or "") + (result.stderr or "")
    if output.strip():
        print(strip_control(output.strip()))
    rate = parse_survival_rate(output)
    if rate is None:
        raise GateError(
            EXIT_TOOL_FAILED,
            f"cr-rate exited {result.returncode} with no parseable survival rate "
            "(tool failure, not a gate verdict)",
        )
    if rate > 0:
        print(
            f"-- mutation gate: FAILED (survival rate {rate}%; see cr-report above) --"
        )
        return True
    if result.returncode != 0:
        raise GateError(
            EXIT_TOOL_FAILED,
            f"cr-rate exited {result.returncode} despite a 0.00 survival rate "
            "(tool failure, not a gate verdict)",
        )
    print("-- mutation gate: all scoped mutants caught --")
    return False


def _run_gate(args: argparse.Namespace, tmpdir: str) -> int:
    """Run preflight and both gates; return the process exit code."""
    started = time.monotonic()

    git = _resolve_tool("git")
    if git is None:
        raise GateError(EXIT_ENV_NOT_READY, "git not found on PATH")

    tools: list[tuple[str, str]] = [("git", git), ("python", sys.executable)]
    _refuse_repo_local_tools(tuple(tools), os.getcwd())

    toplevel = run_capture([git, "rev-parse", "--show-toplevel"])
    if toplevel.returncode != 0:
        raise GateError(EXIT_ENV_NOT_READY, "not inside a git repository")
    repo_root = toplevel.stdout.strip()
    repo_cwd = os.path.normpath(repo_root)

    _refuse_repo_local_tools(tuple(tools), repo_root)

    base_ref, base_sha = _resolve_base_ref(git, repo_cwd, args.base)

    merge = run_capture([git, "merge-base", base_sha, "HEAD"], cwd=repo_cwd)
    if merge.returncode != 0:
        raise GateError(
            EXIT_ENV_NOT_READY, f"could not compute merge-base of {base_ref} and HEAD"
        )
    merge_base = merge.stdout.strip()
    scope_ref = merge_base

    zero_diff = _git_diff(git, repo_cwd, merge_base)
    added_by_file = parse_added_lines(zero_diff)
    file_status = parse_diff_file_status(zero_diff)

    untracked = _untracked_py(git, repo_cwd)
    if untracked:
        _log(
            "warning: untracked .py files are invisible to git diff; coverage and "
            "mutation miss them, though the file-size gate checks them as new:"
        )
        for name in untracked:
            _log(f"  {name}")
        _log(
            "  a git write makes them visible to every gate (a commit, or "
            "`git add -N <file>`); git writes are the user's, so ask them first."
        )

    # File-size gate runs first, on git and the filesystem alone, so it reports
    # even where the toolchain is absent.
    size_start = time.monotonic()
    size_findings = _evaluate_sizes(
        added_by_file,
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
        if not args.skip_mutants and _tracked_dirty(git, repo_cwd):
            raise GateError(
                EXIT_ENV_NOT_READY,
                "uncommitted tracked changes present; Cosmic Ray mutates source on "
                "disk during exec, so an interrupted run would leave a mutant "
                "indistinguishable from your uncommitted work. The tree must be "
                "clean first; committing is the user's action, so ask them, or run "
                "--skip-mutants.",
            )

        scope_empty, emptied_by_globs = mutation_scope_empty(added_by_file, args.exclude)
        mutation_will_run = not args.skip_mutants and not scope_empty

        cr_tools: dict[str, str] = {}
        config_text = ""
        if mutation_will_run:
            for name in ("cosmic-ray", "cr-filter-git", "cr-report", "cr-rate"):
                resolved = _resolve_tool(name)
                if resolved is None:
                    raise GateError(
                        EXIT_ENV_NOT_READY,
                        f"{name} not found on PATH; install it with: pip install cosmic-ray",
                    )
                cr_tools[name] = resolved
            cr_entries = tuple(cr_tools.items())
            _refuse_repo_local_tools(cr_entries, os.getcwd())
            _refuse_repo_local_tools(cr_entries, repo_root)
            if not os.path.exists(os.path.join(repo_cwd, args.module_path)):
                raise GateError(
                    EXIT_ENV_NOT_READY, f"--module-path not found: {args.module_path}"
                )
            scoped = sorted(
                path
                for path, lines in added_by_file.items()
                if lines and path.endswith(".py") and not is_excluded(path, args.exclude)
            )
            outside = files_outside_module_path(scoped, args.module_path)
            if len(outside) == len(scoped):
                raise GateError(
                    EXIT_ENV_NOT_READY,
                    "no added in-scope file lies under --module-path "
                    f"{args.module_path}; Cosmic Ray would skip every mutant and "
                    "score 0.00 survival, a false pass. Pass the module path that "
                    "holds the changed files.",
                )
            if outside:
                _log(
                    "warning: these changed files are outside --module-path "
                    f"{args.module_path} and will not be mutation-tested: "
                    + ", ".join(outside)
                )
            config_text = build_cosmic_ray_config(
                args.module_path, args.test_command, args.timeout, scope_ref
            )

        pytest_ver = None
        pytest_cov_ver = None
        if not args.lcov_file:
            pytest_ver = _tool_version(
                [sys.executable, "-m", "pytest", "--version"],
                repo_cwd,
                "pytest",
                "pip install pytest pytest-cov",
            )
            pytest_cov_ver = _tool_version(
                [sys.executable, "-c", "import pytest_cov; print(pytest_cov.__version__)"],
                repo_cwd,
                "pytest-cov",
                "pip install pytest-cov",
            )
            pytest_cov_ver = f"pytest-cov {pytest_cov_ver}"
        cosmic_ray_ver = None
        if mutation_will_run:
            cosmic_ray_ver = _tool_version(
                [cr_tools["cosmic-ray"], "--version"],
                repo_cwd,
                "cosmic-ray",
                "pip install cosmic-ray",
            )

        if args.skip_mutants:
            mutation_line = "mutation gate: skipped (--skip-mutants)"
        elif scope_empty:
            mutation_line = "mutation gate: no added in-scope lines (tool not invoked)"
        else:
            mutation_line = (
                f"mutation scope: {scope_ref[:12]} (the resolved merge-base, passed to "
                f"the git filter); module path: {args.module_path}; "
                f"per-mutant timeout: {args.timeout:.0f}s"
            )

        _print_header(
            args,
            base_ref,
            base_sha,
            merge_base,
            pytest_ver,
            pytest_cov_ver,
            cosmic_ray_ver,
            mutation_line,
        )

        cov_start = time.monotonic()
        lcov_text = _obtain_lcov(args, repo_cwd, tmpdir)
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
        elif scope_empty:
            note = " (user --exclude globs emptied the scope)" if emptied_by_globs else ""
            print(
                f"-- mutation gate: nothing to check (no added in-scope lines){note} --\n"
            )
        else:
            mut_start = time.monotonic()
            mutation_failed = _run_mutation_gate(config_text, cr_tools, repo_cwd, tmpdir)
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
    tmpdir = tempfile.mkdtemp(prefix="python-quality-gate-")
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
