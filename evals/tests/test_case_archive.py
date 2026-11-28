"""Tests for case files and fixture archives."""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any

import pytest

import case_archive
from case_archive import (
    ZIP_CREATE_SYSTEM,
    ZIP_REGULAR_FILE_ATTR,
    ZIP_TIMESTAMP,
    EvalError,
    load_case,
    pack_directory,
    parse_case,
    read_members,
    sha256_hex,
    validate_member_path,
    verify_cases,
)

from .conftest import DEFAULT_CHECKS, CaseBuilder, write_tree

PINNED_TREE = {"a.txt": b"alpha\n", "sub/b.txt": b"beta\n"}
PINNED_TREE_SHA256 = "80076395880da191833b2e9160adb975dc44f7660322f0588c193789faa61d54"
A_LATER_MTIME = 1_900_000_000
ONE_FILE_TREE = {"a.txt": b"alpha\n"}
LOCAL_HEADER_FLAGS_OFFSET = 6
CENTRAL_HEADER_SIGNATURE = b"PK\x01\x02"
CENTRAL_HEADER_FLAGS_OFFSET = 8
ENCRYPTED_FLAG = 0x1


def valid_case(**overrides: Any) -> bytes:
    case: dict[str, Any] = {
        "schema": 1,
        "id": "sample",
        "archive": "sample.zip",
        "sha256": "00",
        "members": [{"path": "a.txt", "sha256": "11"}],
        "prompt": ["line one", "line two"],
        "checks": DEFAULT_CHECKS,
    }
    case.update(overrides)
    return json.dumps(case).encode("utf-8")


def zip_of(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_pack_directory_known_tree_returns_pinned_sha256(tmp_path: Path) -> None:
    write_tree(tmp_path, PINNED_TREE)

    archive_bytes, _ = pack_directory(tmp_path)

    assert sha256_hex(archive_bytes) == PINNED_TREE_SHA256


def test_pack_directory_changed_mtimes_returns_identical_bytes(tmp_path: Path) -> None:
    write_tree(tmp_path, PINNED_TREE)
    first, _ = pack_directory(tmp_path)
    os.utime(tmp_path / "a.txt", (A_LATER_MTIME, A_LATER_MTIME))

    second, _ = pack_directory(tmp_path)

    assert second == first


def test_pack_directory_members_use_constant_header_fields(tmp_path: Path) -> None:
    write_tree(tmp_path, PINNED_TREE)

    archive_bytes, _ = pack_directory(tmp_path)

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        headers = [
            (
                info.filename,
                info.date_time,
                info.compress_type,
                info.create_system,
                info.external_attr,
            )
            for info in archive.infolist()
        ]
    assert headers == [
        (
            name,
            ZIP_TIMESTAMP,
            zipfile.ZIP_STORED,
            ZIP_CREATE_SYSTEM,
            ZIP_REGULAR_FILE_ATTR,
        )
        for name in ("a.txt", "sub/b.txt")
    ]


def test_pack_directory_bytecode_cache_is_left_out(tmp_path: Path) -> None:
    write_tree(tmp_path, {**PINNED_TREE, "sub/__pycache__/b.cpython-311.pyc": b"\x00"})

    _, members = pack_directory(tmp_path)

    assert [member.path for member in members] == ["a.txt", "sub/b.txt"]


def test_pack_directory_git_directory_raises(tmp_path: Path) -> None:
    write_tree(tmp_path, {**PINNED_TREE, ".git/config": b"[core]\n"})

    with pytest.raises(EvalError, match=r"\.git"):
        pack_directory(tmp_path)


def test_pack_directory_link_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_tree(tmp_path, PINNED_TREE)
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "a.txt")

    with pytest.raises(EvalError, match="links"):
        pack_directory(tmp_path)


def test_pack_directory_empty_tree_raises(tmp_path: Path) -> None:
    with pytest.raises(EvalError, match="nothing to pack"):
        pack_directory(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc/passwd",
        "../up.txt",
        "a/../b.txt",
        "a//b.txt",
        "./a.txt",
        "a\\b.txt",
        "C:/x.txt",
        "dir/",
        "name.",
        "name ",
        "dir /a.txt",
        "a/NUL",
        "COM1.txt",
        "a\x01b.txt",
    ],
)
def test_validate_member_path_unsafe_path_raises(path: str) -> None:
    with pytest.raises(EvalError, match="unsafe path"):
        validate_member_path(path)


