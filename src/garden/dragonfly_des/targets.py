"""Dragonfly DES typed target helpers."""

from __future__ import annotations

from typing import Any


DES_OBJECT_TARGET_TYPE = "dragonfly_des_object"
DES_DOMAIN = "dragonfly_des"

DES_OBJECT_KINDS = {
    "thermal_connector",
    "horizontal_pipe_parameter",
    "ghe_soil_parameter",
    "ghe_fluid_parameter",
    "ghe_pipe_parameter",
    "ghe_borehole_parameter",
    "ghe_design_parameter",
    "ground_heat_exchanger",
    "fourth_gen_thermal_loop",
    "fifth_gen_thermal_loop",
    "ghe_thermal_loop",
}


def make_des_object_target(
    *,
    garden_id: str,
    kind: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a Dragonfly DES object target."""
    if kind not in DES_OBJECT_KINDS:
        allowed = ", ".join(sorted(DES_OBJECT_KINDS))
        raise ValueError(f"Unsupported Dragonfly DES object kind: {kind}. Allowed: {allowed}.")
    return {
        "target_type": DES_OBJECT_TARGET_TYPE,
        "domain": DES_DOMAIN,
        "kind": kind,
        "id": identifier,
        "identifier": identifier,
        "path": path,
        "garden_id": garden_id,
    }


def normalize_des_object_target(
    value: Any,
    *,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly DES object target dict."""
    if not isinstance(value, dict):
        raise ValueError("Expected a Dragonfly DES object target dict.")
    if "selector" in value:
        raise ValueError("Dragonfly DES object targets do not accept selector-shaped inputs.")
    if value.get("target_type") != DES_OBJECT_TARGET_TYPE:
        raise ValueError("target must have target_type 'dragonfly_des_object'.")
    if value.get("domain") != DES_DOMAIN:
        raise ValueError("target must reference domain 'dragonfly_des'.")
    kind = value.get("kind")
    if kind not in DES_OBJECT_KINDS:
        allowed = ", ".join(sorted(DES_OBJECT_KINDS))
        raise ValueError(f"target kind must be one of: {allowed}.")
    if expected_kind is not None and kind != expected_kind:
        raise ValueError(f"Expected Dragonfly DES target kind '{expected_kind}'.")
    for field in ("id", "identifier", "path", "garden_id"):
        field_value = value.get(field)
        if not isinstance(field_value, str) or not field_value:
            raise ValueError(f"Dragonfly DES target requires non-empty '{field}'.")
    return dict(value)
