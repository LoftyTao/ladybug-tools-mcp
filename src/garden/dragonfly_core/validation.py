"""Dragonfly model validation services."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from ladybug_tools_mcp.contracts.report import make_report


def validate_dragonfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Dragonfly model and return structured validation issues."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_dragonfly_model(garden_root_path, resolved_model_target)

    try:
        issues = model.check_all(raise_exception=False, detailed=True)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Failed to validate Dragonfly model. {exc}") from exc

    issue_codes = [
        issue["code"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    ]
    issue_types = [
        issue["error_type"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("error_type"), str)
    ]
    element_types = [
        issue["element_type"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("element_type"), str)
    ]
    is_valid = len(issues) == 0

    return {
        "is_valid": is_valid,
        "valid": is_valid,
        "issues": issues,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "model_identifier": str(resolved_model_target["model_identifier"]),
            "is_valid": is_valid,
            "issue_count": len(issues),
            "issue_codes": sorted(set(issue_codes)),
            "issue_types": sorted(set(issue_types)),
            "issue_counts_by_code": dict(sorted(Counter(issue_codes).items())),
            "issue_counts_by_type": dict(sorted(Counter(issue_types).items())),
            "issue_element_types": sorted(set(element_types)),
            "object_counts": {
                "buildings": len(model.buildings),
                "stories": len(model.stories),
                "room2ds": len(model.room_2ds),
                "room3ds": len(model.room_3ds),
                "context_shades": len(model.context_shades),
            },
        },
        "report": make_report(
            status="ok" if is_valid else "invalid",
            message=(
                f"Dragonfly model is valid: {model.identifier}"
                if is_valid
                else (
                    "Dragonfly model has "
                    f"{len(issues)} validation issue(s): {model.identifier}"
                )
            ),
            details={
                "is_valid": is_valid,
                "issue_count": len(issues),
                "issue_codes": sorted(set(issue_codes)),
                "issue_types": sorted(set(issue_types)),
            },
        ),
    }
