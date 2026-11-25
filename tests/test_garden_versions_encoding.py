"""Regression tests for Garden Git version encoding."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from garden.store import create_garden
from garden.versions import (
    create_garden_version,
    list_garden_versions,
    restore_garden_version,
)


def test_chinese_version_subjects_round_trip_with_cp936_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create, list, and restore Chinese subjects even on a CP936 host."""
    # Simulate subprocess text mode inheriting a CP936 locale. _run_git must
    # override that default so UTF-8 Git output remains readable.
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp936")

    garden_root = tmp_path / "chinese_versions"
    create_garden(name="chinese_versions", root_dir=str(garden_root))
    model_path = garden_root / "models" / "sample.json"
    model_path.parent.mkdir(parents=True)

    model_path.write_text('{"design": "baseline"}\n', encoding="utf-8")
    baseline = create_garden_version(
        garden_root=str(garden_root),
        subject="基准方案",
    )

    model_path.write_text('{"design": "summer"}\n', encoding="utf-8")
    create_garden_version(
        garden_root=str(garden_root),
        subject="夏季方案",
    )

    versions = list_garden_versions(garden_root=str(garden_root))
    assert [version["subject"] for version in versions["matches"][:2]] == [
        "夏季方案",
        "基准方案",
    ]

    restore_garden_version(
        garden_root=str(garden_root),
        version_id=baseline["version_id"],
        subject="恢复基准方案",
    )
    assert model_path.read_text(encoding="utf-8") == '{"design": "baseline"}\n'
    assert list_garden_versions(garden_root=str(garden_root))["matches"][0][
        "subject"
    ] == "恢复基准方案"
