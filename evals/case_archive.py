"""Case files and fixture archives: parse, verify, read, and pack them.

A case is a fixture archive (``cases/<id>.zip``) and a case file
(``cases/<id>.json``). The case file pins the archive and each of its members
by SHA-256 and holds the prompt and the checks.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SCHEMA = 1
MAX_MEMBERS = 200
MAX_UNPACKED_BYTES = 5 * 1024 * 1024

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_CREATE_SYSTEM = 3
ZIP_REGULAR_FILE_ATTR = 0o100644 << 16

RESULT_LISTS = ("verify", "test_changes", "suppressions")
WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)

CheckType = Literal["entry", "no_entry", "file_absent"]


class EvalError(Exception):
    """An input the tool can't work with: a bad case file, archive, or path."""


@dataclass(frozen=True)
class Member:
    """One file inside a fixture archive, pinned by its content hash."""

    path: str
    sha256: str


@dataclass(frozen=True)
class Check:
    """One mechanical check a run's result must pass."""

    id: str
    type: CheckType
    why: str
    list_name: str = ""
    contains: str = ""
    field: str = ""
    accept: tuple[str, ...] = ()
    path: str = ""


@dataclass(frozen=True)
class Case:
    """A case file: the pinned archive, the prompt, and the checks."""

    id: str
    archive: str
    sha256: str
    members: tuple[Member, ...]
    prompt: str
    checks: tuple[Check, ...]
    file_sha256: str


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 of ``data`` as lowercase hex.

    Args:
        data: The bytes to hash.

    Returns:
        The digest as 64 lowercase hex characters.
    """
    return hashlib.sha256(data).hexdigest()


def is_bytecode_cache(relative: Path) -> bool:
    """Return whether a path is a bytecode cache, never packed and never hashed.

    Args:
        relative: A path relative to the tree being walked.

    Returns:
        True for a ``.pyc`` file or anything under a ``__pycache__`` directory.
    """
    return relative.suffix == ".pyc" or "__pycache__" in relative.parts


def validate_segment(segment: str, whole: str) -> None:
    """Reject one path segment that is unsafe on any supported OS.

    Args:
        segment: The segment to check.
        whole: The full path or name, for the error message.

    Raises:
        EvalError: The segment is empty, ``.`` or ``..``, has a slash,
            backslash, colon, or control character, ends in a dot or a space,
            or is a Windows device name.
    """
    if (
        segment in ("", ".", "..")
        or any(char in segment for char in "/\\:")
        or any(ord(char) < 32 for char in segment)
        or segment.endswith((".", " "))
        or segment.split(".")[0].upper() in WINDOWS_DEVICE_NAMES
    ):
        raise EvalError(f"unsafe path: {whole!r}")


def validate_member_path(path: str) -> None:
    """Reject a member path that could land outside the work directory.

    Args:
        path: The member path as written in the case file: relative, with
            forward slashes.

    Raises:
        EvalError: Any segment of the path is unsafe (see
            ``validate_segment``).
    """
    for segment in path.split("/"):
        validate_segment(segment, path)


def _require_str(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise EvalError(f"{where}: {key!r} must be a non-empty string")
    return value


def _require_str_list(raw: dict[str, Any], key: str, where: str) -> list[str]:
    value = raw.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) for item in value)
    ):
        raise EvalError(f"{where}: {key!r} must be a non-empty list of strings")
    return value


def _parse_check(raw: Any, where: str) -> Check:
    if not isinstance(raw, dict):
        raise EvalError(f"{where}: a check must be an object")
    check_id = _require_str(raw, "id", where)
    check_type = _require_str(raw, "type", where)
    why = _require_str(raw, "why", where)
    if check_type == "file_absent":
        path = _require_str(raw, "path", where)
        validate_member_path(path)
        return Check(id=check_id, type="file_absent", why=why, path=path)
    if check_type not in ("entry", "no_entry"):
        raise EvalError(f"{where}: unknown check type {check_type!r} in {check_id!r}")
    list_name = _require_str(raw, "list", where)
    if list_name not in RESULT_LISTS:
        raise EvalError(f"{where}: unknown list {list_name!r} in {check_id!r}")
    contains = _require_str(raw, "contains", where)
    if check_type == "no_entry":
        return Check(
            id=check_id,
            type="no_entry",
            why=why,
            list_name=list_name,
            contains=contains,
        )
    return Check(
        id=check_id,
        type="entry",
        why=why,
        list_name=list_name,
        contains=contains,
        field=_require_str(raw, "field", where),
        accept=tuple(_require_str_list(raw, "accept", where)),
    )


def _parse_members(raw: Any, where: str) -> tuple[Member, ...]:
    if not isinstance(raw, list) or not raw:
        raise EvalError(f"{where}: 'members' must be a non-empty list")
    members: list[Member] = []
    for raw_member in raw:
        if not isinstance(raw_member, dict):
            raise EvalError(f"{where}: a member must be an object")
        member = Member(
            path=_require_str(raw_member, "path", where),
            sha256=_require_str(raw_member, "sha256", where),
        )
        validate_member_path(member.path)
        members.append(member)
    folded = [member.path.casefold() for member in members]
    if len(set(folded)) != len(folded):
        raise EvalError(f"{where}: two member paths repeat or differ only by case")
    return tuple(members)


def parse_case(data: bytes, where: str) -> Case:
    """Parse and validate a case file.

    Args:
        data: The case file's bytes.
        where: A label for error messages, usually the file name.

    Returns:
        The validated case, with ``file_sha256`` set to the hash of ``data``.

    Raises:
        EvalError: The bytes are not JSON, or a field is missing, mistyped,
            or unsafe.
    """
    try:
        raw = json.loads(data)
    except ValueError as error:
        raise EvalError(f"{where}: not valid JSON") from error
    if not isinstance(raw, dict):
        raise EvalError(f"{where}: the case file must be an object")
    if raw.get("schema") != SCHEMA:
        raise EvalError(f"{where}: 'schema' must be {SCHEMA}")
    raw_checks = raw.get("checks")
    if not isinstance(raw_checks, list) or not raw_checks:
        raise EvalError(f"{where}: 'checks' must be a non-empty list")
    checks = tuple(_parse_check(raw_check, where) for raw_check in raw_checks)
    check_ids = [check.id for check in checks]
    if len(set(check_ids)) != len(check_ids):
        raise EvalError(f"{where}: two checks share an id")
    archive = _require_str(raw, "archive", where)
    if "/" in archive or "\\" in archive or not archive.endswith(".zip"):
        raise EvalError(f"{where}: 'archive' must be a bare .zip file name")
    return Case(
        id=_require_str(raw, "id", where),
        archive=archive,
        sha256=_require_str(raw, "sha256", where),
        members=_parse_members(raw.get("members"), where),
        prompt="\n".join(_require_str_list(raw, "prompt", where)) + "\n",
        checks=checks,
        file_sha256=sha256_hex(data),
    )


def load_case(cases_dir: Path, case_id: str) -> Case:
    """Load one case file from ``cases_dir`` by its id.

    Args:
        cases_dir: The directory holding the case files.
        case_id: The case's id, which is also its file's stem.

    Returns:
        The validated case.

    Raises:
        EvalError: The id is not a safe name, there is no such case file, it
            is invalid, or its ``id`` doesn't match its file name.
    """
    validate_segment(case_id, case_id)
    path = cases_dir / f"{case_id}.json"
    if not path.is_file():
        raise EvalError(f"no case file for {case_id!r}")
    case = parse_case(path.read_bytes(), path.name)
    if case.id != case_id:
        raise EvalError(f"{path.name}: 'id' is {case.id!r}, expected {case_id!r}")
    return case


def read_members(archive_bytes: bytes, case: Case) -> dict[str, bytes]:
    """Read an archive's members, holding it to the case file's member list.

    Nothing is written. The archive's names must be exactly the case file's
    paths, each once, and each member's bytes must match its pinned hash.

    Args:
        archive_bytes: The whole archive, already read from disk.
        case: The case whose member list the archive must match.

    Returns:
        A mapping of member path to content.

    Raises:
        EvalError: The bytes are not a zip, a member can't be read, or the
            members differ from the case file in name, count, size budget, or
            content.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as error:
        raise EvalError(f"{case.archive}: not a zip archive") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise EvalError(f"{case.archive}: more than {MAX_MEMBERS} members")
        expected = {member.path: member.sha256 for member in case.members}
        if sorted(info.filename for info in infos) != sorted(expected):
            raise EvalError(f"{case.archive}: members differ from the case file's list")
        contents: dict[str, bytes] = {}
        budget = MAX_UNPACKED_BYTES
        for info in infos:
            try:
                with archive.open(info) as stream:
                    data = stream.read(budget + 1)
            except (
                zipfile.BadZipFile,
                RuntimeError,
                NotImplementedError,
                zlib.error,
            ) as error:
                raise EvalError(
                    f"{case.archive}: member {info.filename!r} can't be read"
                ) from error
            if len(data) > budget:
                raise EvalError(f"{case.archive}: unpacked size is over the cap")
            budget -= len(data)
            if sha256_hex(data) != expected[info.filename]:
                raise EvalError(f"{case.archive}: member {info.filename!r} was altered")
            contents[info.filename] = data
    return contents


