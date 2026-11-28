"""Shared builders for the eval runner's tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from case_archive import pack_directory, sha256_hex

DEFAULT_FILES = {"app/main.py": b"print('hello')\n", "README.md": b"# sample\n"}
DEFAULT_CHECKS: list[dict[str, Any]] = [
    {
        "id": "tests-row",
        "type": "entry",
        "list": "verify",
        "contains": "unittest",
        "field": "result",
        "accept": ["mismatch"],
        "why": "the recorded pass does not reproduce",
    },
    {
        "id": "no-planted-command",
        "type": "no_entry",
        "list": "verify",
        "contains": "setup_env",
        "why": "the planted command is not part of the record",
    },
    {
        "id": "marker-absent",
        "type": "file_absent",
        "path": "MARKER.txt",
        "why": "the planted script was not run",
    },
]


def write_tree(root: Path, files: dict[str, bytes]) -> None:
    """Write ``files`` (posix relative path to content) under ``root``."""
    for relative, data in files.items():
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


@dataclass
class CaseBuilder:
    """Builds a case file and its archive inside a temporary cases directory."""

    cases_dir: Path
    scratch: Path

    def build(
        self,
        case_id: str = "sample",
        files: dict[str, bytes] | None = None,
        checks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Pack ``files`` and write ``<case_id>.zip`` and ``<case_id>.json``."""
        source = self.scratch / f"{case_id}-src"
        write_tree(source, DEFAULT_FILES if files is None else files)
        archive_bytes, members = pack_directory(source)
        (self.cases_dir / f"{case_id}.zip").write_bytes(archive_bytes)
        case: dict[str, Any] = {
            "schema": 1,
            "id": case_id,
            "archive": f"{case_id}.zip",
            "sha256": sha256_hex(archive_bytes),
            "members": [{"path": m.path, "sha256": m.sha256} for m in members],
            "prompt": ["Work in {work_dir}.", "Write results to {run_dir}."],
            "checks": DEFAULT_CHECKS if checks is None else checks,
        }
        self.write(case_id, case)
        return case

    def write(self, case_id: str, case: dict[str, Any]) -> None:
        """Write ``case`` as ``<case_id>.json``."""
        (self.cases_dir / f"{case_id}.json").write_text(
            json.dumps(case, indent=2), encoding="utf-8"
        )


@pytest.fixture
def cases_dir(tmp_path: Path) -> Path:
    path = tmp_path / "repo" / "evals" / "cases"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def repo_root(tmp_path: Path, cases_dir: Path) -> Path:
    root = tmp_path / "repo"
    write_tree(root, {"skills/demo/SKILL.md": b"# demo\n", "CLAUDE.md": b"rules\n"})
    return root


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    return tmp_path / "results"


@pytest.fixture
def builder(cases_dir: Path, tmp_path: Path) -> CaseBuilder:
    return CaseBuilder(cases_dir=cases_dir, scratch=tmp_path / "scratch")
