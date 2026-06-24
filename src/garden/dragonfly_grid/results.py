"""Dragonfly Electric Grid result readers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.report import make_report

OPENDSS_RESULT_ARTIFACT_TYPE = "dragonfly_grid_opendss_result_csv"


def read_opendss_result(
    *,
    garden_root: str,
    result_target: dict[str, Any],
    max_rows: int = 25,
) -> dict[str, Any]:
    """Read a registered OpenDSS CSV result artifact into a compact preview."""
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")
    root = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(root)
    path = _resolve_result_path(root, manifest, result_target)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    preview = rows[:max_rows]
    return {
        "target": result_target,
        "result_target": result_target,
        "preview_rows": preview,
        "summary_view": {
            "garden_target": manifest.target(),
            "result_target": result_target,
            "columns": reader.fieldnames or [],
            "row_count": len(rows),
            "preview_count": len(preview),
            "body_returned": True,
        },
        "report": make_report(
            status="ok",
            message=f"Read OpenDSS result artifact: {result_target.get('identifier')}",
        ),
    }


def _resolve_result_path(root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    if not isinstance(target, dict):
        raise ValueError("result_target must be a dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("result_target must have target_type 'artifact'.")
    if target.get("domain") != "dragonfly_grid":
        raise ValueError("result_target must reference domain 'dragonfly_grid'.")
    if target.get("artifact_type") != OPENDSS_RESULT_ARTIFACT_TYPE:
        raise ValueError(f"result_target artifact_type must be '{OPENDSS_RESULT_ARTIFACT_TYPE}'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("result_target belongs to a different Garden.")
    raw_path = target.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("result_target requires a Garden-relative path.")
    path = (root / raw_path).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"OpenDSS result artifact was not found: {raw_path}")
    return path

