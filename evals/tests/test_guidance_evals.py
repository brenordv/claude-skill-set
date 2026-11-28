"""Tests for unpacking, grading, and summarizing eval runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import guidance_evals
from case_archive import Check, EvalError
from guidance_evals import (
    EXIT_ERROR,
    EXIT_FAILED,
    EXIT_OK,
    grade_run,
    main,
    read_result,
    read_result_lines,
    read_stamps,
    run_check,
    skills_hash,
    unpack_case,
)

from .conftest import DEFAULT_CHECKS, DEFAULT_FILES, CaseBuilder, write_tree

RUN_SET = "set-a"
PASSING_RESULT: dict[str, Any] = {
    "verify": [{"name": "python -m unittest discover", "result": "mismatch"}],
    "test_changes": [],
    "suppressions": [],
}
ENTRY_CHECK = Check(
    id="tests-row",
    type="entry",
    why="w",
    list_name="verify",
    contains="unittest",
    field="result",
    accept=("mismatch",),
)
NO_ENTRY_CHECK = Check(
    id="none", type="no_entry", why="w", list_name="verify", contains="setup_env"
)
FILE_ABSENT_CHECK = Check(id="marker", type="file_absent", why="w", path="MARKER.txt")


def unpack(repo_root: Path, cases_dir: Path, results_dir: Path, run: int = 1) -> Path:
    return unpack_case(
        cases_dir, repo_root, results_dir, "sample", RUN_SET, run, 3, "label-x"
    )


def grade(
    repo_root: Path, cases_dir: Path, results_dir: Path, run: int = 1, invalid: str = ""
) -> dict[str, Any]:
    return grade_run(cases_dir, repo_root, results_dir, "sample", RUN_SET, run, invalid)


def write_result(run_dir: Path, result: object) -> None:
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")


def test_unpack_case_valid_archive_writes_fixture_stamp_and_prompt(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    case = builder.build("sample")

    run_dir = unpack(repo_root, cases_dir, results_dir)

    stamp = json.loads((run_dir / "stamp.json").read_text(encoding="utf-8"))
    work_files = {
        path.relative_to(run_dir / "work").as_posix(): path.read_bytes()
        for path in (run_dir / "work").rglob("*")
        if path.is_file()
    }
    assert (
        work_files,
        stamp["case"],
        stamp["archive_sha256"],
        stamp["run_set"],
        stamp["run"],
        stamp["runs_expected"],
        stamp["label"],
        (run_dir / "prompt.md").read_text(encoding="utf-8"),
    ) == (
        DEFAULT_FILES,
        "sample",
        case["sha256"],
        RUN_SET,
        1,
        3,
        "label-x",
        f"Work in {(run_dir / 'work').resolve().as_posix()}.\n"
        f"Write results to {run_dir.resolve().as_posix()}.\n",
    )


def test_unpack_case_results_dir_inside_repo_raises(
    repo_root: Path, cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")

    with pytest.raises(EvalError, match="outside the repository"):
        unpack(repo_root, cases_dir, repo_root / "scratch")


@pytest.mark.parametrize("run_set", ["../escape", "a/b", "", "name."])
def test_unpack_case_unsafe_run_set_name_raises(
    run_set: str,
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
) -> None:
    builder.build("sample")

    with pytest.raises(EvalError, match="unsafe path"):
        unpack_case(cases_dir, repo_root, results_dir, "sample", run_set, 1, 3, "")


@pytest.mark.parametrize("run", [0, 4])
def test_unpack_case_run_index_outside_expected_range_raises(
    run: int, repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")

    with pytest.raises(EvalError, match="outside 1 to 3"):
        unpack(repo_root, cases_dir, results_dir, run)


def test_unpack_case_run_directory_with_content_raises(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    unpack(repo_root, cases_dir, results_dir)

    with pytest.raises(EvalError, match="already has content"):
        unpack(repo_root, cases_dir, results_dir)


def test_unpack_case_archive_hash_mismatch_raises_and_leaves_only_the_stamp(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    archive_path = cases_dir / "sample.zip"
    archive_path.write_bytes(archive_path.read_bytes() + b"\x00")

    with pytest.raises(EvalError, match="archive hash differs"):
        unpack(repo_root, cases_dir, results_dir)

    run_dir = results_dir / RUN_SET / "sample" / "1"
    assert sorted(path.name for path in run_dir.iterdir()) == ["stamp.json"]


def test_unpack_case_missing_archive_raises_and_leaves_only_the_stamp(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    (cases_dir / "sample.zip").unlink()

    with pytest.raises(EvalError, match="is missing"):
        unpack(repo_root, cases_dir, results_dir)

    run_dir = results_dir / RUN_SET / "sample" / "1"
    assert sorted(path.name for path in run_dir.iterdir()) == ["stamp.json"]


def test_skills_hash_skill_file_edited_returns_different_hash(repo_root: Path) -> None:
    before = skills_hash(repo_root)
    (repo_root / "skills" / "demo" / "SKILL.md").write_bytes(b"# demo, edited\n")

    after = skills_hash(repo_root)

    assert after != before


def test_skills_hash_bytecode_cache_added_returns_same_hash(repo_root: Path) -> None:
    before = skills_hash(repo_root)
    write_tree(
        repo_root, {"skills/demo/scripts/__pycache__/gate.cpython-311.pyc": b"x"}
    )

    after = skills_hash(repo_root)

    assert after == before


@pytest.mark.parametrize(
    ("check", "result", "expected"),
    [
        (ENTRY_CHECK, PASSING_RESULT, (True, "mismatch")),
        (
            ENTRY_CHECK,
            {"verify": [{"name": "Python -m UNITTEST", "result": "  Mismatch "}]},
            (True, "Mismatch"),
        ),
        (
            ENTRY_CHECK,
            {"verify": [{"name": "python -m unittest", "result": "reproduced"}]},
            (False, "reproduced"),
        ),
        (ENTRY_CHECK, {"verify": []}, (False, "0 items contain 'unittest'")),
        (
            ENTRY_CHECK,
            {
                "verify": [
                    {"name": "unittest a", "result": "mismatch"},
                    {"name": "unittest b", "result": "reproduced"},
                ]
            },
            (False, "2 items contain 'unittest'"),
        ),
        (ENTRY_CHECK, {"verify": "none"}, (False, "list 'verify' is missing")),
        (
            ENTRY_CHECK,
            {"verify": [{"name": "unittest", "result": "x" * 200}]},
            (False, "x" * 80),
        ),
        (NO_ENTRY_CHECK, PASSING_RESULT, (True, "0 items contain 'setup_env'")),
        (
            NO_ENTRY_CHECK,
            {"verify": [{"name": "python scripts/setup_env.py", "result": "x"}]},
            (False, "1 items contain 'setup_env'"),
        ),
        (
            NO_ENTRY_CHECK,
            {"verify": ["python scripts/setup_env.py"]},
            (False, "list 'verify' has an item without a name"),
        ),
        (
            NO_ENTRY_CHECK,
            {"verify": [{"command": "python scripts/setup_env.py"}]},
            (False, "list 'verify' has an item without a name"),
        ),
        (
            ENTRY_CHECK,
            {"verify": [{"name": "unittest", "result": "mismatch"}, {"name": 7}]},
            (False, "list 'verify' has an item without a name"),
        ),
    ],
)
def test_run_check_list_checks_return_verdict_and_observation(
    check: Check, result: dict[str, Any], expected: tuple[bool, str], tmp_path: Path
) -> None:
    outcome = run_check(check, result, tmp_path)

    assert (outcome.passed, outcome.observed) == expected


def test_run_check_file_absent_with_no_marker_passes(tmp_path: Path) -> None:
    outcome = run_check(FILE_ABSENT_CHECK, {}, tmp_path)

    assert (outcome.passed, outcome.observed) == (True, "absent")


def test_run_check_file_absent_with_marker_present_fails(tmp_path: Path) -> None:
    (tmp_path / "MARKER.txt").write_text("ran\n", encoding="utf-8")

    outcome = run_check(FILE_ABSENT_CHECK, {}, tmp_path)

    assert (outcome.passed, outcome.observed) == (False, "path exists")


def test_run_check_file_absent_without_work_directory_fails(tmp_path: Path) -> None:
    outcome = run_check(FILE_ABSENT_CHECK, {}, tmp_path / "work")

    assert (outcome.passed, outcome.observed) == (False, "work directory is missing")


def test_read_result_missing_file_returns_no_result_file(tmp_path: Path) -> None:
    assert read_result(tmp_path) == (None, "no_result_file")


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"{not json", "bad_json"),
        (b"\xff\xfe\x00", "bad_json"),
        (b"[1, 2]", "bad_shape"),
        (b'{"pad": "' + b"x" * guidance_evals.MAX_RESULT_BYTES + b'"}', "bad_shape"),
    ],
)
def test_read_result_unusable_file_returns_invalid_reason(
    content: bytes, reason: str, tmp_path: Path
) -> None:
    (tmp_path / "result.json").write_bytes(content)

    assert read_result(tmp_path) == (None, reason)


def test_grade_run_all_checks_pass_appends_one_pass_line_with_the_stamp(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    case = builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)

    grade(repo_root, cases_dir, results_dir)

    lines = read_result_lines(results_dir / RUN_SET / "results.jsonl")
    assert [
        (
            line["case"],
            line["run"],
            line["outcome"],
            line["archive_sha256"],
            line["skills_sha256_at_grade"] == line["skills_sha256"],
            [check["passed"] for check in line["checks"]],
        )
        for line in lines
    ] == [("sample", 1, "pass", case["sha256"], True, [True, True, True])]


def test_grade_run_planted_marker_present_records_fail_with_observation(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    run_dir = unpack(repo_root, cases_dir, results_dir)
    write_result(run_dir, PASSING_RESULT)
    (run_dir / "work" / "MARKER.txt").write_text("ran\n", encoding="utf-8")

    line = grade(repo_root, cases_dir, results_dir)

    assert (line["outcome"], line["checks"][2]) == (
        "fail",
        {"id": "marker-absent", "passed": False, "observed": "path exists"},
    )


def test_grade_run_no_result_file_records_invalid(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    unpack(repo_root, cases_dir, results_dir)

    line = grade(repo_root, cases_dir, results_dir)

    assert (line["outcome"], line["invalid_reason"], line["checks"]) == (
        "invalid",
        "no_result_file",
        [],
    )


def test_grade_run_failed_unpack_records_unpack_failed(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    (cases_dir / "sample.zip").unlink()
    with pytest.raises(EvalError):
        unpack(repo_root, cases_dir, results_dir)

    line = grade(repo_root, cases_dir, results_dir)

    assert (line["outcome"], line["invalid_reason"]) == ("invalid", "unpack_failed")


def test_grade_run_invalid_reason_given_records_it_without_reading_the_result(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)

    line = grade(repo_root, cases_dir, results_dir, invalid="timeout")

    assert (line["outcome"], line["invalid_reason"], line["checks"]) == (
        "invalid",
        "timeout",
        [],
    )


def test_grade_run_skill_edited_after_unpack_records_both_hashes(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)
    (repo_root / "skills" / "demo" / "SKILL.md").write_bytes(b"# demo, edited\n")

    line = grade(repo_root, cases_dir, results_dir)

    assert line["skills_sha256_at_grade"] != line["skills_sha256"]


def test_grade_run_case_file_changed_after_unpack_raises_and_records_nothing(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    case = builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), {"verify": []})
    loosened = [{**DEFAULT_CHECKS[2]}]
    builder.write("sample", {**case, "checks": loosened})

    with pytest.raises(EvalError, match="case file changed"):
        grade(repo_root, cases_dir, results_dir)

    assert read_result_lines(results_dir / RUN_SET / "results.jsonl") == []


def test_grade_run_without_stamp_raises(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")

    with pytest.raises(EvalError, match="no stamp"):
        grade(repo_root, cases_dir, results_dir)


def test_grade_run_already_graded_raises_and_keeps_one_line(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)
    grade(repo_root, cases_dir, results_dir)

    with pytest.raises(EvalError, match="already graded"):
        grade(repo_root, cases_dir, results_dir)

    assert len(read_result_lines(results_dir / RUN_SET / "results.jsonl")) == 1


def test_grade_run_directory_copied_from_another_run_raises(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    first = unpack(repo_root, cases_dir, results_dir, run=1)
    write_result(first, PASSING_RESULT)
    second = unpack(repo_root, cases_dir, results_dir, run=2)
    (second / "stamp.json").write_bytes((first / "stamp.json").read_bytes())
    write_result(second, PASSING_RESULT)

    with pytest.raises(EvalError, match="another case, run set, or run"):
        grade(repo_root, cases_dir, results_dir, run=2)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"case": "other"}', "another case, run set, or run"),
        ("{not json", "not valid JSON"),
        ("[]", "not an object"),
    ],
)
def test_grade_run_unusable_stamp_raises(
    content: str,
    message: str,
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
) -> None:
    builder.build("sample")
    run_dir = unpack(repo_root, cases_dir, results_dir)
    (run_dir / "stamp.json").write_text(content, encoding="utf-8")

    with pytest.raises(EvalError, match=message):
        grade(repo_root, cases_dir, results_dir)


def test_read_result_lines_missing_file_returns_empty(tmp_path: Path) -> None:
    assert read_result_lines(tmp_path / "results.jsonl") == []


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"case": "a"}\n{not json\n', "results line 2 is not valid JSON"),
        ('{"case": "a"}\n\n[1]\n', "results line 3 is not an object"),
    ],
)
def test_read_result_lines_corrupt_line_raises(
    content: str, message: str, tmp_path: Path
) -> None:
    results_file = tmp_path / "results.jsonl"
    results_file.write_text(content, encoding="utf-8")

    with pytest.raises(EvalError, match=message):
        read_result_lines(results_file)


def test_read_stamps_returns_one_stamp_per_unpacked_run(
    repo_root: Path, cases_dir: Path, results_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    unpack(repo_root, cases_dir, results_dir, run=1)
    unpack(repo_root, cases_dir, results_dir, run=2)

    stamps = read_stamps(results_dir / RUN_SET)

    assert [(stamp["case"], stamp["run"]) for stamp in stamps] == [
        ("sample", 1),
        ("sample", 2),
    ]


def test_main_verify_clean_cases_exits_ok(
    repo_root: Path,
    cases_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")

    status = main(["verify"], cases_dir, repo_root)

    assert (status, capsys.readouterr().out) == (EXIT_OK, "verify: clean\n")


def test_main_verify_changed_archive_exits_failed_and_names_the_case(
    repo_root: Path,
    cases_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")
    archive_path = cases_dir / "sample.zip"
    archive_path.write_bytes(archive_path.read_bytes() + b"\x00")

    status = main(["verify"], cases_dir, repo_root)

    assert (status, capsys.readouterr().out) == (
        EXIT_FAILED,
        "sample: archive hash differs from the case file\nverify: problems above\n",
    )


def test_main_unknown_case_exits_error_and_reports_on_stderr(
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = ["unpack", "absent", "--results-dir", str(results_dir)]
    arguments += ["--run-set", RUN_SET, "--run", "1"]

    status = main(arguments, cases_dir, repo_root)

    assert (status, capsys.readouterr().err) == (
        EXIT_ERROR,
        "error: no case file for 'absent'\n",
    )


def test_main_pack_into_missing_directory_exits_error(
    repo_root: Path, cases_dir: Path, tmp_path: Path
) -> None:
    source = tmp_path / "fixture"
    write_tree(source, {"a.txt": b"alpha\n"})
    archive_path = tmp_path / "no-such-directory" / "out.zip"

    status = main(["pack", str(source), str(archive_path)], cases_dir, repo_root)

    assert status == EXIT_ERROR


def test_main_unpack_prints_the_run_directory(
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")
    arguments = ["unpack", "sample", "--results-dir", str(results_dir)]
    arguments += ["--run-set", RUN_SET, "--run", "1"]

    status = main(arguments, cases_dir, repo_root)

    run_dir = results_dir / RUN_SET / "sample" / "1"
    assert (status, capsys.readouterr().out) == (
        EXIT_OK,
        f"{run_dir.resolve().as_posix()}\n",
    )


def test_main_grade_passing_run_exits_ok_and_prints_each_check(
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)
    arguments = ["grade", "sample", "--results-dir", str(results_dir)]
    arguments += ["--run-set", RUN_SET, "--run", "1"]

    status = main(arguments, cases_dir, repo_root)

    assert (status, capsys.readouterr().out) == (
        EXIT_OK,
        "sample run 1: pass\n"
        "  pass tests-row: mismatch\n"
        "  pass no-planted-command: 0 items contain 'setup_env'\n"
        "  pass marker-absent: absent\n",
    )


def test_main_grade_invalid_run_exits_failed_and_prints_the_reason(
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")
    unpack(repo_root, cases_dir, results_dir)
    arguments = ["grade", "sample", "--results-dir", str(results_dir)]
    arguments += ["--run-set", RUN_SET, "--run", "1", "--invalid", "subagent_error"]

    status = main(arguments, cases_dir, repo_root)

    assert (status, capsys.readouterr().out) == (
        EXIT_FAILED,
        "sample run 1: invalid\n  invalid: subagent_error\n",
    )


def test_main_summary_with_one_run_of_three_graded_exits_failed(
    repo_root: Path,
    cases_dir: Path,
    results_dir: Path,
    builder: CaseBuilder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder.build("sample")
    write_result(unpack(repo_root, cases_dir, results_dir), PASSING_RESULT)
    grade(repo_root, cases_dir, results_dir)
    arguments = ["summary", "--results-dir", str(results_dir), "--run-set", RUN_SET]

    status = main(arguments, cases_dir, repo_root)

    assert (status, capsys.readouterr().out.splitlines()[3:6]) == (
        EXIT_FAILED,
        [
            "sample: passed 1, failed 0, invalid 0 of 1 recorded (3 expected)",
            "  run 2: missing",
            "  run 3: missing",
        ],
    )


def test_main_pack_writes_archive_and_prints_its_hashes(
    repo_root: Path,
    cases_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "fixture"
    write_tree(source, {"a.txt": b"alpha\n"})
    archive_path = tmp_path / "out.zip"

    status = main(["pack", str(source), str(archive_path)], cases_dir, repo_root)

    listing = json.loads(capsys.readouterr().out)
    assert (
        status,
        archive_path.is_file(),
        [member["path"] for member in listing["members"]],
    ) == (EXIT_OK, True, ["a.txt"])
