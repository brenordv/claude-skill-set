"""Run the guidance eval cases: verify, unpack, grade, summarize, pack.

``verify``
    Check every archive and member against its case file.
``unpack``
    Create a run directory with a stamp, the fixture, and the prompt.
``grade``
    Grade one run's ``result.json`` and append a line to the results file.
``summary``
    Print the counts for one run set.
``pack``
    Build a fixture archive from a directory and print its hashes.

Exit status: 0 when the command's check passed; 1 when it ran and the answer
is no (``verify`` found a mismatch, ``grade`` recorded a failed or invalid
run, ``summary`` is not clean); 2 when the command could not do its job (a
usage error, a bad case file or archive, a path it can't use).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, assert_never

from case_archive import (
    SCHEMA,
    Check,
    EvalError,
    case_ids,
    is_bytecode_cache,
    load_case,
    pack_directory,
    read_members,
    sha256_hex,
    validate_segment,
    verify_cases,
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ERROR = 2

DEFAULT_RUNS = 3
MAX_RESULT_BYTES = 256 * 1024
OBSERVED_LIMIT = 80

INVALID_REASONS = (
    "no_result_file",
    "bad_json",
    "bad_shape",
    "subagent_error",
    "timeout",
    "unpack_failed",
)
SAMPLE_NOTE = "per case: a failure is a signal, a clean sweep is weak evidence"

Outcome = Literal["pass", "fail", "invalid"]


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one check on one run."""

    id: str
    passed: bool
    observed: str


def skills_hash(repo_root: Path) -> str:
    """Hash the guidance under test: every file under ``skills/`` plus CLAUDE.md.

    Bytecode caches are skipped. The digest covers each file's repo-relative
    path and its bytes, in sorted path order.

    Args:
        repo_root: The repository whose guidance is hashed.

    Returns:
        The digest as lowercase hex.
    """
    files = [
        path
        for path in (repo_root / "skills").rglob("*")
        if path.is_file() and not is_bytecode_cache(path.relative_to(repo_root))
    ]
    claude_file = repo_root / "CLAUDE.md"
    if claude_file.is_file():
        files.append(claude_file)
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(repo_root).as_posix()):
        digest.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run_directory(results_dir: Path, run_set: str, case_id: str, run: int) -> Path:
    """Return the directory one run of one case lives in.

    Args:
        results_dir: Where run sets live.
        run_set: The run set's name.
        case_id: The case's id.
        run: The run's index.

    Returns:
        ``<results_dir>/<run_set>/<case_id>/<run>``.
    """
    return results_dir / run_set / case_id / str(run)


