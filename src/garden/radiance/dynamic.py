"""Honeybee Radiance dynamic state foundation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fnmatch import fnmatch
from honeybee_radiance.dynamic.multiphase import automatic_aperture_grouping
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
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.ladybug_tools_config import apply_ladybug_tools_runtime_to_path
from garden.libraries.properties import get_garden_properties_library_object
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


def _modifier_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
    field_name: str = "modifier",
) -> Modifier | None:
    """Resolve a Radiance modifier from dict, standards identifier, or Garden target."""
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


def _serialize_state_dict(state: RadianceShadeState | RadianceSubFaceState) -> dict[str, Any]:
    """Serialize a Radiance state while working around the SDK's _modifier_direct bug."""
    had_none_modifier = state._modifier is None and getattr(state, "_modifier_direct", None) is not None
    if had_none_modifier:
        state._modifier = state._modifier_direct
    try:
        data = state.to_dict()
    finally:
        if had_none_modifier:
            state._modifier = None
    if had_none_modifier:
        data.pop("modifier", None)
    if getattr(state, "modifier_direct", None) is not None:
        data["modifier_direct"] = state.modifier_direct.to_dict()
    return data


def _state_geometry_from_input(
    data: dict[str, Any] | StateGeometry,
    *,
    garden_root: str | None = None,
    default_identifier: str = "state_geometry",
) -> StateGeometry:
    if isinstance(data, StateGeometry):
        return data
    if (
        isinstance(data, dict)
        and isinstance(data.get("object_dict"), dict)
        and data["object_dict"].get("type") == "StateGeometry"
    ):
        data = data["object_dict"]
    if (
        isinstance(data, dict)
        and isinstance(data.get("geometry"), dict)
        and data["geometry"].get("type") == "StateGeometry"
    ):
        data = data["geometry"]
    if not isinstance(data, dict):
        raise ValueError("State geometry input must be a StateGeometry object_dict or inline dict.")
    if data.get("type") == "StateGeometry":
        payload = dict(data)
        for mod_key in ("modifier", "modifier_direct"):
            modifier_value = payload.get(mod_key)
            if isinstance(modifier_value, str) or (
                isinstance(modifier_value, dict)
                and modifier_value.get("target_type") == "garden_properties_library_object"
            ):
                mod = _modifier_from_input(
                    modifier_value,
                    garden_root=garden_root,
                    field_name=mod_key,
                )
                payload[mod_key] = mod.to_dict() if mod is not None else None
        try:
            return StateGeometry.from_dict(payload)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Invalid Radiance StateGeometry input. {exc}") from exc

    identifier = str(data.get("identifier") or default_identifier)
    geometry = data.get("geometry")
    vertices = data.get("vertices")
    if geometry is not None and vertices is not None:
        raise ValueError("StateGeometry inline dict must use either geometry or vertices, not both.")
    if geometry is None and vertices is None:
        raise ValueError("StateGeometry input requires geometry or vertices.")
    modifier_obj = _modifier_from_input(
        data.get("modifier"),
        garden_root=garden_root,
        field_name="modifier",
    )
    modifier_direct_obj = _modifier_from_input(
        data.get("modifier_direct"),
        garden_root=garden_root,
        field_name="modifier_direct",
    )
    try:
        if geometry is not None:
            sg = StateGeometry(
                identifier,
                face3d_from_dict(geometry),
                modifier=modifier_obj,
            )
        else:
            sg = StateGeometry.from_vertices(
                identifier,
                vertices,
                modifier=modifier_obj,
            )
        if modifier_direct_obj is not None:
            sg.modifier_direct = modifier_direct_obj
        return sg
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid inline Radiance StateGeometry input. {exc}") from exc


