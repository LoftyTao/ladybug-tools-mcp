"""Honeybee Radiance dynamic state foundation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee_radiance.dynamic.state import RadianceShadeState, RadianceSubFaceState
from honeybee_radiance.dynamic.stategeo import StateGeometry
from honeybee_radiance.lib.modifiers import modifier_by_identifier
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.mutil import dict_to_modifier

from garden.honeybee_core.edit import (
    edit_honeybee_aperture,
    edit_honeybee_door,
    edit_honeybee_shade,
)
from garden.honeybee_core.geometry import face3d_from_dict
from garden.libraries.properties import get_garden_properties_library_object
from ladybug_tools_mcp.contracts.report import make_report


def _unwrap_object_dict(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        return data["object_dict"]
    if (
        isinstance(data, dict)
        and isinstance(data.get("target"), dict)
        and data["target"].get("target_type") == "garden_properties_library_object"
    ):
        return data["target"]
    return data


def _modifier_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
    field_name: str = "modifier",
) -> Modifier | None:
    """Resolve a Radiance modifier from dict, standards identifier, or Garden target."""
    data = _unwrap_object_dict(data)
    if data is None:
        return None
    if isinstance(data, dict) and data.get("target_type") == "garden_properties_library_object":
        if garden_root is None:
            raise ValueError(f"{field_name} target requires garden_root.")
        if data.get("domain") != "honeybee_radiance" or data.get("object_family") != "modifier":
            raise ValueError(f"{field_name} target must reference honeybee_radiance:modifier.")
        data = get_garden_properties_library_object(
            garden_root=garden_root,
            target=data,
        )["object_dict"]
    try:
        if isinstance(data, str):
            data = {
                "generic_black": "black",
                "black_modifier": "black",
                "default_black": "black",
            }.get(data.strip().lower(), data)
            return modifier_by_identifier(data)
        if isinstance(data, dict):
            return dict_to_modifier(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Radiance {field_name} input. {exc}") from exc
    raise ValueError(f"{field_name} must be a modifier dict, target, or standards identifier.")


def _state_geometry_from_input(data: dict[str, Any]) -> StateGeometry:
    data = _unwrap_object_dict(data)
    if (
        isinstance(data, dict)
        and isinstance(data.get("geometry"), dict)
        and data["geometry"].get("type") == "StateGeometry"
    ):
        data = data["geometry"]
    if not isinstance(data, dict):
        raise ValueError("State geometry input must be a StateGeometry object_dict.")
    try:
        return StateGeometry.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Radiance StateGeometry input. {exc}") from exc


def _state_geometries_from_input(data: list[dict[str, Any]] | None) -> list[StateGeometry] | None:
    if data is None:
        return None
    if not isinstance(data, list):
        raise ValueError("shades must be a list of StateGeometry dictionaries.")
    return [_state_geometry_from_input(item) for item in data]


def _state_geometry_summary(state_geometry: StateGeometry) -> dict[str, Any]:
    modifier = state_geometry.modifier
    return {
        "type": "StateGeometry",
        "identifier": state_geometry.identifier,
        "display_name": state_geometry.display_name,
        "area": round(float(state_geometry.area), 6),
        "center": [
            round(float(state_geometry.center.x), 6),
            round(float(state_geometry.center.y), 6),
            round(float(state_geometry.center.z), 6),
        ],
        "modifier": modifier.identifier if modifier is not None else None,
    }


def _state_summary(state: RadianceShadeState | RadianceSubFaceState, *, state_type: str) -> dict[str, Any]:
    modifier = state.modifier
    shades = list(state.shades) if state.shades else []
    return {
        "type": state.__class__.__name__,
        "state_type": state_type,
        "modifier": modifier.identifier if modifier is not None else None,
        "shade_count": len(shades),
        "state_geometry_identifiers": [shade.identifier for shade in shades],
    }


def create_radiance_state_geometry(
    *,
    identifier: str,
    geometry: dict[str, Any] | None = None,
    vertices: list[list[float]] | None = None,
    modifier: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Radiance StateGeometry dictionary."""
    if geometry is not None and vertices is not None:
        raise ValueError("Use either geometry or vertices, not both.")
    if geometry is None and vertices is None:
        raise ValueError("create_radiance_state_geometry requires geometry or vertices.")
    modifier_obj = _modifier_from_input(
        modifier,
        garden_root=garden_root,
        field_name="modifier",
    )
    if geometry is not None:
        state_geometry = StateGeometry(
            identifier,
            face3d_from_dict(geometry),
            modifier=modifier_obj,
        )
    else:
        state_geometry = StateGeometry.from_vertices(
            identifier,
            vertices,
            modifier=modifier_obj,
        )
    return {
        "object_dict": state_geometry.to_dict(),
        "summary_view": _state_geometry_summary(state_geometry),
        "report": make_report(
            status="ok",
            message=f"Created Radiance StateGeometry: {identifier}",
        ),
    }


