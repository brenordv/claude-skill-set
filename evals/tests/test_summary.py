"""Tests for the run-set summary."""

from __future__ import annotations

from typing import Any

import pytest

from case_archive import EvalError
from guidance_evals import SAMPLE_NOTE, summarize

RUN_SET = "set-a"


def record(case: str, run: int, **extra: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "case": case,
        "run": run,
        "runs_expected": 3,
        "skills_sha256": "a" * 64,
        "archive_sha256": "b" * 64,
        "case_file_sha256": "c" * 64,
        "label": "",
    }
    fields.update(extra)
    return fields


def result_line(case: str, run: int, outcome: str, **extra: Any) -> dict[str, Any]:
    return record(
        case, run, outcome=outcome, **{"invalid_reason": "", "checks": [], **extra}
    )


def test_summarize_every_expected_run_passed_is_clean() -> None:
    lines = [result_line("sample", run, "pass", label="v20") for run in (1, 2, 3)]
    stamps = [record("sample", run, label="v20") for run in (1, 2, 3)]

    text, clean = summarize(lines, stamps, ["sample"], RUN_SET)

    assert (text, clean) == (
        f"run set {RUN_SET}\n"
        "skills hash: aaaaaaaaaaaa\n"
        "label: v20\n"
        "sample: passed 3, failed 0, invalid 0 of 3 recorded (3 expected)\n"
        f"n=3 {SAMPLE_NOTE}\n",
        True,
    )


def test_summarize_failed_and_invalid_runs_are_listed_and_not_clean() -> None:
    lines = [
        result_line("sample", 1, "pass"),
        result_line(
            "sample",
            2,
            "fail",
            checks=[
                {"id": "tests-row", "passed": False, "observed": "reproduced"},
                {"id": "marker-absent", "passed": True, "observed": "absent"},
            ],
        ),
        result_line("sample", 3, "invalid", invalid_reason="timeout"),
    ]

    text, clean = summarize(lines, [], ["sample"], RUN_SET)

    assert (text.splitlines()[2:5], clean) == (
        [
            "sample: passed 1, failed 1, invalid 1 of 3 recorded (3 expected)",
            "  run 2: check tests-row failed, observed: reproduced",
            "  run 3: invalid, timeout",
        ],
        False,
    )


def test_summarize_run_unpacked_but_never_graded_is_named_and_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 2)]
    stamps = [record("sample", run) for run in (1, 2, 3)]

    text, clean = summarize(lines, stamps, ["sample"], RUN_SET)

    assert (text.splitlines()[2:4], clean) == (
        [
            "sample: passed 2, failed 0, invalid 0 of 2 recorded (3 expected)",
            "  run 3: unpacked, never graded",
        ],
        False,
    )


def test_summarize_run_index_gap_is_named_and_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 2, 7)]

    text, clean = summarize(lines, [], ["sample"], RUN_SET)

    assert (text.splitlines()[3:5], clean) == (
        ["  run 3: missing", "  run 7: outside 1 to 3"],
        False,
    )


def test_summarize_run_recorded_twice_is_named_and_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 1, 2, 3)]

    text, clean = summarize(lines, [], ["sample"], RUN_SET)

    assert (text.splitlines()[3], clean) == ("  run 1: recorded more than once", False)


def test_summarize_case_with_no_runs_is_named_and_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 2, 3)]

    text, clean = summarize(lines, [], ["other", "sample"], RUN_SET)

    assert (text.splitlines()[2], clean) == ("other: not run", False)


def test_summarize_skill_text_changed_mid_set_warns_and_is_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 2)]
    lines.append(result_line("sample", 3, "pass", skills_sha256_at_grade="d" * 64))

    text, clean = summarize(lines, [], ["sample"], RUN_SET)

    assert (text.splitlines()[1:3], clean) == (
        [
            "skills hash: aaaaaaaaaaaa, dddddddddddd",
            "WARNING: the skill text changed during this run set",
        ],
        False,
    )


def test_summarize_fixture_changed_mid_set_warns_and_is_not_clean() -> None:
    lines = [result_line("sample", run, "pass") for run in (1, 2)]
    lines.append(result_line("sample", 3, "pass", archive_sha256="e" * 64))

    text, clean = summarize(lines, [], ["sample"], RUN_SET)

    assert (text.splitlines()[3], clean) == (
        "  WARNING: the fixture or case file changed during this run set",
        False,
    )


def test_summarize_unknown_outcome_raises() -> None:
    lines = [result_line("sample", 1, "skipped")]

    with pytest.raises(EvalError, match="unknown outcome 'skipped'"):
        summarize(lines, [], ["sample"], RUN_SET)


def test_summarize_nothing_recorded_reports_it() -> None:
    assert summarize([], [], ["sample"], RUN_SET) == (
        f"run set {RUN_SET}: no runs recorded\n",
        False,
    )