def _state_geometries_from_input(
    data: list[dict[str, Any] | None] | None,
    *,
    garden_root: str | None = None,
    prefix: str = "state_geometry",
) -> list[StateGeometry] | None:
    if data is None:
        return None
    if not isinstance(data, list):
        raise ValueError("shades must be a list of StateGeometry dictionaries.")
    items = [item for item in data if item is not None]
    return [
        _state_geometry_from_input(
            item,
            garden_root=garden_root,
            default_identifier=f"{prefix}_{index}",
        )
        for index, item in enumerate(items)
    ]


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
    modifier_direct = getattr(state, "modifier_direct", None)
    shades = list(state.shades) if state.shades else []
    summary = {
        "type": state.__class__.__name__,
        "state_type": state_type,
        "modifier": modifier.identifier if modifier is not None else None,
        "modifier_direct": modifier_direct.identifier if modifier_direct is not None else None,
        "shade_count": len(shades),
        "state_geometry_identifiers": [shade.identifier for shade in shades],
    }
    if isinstance(state, RadianceSubFaceState):
        summary["has_vmtx_geometry"] = state.vmtx_geometry is not None
        summary["has_dmtx_geometry"] = state.dmtx_geometry is not None
    return summary


def create_radiance_state_geometry(
    *,
    identifier: str,
    geometry: dict[str, Any] | None = None,
    vertices: list[list[float]] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_direct: dict[str, Any] | str | None = None,
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
    modifier_direct_obj = _modifier_from_input(
        modifier_direct,
        garden_root=garden_root,
        field_name="modifier_direct",
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
    if modifier_direct_obj is not None:
        state_geometry.modifier_direct = modifier_direct_obj
    obj_dict = state_geometry.to_dict()
    if modifier_direct_obj is not None:
        obj_dict["modifier_direct"] = modifier_direct_obj.to_dict()
    return {
        "object_dict": obj_dict,
        "summary_view": _state_geometry_summary(state_geometry),
        "report": make_report(
            status="ok",
            message=f"Created Radiance StateGeometry: {identifier}",
        ),
    }


def create_radiance_shade_state(
    *,
    modifier: dict[str, Any] | str | None = None,
    modifier_direct: dict[str, Any] | str | None = None,
    shades: list[dict[str, Any] | None] | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a RadianceShadeState dictionary."""
    state = RadianceShadeState(
        modifier=_modifier_from_input(modifier, garden_root=garden_root),
        shades=_state_geometries_from_input(shades, garden_root=garden_root),
    )
    mod_direct = _modifier_from_input(
        modifier_direct,
        garden_root=garden_root,
        field_name="modifier_direct",
    )
    if mod_direct is not None:
        state.modifier_direct = mod_direct
    return {
        "object_dict": _serialize_state_dict(state),
        "summary_view": _state_summary(state, state_type="shade"),
        "report": make_report(status="ok", message="Created RadianceShadeState."),
    }


def _face3d_from_geo_input(data: Any, *, field_name: str) -> Any:
    if data is None:
        return None
    if isinstance(data, dict):
        return face3d_from_dict(data)
    if isinstance(data, list):
        from ladybug_geometry.geometry3d.face import Face3D

        return Face3D.from_vertices(data)
    raise ValueError(f"{field_name} must be a Face3D dictionary or vertex list.")


def create_radiance_subface_state(
    *,
    modifier: dict[str, Any] | str | None = None,
    modifier_direct: dict[str, Any] | str | None = None,
    shades: list[dict[str, Any] | None] | None = None,
    vmtx_geometry: dict[str, Any] | list[list[float]] | None = None,
    dmtx_geometry: dict[str, Any] | list[list[float]] | None = None,
    tmtx_thickness: float | None = None,
    parent_geometry: dict[str, Any] | list[list[float]] | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a RadianceSubFaceState dictionary."""
    state = RadianceSubFaceState(
        modifier=_modifier_from_input(modifier, garden_root=garden_root),
        shades=_state_geometries_from_input(shades, garden_root=garden_root),
    )
    mod_direct = _modifier_from_input(
        modifier_direct,
        garden_root=garden_root,
        field_name="modifier_direct",
    )
    if mod_direct is not None:
        state.modifier_direct = mod_direct
    if vmtx_geometry is not None:
        state.vmtx_geometry = _face3d_from_geo_input(vmtx_geometry, field_name="vmtx_geometry")
    if dmtx_geometry is not None:
        state.dmtx_geometry = _face3d_from_geo_input(dmtx_geometry, field_name="dmtx_geometry")
    if tmtx_thickness is not None and parent_geometry is not None:
        parent_face = _face3d_from_geo_input(parent_geometry, field_name="parent_geometry")
        dist = float(tmtx_thickness) / 2.0
        out_vec = parent_face.normal * dist
        in_vec = out_vec.reverse()
        base_geo = parent_face.flip()
        if state.dmtx_geometry is None:
            state.dmtx_geometry = base_geo.move(out_vec)
        if state.vmtx_geometry is None:
            state.vmtx_geometry = base_geo.move(in_vec)
    return {
        "object_dict": _serialize_state_dict(state),
        "summary_view": _state_summary(state, state_type="subface"),
        "report": make_report(status="ok", message="Created RadianceSubFaceState."),
    }


def _target_object_type(target: dict[str, Any]) -> str:
    object_type = str(target.get("object_type") or "")
    return object_type.lower()


def _coerce_state_dict(
    state: dict[str, Any],
    *,
    object_type: str,
    garden_root: str,
    dynamic_group_identifier: str,
    state_index: int,
) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("Each entry in states must be a state dictionary.")
    if state.get("type") is None:
        unwrapped = state.get("object_dict") or state.get("state_dict")
        if isinstance(unwrapped, dict):
            state = unwrapped
    if object_type == "shade":
        state_cls: type[RadianceShadeState] | type[RadianceSubFaceState] = RadianceShadeState
        expected_type = "RadianceShadeState"
    elif object_type in {"aperture", "door"}:
        state_cls = RadianceSubFaceState
        expected_type = "RadianceSubFaceState"
    else:
        raise ValueError("Dynamic Radiance groups support only shade, aperture, and door targets.")

    raw_type = state.get("type")
    if raw_type == expected_type:
        try:
            loaded = state_cls.from_dict(state)
            serialized = _serialize_state_dict(loaded)
            if isinstance(state.get("modifier_direct"), dict):
                serialized["modifier_direct"] = state["modifier_direct"]
            return serialized
        except Exception:
            pass
    elif raw_type is not None and raw_type not in {"shade", "subface"}:
        try:
            loaded = state_cls.from_dict(state)
            return _serialize_state_dict(loaded)
        except Exception as exc:
            raise ValueError(f"Invalid {expected_type} input. {exc}") from exc

    if "vertices" in state or "geometry" in state:
        raise ValueError(
            "Place state geometry ('vertices' or 'geometry') inside states[i]['shades'] list."
        )
    modifier_obj = _modifier_from_input(
        state.get("modifier"),
        garden_root=garden_root,
        field_name="modifier",
    )
    modifier_direct_obj = _modifier_from_input(
        state.get("modifier_direct"),
        garden_root=garden_root,
        field_name="modifier_direct",
    )
    prefix = str(
        state.get("identifier") or f"{dynamic_group_identifier}_state{state_index}_shade"
    )
    shades_objs = _state_geometries_from_input(
        state.get("shades"),
        garden_root=garden_root,
        prefix=prefix,
    )
    try:
        state_obj = state_cls(modifier=modifier_obj, shades=shades_objs)
        if modifier_direct_obj is not None:
            state_obj.modifier_direct = modifier_direct_obj
        if isinstance(state_obj, RadianceSubFaceState):
            if state.get("vmtx_geometry") is not None:
                state_obj.vmtx_geometry = _face3d_from_geo_input(
                    state.get("vmtx_geometry"),
                    field_name="vmtx_geometry",
                )
            if state.get("dmtx_geometry") is not None:
                state_obj.dmtx_geometry = _face3d_from_geo_input(
                    state.get("dmtx_geometry"),
                    field_name="dmtx_geometry",
                )
    except Exception as exc:
        raise ValueError(f"Invalid {expected_type} inline input. {exc}") from exc
    result_dict = _serialize_state_dict(state_obj)
    if state.get("tmtx_thickness") is not None:
        result_dict["_tmtx_thickness"] = float(state["tmtx_thickness"])
    return result_dict
    return state_obj.to_dict()


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
    targets: list[dict[str, Any]] | None = None,
    dynamic_group_identifier: str | None = None,
    states: list[dict[str, Any]] | None = None,
    operation: str = "replace_all",
    model_target: dict[str, Any] | None = None,
    size: float = 0.2,
    threshold: float = 0.001,
    ambient_division: int = 1000,
    room_based: bool = True,
    view_factor_or_orientation: bool = True,
    vertical_tolerance: float | None = None,
    tmtx_thickness: float | None = None,
) -> dict[str, Any]:
    """Apply a dynamic group/states to objects OR auto-group model exterior apertures."""
    normalized_op = operation.strip().lower().replace("-", "_")
    if normalized_op == "auto_group":
        return auto_group_radiance_apertures(
            garden_root=garden_root,
            model_target=model_target,
            size=size,
            threshold=threshold,
            ambient_division=ambient_division,
            room_based=room_based,
            view_factor_or_orientation=view_factor_or_orientation,
            vertical_tolerance=vertical_tolerance,
            states=states,
        )
    if not targets:
        raise ValueError("targets must include at least one shade, aperture, or door target.")
    if not dynamic_group_identifier:
        raise ValueError("dynamic_group_identifier is required when operation is not auto_group.")
    if normalized_op not in {"replace_all", "add", "clear"}:
        raise ValueError("operation must be replace_all, add, clear, or auto_group.")
    state_list = [] if states is None else states
    if normalized_op != "clear" and not isinstance(state_list, list):
        raise ValueError("states must be a list when operation is not clear.")
    if normalized_op != "clear" and not state_list:
        raise ValueError(
            "setup_radiance_dynamic_group requires at least one Radiance state "
            "for replace_all/add. Pass inline state dictionaries (for example "
            "[{'modifier': ..., 'shades': [...]}]) or use operation='clear'."
        )
    root = str(Path(garden_root).expanduser().resolve())
    root_path = Path(root)
    updated: list[dict[str, Any]] = []
    cached_models: dict[str, Any] = {}
    for target in targets:
        object_type = _target_object_type(target)
        if object_type not in {"shade", "aperture", "door"}:
            raise ValueError("Dynamic Radiance groups support only shade, aperture, and door targets.")
        target_geo = None
        if tmtx_thickness is not None or any(
            isinstance(item, dict) and item.get("tmtx_thickness") is not None
            for item in state_list
        ):
            model_id = str(target.get("model_identifier") or "")
            mt_candidate = target.get("model_target") or model_target or (
                {"target_type": "honeybee_model", "id": model_id} if model_id else None
            )
            cache_key = model_id or json.dumps(mt_candidate or {}, sort_keys=True)
            if cache_key not in cached_models:
                _, resolved_mt = resolve_model_target(root_path, mt_candidate)
                cached_models[cache_key] = load_honeybee_model(root_path, resolved_mt)
            model_obj = cached_models[cache_key]
            obj_id = str(target.get("object_identifier") or target.get("identifier") or "")
            candidates = (
                model_obj.apertures
                if object_type == "aperture"
                else (model_obj.doors if object_type == "door" else model_obj.shades)
            )
            for item_geo in candidates:
                if item_geo.identifier == obj_id:
                    target_geo = item_geo.geometry
                    break

        coerced_states = []
        if normalized_op != "clear":
            for index, item in enumerate(state_list):
                coerced = _coerce_state_dict(
                    item,
                    object_type=object_type,
                    garden_root=root,
                    dynamic_group_identifier=dynamic_group_identifier,
                    state_index=index,
                )
                eff_thickness = coerced.pop("_tmtx_thickness", None)
                if eff_thickness is None:
                    eff_thickness = tmtx_thickness
                if (
                    eff_thickness is not None
                    and object_type in {"aperture", "door"}
                    and target_geo is not None
                ):
                    dist = float(eff_thickness) / 2.0
                    out_vec = target_geo.normal * dist
                    in_vec = out_vec.reverse()
                    base_geo = target_geo.flip()
                    if "dmtx_geometry" not in coerced:
                        coerced["dmtx_geometry"] = base_geo.move(out_vec).to_dict()
                    if "vmtx_geometry" not in coerced:
                        coerced["vmtx_geometry"] = base_geo.move(in_vec).to_dict()
                coerced_states.append(coerced)

        result = _edit_dynamic_target(
            garden_root=root,
            target=target,
            dynamic_group_identifier=dynamic_group_identifier,
            states_update={"operation": normalized_op, "states": coerced_states},
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
            "operation": normalized_op,
            "updated_count": len(updated),
            "state_count": 0 if normalized_op == "clear" else len(state_list),
            "object_types": [_target_object_type(target) for target in targets],
        },
        "report": make_report(
            status="ok",
            message=f"Applied Radiance dynamic group to {len(updated)} object(s).",
        ),
    }


def auto_group_radiance_apertures(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    size: float = 0.2,
    threshold: float = 0.001,
    ambient_division: int = 1000,
    room_based: bool = True,
    view_factor_or_orientation: bool = True,
    vertical_tolerance: float | None = None,
    states: list[dict[str, Any]] | None = None,
    octree: str | None = None,
    rflux_sky: str | None = None,
) -> dict[str, Any]:
    """Automatically group exterior apertures in a Honeybee model by view factor or orientation."""
    import tempfile

    apply_ladybug_tools_runtime_to_path()
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    state_objs: list[RadianceSubFaceState] | None = None
    if states:
        state_objs = []
        for idx, item in enumerate(states):
            coerced = _coerce_state_dict(
                item,
                object_type="aperture",
                garden_root=str(garden_root_path),
                dynamic_group_identifier="auto_group",
                state_index=idx,
            )
            state_objs.append(RadianceSubFaceState.from_dict(coerced))

    with tempfile.TemporaryDirectory(prefix="hb_auto_group_") as tmp_dir:
        grouped_model = automatic_aperture_grouping(
            model,
            octree=octree,
            rflux_sky=rflux_sky,
            size=float(size),
            threshold=float(threshold),
            ambient_division=int(ambient_division),
            room_based=bool(room_based),
            view_factor_or_orientation=bool(view_factor_or_orientation),
            vertical_tolerance=vertical_tolerance,
            states=state_objs,
            working_folder=tmp_dir,
        )

    updated_model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        grouped_model,
        name=str(resolved_model_target["model_identifier"]),
    )
    groups: dict[str, list[str]] = {}
    for aperture in grouped_model.apertures:
        dg_id = aperture.properties.radiance.dynamic_group_identifier
        if dg_id:
            groups.setdefault(dg_id, []).append(aperture.identifier)

    return {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "updated_model_target": updated_model_target,
        "groups": groups,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": updated_model_target,
            "model_path": persisted_path,
            "operation": "auto_group",
            "group_count": len(groups),
            "grouped_aperture_count": sum(len(items) for items in groups.values()),
            "groups": groups,
            "method": "view_factor" if view_factor_or_orientation else "orientation",
            "room_based": room_based,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            base_honeybee_model_changed=True,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "auto_group_radiance_apertures",
                "group_count": len(groups),
                "grouped_aperture_count": sum(len(items) for items in groups.values()),
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Auto-grouped apertures into {len(groups)} dynamic group(s).",
        ),
    }
