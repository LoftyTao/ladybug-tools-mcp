"""Fairyfly model validation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.fairyfly.model import _model_counts
from garden.fairyfly.model_io import load_fairyfly_model, resolve_model_target
from ladybug_tools_mcp.contracts.report import make_report


def _issue_messages(check_result: Any) -> list[str]:
    if check_result is None:
        return []
    if isinstance(check_result, str):
        return [check_result] if check_result else []
    if isinstance(check_result, list):
        return [str(item) for item in check_result if item]
    if isinstance(check_result, tuple):
        return [str(item) for item in check_result if item]
    return [str(check_result)] if check_result else []


def validate_fairyfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Garden-backed Fairyfly model with the Fairyfly SDK."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_target)
    try:
        issues = _issue_messages(
            model.check_all(raise_exception=False, detailed=True)
        )
    except AttributeError:
        issues = []
    valid = len(issues) == 0
    return {
        "valid": valid,
        "is_valid": valid,
        "issues": issues,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "object_counts": _model_counts(model),
            "issue_count": len(issues),
        },
        "report": make_report(
            status="ok" if valid else "warning",
            message="Fairyfly model validation completed.",
            warnings=issues,
        ),
    }