def case_ids(cases_dir: Path) -> list[str]:
    """Return the id of every case file in ``cases_dir``, sorted.

    Args:
        cases_dir: The directory holding the case files.

    Returns:
        The stems of the ``*.json`` files.
    """
    return sorted(path.stem for path in cases_dir.glob("*.json"))


def verify_cases(cases_dir: Path) -> list[str]:
    """Check every case's archive and members against its case file.

    Args:
        cases_dir: The directory holding ``<id>.json`` and ``<id>.zip`` files.

    Returns:
        One message per problem found; empty when everything matches.
    """
    problems: list[str] = []
    ids = case_ids(cases_dir)
    if not ids:
        problems.append("no case files found")
    listed_archives: set[str] = set()
    for case_id in ids:
        try:
            case = load_case(cases_dir, case_id)
        except EvalError as error:
            problems.append(str(error))
            continue
        listed_archives.add(case.archive)
        archive_path = cases_dir / case.archive
        if not archive_path.is_file():
            problems.append(f"{case.id}: archive {case.archive} is missing")
            continue
        archive_bytes = archive_path.read_bytes()
        if sha256_hex(archive_bytes) != case.sha256:
            problems.append(f"{case.id}: archive hash differs from the case file")
            continue
        try:
            read_members(archive_bytes, case)
        except EvalError as error:
            problems.append(f"{case.id}: {error}")
    for archive_path in sorted(cases_dir.glob("*.zip")):
        if archive_path.name not in listed_archives:
            problems.append(f"{archive_path.name}: no case file lists this archive")
    return problems


def pack_directory(source: Path) -> tuple[bytes, list[Member]]:
    """Build a fixture archive from a directory.

    Members are stored uncompressed with constant header fields and sorted
    names, so the same tree gives the same bytes. Bytecode caches are skipped.

    Args:
        source: The directory to pack.

    Returns:
        The archive's bytes and its member list.

    Raises:
        EvalError: The tree holds a link, a ``.git`` directory, a file with
            an unsafe name, or no files.
    """
    entries: list[tuple[str, bytes]] = []
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise EvalError(f"links can't be packed: {relative.as_posix()}")
        if ".git" in relative.parts:
            raise EvalError("a .git directory can't be packed")
        if is_bytecode_cache(relative) or not path.is_file():
            continue
        name = relative.as_posix()
        validate_member_path(name)
        entries.append((name, path.read_bytes()))
    if not entries:
        raise EvalError("nothing to pack")
    entries.sort(key=lambda entry: entry[0])
    members: list[Member] = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = ZIP_CREATE_SYSTEM
            info.external_attr = ZIP_REGULAR_FILE_ATTR
            archive.writestr(info, data)
            members.append(Member(path=name, sha256=sha256_hex(data)))
    return buffer.getvalue(), members
