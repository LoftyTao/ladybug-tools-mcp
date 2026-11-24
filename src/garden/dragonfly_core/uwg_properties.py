"""Dragonfly UWG property services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dragonfly_uwg._extend_dragonfly  # noqa: F401
from dragonfly_uwg.simulation.boundary import BoundaryLayerParameter
from dragonfly_uwg.simulation.refsite import ReferenceEPWSite
from dragonfly_uwg.simulation.vegetation import VegetationParameter
from dragonfly_uwg.terrain import Terrain
from dragonfly_uwg.traffic import TrafficParameter
from ladybug_geometry.geometry2d import Point2D, Polygon2D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    normalize_dragonfly_model_target,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import (
    is_dragonfly_model_target,
    normalize_dragonfly_object_target,
)
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


MODEL_UWG_FIELDS = (
    "terrain",
    "traffic",
    "tree_coverage_fraction",
    "grass_coverage_fraction",
)
BUILDING_UWG_FIELDS = (
    "program",
    "vintage",
    "fract_heat_to_canyon",
    "shgc",
    "wall_albedo",
    "roof_albedo",
    "roof_veg_fraction",
)
CONTEXT_UWG_FIELDS = ("is_vegetation",)


def get_dragonfly_uwg_properties_summary(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    climate_zone: str | None = None,
) -> dict[str, Any]:
    """Read compact Dragonfly UWG extension properties and computed metrics from a Garden."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)

    buildings = [
        {
            "identifier": building.identifier,
            "display_name": getattr(building, "display_name", None),
            "uwg": _uwg_summary(building),
        }
        for building in model.buildings
    ]
    context_shades = [
        {
            "identifier": shade.identifier,
            "display_name": getattr(shade, "display_name", None),
            "uwg": _uwg_summary(shade),
        }
        for shade in model.context_shades
    ]
    model_uwg = model.properties.uwg
    computed_metrics: dict[str, Any] = {}
    for metric in (
        "footprint_density",
        "facade_to_site",
        "exposed_ground_area",
        "grass_coverage_from_geometry",
    ):
        try:
            computed_metrics[metric] = round(float(getattr(model_uwg, metric)), 6)
        except Exception:
            computed_metrics[metric] = None
    try:
        computed_metrics["is_tree_coverage_autocalculated"] = bool(
            model_uwg.is_tree_coverage_autocalcualted
        )
    except Exception:
        computed_metrics["is_tree_coverage_autocalculated"] = None
    if climate_zone is not None:
        try:
            computed_metrics["average_shgc"] = round(
                float(model_uwg.average_shgc(climate_zone)), 6
            )
        except Exception:
            computed_metrics["average_shgc"] = None

    summary_view = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "model": {
            "identifier": model.identifier,
            "display_name": getattr(model, "display_name", None),
            "uwg": _uwg_summary(model),
            "computed_metrics": computed_metrics,
        },
        "buildings": buildings,
        "context_shades": context_shades,
        "counts": {
            "buildings": len(buildings),
            "context_shades": len(context_shades),
        },
    }
    return {
        "model_target": resolved_model_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Read Dragonfly UWG properties summary: {model.identifier}",
        ),
    }


