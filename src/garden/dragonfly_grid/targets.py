"""Dragonfly Electric Grid typed target helpers."""

from __future__ import annotations

from typing import Any


GRID_OBJECT_TARGET_TYPE = "dragonfly_grid_object"
GRID_DOMAIN = "dragonfly_grid"

GRID_OBJECT_KINDS = {
    "substation",
    "transformer",
    "electrical_connector",
    "electrical_network",
    "road_network",
    "ground_photovoltaics",
    "financial_parameters",
}


def make_grid_object_target(
    *,
    garden_id: str,
    kind: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a Dragonfly Electric Grid object target."""
    if kind not in GRID_OBJECT_KINDS:
        allowed = ", ".join(sorted(GRID_OBJECT_KINDS))
        raise ValueError(f"Unsupported Dragonfly Grid object kind: {kind}. Allowed: {allowed}.")
    return {
        "target_type": GRID_OBJECT_TARGET_TYPE,
        "domain": GRID_DOMAIN,
        "kind": kind,
        "id": identifier,
        "identifier": identifier,
        "path": path,
        "garden_id": garden_id,
    }


def normalize_grid_object_target(
    value: Any,
    *,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly Electric Grid object target dict."""
    if not isinstance(value, dict):
        raise ValueError("Expected a Dragonfly Grid object target dict.")
    if "selector" in value:
        raise ValueError("Dragonfly Grid object targets do not accept selector-shaped inputs.")
    if value.get("target_type") != GRID_OBJECT_TARGET_TYPE:
        raise ValueError("target must have target_type 'dragonfly_grid_object'.")
    if value.get("domain") != GRID_DOMAIN:
        raise ValueError("target must reference domain 'dragonfly_grid'.")
    kind = value.get("kind")
    if kind not in GRID_OBJECT_KINDS:
        allowed = ", ".join(sorted(GRID_OBJECT_KINDS))
        raise ValueError(f"target kind must be one of: {allowed}.")
    if expected_kind is not None and kind != expected_kind:
        raise ValueError(f"Expected Dragonfly Grid target kind '{expected_kind}'.")
    for field in ("id", "identifier", "path", "garden_id"):
        field_value = value.get(field)
        if not isinstance(field_value, str) or not field_value:
            raise ValueError(f"Dragonfly Grid target requires non-empty '{field}'.")
    return dict(value)

