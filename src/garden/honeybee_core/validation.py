"""Honeybee model validation services."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
)


def validate_honeybee_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Honeybee model and return structured validation issues."""
    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    try:
        issues = model.check_all(raise_exception=False, detailed=True)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Failed to validate Honeybee model. {exc}") from exc

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
            "model_target": model_target,
            "model_identifier": str(model_target["model_identifier"]),
            "is_valid": is_valid,
            "issue_count": len(issues),
            "issue_codes": sorted(set(issue_codes)),
            "issue_types": sorted(set(issue_types)),
            "issue_counts_by_code": dict(sorted(Counter(issue_codes).items())),
            "issue_counts_by_type": dict(sorted(Counter(issue_types).items())),
            "issue_element_types": sorted(set(element_types)),
            "object_counts": {
                "rooms": len(model.rooms),
                "faces": len(model.faces),
                "apertures": len(model.apertures),
                "doors": len(model.doors),
                "shades": len(model.shades),
            },
        },
        "report": make_report(
            status="ok" if is_valid else "invalid",
            message=(
                f"Honeybee model is valid: {model.identifier}"
                if is_valid
                else f"Honeybee model has {len(issues)} validation issue(s): {model.identifier}"
            ),
            details={
                "is_valid": is_valid,
                "issue_count": len(issues),
                "issue_codes": sorted(set(issue_codes)),
                "issue_types": sorted(set(issue_types)),
            },
        ),
    }