def create_uwg_helper(
    *,
    helper_type: str,
    params: dict[str, Any] | None = None,
    garden_root: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and construct a typed dragonfly_uwg parameter or Terrain helper dictionary."""
    raw = dict(params or {})
    kind = helper_type.strip().lower().replace("-", "_")
    if kind == "terrain":
        if raw.pop("from_buildings", False) or "geometry" not in raw:
            if garden_root is None:
                raise ValueError(
                    "Terrain without explicit geometry requires garden_root to derive bounding rect from Buildings."
                )
            garden_root_path = Path(garden_root).expanduser().resolve()
            _, resolved_model_target = resolve_model_target(garden_root_path, model_target)
            model = load_dragonfly_model(garden_root_path, resolved_model_target)
            obj = Terrain.from_building_bounding_rect(model.buildings)
            for attr in (
                "pavement_albedo",
                "pavement_thickness",
                "pavement_conductivity",
                "pavement_heat_capacity",
            ):
                if attr in raw and raw[attr] is not None:
                    setattr(obj, attr, float(raw[attr]))
        else:
            obj = _coerce_terrain(raw)
    elif kind in {"traffic", "traffic_parameter"}:
        obj = TrafficParameter.from_dict(raw) if "type" in raw else TrafficParameter(**raw)
    elif kind in {"vegetation", "vegetation_parameter"}:
        obj = VegetationParameter.from_dict(raw) if "type" in raw else VegetationParameter(**raw)
    elif kind in {"reference_epw_site", "refsite"}:
        obj = ReferenceEPWSite.from_dict(raw) if "type" in raw else ReferenceEPWSite(**raw)
    elif kind in {"boundary_layer", "boundary_layer_parameter"}:
        obj = BoundaryLayerParameter.from_dict(raw) if "type" in raw else BoundaryLayerParameter(**raw)
    else:
        raise ValueError(
            "helper_type must be terrain, traffic_parameter, vegetation_parameter, "
            "reference_epw_site, or boundary_layer_parameter."
        )
    data = obj.to_dict()
    return {
        "helper": data,
        "object_dict": data,
        "summary_view": {
            "helper_type": kind,
            "sdk_type": data.get("type"),
        },
        "report": make_report(
            status="ok",
            message=f"Constructed UWG {data.get('type', kind)} helper.",
        ),
    }


def _coerce_terrain(value: dict[str, Any], buildings: list[Any] | None = None) -> Terrain:
    if value.get("type") == "Terrain":
        return Terrain.from_dict(value)
    data = dict(value)
    if (data.pop("from_buildings", False) or "geometry" not in data) and buildings:
        terrain = Terrain.from_building_bounding_rect(buildings)
        for attr in (
            "pavement_albedo",
            "pavement_thickness",
            "pavement_conductivity",
            "pavement_heat_capacity",
        ):
            if attr in data and data[attr] is not None:
                setattr(terrain, attr, float(data[attr]))
        return terrain
    geo = data.pop("geometry")
    from ladybug_geometry.geometry3d.face import Face3D
    from ladybug_geometry.geometry3d.pointvector import Point3D

    def _face_from_item(item: Any) -> Face3D:
        if isinstance(item, Face3D):
            return item
        if isinstance(item, dict):
            return Face3D.from_dict(item)
        return Face3D([Point3D(float(pt[0]), float(pt[1]), float(pt[2]) if len(pt) > 2 else 0.0) for pt in item])

    if isinstance(geo, (list, tuple)) and geo and isinstance(geo[0], (list, tuple)) and geo[0] and isinstance(geo[0][0], (list, tuple)):
        faces = tuple(_face_from_item(item) for item in geo)
    elif isinstance(geo, (list, tuple)) and geo and isinstance(geo[0], (Face3D, dict)):
        faces = tuple(_face_from_item(item) for item in geo)
    else:
        faces = (_face_from_item(geo),)
    return Terrain(faces, **data)


def apply_dragonfly_uwg_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    terrain: dict[str, Any] | None = None,
    traffic: dict[str, Any] | None = None,
    tree_coverage_fraction: float | None = None,
    grass_coverage_fraction: float | None = None,
    program: str | None = None,
    vintage: str | None = None,
    fract_heat_to_canyon: float | None = None,
    shgc: float | None = None,
    wall_albedo: float | None = None,
    roof_albedo: float | None = None,
    roof_veg_fraction: float | None = None,
    is_vegetation: bool | None = None,
    infer_program_from_energy_program: bool = False,
) -> dict[str, Any]:
    """Apply narrow SDK-backed Dragonfly UWG properties to a model host."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    host_type, host, normalized_target = _resolve_host(
        model,
        host_target,
        resolved_model_target,
    )
    raw_updates = {
        "terrain": terrain,
        "traffic": traffic,
        "tree_coverage_fraction": tree_coverage_fraction,
        "grass_coverage_fraction": grass_coverage_fraction,
        "program": program,
        "vintage": vintage,
        "fract_heat_to_canyon": fract_heat_to_canyon,
        "shgc": shgc,
        "wall_albedo": wall_albedo,
        "roof_albedo": roof_albedo,
        "roof_veg_fraction": roof_veg_fraction,
        "is_vegetation": is_vegetation,
    }
    allowed = _allowed_fields(host_type)
    rejected = [
        key for key, value in raw_updates.items() if value is not None and key not in allowed
    ]
    if rejected:
        raise ValueError(
            "apply_dragonfly_uwg_properties supports model, building, and "
            f"context_shade hosts. Fields not valid for {host_type}: "
            f"{', '.join(rejected)}."
        )

    updates = _coerce_updates(raw_updates, buildings=list(model.buildings))
    updated_fields = [key for key in allowed if updates.get(key) is not None]
    if infer_program_from_energy_program:
        if host_type not in {"building", "model"}:
            raise ValueError(
                "infer_program_from_energy_program requires a building or model host_target."
            )
        updated_fields.append("infer_program_from_energy_program")
    if not updated_fields:
        raise ValueError(
            "apply_dragonfly_uwg_properties requires at least one supported "
            "UWG property input."
        )

    uwg = host.properties.uwg
    for field in updated_fields:
        if field == "infer_program_from_energy_program":
            continue
        setattr(uwg, field, updates[field])
    if infer_program_from_energy_program:
        if host_type == "building":
            host.properties.uwg.infer_program_from_energy_program()
        else:
            for bldg in model.buildings:
                bldg.properties.uwg.infer_program_from_energy_program()

    updated_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=str(resolved_model_target["model_identifier"]),
        included_prop=["energy", "radiance", "uwg"],
        set_base=manifest.base_dragonfly_model == resolved_model_target,
    )
    summary_view = {
        "target": normalized_target,
        "model_target": updated_model_target,
        "host_type": host_type,
        "updated_fields": updated_fields,
        "uwg": _uwg_summary(host),
    }
    return {
        "target": normalized_target,
        "host_target": normalized_target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "apply_dragonfly_uwg_properties",
                "target": normalized_target,
                "updated_fields": updated_fields,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Applied Dragonfly UWG properties to {host_type}.",
        ),
    }