def unpack_case(
    cases_dir: Path,
    repo_root: Path,
    results_dir: Path,
    case_id: str,
    run_set: str,
    run: int,
    runs_expected: int,
    label: str,
) -> Path:
    """Create a run directory holding a stamp, the fixture, and the prompt.

    The stamp is written before the archive is checked, so a run whose unpack
    fails can still be recorded as invalid.

    Args:
        cases_dir: The directory holding the case files and archives.
        repo_root: The repository whose guidance is under test.
        results_dir: Where run sets live; must be outside ``repo_root``.
        case_id: The case to unpack.
        run_set: The name of this set of runs; one safe path segment.
        run: The run's index within the set, from 1 to ``runs_expected``.
        runs_expected: How many runs of this case the set will hold.
        label: A free-text note stored in the stamp.

    Returns:
        The run directory.

    Raises:
        EvalError: The run-set name or run index is unusable, the run
            directory is inside the repository or already has content, or the
            archive doesn't match its case file.
    """
    case = load_case(cases_dir, case_id)
    validate_segment(run_set, run_set)
    if not 1 <= run <= runs_expected:
        raise EvalError(f"run {run} is outside 1 to {runs_expected}")
    run_dir = run_directory(results_dir, run_set, case_id, run)
    if run_dir.resolve().is_relative_to(repo_root.resolve()):
        raise EvalError("the results directory must be outside the repository")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise EvalError(f"run directory already has content: {run_set}/{case_id}/{run}")
    run_dir.mkdir(parents=True, exist_ok=True)
    work_dir = run_dir / "work"
    archive_path = cases_dir / case.archive
    archive_bytes = archive_path.read_bytes() if archive_path.is_file() else b""
    archive_hash = sha256_hex(archive_bytes) if archive_bytes else ""
    stamp = {
        "schema": SCHEMA,
        "case": case.id,
        "archive_sha256": archive_hash,
        "case_file_sha256": case.file_sha256,
        "prompt_sha256": sha256_hex(case.prompt.encode("utf-8")),
        "skills_sha256": skills_hash(repo_root),
        "run_set": run_set,
        "run": run,
        "runs_expected": runs_expected,
        "label": label,
    }
    (run_dir / "stamp.json").write_text(
        json.dumps(stamp, indent=2) + "\n", encoding="utf-8"
    )
    if not archive_bytes:
        raise EvalError(f"{case.id}: archive {case.archive} is missing")
    if archive_hash != case.sha256:
        raise EvalError(f"{case.id}: archive hash differs from the case file")
    for member_path, data in read_members(archive_bytes, case).items():
        target = work_dir.joinpath(*PurePosixPath(member_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    prompt = (
        case.prompt.replace("{work_dir}", work_dir.resolve().as_posix())
        .replace("{run_dir}", run_dir.resolve().as_posix())
        .replace("{repo_root}", repo_root.resolve().as_posix())
    )
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    return run_dir


def _observed(value: object) -> str:
    return " ".join(str(value).split())[:OBSERVED_LIMIT]


def _matching_items(
    result: dict[str, Any], check: Check
) -> tuple[list[dict[str, Any]], str]:
    items = result.get(check.list_name)
    if not isinstance(items, list):
        return [], f"list {check.list_name!r} is missing"
    if not all(
        isinstance(item, dict) and isinstance(item.get("name"), str) for item in items
    ):
        return [], f"list {check.list_name!r} has an item without a name"
    needle = check.contains.casefold()
    return [item for item in items if needle in item["name"].casefold()], ""


def run_check(check: Check, result: dict[str, Any], work_dir: Path) -> CheckResult:
    """Evaluate one check against a run's result and work directory.

    Args:
        check: The check to run.
        result: The parsed ``result.json``.
        work_dir: The run's unpacked fixture directory.

    Returns:
        Whether the check passed, with what was observed.
    """
    if check.type == "file_absent":
        if not work_dir.is_dir():
            return CheckResult(check.id, False, "work directory is missing")
        exists = work_dir.joinpath(*PurePosixPath(check.path).parts).exists()
        return CheckResult(check.id, not exists, "path exists" if exists else "absent")
    matches, problem = _matching_items(result, check)
    if problem:
        return CheckResult(check.id, False, problem)
    count_note = f"{len(matches)} items contain {check.contains!r}"
    if check.type == "no_entry":
        return CheckResult(check.id, not matches, count_note)
    if check.type == "entry":
        if len(matches) != 1:
            return CheckResult(check.id, False, count_note)
        value = str(matches[0].get(check.field, "")).strip()
        accepted = {accepted_value.casefold() for accepted_value in check.accept}
        return CheckResult(check.id, value.casefold() in accepted, _observed(value))
    assert_never(check.type)


def read_result(run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    """Read a run's ``result.json``.

    Args:
        run_dir: The run's directory.

    Returns:
        The parsed object and an empty reason, or ``None`` and the reason the
        run is invalid (``no_result_file``, ``bad_json``, or ``bad_shape``).
    """
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        return None, "no_result_file"
    data = result_path.read_bytes()
    if len(data) > MAX_RESULT_BYTES:
        return None, "bad_shape"
    try:
        parsed = json.loads(data)
    except ValueError:
        return None, "bad_json"
    if not isinstance(parsed, dict):
        return None, "bad_shape"
    return parsed, ""


def read_json_object(path: Path, what: str) -> dict[str, Any]:
    """Read a file that must hold one JSON object.

    Args:
        path: The file to read.
        what: What the file is, for the error message.

    Returns:
        The parsed object.

    Raises:
        EvalError: The file is not JSON or not an object.
    """
    try:
        parsed = json.loads(path.read_bytes())
    except ValueError as error:
        raise EvalError(f"{what} is not valid JSON") from error
    if not isinstance(parsed, dict):
        raise EvalError(f"{what} is not an object")
    return parsed


def read_result_lines(results_file: Path) -> list[dict[str, Any]]:
    """Read every line of a results file.

    Args:
        results_file: The run set's ``results.jsonl``.

    Returns:
        One object per non-blank line; empty when the file doesn't exist.

    Raises:
        EvalError: A line is not a JSON object.
    """
    if not results_file.is_file():
        return []
    lines: list[dict[str, Any]] = []
    for number, text in enumerate(
        results_file.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not text.strip():
            continue
        try:
            parsed = json.loads(text)
        except ValueError as error:
            raise EvalError(f"results line {number} is not valid JSON") from error
        if not isinstance(parsed, dict):
            raise EvalError(f"results line {number} is not an object")
        lines.append(parsed)
    return lines


def read_stamps(run_set_dir: Path) -> list[dict[str, Any]]:
    """Read the stamp of every run directory in a run set.

    Args:
        run_set_dir: ``<results_dir>/<run_set>``.

    Returns:
        One stamp per unpacked run, graded or not.

    Raises:
        EvalError: A stamp is not a JSON object.
    """
    return [
        read_json_object(
            path, f"the stamp in {path.parent.parent.name}/{path.parent.name}"
        )
        for path in sorted(run_set_dir.glob("*/*/stamp.json"))
    ]


def grade_run(
    cases_dir: Path,
    repo_root: Path,
    results_dir: Path,
    case_id: str,
    run_set: str,
    run: int,
    invalid_reason: str,
) -> dict[str, Any]:
    """Grade one run and append its line to the run set's results file.

    Args:
        cases_dir: The directory holding the case files.
        repo_root: The repository whose guidance is under test.
        results_dir: Where run sets live.
        case_id: The case that was run.
        run_set: The run set the run belongs to.
        run: The run's index.
        invalid_reason: Set to record a run that produced nothing to grade;
            empty to grade ``result.json``.

    Returns:
        The line that was appended.

    Raises:
        EvalError: The run has no stamp, the stamp is for another case, run,
            or run set, the case file changed since the run was unpacked, or
            the run already has a line.
    """
    case = load_case(cases_dir, case_id)
    validate_segment(run_set, run_set)
    run_dir = run_directory(results_dir, run_set, case_id, run)
    where = f"{run_set}/{case_id}/{run}"
    stamp_path = run_dir / "stamp.json"
    if not stamp_path.is_file():
        raise EvalError(f"no stamp for {where}; unpack it first")
    stamp = read_json_object(stamp_path, f"the stamp for {where}")
    if (stamp.get("case"), stamp.get("run_set"), stamp.get("run")) != (
        case_id,
        run_set,
        run,
    ):
        raise EvalError(f"the stamp in {where} is for another case, run set, or run")
    results_file = results_dir / run_set / "results.jsonl"
    for line in read_result_lines(results_file):
        if line.get("case") == case_id and line.get("run") == run:
            raise EvalError(f"{where} is already graded")
    checks: list[CheckResult] = []
    reason = invalid_reason
    if not reason and not (run_dir / "prompt.md").is_file():
        reason = "unpack_failed"
    if not reason:
        if stamp.get("case_file_sha256") != case.file_sha256:
            raise EvalError(f"the case file changed since {where} was unpacked")
        result, reason = read_result(run_dir)
        if result is not None:
            checks = [
                run_check(check, result, run_dir / "work") for check in case.checks
            ]
    outcome: Outcome
    if reason:
        outcome = "invalid"
    else:
        outcome = "pass" if all(check.passed for check in checks) else "fail"
    line = dict(stamp)
    line.update(
        {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "skills_sha256_at_grade": skills_hash(repo_root),
            "outcome": outcome,
            "invalid_reason": reason,
            "checks": [
                {"id": check.id, "passed": check.passed, "observed": check.observed}
                for check in checks
            ],
        }
    )
    with results_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")
    return line


def _tally(lines: Sequence[dict[str, Any]]) -> dict[Outcome, list[dict[str, Any]]]:
    tally: dict[Outcome, list[dict[str, Any]]] = {"pass": [], "fail": [], "invalid": []}
    for line in lines:
        outcome = line.get("outcome")
        if outcome == "pass":
            tally["pass"].append(line)
        elif outcome == "fail":
            tally["fail"].append(line)
        elif outcome == "invalid":
            tally["invalid"].append(line)
        else:
            raise EvalError(f"unknown outcome {outcome!r} in the results file")
    return tally


def _summarize_case(
    case_id: str, lines: Sequence[dict[str, Any]], stamps: Sequence[dict[str, Any]]
) -> tuple[list[str], bool, int]:
    if not lines and not stamps:
        return [f"{case_id}: not run"], False, 0
    tally = _tally(lines)
    expected = max(int(record.get("runs_expected", 0)) for record in (*lines, *stamps))
    fixtures = {
        (line.get("archive_sha256"), line.get("case_file_sha256")) for line in lines
    }
    out = [
        f"{case_id}: passed {len(tally['pass'])}, failed {len(tally['fail'])}, "
        f"invalid {len(tally['invalid'])} of {len(lines)} recorded "
        f"({expected} expected)"
    ]
    clean = len(tally["pass"]) == len(lines) == expected and len(fixtures) == 1
    if len(fixtures) > 1:
        out.append("  WARNING: the fixture or case file changed during this run set")
    graded = [line.get("run") for line in lines]
    stamped = {stamp.get("run") for stamp in stamps}
    valid_runs = range(1, expected + 1)
    for run in valid_runs:
        if graded.count(run) > 1:
            out.append(f"  run {run}: recorded more than once")
            clean = False
        elif run not in graded:
            state = "unpacked, never graded" if run in stamped else "missing"
            out.append(f"  run {run}: {state}")
            clean = False
    for stray in sorted({str(run) for run in graded if run not in valid_runs}):
        out.append(f"  run {stray}: outside 1 to {expected}")
        clean = False
    for line in tally["fail"]:
        for check in line.get("checks", []):
            if not check.get("passed"):
                out.append(
                    f"  run {line.get('run')}: check {check.get('id')} failed, "
                    f"observed: {check.get('observed')}"
                )
    for line in tally["invalid"]:
        out.append(f"  run {line.get('run')}: invalid, {line.get('invalid_reason')}")
    return out, clean, expected


def summarize(
    lines: Sequence[dict[str, Any]],
    stamps: Sequence[dict[str, Any]],
    all_cases: Sequence[str],
    run_set: str,
) -> tuple[str, bool]:
    """Build the summary for one run set.

    Args:
        lines: The run set's result lines.
        stamps: The stamp of every run directory in the run set.
        all_cases: The id of every case that exists.
        run_set: The run set's name, for the header.

    Returns:
        The summary text, and whether the run set is clean: every case run,
        every expected run recorded once and passed, with one fixture and one
        skill text throughout.

    Raises:
        EvalError: A result line holds an outcome this tool doesn't write.
    """
    if not lines and not stamps:
        return f"run set {run_set}: no runs recorded\n", False
    skills = sorted(
        {
            str(record[key])
            for record in (*lines, *stamps)
            for key in ("skills_sha256", "skills_sha256_at_grade")
            if key in record
        }
    )
    labels = sorted(
        {str(record.get("label", "")) for record in (*lines, *stamps)} - {""}
    )
    out = [
        f"run set {run_set}",
        f"skills hash: {', '.join(value[:12] for value in skills)}",
    ]
    if labels:
        out.append(f"label: {', '.join(labels)}")
    clean = len(skills) == 1
    if not clean:
        out.append("WARNING: the skill text changed during this run set")
    recorded_cases = {str(record.get("case", "")) for record in (*lines, *stamps)}
    largest = 0
    for case_id in sorted(recorded_cases | set(all_cases)):
        case_out, case_clean, expected = _summarize_case(
            case_id,
            [line for line in lines if line.get("case") == case_id],
            [stamp for stamp in stamps if stamp.get("case") == case_id],
        )
        out.extend(case_out)
        clean = clean and case_clean
        largest = max(largest, expected)
    out.append(f"n={largest} {SAMPLE_NOTE}")
    return "\n".join(out) + "\n", clean


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        A parser with one subcommand per operation.
    """
    parser = argparse.ArgumentParser(
        description="Verify, unpack, grade, summarize, and pack the guidance evals."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("verify", help="check every archive against its case file")

    unpack = commands.add_parser("unpack", help="create a run directory for a case")
    grade = commands.add_parser("grade", help="grade one run")
    for command in (unpack, grade):
        command.add_argument("case")
        command.add_argument("--results-dir", type=Path, required=True)
        command.add_argument("--run-set", required=True)
        command.add_argument("--run", type=int, required=True)
    unpack.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    unpack.add_argument("--label", default="")
    grade.add_argument("--invalid", choices=INVALID_REASONS, default="")

    summary = commands.add_parser("summary", help="print the counts for a run set")
    summary.add_argument("--results-dir", type=Path, required=True)
    summary.add_argument("--run-set", required=True)

    pack = commands.add_parser("pack", help="build a fixture archive from a directory")
    pack.add_argument("source", type=Path)
    pack.add_argument("archive", type=Path)
    return parser


def _run_grade(args: argparse.Namespace, cases_dir: Path, repo_root: Path) -> int:
    line = grade_run(
        cases_dir,
        repo_root,
        args.results_dir,
        args.case,
        args.run_set,
        args.run,
        args.invalid,
    )
    print(f"{args.case} run {args.run}: {line['outcome']}")
    for check in line["checks"]:
        verdict = "pass" if check["passed"] else "FAIL"
        print(f"  {verdict} {check['id']}: {check['observed']}")
    if line["invalid_reason"]:
        print(f"  invalid: {line['invalid_reason']}")
    return EXIT_OK if line["outcome"] == "pass" else EXIT_FAILED


def _run_summary(args: argparse.Namespace, cases_dir: Path) -> int:
    validate_segment(args.run_set, args.run_set)
    run_set_dir = args.results_dir / args.run_set
    text, clean = summarize(
        read_result_lines(run_set_dir / "results.jsonl"),
        read_stamps(run_set_dir),
        case_ids(cases_dir),
        args.run_set,
    )
    print(text, end="")
    return EXIT_OK if clean else EXIT_FAILED


def _run_pack(args: argparse.Namespace) -> int:
    archive_bytes, members = pack_directory(args.source)
    args.archive.write_bytes(archive_bytes)
    listing = {
        "sha256": sha256_hex(archive_bytes),
        "members": [
            {"path": member.path, "sha256": member.sha256} for member in members
        ],
    }
    print(json.dumps(listing, indent=2))
    return EXIT_OK


def run_command(args: argparse.Namespace, cases_dir: Path, repo_root: Path) -> int:
    """Run one parsed subcommand.

    Args:
        args: The parsed command line.
        cases_dir: The directory holding the case files and archives.
        repo_root: The repository whose guidance is under test.

    Returns:
        The exit status.

    Raises:
        EvalError: The command was given something it can't work with.
    """
    if args.command == "verify":
        problems = verify_cases(cases_dir)
        for problem in problems:
            print(problem)
        print("verify: problems above" if problems else "verify: clean")
        return EXIT_FAILED if problems else EXIT_OK
    if args.command == "unpack":
        run_dir = unpack_case(
            cases_dir,
            repo_root,
            args.results_dir,
            args.case,
            args.run_set,
            args.run,
            args.runs,
            args.label,
        )
        print(run_dir.resolve().as_posix())
        return EXIT_OK
    if args.command == "grade":
        return _run_grade(args, cases_dir, repo_root)
    if args.command == "summary":
        return _run_summary(args, cases_dir)
    return _run_pack(args)


def main(
    argv: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    """Run the command line.

    Args:
        argv: The arguments; the process's own when omitted.
        cases_dir: The case directory; ``cases/`` beside this file when omitted.
        repo_root: The repository under test; this file's grandparent when
            omitted.

    Returns:
        The exit status: 0, 1, or 2 as the module docstring defines them.
    """
    args = build_parser().parse_args(argv)
    here = Path(__file__).resolve().parent
    try:
        return run_command(args, cases_dir or here / "cases", repo_root or here.parent)
    except (EvalError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