def test_parse_case_valid_file_returns_case_with_joined_prompt() -> None:
    data = valid_case()

    case = parse_case(data, "sample.json")

    assert (case.id, case.prompt, case.file_sha256, len(case.checks)) == (
        "sample",
        "line one\nline two\n",
        sha256_hex(data),
        3,
    )


def test_parse_case_not_json_raises() -> None:
    with pytest.raises(EvalError, match="not valid JSON"):
        parse_case(b"{not json", "sample.json")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema": 2}, "'schema' must be 1"),
        ({"id": ""}, "'id' must be a non-empty string"),
        ({"archive": "sub/sample.zip"}, "bare .zip file name"),
        ({"archive": "sample.tar"}, "bare .zip file name"),
        ({"members": []}, "'members' must be a non-empty list"),
        ({"members": ["a.txt"]}, "a member must be an object"),
        ({"members": [{"path": "../a.txt", "sha256": "11"}]}, "unsafe path"),
        (
            {
                "members": [
                    {"path": "a.txt", "sha256": "1"},
                    {"path": "A.TXT", "sha256": "2"},
                ]
            },
            "repeat or differ only by case",
        ),
        ({"prompt": "one string"}, "'prompt' must be a non-empty list of strings"),
        ({"checks": []}, "'checks' must be a non-empty list"),
        ({"checks": ["entry"]}, "a check must be an object"),
        ({"checks": [DEFAULT_CHECKS[0], DEFAULT_CHECKS[0]]}, "two checks share an id"),
        ({"checks": [{"id": "x", "type": "regex", "why": "w"}]}, "unknown check type"),
        (
            {
                "checks": [
                    {"id": "x", "type": "file_absent", "why": "w", "path": "../m"}
                ]
            },
            "unsafe path",
        ),
        (
            {
                "checks": [
                    {
                        "id": "x",
                        "type": "no_entry",
                        "why": "w",
                        "list": "files",
                        "contains": "a",
                    }
                ]
            },
            "unknown list",
        ),
        (
            {
                "checks": [
                    {
                        "id": "x",
                        "type": "entry",
                        "why": "w",
                        "list": "verify",
                        "contains": "a",
                        "field": "result",
                        "accept": [],
                    }
                ]
            },
            "'accept' must be a non-empty list of strings",
        ),
    ],
)
def test_parse_case_invalid_field_raises(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(EvalError, match=message):
        parse_case(valid_case(**overrides), "sample.json")


def test_parse_case_top_level_list_raises() -> None:
    with pytest.raises(EvalError, match="must be an object"):
        parse_case(b"[]", "sample.json")


def test_load_case_missing_file_raises(cases_dir: Path) -> None:
    with pytest.raises(EvalError, match="no case file"):
        load_case(cases_dir, "absent")


def test_load_case_id_differs_from_file_name_raises(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    case = builder.build("sample")
    builder.write("other", case)

    with pytest.raises(EvalError, match="expected 'other'"):
        load_case(cases_dir, "other")


def test_read_members_matching_archive_returns_contents(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample", files=PINNED_TREE)
    case = load_case(cases_dir, "sample")

    contents = read_members((cases_dir / "sample.zip").read_bytes(), case)

    assert contents == PINNED_TREE


def test_read_members_not_a_zip_raises(cases_dir: Path, builder: CaseBuilder) -> None:
    builder.build("sample")
    case = load_case(cases_dir, "sample")

    with pytest.raises(EvalError, match="not a zip archive"):
        read_members(b"plain bytes", case)


def test_read_members_extra_member_raises(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample", files=PINNED_TREE)
    case = load_case(cases_dir, "sample")

    with pytest.raises(EvalError, match="members differ"):
        read_members(zip_of({**PINNED_TREE, "extra.txt": b"x"}), case)


def test_read_members_altered_member_raises(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample", files=PINNED_TREE)
    case = load_case(cases_dir, "sample")

    with pytest.raises(EvalError, match=r"'a\.txt' was altered"):
        read_members(zip_of({**PINNED_TREE, "a.txt": b"changed\n"}), case)


def test_read_members_over_size_cap_raises(
    cases_dir: Path, builder: CaseBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder.build("sample", files=PINNED_TREE)
    case = load_case(cases_dir, "sample")
    monkeypatch.setattr(case_archive, "MAX_UNPACKED_BYTES", 8)

    with pytest.raises(EvalError, match="over the cap"):
        read_members((cases_dir / "sample.zip").read_bytes(), case)


def test_read_members_too_many_members_raises(
    cases_dir: Path, builder: CaseBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder.build("sample", files=PINNED_TREE)
    case = load_case(cases_dir, "sample")
    monkeypatch.setattr(case_archive, "MAX_MEMBERS", 1)

    with pytest.raises(EvalError, match="more than 1 members"):
        read_members((cases_dir / "sample.zip").read_bytes(), case)


def test_read_members_member_with_bad_checksum_raises(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample", files=ONE_FILE_TREE)
    case = load_case(cases_dir, "sample")
    intact = (cases_dir / "sample.zip").read_bytes()
    corrupted = intact.replace(b"alpha\n", b"alphA\n", 1)

    with pytest.raises(EvalError, match=r"'a\.txt' can't be read"):
        read_members(corrupted, case)


def test_read_members_encrypted_member_raises(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample", files=ONE_FILE_TREE)
    case = load_case(cases_dir, "sample")
    flagged = bytearray((cases_dir / "sample.zip").read_bytes())
    flagged[LOCAL_HEADER_FLAGS_OFFSET] |= ENCRYPTED_FLAG
    central_header = flagged.index(CENTRAL_HEADER_SIGNATURE)
    flagged[central_header + CENTRAL_HEADER_FLAGS_OFFSET] |= ENCRYPTED_FLAG

    with pytest.raises(EvalError, match=r"'a\.txt' can't be read"):
        read_members(bytes(flagged), case)


def test_load_case_unsafe_id_raises(cases_dir: Path) -> None:
    with pytest.raises(EvalError, match="unsafe path"):
        load_case(cases_dir, "../outside")


def test_verify_cases_matching_archives_returns_no_problems(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("first")
    builder.build("second", files=PINNED_TREE)

    problems = verify_cases(cases_dir)

    assert problems == []


def test_verify_cases_one_changed_byte_names_the_case(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    archive_path = cases_dir / "sample.zip"
    archive_path.write_bytes(archive_path.read_bytes() + b"\x00")

    problems = verify_cases(cases_dir)

    assert problems == ["sample: archive hash differs from the case file"]


def test_verify_cases_missing_archive_is_reported(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    (cases_dir / "sample.zip").unlink()

    problems = verify_cases(cases_dir)

    assert problems == ["sample: archive sample.zip is missing"]


def test_verify_cases_unlisted_archive_is_reported(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    builder.build("sample")
    (cases_dir / "stray.zip").write_bytes(zip_of(PINNED_TREE))

    problems = verify_cases(cases_dir)

    assert problems == ["stray.zip: no case file lists this archive"]


def test_verify_cases_invalid_case_file_is_reported(cases_dir: Path) -> None:
    (cases_dir / "broken.json").write_text("{not json", encoding="utf-8")

    problems = verify_cases(cases_dir)

    assert problems == ["broken.json: not valid JSON"]


def test_verify_cases_member_swapped_under_matching_archive_hash_is_reported(
    cases_dir: Path, builder: CaseBuilder
) -> None:
    case = builder.build("sample", files=PINNED_TREE)
    swapped = zip_of({**PINNED_TREE, "a.txt": b"changed\n"})
    (cases_dir / "sample.zip").write_bytes(swapped)
    builder.write("sample", {**case, "sha256": sha256_hex(swapped)})

    problems = verify_cases(cases_dir)

    assert problems == ["sample: sample.zip: member 'a.txt' was altered"]


def test_verify_cases_empty_directory_is_reported(cases_dir: Path) -> None:
    problems = verify_cases(cases_dir)

    assert problems == ["no case files found"]