def _coerce_updates(updates: dict[str, Any], *, buildings: list[Any] | None = None) -> dict[str, Any]:
    coerced = dict(updates)
    if isinstance(coerced.get("terrain"), dict):
        coerced["terrain"] = _coerce_terrain(coerced["terrain"], buildings=buildings)
    if isinstance(coerced.get("traffic"), dict):
        raw_t = coerced["traffic"]
        coerced["traffic"] = (
            TrafficParameter.from_dict(raw_t)
            if "type" in raw_t
            else TrafficParameter(**raw_t)
        )
    return coerced


def _allowed_fields(host_type: str) -> tuple[str, ...]:
    if host_type == "model":
        return MODEL_UWG_FIELDS
    if host_type == "building":
        return BUILDING_UWG_FIELDS
    if host_type == "context_shade":
        return CONTEXT_UWG_FIELDS
    raise ValueError(
        "apply_dragonfly_uwg_properties supports model, building, and "
        "context_shade hosts."
    )


def _resolve_host(
    model: Any,
    host_target: dict[str, Any],
    model_target: dict[str, Any],
) -> tuple[str, Any, dict[str, Any]]:
    if is_dragonfly_model_target(host_target):
        normalized = normalize_dragonfly_model_target(host_target)
        if normalized["model_identifier"] != model_target["model_identifier"]:
            raise ValueError("UWG model host target must match the loaded model_target.")
        return "model", model, normalized

    normalized_object = normalize_dragonfly_object_target(host_target)
    host_type = normalized_object["object_type"]
    identifier = normalized_object["object_identifier"]
    if host_type == "building":
        return (
            "building",
            _one_by_identifier(model.buildings_by_identifier([identifier]), identifier, "Building"),
            normalized_object,
        )
    if host_type == "context_shade":
        return (
            "context_shade",
            _one_by_identifier(
                model.context_shade_by_identifier([identifier]),
                identifier,
                "ContextShade",
            ),
            normalized_object,
        )
    if host_type in {"room2d", "story"}:
        raise ValueError(
            "apply_dragonfly_uwg_properties supports model, building, and "
            "context_shade hosts. Room2D and Story UWG properties have no "
            "editable MCP fields in this slice."
        )
    raise ValueError(
        "apply_dragonfly_uwg_properties supports model, building, and "
        f"context_shade hosts, not {host_type}."
    )


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _uwg_summary(host: Any) -> dict[str, Any]:
    properties = getattr(getattr(host, "properties", None), "uwg", None)
    if properties is None:
        return {"available": False, "to_dict_available": False}
    summary: dict[str, Any] = {
        "available": True,
        "type": properties.__class__.__name__,
        "to_dict_available": hasattr(properties, "to_dict"),
    }
    fields: dict[str, Any] = {}
    for field in (*MODEL_UWG_FIELDS, *BUILDING_UWG_FIELDS, *CONTEXT_UWG_FIELDS):
        if not hasattr(properties, field):
            continue
        value = getattr(properties, field)
        if value is None or isinstance(value, (str, int, float, bool)):
            fields[field] = value
        elif hasattr(value, "to_dict"):
            fields[field] = value.to_dict()
    if fields:
        summary["fields"] = fields
    return summary