def create_radiance_shade_state(
    *,
    modifier: dict[str, Any] | str | None = None,
    shades: list[dict[str, Any]] | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a RadianceShadeState dictionary."""
    state = RadianceShadeState(
        modifier=_modifier_from_input(modifier, garden_root=garden_root),
        shades=_state_geometries_from_input(shades),
    )
    return {
        "object_dict": state.to_dict(),
        "summary_view": _state_summary(state, state_type="shade"),
        "report": make_report(status="ok", message="Created RadianceShadeState."),
    }


def create_radiance_subface_state(
    *,
    modifier: dict[str, Any] | str | None = None,
    shades: list[dict[str, Any]] | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a RadianceSubFaceState dictionary."""
    state = RadianceSubFaceState(
        modifier=_modifier_from_input(modifier, garden_root=garden_root),
        shades=_state_geometries_from_input(shades),
    )
    return {
        "object_dict": state.to_dict(),
        "summary_view": _state_summary(state, state_type="subface"),
        "report": make_report(status="ok", message="Created RadianceSubFaceState."),
    }


def _target_object_type(target: dict[str, Any]) -> str:
    object_type = str(target.get("object_type") or target.get("target_type") or "")
    return object_type.lower()


def _edit_dynamic_target(
    *,
    garden_root: str,
    target: dict[str, Any],
    dynamic_group_identifier: str,
    states_update: dict[str, Any],
) -> dict[str, Any]:
    object_type = _target_object_type(target)
    if object_type == "shade":
        return edit_honeybee_shade(
            garden_root=garden_root,
            target=target,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states_update,
        )
    if object_type == "aperture":
        return edit_honeybee_aperture(
            garden_root=garden_root,
            target=target,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states_update,
        )
    if object_type == "door":
        return edit_honeybee_door(
            garden_root=garden_root,
            target=target,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states_update,
        )
    raise ValueError("Dynamic Radiance groups support only shade, aperture, and door targets.")


def setup_radiance_dynamic_group(
    *,
    garden_root: str,
    targets: list[dict[str, Any]],
    dynamic_group_identifier: str,
    states: list[dict[str, Any]] | None = None,
    operation: str = "replace_all",
) -> dict[str, Any]:
    """Apply a dynamic group identifier and state update to multiple model objects."""
    if not targets:
        raise ValueError("targets must include at least one shade, aperture, or door target.")
    operation = operation.strip().lower()
    if operation not in {"replace_all", "add", "clear"}:
        raise ValueError("operation must be replace_all, add, or clear.")
    state_list = [] if states is None else states
    if operation != "clear" and not isinstance(state_list, list):
        raise ValueError("states must be a list when operation is not clear.")
    if operation != "clear" and not state_list:
        raise ValueError(
            "setup_radiance_dynamic_group requires at least one Radiance state "
            "for replace_all/add. Pass states=[create_radiance_shade_state(...)["
            "\"object_dict\"]] or use operation='clear'."
        )
    root = str(Path(garden_root).expanduser().resolve())
    states_update = {"operation": operation, "states": state_list}
    updated: list[dict[str, Any]] = []
    for target in targets:
        result = _edit_dynamic_target(
            garden_root=root,
            target=target,
            dynamic_group_identifier=dynamic_group_identifier,
            states_update=states_update,
        )
        updated.append(
            {
                "target": result.get("target", target),
                "updated_fields": result.get("summary_view", {}).get("updated_fields", []),
                "persistence_receipt": result.get("persistence_receipt"),
            }
        )
    return {
        "updated": updated,
        "summary_view": {
            "garden_root": root,
            "dynamic_group_identifier": dynamic_group_identifier,
            "operation": operation,
            "updated_count": len(updated),
            "state_count": 0 if operation == "clear" else len(state_list),
            "object_types": [_target_object_type(target) for target in targets],
        },
        "report": make_report(
            status="ok",
            message=f"Applied Radiance dynamic group to {len(updated)} object(s).",
        ),
    }
