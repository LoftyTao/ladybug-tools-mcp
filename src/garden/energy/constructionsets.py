"""Honeybee Energy construction set foundation creation services."""

from __future__ import annotations

from typing import Any

from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.construction.dictutil import dict_to_construction
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.constructionset import (
    ApertureConstructionSet,
    ConstructionSet,
    DoorConstructionSet,
    FloorConstructionSet,
    RoofCeilingConstructionSet,
    WallConstructionSet,
)
from honeybee_energy.lib.constructions import (
    opaque_construction_by_identifier,
    shade_construction_by_identifier,
    window_construction_by_identifier,
)
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.materials import (
    opaque_material_by_identifier,
    window_material_by_identifier,
)
from honeybee_energy.material.dictutil import dict_to_material
from honeybee_energy.material.frame import EnergyWindowFrame
from honeybee_energy.material.gas import (
    EnergyWindowMaterialGas,
    EnergyWindowMaterialGasCustom,
    EnergyWindowMaterialGasMixture,
)
from honeybee_energy.material.glazing import (
    EnergyWindowMaterialGlazing,
    EnergyWindowMaterialSimpleGlazSys,
)
from honeybee_energy.material.opaque import (
    EnergyMaterial,
    EnergyMaterialNoMass,
    EnergyMaterialVegetation,
)
from honeybee_energy.material.shade import (
    EnergyWindowMaterialBlind,
    EnergyWindowMaterialShade,
)

from ladybug_tools_mcp.contracts import make_report
from garden.energy._schemas import (
    INLINE_CONSTRUCTION_MODELS,
    InlineAirBoundaryConstructionSpec,
    InlineOpaqueConstructionSpec,
    InlineShadeConstructionSpec,
    InlineWindowConstructionSpec,
    InlineWindowDynamicConstructionSpec,
    InlineWindowShadeConstructionSpec,
    OpaqueConstructionParams,
    WindowConstructionParams,
    validate_construction_params,
    validate_inline_construction_dict,
    validate_material_params,
)
from garden.energy.programtypes import _schedule_from_input
from garden.libraries.properties import (
    get_garden_properties_library_object,
    save_garden_properties_library_object,
)


OpaqueMaterial = EnergyMaterial | EnergyMaterialNoMass | EnergyMaterialVegetation
WindowMaterial = (
    EnergyWindowMaterialGlazing
    | EnergyWindowMaterialSimpleGlazSys
    | EnergyWindowMaterialGas
    | EnergyWindowMaterialGasCustom
    | EnergyWindowMaterialGasMixture
    | EnergyWindowMaterialShade
    | EnergyWindowMaterialBlind
)
AnyMaterial = OpaqueMaterial | WindowMaterial | EnergyWindowFrame
_WINDOW_CONSTRUCTION_TYPES = (
    WindowConstruction,
    WindowConstructionShade,
    WindowConstructionDynamic,
)
AnyConstruction = (
    OpaqueConstruction
    | WindowConstruction
    | WindowConstructionShade
    | WindowConstructionDynamic
    | ShadeConstruction
    | AirBoundaryConstruction
)


def _library_object_dict_from_target(
    *,
    garden_root: str | None,
    data: Any,
    field_name: str,
    domain: str,
    object_family: str,
) -> Any:
    if not isinstance(data, dict) or data.get("target_type") != "garden_properties_library_object":
        return data
    if garden_root is None:
        raise ValueError(f"{field_name} target requires garden_root.")
    if data.get("domain") != domain or data.get("object_family") != object_family:
        raise ValueError(f"{field_name} target must reference {domain}:{object_family}.")
    return get_garden_properties_library_object(
        garden_root=garden_root,
        target=data,
    )["object_dict"]


def _public_value(value: Any) -> Any:
    if hasattr(value, "identifier"):
        return value.identifier
    if isinstance(value, (tuple, list)):
        return [_public_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _matrix_value(value: Any) -> Any:
    value = _public_value(value)
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return value


def _add_existing_fields(target: dict[str, Any], obj: Any, fields: tuple[str, ...]) -> None:
    for field in fields:
        if hasattr(obj, field):
            target[field] = _public_value(getattr(obj, field))


def _result(obj: Any, summary_view: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "object_dict": obj.to_dict(),
        "summary_view": summary_view,
        "report": make_report(status="ok", message=message),
    }


def _save_library_result(
    result: dict[str, Any],
    *,
    garden_root: str | None,
    object_family: str,
    ready_for: str,
    return_object_dict: bool,
) -> dict[str, Any]:
    if not garden_root:
        return result
    saved = save_garden_properties_library_object(
        garden_root=garden_root,
        domain="honeybee_energy",
        object_family=object_family,
        object_dict=result["object_dict"],
    )
    result["target"] = saved["target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["target"] = saved["target"]
    result["summary_view"]["ready_for"] = ready_for
    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def _normalized_detail(return_detail: str) -> str:
    detail = return_detail.lower().strip()
    if detail not in {"summary", "full"}:
        raise ValueError("return_detail must be either 'summary' or 'full'.")
    return detail


_MATERIAL_SUMMARY_FIELDS = (
    "thickness",
    "r_value",
    "u_value",
    "r_factor",
    "u_factor",
    "conductivity",
    "density",
    "specific_heat",
    "solar_transmittance",
    "visible_transmittance",
    "solar_reflectance",
    "visible_reflectance",
    "shgc",
    "vt",
    "gas_type",
    "gas_types",
    "gas_count",
    "width",
    "conductance",
    "plant_height",
    "leaf_area_index",
    "slat_orientation",
    "slat_angle",
)


_MATERIAL_FULL_FIELDS = (
    "display_name",
    "roughness",
    "thickness",
    "conductivity",
    "density",
    "specific_heat",
    "thermal_absorptance",
    "solar_absorptance",
    "visible_absorptance",
    "solar_reflectance",
    "visible_reflectance",
    "resistivity",
    "u_value",
    "r_value",
    "mass_area_density",
    "area_heat_capacity",
    "soil_thermal_absorptance",
    "soil_solar_absorptance",
    "soil_visible_absorptance",
    "plant_height",
    "leaf_area_index",
    "leaf_reflectivity",
    "leaf_emissivity",
    "min_stomatal_resist",
    "sat_vol_moist_cont",
    "residual_vol_moist_cont",
    "init_vol_moist_cont",
    "moist_diff_model",
    "soil_layer",
    "solar_reflectance_back",
    "visible_reflectance_back",
    "infrared_transmittance",
    "emissivity",
    "emissivity_back",
    "dirt_correction",
    "solar_diffusing",
    "solar_transmissivity",
    "visible_transmissivity",
    "u_factor",
    "shgc",
    "vt",
    "r_factor",
    "solar_transmittance",
    "visible_transmittance",
    "gas_type",
    "gas_types",
    "gas_fractions",
    "gas_count",
    "viscosity",
    "prandtl",
    "conductivity_coeff_a",
    "viscosity_coeff_a",
    "specific_heat_coeff_a",
    "conductivity_coeff_b",
    "viscosity_coeff_b",
    "specific_heat_coeff_b",
    "conductivity_coeff_c",
    "viscosity_coeff_c",
    "specific_heat_coeff_c",
    "specific_heat_ratio",
    "molecular_weight",
    "slat_orientation",
    "slat_width",
    "slat_separation",
    "slat_thickness",
    "slat_angle",
    "slat_conductivity",
    "beam_solar_transmittance",
    "beam_solar_reflectance",
    "beam_solar_reflectance_back",
    "diffuse_solar_transmittance",
    "diffuse_solar_reflectance",
    "diffuse_solar_reflectance_back",
    "beam_visible_transmittance",
    "beam_visible_reflectance",
    "beam_visible_reflectance_back",
    "diffuse_visible_transmittance",
    "diffuse_visible_reflectance",
    "diffuse_visible_reflectance_back",
    "distance_to_glass",
    "top_opening_multiplier",
    "bottom_opening_multiplier",
    "left_opening_multiplier",
    "right_opening_multiplier",
    "opening_multiplier",
    "airflow_permeability",
    "slat_resistivity",
    "width",
    "conductance",
    "edge_to_center_ratio",
    "outside_projection",
    "inside_projection",
)


def _material_property_matrix(material: AnyMaterial) -> dict[str, Any]:
    rows = []
    seen = set()
    for field in _MATERIAL_FULL_FIELDS:
        if field in seen or not hasattr(material, field):
            continue
        seen.add(field)
        rows.append([field, _matrix_value(getattr(material, field))])
    return {"columns": ["property", "value"], "rows": rows}


def _material_summary(
    material: AnyMaterial,
    *,
    return_detail: str = "summary",
) -> dict[str, Any]:
    detail = _normalized_detail(return_detail)
    summary: dict[str, Any] = {
        "type": material.__class__.__name__,
        "identifier": material.identifier,
    }
    _add_existing_fields(summary, material, _MATERIAL_SUMMARY_FIELDS)
    if detail == "full":
        summary["property_matrix"] = _material_property_matrix(material)
    return summary


_MATERIAL_MATRIX_COLUMNS = [
    "index",
    "identifier",
    "type",
    "thickness",
    "r_value",
    "u_value",
    "conductivity",
    "density",
    "specific_heat",
    "solar_transmittance",
    "visible_transmittance",
    "solar_reflectance",
    "visible_reflectance",
    "shgc",
]


def _material_matrix(materials: list[AnyMaterial]) -> dict[str, Any]:
    rows = []
    for index, material in enumerate(materials):
        rows.append(
            [
                index,
                material.identifier,
                material.__class__.__name__,
                _matrix_value(getattr(material, "thickness", None)),
                _matrix_value(getattr(material, "r_value", None)),
                _matrix_value(getattr(material, "u_value", None)),
                _matrix_value(getattr(material, "conductivity", None)),
                _matrix_value(getattr(material, "density", None)),
                _matrix_value(getattr(material, "specific_heat", None)),
                _matrix_value(getattr(material, "solar_transmittance", None)),
                _matrix_value(getattr(material, "visible_transmittance", None)),
                _matrix_value(getattr(material, "solar_reflectance", None)),
                _matrix_value(getattr(material, "visible_reflectance", None)),
                _matrix_value(getattr(material, "shgc", None)),
            ]
        )
    return {"columns": _MATERIAL_MATRIX_COLUMNS, "rows": rows}


def _construction_summary(
    construction: AnyConstruction,
    *,
    return_detail: str = "summary",
) -> dict[str, Any]:
    detail = _normalized_detail(return_detail)
    summary: dict[str, Any] = {
        "type": construction.__class__.__name__,
        "identifier": construction.identifier,
    }
    materials = []
    if hasattr(construction, "materials"):
        materials = list(construction.materials)
        summary["layers"] = [mat.identifier for mat in materials]
        summary["layer_count"] = len(materials)
    if hasattr(construction, "frame"):
        frame = construction.frame
        summary["frame"] = frame.identifier if frame else None
    if hasattr(construction, "constructions"):
        summary["constructions"] = [constr.identifier for constr in construction.constructions]
    _add_existing_fields(
        summary,
        construction,
        (
            "r_value",
            "u_value",
            "r_factor",
            "u_factor",
            "thickness",
            "mass_area_density",
            "area_heat_capacity",
            "solar_transmittance",
            "solar_reflectance",
            "solar_absorptance",
            "visible_transmittance",
            "visible_reflectance",
            "visible_absorptance",
            "shgc",
            "glazing_count",
            "gap_count",
            "has_frame",
            "has_shade",
            "is_dynamic",
            "is_specular",
            "is_switchable_glazing",
            "window_construction",
            "shade_material",
            "shade_location",
            "control_type",
            "setpoint",
            "schedule",
            "air_mixing_per_area",
        ),
    )
    if detail == "full" and materials:
        summary["layer_matrix"] = _material_matrix(materials)
    return summary


def _subset_summary(subset: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": subset.__class__.__name__}
    for field in (
        "exterior_construction",
        "interior_construction",
        "ground_construction",
        "window_construction",
        "skylight_construction",
        "operable_construction",
        "exterior_glass_construction",
        "interior_glass_construction",
        "overhead_construction",
    ):
        if hasattr(subset, field):
            construction = getattr(subset, field)
            summary[field] = construction.identifier if construction else None
    if hasattr(subset, "modified_constructions"):
        summary["modified_constructions"] = [
            constr.identifier for constr in subset.modified_constructions
        ]
    if hasattr(subset, "is_modified"):
        summary["is_modified"] = subset.is_modified
    return summary


def _slot_matrix(construction_set: ConstructionSet) -> dict[str, Any]:
    rows = []
    for subset_name, subset in (
        ("wall_set", construction_set.wall_set),
        ("floor_set", construction_set.floor_set),
        ("roof_ceiling_set", construction_set.roof_ceiling_set),
        ("aperture_set", construction_set.aperture_set),
        ("door_set", construction_set.door_set),
    ):
        for field, identifier in _subset_summary(subset).items():
            if field in {"type", "modified_constructions", "is_modified"} or identifier is None:
                continue
            construction = getattr(subset, field)
            rows.append(
                [
                    subset_name,
                    field,
                    construction.identifier,
                    construction.__class__.__name__,
                    _matrix_value(getattr(construction, "u_factor", None)),
                    _matrix_value(getattr(construction, "r_factor", None)),
                    _matrix_value(getattr(construction, "u_value", None)),
                    _matrix_value(getattr(construction, "r_value", None)),
                    _matrix_value(
                        [mat.identifier for mat in getattr(construction, "materials", [])]
                    ),
                ]
            )
    for field in ("shade_construction", "air_boundary_construction"):
        construction = getattr(construction_set, field)
        if construction is None:
            continue
        rows.append(
            [
                "construction_set",
                field,
                construction.identifier,
                construction.__class__.__name__,
                _matrix_value(getattr(construction, "u_factor", None)),
                _matrix_value(getattr(construction, "r_factor", None)),
                _matrix_value(getattr(construction, "u_value", None)),
                _matrix_value(getattr(construction, "r_value", None)),
                _matrix_value([mat.identifier for mat in getattr(construction, "materials", [])]),
            ]
        )
    return {
        "columns": [
            "subset",
            "slot",
            "construction_identifier",
            "construction_type",
            "u_factor",
            "r_factor",
            "u_value",
            "r_value",
            "layers",
        ],
        "rows": rows,
    }


def _construction_set_summary(
    construction_set: ConstructionSet,
    *,
    return_detail: str = "summary",
) -> dict[str, Any]:
    detail = _normalized_detail(return_detail)
    modified = [constr.identifier for constr in construction_set.modified_constructions_unique]
    unique = [constr.identifier for constr in construction_set.constructions_unique]
    summary = {
        "type": "ConstructionSet",
        "identifier": construction_set.identifier,
        "wall_set": _subset_summary(construction_set.wall_set),
        "floor_set": _subset_summary(construction_set.floor_set),
        "roof_ceiling_set": _subset_summary(construction_set.roof_ceiling_set),
        "aperture_set": _subset_summary(construction_set.aperture_set),
        "door_set": _subset_summary(construction_set.door_set),
        "shade_construction": construction_set.shade_construction.identifier
        if construction_set.shade_construction
        else None,
        "air_boundary_construction": construction_set.air_boundary_construction.identifier
        if construction_set.air_boundary_construction
        else None,
        "construction_count": len(unique),
        "constructions": unique,
        "modified_construction_count": len(modified),
        "modified_constructions": modified,
        "material_count": len(construction_set.materials_unique),
        "modified_material_count": len(construction_set.modified_materials_unique),
    }
    if detail == "full":
        summary["slot_matrix"] = _slot_matrix(construction_set)
        summary["material_matrix"] = _material_matrix(list(construction_set.materials_unique))
    return summary


def _material_from_input(
    data: dict[str, Any] | str,
    *,
    field_name: str,
    garden_root: str | None = None,
) -> AnyMaterial:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="material",
    )
    try:
        if isinstance(data, str):
            try:
                return opaque_material_by_identifier(data)
            except Exception:
                try:
                    return window_material_by_identifier(data)
                except Exception:
                    if garden_root is not None:
                        return dict_to_material(
                            get_garden_properties_library_object(
                                garden_root=garden_root,
                                domain="honeybee_energy",
                                object_family="material",
                                identifier=data,
                            )["object_dict"]
                        )
                    raise
        if isinstance(data, dict):
            return dict_to_material(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid Honeybee Energy material. {exc}") from exc
    raise ValueError(f"{field_name} must be a material dict or library identifier.")


def _build_window_shade_construction(
    *,
    identifier: str,
    window_construction: dict[str, Any] | str,
    shade_material: dict[str, Any] | str,
    shade_location: str = "Interior",
    control_type: str = "AlwaysOn",
    setpoint: float | None = None,
    schedule: dict[str, Any] | str | None = None,
    field_name: str = "window_shade",
    garden_root: str | None = None,
) -> WindowConstructionShade:
    base_window = _construction_from_input(
        window_construction,
        field_name=f"{field_name}.window_construction",
        expected_types=(WindowConstruction,),
        garden_root=garden_root,
    )
    shade_mat = _material_from_input(
        shade_material,
        field_name=f"{field_name}.shade_material",
        garden_root=garden_root,
    )
    schedule_obj = (
        _schedule_from_input(
            schedule,
            field_name=f"{field_name}.schedule",
            garden_root=garden_root,
        )
        if schedule is not None
        else None
    )
    try:
        return WindowConstructionShade(
            identifier,
            base_window,
            shade_mat,
            shade_location=shade_location,
            control_type=control_type,
            setpoint=setpoint,
            schedule=schedule_obj,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid WindowConstructionShade input. {exc}") from exc


def _build_window_dynamic_construction(
    *,
    identifier: str,
    constructions: list[dict[str, Any] | str],
    schedule: dict[str, Any] | str,
    field_name: str = "window_dynamic",
    garden_root: str | None = None,
) -> WindowConstructionDynamic:
    if not isinstance(constructions, (list, tuple)) or len(constructions) < 2:
        raise ValueError(
            f"{field_name} requires at least two WindowConstruction items in constructions."
        )
    if schedule is None:
        raise ValueError(f"{field_name} requires a schedule.")
    state_constructions = [
        _construction_from_input(
            constr,
            field_name=f"{field_name}.constructions",
            expected_types=(WindowConstruction,),
            garden_root=garden_root,
        )
        for constr in constructions
    ]
    schedule_obj = _schedule_from_input(
        schedule,
        field_name=f"{field_name}.schedule",
        garden_root=garden_root,
    )
    try:
        return WindowConstructionDynamic(
            identifier,
            state_constructions,
            schedule_obj,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid WindowConstructionDynamic input. {exc}") from exc


def _inline_construction_from_dict(
    data: dict[str, Any],
    *,
    field_name: str,
    expected_types: tuple[type, ...] | None = None,
    garden_root: str | None = None,
) -> AnyConstruction:
    raw_type = str(data.get("construction_type") or "").strip().lower().replace("-", "_")
    if not raw_type:
        if "air_mixing_per_area" in data or "air_mixing_schedule" in data:
            raw_type = "air_boundary"
        elif "shade_material" in data:
            raw_type = "window_shade"
        elif "constructions" in data:
            raw_type = "window_dynamic"
        elif "u_factor" in data or "shgc" in data or "frame" in data or (
            expected_types is not None
            and any(cls in expected_types for cls in _WINDOW_CONSTRUCTION_TYPES)
            and OpaqueConstruction not in expected_types
            and "materials" not in data
        ):
            raw_type = "window"
        elif (
            "solar_reflectance" in data
            or "visible_reflectance" in data
            or "is_specular" in data
            or (expected_types is not None and expected_types == (ShadeConstruction,))
        ):
            raw_type = "shade"
        elif "materials" in data:
            if (
                expected_types is not None
                and WindowConstruction in expected_types
                and OpaqueConstruction not in expected_types
            ):
                raw_type = "window"
            else:
                raw_type = "opaque"
        elif expected_types is not None and expected_types == (AirBoundaryConstruction,):
            raw_type = "air_boundary"
    if not raw_type:
        raise ValueError(
            f"{field_name} inline construction dictionary must specify materials, u_factor/shgc, or construction_type."
        )
    if raw_type not in INLINE_CONSTRUCTION_MODELS:
        raise ValueError(
            f"{field_name} inline construction dictionary has unsupported construction_type={raw_type!r}; "
            "must specify materials, u_factor/shgc, or a valid construction_type."
        )
    spec = validate_inline_construction_dict(raw_type, data, field_name=field_name)
    identifier = str(getattr(spec, "identifier", None) or f"custom_{raw_type}")
    if isinstance(spec, InlineOpaqueConstructionSpec):
        return OpaqueConstruction(
            identifier,
            [
                _material_from_input(mat, field_name=f"{field_name}.materials", garden_root=garden_root)
                for mat in spec.materials
            ],
        )
    if isinstance(spec, InlineWindowConstructionSpec):
        if spec.materials is not None:
            frame = (
                _material_from_input(spec.frame, field_name=f"{field_name}.frame", garden_root=garden_root)
                if spec.frame is not None
                else None
            )
            return WindowConstruction(
                identifier,
                [
                    _material_from_input(mat, field_name=f"{field_name}.materials", garden_root=garden_root)
                    for mat in spec.materials
                ],
                frame=frame,
            )
        assert spec.u_factor is not None and spec.shgc is not None
        return WindowConstruction.from_simple_parameters(
            identifier,
            spec.u_factor,
            spec.shgc,
            vt=spec.vt,
        )
    if isinstance(spec, InlineWindowShadeConstructionSpec):
        return _build_window_shade_construction(
            identifier=identifier,
            window_construction=spec.window_construction,
            shade_material=spec.shade_material,
            shade_location=spec.shade_location,
            control_type=spec.control_type,
            setpoint=spec.setpoint,
            schedule=spec.schedule,
            field_name=field_name,
            garden_root=garden_root,
        )
    if isinstance(spec, InlineWindowDynamicConstructionSpec):
        return _build_window_dynamic_construction(
            identifier=identifier,
            constructions=spec.constructions,
            schedule=spec.schedule,
            field_name=field_name,
            garden_root=garden_root,
        )
    if isinstance(spec, InlineShadeConstructionSpec):
        return ShadeConstruction(
            identifier,
            solar_reflectance=spec.solar_reflectance,
            visible_reflectance=spec.visible_reflectance,
            is_specular=spec.is_specular,
        )
    if isinstance(spec, InlineAirBoundaryConstructionSpec):
        return AirBoundaryConstruction(
            identifier,
            air_mixing_per_area=spec.air_mixing_per_area,
            air_mixing_schedule=_schedule_from_input(
                spec.air_mixing_schedule,
                field_name=f"{field_name}.air_mixing_schedule",
                garden_root=garden_root,
            ),
        )
    raise ValueError(
        f"{field_name} inline construction dictionary must specify materials, u_factor/shgc, or construction_type."
    )


def _construction_from_input(
    data: dict[str, Any] | str,
    *,
    field_name: str,
    expected_types: tuple[type, ...] | None = None,
    garden_root: str | None = None,
) -> AnyConstruction:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="construction",
    )
    if isinstance(data, dict) and "type" not in data and set(data) == {"identifier"} and isinstance(data.get("identifier"), str):
        data = data["identifier"]
    try:
        if isinstance(data, str):
            construction = None
            lookups = []
            if expected_types is None:
                lookups = [
                    opaque_construction_by_identifier,
                    window_construction_by_identifier,
                    shade_construction_by_identifier,
                ]
            else:
                if OpaqueConstruction in expected_types or AirBoundaryConstruction in expected_types:
                    lookups.append(opaque_construction_by_identifier)
                if any(cls in expected_types for cls in _WINDOW_CONSTRUCTION_TYPES):
                    lookups.append(window_construction_by_identifier)
                if ShadeConstruction in expected_types:
                    lookups.append(shade_construction_by_identifier)
            last_exc: Exception | None = None
            for lookup in lookups:
                try:
                    construction = lookup(data)
                    break
                except Exception as exc:
                    last_exc = exc
            if construction is None:
                if garden_root is not None:
                    construction = dict_to_construction(
                        get_garden_properties_library_object(
                            garden_root=garden_root,
                            domain="honeybee_energy",
                            object_family="construction",
                            identifier=data,
                        )["object_dict"]
                    )
                elif last_exc is not None:
                    raise last_exc
                else:
                    raise ValueError(f"Unknown construction identifier: {data}")
        elif isinstance(data, dict):
            if "type" in data:
                construction = dict_to_construction(data)
            else:
                construction = _inline_construction_from_dict(
                    data,
                    field_name=field_name,
                    expected_types=expected_types,
                    garden_root=garden_root,
                )
        else:
            raise TypeError("not a construction input")
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(
            f"{field_name} must be a valid Honeybee Energy construction. {exc}"
        ) from exc
    if expected_types is not None and not isinstance(construction, expected_types):
        expected_names = ", ".join(cls.__name__ for cls in expected_types)
        raise ValueError(f"{field_name} must resolve to one of: {expected_names}.")
    return construction


def _construction_set_from_input(
    data: dict[str, Any] | str | None,
    *,
    field_name: str,
    garden_root: str | None = None,
) -> ConstructionSet | None:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="construction_set",
    )
    if data is None:
        return None
    if isinstance(data, dict) and "type" not in data and set(data) == {"identifier"} and isinstance(data.get("identifier"), str):
        data = data["identifier"]
    try:
        if isinstance(data, str):
            try:
                return construction_set_by_identifier(data)
            except Exception:
                if garden_root is not None:
                    return ConstructionSet.from_dict(
                        get_garden_properties_library_object(
                            garden_root=garden_root,
                            domain="honeybee_energy",
                            object_family="construction_set",
                            identifier=data,
                        )["object_dict"]
                    )
                raise
        if isinstance(data, dict):
            return ConstructionSet.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid ConstructionSet. {exc}") from exc
    raise ValueError(f"{field_name} must be a ConstructionSet dict or library identifier.")


def _subset_from_slots(
    data: dict[str, Any],
    cls: type,
    *,
    field_name: str,
    slot_types: dict[str, tuple[type, ...]],
    garden_root: str | None = None,
    base_subset: Any = None,
) -> Any:
    unknown = sorted(set(data) - {"type", *slot_types})
    if unknown:
        raise ValueError(
            f"{field_name} contains unsupported {cls.__name__} field(s): {', '.join(unknown)}."
        )
    resolved: dict[str, Any] = {}
    for slot, expected in slot_types.items():
        value = data.get(slot)
        if value is not None:
            resolved[slot] = _construction_from_input(
                value,
                field_name=f"{field_name}.{slot}",
                expected_types=expected,
                garden_root=garden_root,
            )
        elif base_subset is not None:
            base_val = getattr(base_subset, slot, None)
            if base_val is not None:
                resolved[slot] = base_val.duplicate() if hasattr(base_val, "duplicate") else base_val
    try:
        return cls(**resolved)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid {cls.__name__}. {exc}") from exc


def _subset_from_input(data: dict[str, Any] | None, cls: type, *, field_name: str) -> Any:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a {cls.__name__} dictionary.")
    try:
        return cls.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid {cls.__name__}. {exc}") from exc


def _opaque_subset_from_input(
    data: dict[str, Any] | str | None,
    cls: type,
    *,
    field_name: str,
    garden_root: str | None = None,
    base_subset: Any = None,
) -> Any:
    """Resolve subset input, supporting slot dicts, SDK dicts, or a single OpaqueConstruction."""
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    slot_types = {
        "exterior_construction": (OpaqueConstruction,),
        "interior_construction": (OpaqueConstruction,),
        "ground_construction": (OpaqueConstruction,),
    }
    if isinstance(data, dict) and data.get("target_type") != "garden_properties_library_object":
        if data.get("type") == cls.__name__ or any(slot in data for slot in slot_types) or data == {}:
            if data.get("type") == cls.__name__ and all(
                not isinstance(data.get(slot), dict) or "type" in data.get(slot, {})
                for slot in slot_types
                if data.get(slot) is not None
            ):
                if base_subset is None and not any(isinstance(data.get(slot), str) for slot in slot_types):
                    return _subset_from_input(data, cls, field_name=field_name)
            return _subset_from_slots(
                data,
                cls,
                field_name=field_name,
                slot_types=slot_types,
                garden_root=garden_root,
                base_subset=base_subset,
            )
    construction = _construction_from_input(
        data,
        field_name=field_name,
        expected_types=(OpaqueConstruction,),
        garden_root=garden_root,
    )
    resolved: dict[str, Any] = {"exterior_construction": construction}
    if base_subset is not None:
        for slot in ("interior_construction", "ground_construction"):
            base_val = getattr(base_subset, slot, None)
            if base_val is not None:
                resolved[slot] = base_val.duplicate() if hasattr(base_val, "duplicate") else base_val
    return cls(**resolved)


def _aperture_set_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
    base_subset: ApertureConstructionSet | None = None,
) -> ApertureConstructionSet | None:
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    slot_types = {
        "window_construction": _WINDOW_CONSTRUCTION_TYPES,
        "interior_construction": _WINDOW_CONSTRUCTION_TYPES,
        "skylight_construction": _WINDOW_CONSTRUCTION_TYPES,
        "operable_construction": _WINDOW_CONSTRUCTION_TYPES,
    }
    if isinstance(data, dict) and data.get("target_type") != "garden_properties_library_object":
        if data.get("type") == "ApertureConstructionSet" or any(slot in data for slot in slot_types) or data == {}:
            if data.get("type") == "ApertureConstructionSet" and all(
                not isinstance(data.get(slot), dict) or "type" in data.get(slot, {})
                for slot in slot_types
                if data.get(slot) is not None
            ):
                if base_subset is None and not any(isinstance(data.get(slot), str) for slot in slot_types):
                    return _subset_from_input(data, ApertureConstructionSet, field_name="aperture_set")
            return _subset_from_slots(
                data,
                ApertureConstructionSet,
                field_name="aperture_set",
                slot_types=slot_types,
                garden_root=garden_root,
                base_subset=base_subset,
            )
    try:
        window_construction = _construction_from_input(
            data,
            field_name="aperture_set",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(
            "aperture_set must be an ApertureConstructionSet or a "
            "WindowConstruction, WindowConstructionShade, or WindowConstructionDynamic "
            f"input that can be wrapped. {exc}"
        ) from exc
    resolved: dict[str, Any] = {"window_construction": window_construction}
    if base_subset is not None:
        for slot in ("interior_construction", "skylight_construction", "operable_construction"):
            base_val = getattr(base_subset, slot, None)
            if base_val is not None:
                resolved[slot] = base_val.duplicate() if hasattr(base_val, "duplicate") else base_val
    return ApertureConstructionSet(**resolved)


def _door_set_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
    base_subset: DoorConstructionSet | None = None,
) -> DoorConstructionSet | None:
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    slot_types = {
        "exterior_construction": (OpaqueConstruction,),
        "interior_construction": (OpaqueConstruction,),
        "exterior_glass_construction": _WINDOW_CONSTRUCTION_TYPES,
        "interior_glass_construction": _WINDOW_CONSTRUCTION_TYPES,
        "overhead_construction": (OpaqueConstruction,),
    }
    if isinstance(data, dict) and data.get("target_type") != "garden_properties_library_object":
        if data.get("type") == "DoorConstructionSet" or any(slot in data for slot in slot_types) or data == {}:
            if data.get("type") == "DoorConstructionSet" and all(
                not isinstance(data.get(slot), dict) or "type" in data.get(slot, {})
                for slot in slot_types
                if data.get(slot) is not None
            ):
                if base_subset is None and not any(isinstance(data.get(slot), str) for slot in slot_types):
                    return _subset_from_input(data, DoorConstructionSet, field_name="door_set")
            return _subset_from_slots(
                data,
                DoorConstructionSet,
                field_name="door_set",
                slot_types=slot_types,
                garden_root=garden_root,
                base_subset=base_subset,
            )
    exterior_construction = _construction_from_input(
        data,
        field_name="door_set",
        expected_types=(OpaqueConstruction,),
        garden_root=garden_root,
    )
    resolved: dict[str, Any] = {"exterior_construction": exterior_construction}
    if base_subset is not None:
        for slot in (
            "interior_construction",
            "exterior_glass_construction",
            "interior_glass_construction",
            "overhead_construction",
        ):
            base_val = getattr(base_subset, slot, None)
            if base_val is not None:
                resolved[slot] = base_val.duplicate() if hasattr(base_val, "duplicate") else base_val
    return DoorConstructionSet(**resolved)


def create_opaque_material(
    *,
    identifier: str,
    thickness: float,
    conductivity: float,
    density: float,
    specific_heat: float,
    roughness: str = "MediumRough",
    thermal_absorptance: float = 0.9,
    solar_absorptance: float = 0.7,
    visible_absorptance: float | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyMaterial object."""
    material = EnergyMaterial(
        identifier,
        thickness,
        conductivity,
        density,
        specific_heat,
        roughness=roughness,
        thermal_absorptance=thermal_absorptance,
        solar_absorptance=solar_absorptance,
        visible_absorptance=visible_absorptance,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyMaterial: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_opaque_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_opaque_no_mass_material(
    *,
    identifier: str,
    r_value: float,
    roughness: str = "MediumRough",
    thermal_absorptance: float = 0.9,
    solar_absorptance: float = 0.7,
    visible_absorptance: float | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyMaterialNoMass object."""
    material = EnergyMaterialNoMass(
        identifier,
        r_value,
        roughness=roughness,
        thermal_absorptance=thermal_absorptance,
        solar_absorptance=solar_absorptance,
        visible_absorptance=visible_absorptance,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyMaterialNoMass: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_opaque_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_vegetation_material(
    *,
    identifier: str,
    thickness: float = 0.1,
    conductivity: float = 0.35,
    density: float = 1100,
    specific_heat: float = 1200,
    roughness: str = "MediumRough",
    soil_thermal_absorptance: float = 0.9,
    soil_solar_absorptance: float = 0.7,
    soil_visible_absorptance: float | None = None,
    plant_height: float = 0.2,
    leaf_area_index: float = 1.0,
    leaf_reflectivity: float = 0.22,
    leaf_emissivity: float = 0.95,
    min_stomatal_resist: float = 180,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyMaterialVegetation object."""
    if thickness < 0.1:
        raise ValueError(
            "vegetation material thickness must be at least 0.1 m for "
            "OpenStudio RoofVegetation export."
        )
    material = EnergyMaterialVegetation(
        identifier,
        thickness=thickness,
        conductivity=conductivity,
        density=density,
        specific_heat=specific_heat,
        roughness=roughness,
        soil_thermal_absorptance=soil_thermal_absorptance,
        soil_solar_absorptance=soil_solar_absorptance,
        soil_visible_absorptance=soil_visible_absorptance,
        plant_height=plant_height,
        leaf_area_index=leaf_area_index,
        leaf_reflectivity=leaf_reflectivity,
        leaf_emissivity=leaf_emissivity,
        min_stomatal_resist=min_stomatal_resist,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyMaterialVegetation: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_opaque_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_window_glazing_material(
    *,
    identifier: str,
    thickness: float = 0.003,
    solar_transmittance: float = 0.85,
    solar_reflectance: float = 0.075,
    visible_transmittance: float = 0.9,
    visible_reflectance: float = 0.075,
    infrared_transmittance: float = 0,
    emissivity: float = 0.84,
    emissivity_back: float = 0.84,
    conductivity: float = 0.9,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialGlazing object."""
    material = EnergyWindowMaterialGlazing(
        identifier,
        thickness=thickness,
        solar_transmittance=solar_transmittance,
        solar_reflectance=solar_reflectance,
        visible_transmittance=visible_transmittance,
        visible_reflectance=visible_reflectance,
        infrared_transmittance=infrared_transmittance,
        emissivity=emissivity,
        emissivity_back=emissivity_back,
        conductivity=conductivity,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialGlazing: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_simple_glazing_material(
    *,
    identifier: str,
    u_factor: float,
    shgc: float,
    vt: float = 0.6,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialSimpleGlazSys object."""
    material = EnergyWindowMaterialSimpleGlazSys(identifier, u_factor, shgc, vt=vt)
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialSimpleGlazSys: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_window_gas_material(
    *,
    identifier: str,
    thickness: float = 0.0125,
    gas_type: str = "Air",
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialGas object."""
    material = EnergyWindowMaterialGas(identifier, thickness=thickness, gas_type=gas_type)
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialGas: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_custom_window_gas_material(
    *,
    identifier: str,
    thickness: float,
    conductivity_coeff_a: float,
    viscosity_coeff_a: float,
    specific_heat_coeff_a: float,
    conductivity_coeff_b: float = 0,
    viscosity_coeff_b: float = 0,
    specific_heat_coeff_b: float = 0,
    conductivity_coeff_c: float = 0,
    viscosity_coeff_c: float = 0,
    specific_heat_coeff_c: float = 0,
    specific_heat_ratio: float = 1.0,
    molecular_weight: float = 20.0,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialGasCustom object."""
    material = EnergyWindowMaterialGasCustom(
        identifier,
        thickness,
        conductivity_coeff_a,
        viscosity_coeff_a,
        specific_heat_coeff_a,
        conductivity_coeff_b=conductivity_coeff_b,
        viscosity_coeff_b=viscosity_coeff_b,
        specific_heat_coeff_b=specific_heat_coeff_b,
        conductivity_coeff_c=conductivity_coeff_c,
        viscosity_coeff_c=viscosity_coeff_c,
        specific_heat_coeff_c=specific_heat_coeff_c,
        specific_heat_ratio=specific_heat_ratio,
        molecular_weight=molecular_weight,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialGasCustom: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_window_gas_mixture_material(
    *,
    identifier: str,
    thickness: float = 0.0125,
    gas_types: list[str] | None = None,
    gas_fractions: list[float] | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialGasMixture object."""
    material = EnergyWindowMaterialGasMixture(
        identifier,
        thickness=thickness,
        gas_types=tuple(gas_types) if gas_types is not None else ("Argon", "Air"),
        gas_fractions=tuple(gas_fractions) if gas_fractions is not None else (0.9, 0.1),
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialGasMixture: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_window_frame_material(
    *,
    identifier: str,
    width: float,
    conductance: float,
    edge_to_center_ratio: float = 1,
    outside_projection: float = 0,
    inside_projection: float = 0,
    thermal_absorptance: float = 0.9,
    solar_absorptance: float = 0.7,
    visible_absorptance: float | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowFrame object."""
    material = EnergyWindowFrame(
        identifier,
        width,
        conductance,
        edge_to_center_ratio=edge_to_center_ratio,
        outside_projection=outside_projection,
        inside_projection=inside_projection,
        thermal_absorptance=thermal_absorptance,
        solar_absorptance=solar_absorptance,
        visible_absorptance=visible_absorptance,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowFrame: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.frame",
        return_object_dict=return_object_dict,
    )


def create_window_shade_material(
    *,
    identifier: str,
    thickness: float = 0.005,
    solar_transmittance: float = 0.4,
    solar_reflectance: float = 0.5,
    visible_transmittance: float = 0.4,
    visible_reflectance: float = 0.4,
    infrared_transmittance: float = 0,
    emissivity: float = 0.9,
    conductivity: float = 0.05,
    distance_to_glass: float = 0.05,
    opening_multiplier: float = 0.5,
    airflow_permeability: float = 0.0,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialShade object."""
    material = EnergyWindowMaterialShade(
        identifier,
        thickness=thickness,
        solar_transmittance=solar_transmittance,
        solar_reflectance=solar_reflectance,
        visible_transmittance=visible_transmittance,
        visible_reflectance=visible_reflectance,
        infrared_transmittance=infrared_transmittance,
        emissivity=emissivity,
        conductivity=conductivity,
        distance_to_glass=distance_to_glass,
        opening_multiplier=opening_multiplier,
        airflow_permeability=airflow_permeability,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialShade: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_window_blind_material(
    *,
    identifier: str,
    slat_orientation: str = "Horizontal",
    slat_width: float = 0.025,
    slat_separation: float = 0.01875,
    slat_thickness: float = 0.001,
    slat_angle: float = 45,
    slat_conductivity: float = 221,
    solar_transmittance: float = 0,
    solar_reflectance: float = 0.5,
    visible_transmittance: float = 0,
    visible_reflectance: float = 0.5,
    infrared_transmittance: float = 0,
    emissivity: float = 0.9,
    distance_to_glass: float = 0.05,
    opening_multiplier: float = 0.5,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy EnergyWindowMaterialBlind object."""
    material = EnergyWindowMaterialBlind(
        identifier,
        slat_orientation=slat_orientation,
        slat_width=slat_width,
        slat_separation=slat_separation,
        slat_thickness=slat_thickness,
        slat_angle=slat_angle,
        slat_conductivity=slat_conductivity,
        solar_transmittance=solar_transmittance,
        solar_reflectance=solar_reflectance,
        visible_transmittance=visible_transmittance,
        visible_reflectance=visible_reflectance,
        infrared_transmittance=infrared_transmittance,
        emissivity=emissivity,
        distance_to_glass=distance_to_glass,
        opening_multiplier=opening_multiplier,
    )
    return _save_library_result(
        _result(
            material,
            _material_summary(material, return_detail=return_detail),
            f"Created EnergyWindowMaterialBlind: {identifier}",
        ),
        garden_root=garden_root,
        object_family="material",
        ready_for="create_window_construction.materials",
        return_object_dict=return_object_dict,
    )


def create_opaque_construction(
    *,
    identifier: str,
    materials: list[dict[str, Any] | str],
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy OpaqueConstruction object."""
    material_objs = [
        _material_from_input(material, field_name="materials", garden_root=garden_root)
        for material in materials
    ]
    construction = OpaqueConstruction(identifier, material_objs)
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created OpaqueConstruction: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="edit_honeybee_face.construction or create_wall_construction_set construction fields",
        return_object_dict=return_object_dict,
    )


def create_window_construction(
    *,
    identifier: str,
    materials: list[dict[str, Any] | str] | None = None,
    u_factor: float | None = None,
    shgc: float | None = None,
    vt: float = 0.6,
    frame: dict[str, Any] | str | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy WindowConstruction object."""
    if materials is None:
        if u_factor is None or shgc is None:
            raise ValueError(
                "create_window_construction requires _materials, or both u_factor_ and shgc_."
            )
        construction = WindowConstruction.from_simple_parameters(
            identifier,
            u_factor,
            shgc,
            vt=vt,
        )
    else:
        material_objs = [
            _material_from_input(material, field_name="materials", garden_root=garden_root)
            for material in materials
        ]
        frame_obj = (
            _material_from_input(frame, field_name="frame", garden_root=garden_root)
            if frame is not None
            else None
        )
        construction = WindowConstruction(identifier, material_objs, frame=frame_obj)
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created WindowConstruction: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="edit_honeybee_aperture.construction or create_aperture_construction_set construction fields",
        return_object_dict=return_object_dict,
    )


def create_window_shade_construction(
    *,
    identifier: str,
    window_construction: dict[str, Any] | str,
    shade_material: dict[str, Any] | str,
    shade_location: str = "Interior",
    control_type: str = "AlwaysOn",
    setpoint: float | None = None,
    schedule: dict[str, Any] | str | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy WindowConstructionShade object."""
    construction = _build_window_shade_construction(
        identifier=identifier,
        window_construction=window_construction,
        shade_material=shade_material,
        shade_location=shade_location,
        control_type=control_type,
        setpoint=setpoint,
        schedule=schedule,
        garden_root=garden_root,
    )
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created WindowConstructionShade: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="edit_honeybee_aperture.construction or create_construction_set.aperture_set",
        return_object_dict=return_object_dict,
    )


def create_window_dynamic_construction(
    *,
    identifier: str,
    constructions: list[dict[str, Any] | str],
    schedule: dict[str, Any] | str,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy WindowConstructionDynamic object."""
    construction = _build_window_dynamic_construction(
        identifier=identifier,
        constructions=constructions,
        schedule=schedule,
        garden_root=garden_root,
    )
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created WindowConstructionDynamic: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="edit_honeybee_aperture.construction or create_construction_set.aperture_set",
        return_object_dict=return_object_dict,
    )


def create_shade_construction(
    *,
    identifier: str,
    solar_reflectance: float = 0.2,
    visible_reflectance: float = 0.2,
    is_specular: bool = False,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ShadeConstruction object."""
    construction = ShadeConstruction(
        identifier,
        solar_reflectance=solar_reflectance,
        visible_reflectance=visible_reflectance,
        is_specular=is_specular,
    )
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created ShadeConstruction: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="edit_honeybee_shade.construction or create_construction_set.shade_construction",
        return_object_dict=return_object_dict,
    )


def create_air_boundary_construction(
    *,
    identifier: str,
    air_mixing_per_area: float = 0.1,
    air_mixing_schedule: dict[str, Any] | str | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy AirBoundaryConstruction object."""
    construction = AirBoundaryConstruction(
        identifier,
        air_mixing_per_area=air_mixing_per_area,
        air_mixing_schedule=_schedule_from_input(
            air_mixing_schedule,
            field_name="air_mixing_schedule",
            garden_root=garden_root,
        ),
    )
    return _save_library_result(
        _result(
            construction,
            _construction_summary(construction, return_detail=return_detail),
            f"Created AirBoundaryConstruction: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction",
        ready_for="create_construction_set.air_boundary_construction",
        return_object_dict=return_object_dict,
    )


def create_wall_construction_set(
    *,
    exterior_construction: dict[str, Any] | str | None = None,
    interior_construction: dict[str, Any] | str | None = None,
    ground_construction: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy WallConstructionSet intermediate object."""
    subset = WallConstructionSet(
        _construction_from_input(
            exterior_construction,
            field_name="exterior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if exterior_construction is not None
        else None,
        _construction_from_input(
            interior_construction,
            field_name="interior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if interior_construction is not None
        else None,
        _construction_from_input(
            ground_construction,
            field_name="ground_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if ground_construction is not None
        else None,
    )
    return _result(subset, _subset_summary(subset), "Created WallConstructionSet.")


def create_floor_construction_set(
    *,
    exterior_construction: dict[str, Any] | str | None = None,
    interior_construction: dict[str, Any] | str | None = None,
    ground_construction: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy FloorConstructionSet intermediate object."""
    subset = FloorConstructionSet(
        _construction_from_input(
            exterior_construction,
            field_name="exterior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if exterior_construction is not None
        else None,
        _construction_from_input(
            interior_construction,
            field_name="interior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if interior_construction is not None
        else None,
        _construction_from_input(
            ground_construction,
            field_name="ground_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if ground_construction is not None
        else None,
    )
    return _result(subset, _subset_summary(subset), "Created FloorConstructionSet.")


def create_roof_ceiling_construction_set(
    *,
    exterior_construction: dict[str, Any] | str | None = None,
    interior_construction: dict[str, Any] | str | None = None,
    ground_construction: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy RoofCeilingConstructionSet intermediate object."""
    subset = RoofCeilingConstructionSet(
        _construction_from_input(
            exterior_construction,
            field_name="exterior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if exterior_construction is not None
        else None,
        _construction_from_input(
            interior_construction,
            field_name="interior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if interior_construction is not None
        else None,
        _construction_from_input(
            ground_construction,
            field_name="ground_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if ground_construction is not None
        else None,
    )
    return _result(
        subset,
        _subset_summary(subset),
        "Created RoofCeilingConstructionSet.",
    )


def create_aperture_construction_set(
    *,
    window_construction: dict[str, Any] | str | None = None,
    interior_construction: dict[str, Any] | str | None = None,
    skylight_construction: dict[str, Any] | str | None = None,
    operable_construction: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy ApertureConstructionSet intermediate object."""
    subset = ApertureConstructionSet(
        _construction_from_input(
            window_construction,
            field_name="window_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if window_construction is not None
        else None,
        _construction_from_input(
            interior_construction,
            field_name="interior_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if interior_construction is not None
        else None,
        _construction_from_input(
            skylight_construction,
            field_name="skylight_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if skylight_construction is not None
        else None,
        _construction_from_input(
            operable_construction,
            field_name="operable_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if operable_construction is not None
        else None,
    )
    return _result(subset, _subset_summary(subset), "Created ApertureConstructionSet.")


def create_door_construction_set(
    *,
    exterior_construction: dict[str, Any] | str | None = None,
    interior_construction: dict[str, Any] | str | None = None,
    exterior_glass_construction: dict[str, Any] | str | None = None,
    interior_glass_construction: dict[str, Any] | str | None = None,
    overhead_construction: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy DoorConstructionSet intermediate object."""
    subset = DoorConstructionSet(
        _construction_from_input(
            exterior_construction,
            field_name="exterior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if exterior_construction is not None
        else None,
        _construction_from_input(
            interior_construction,
            field_name="interior_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if interior_construction is not None
        else None,
        _construction_from_input(
            exterior_glass_construction,
            field_name="exterior_glass_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if exterior_glass_construction is not None
        else None,
        _construction_from_input(
            interior_glass_construction,
            field_name="interior_glass_construction",
            expected_types=_WINDOW_CONSTRUCTION_TYPES,
            garden_root=garden_root,
        )
        if interior_glass_construction is not None
        else None,
        _construction_from_input(
            overhead_construction,
            field_name="overhead_construction",
            expected_types=(OpaqueConstruction,),
            garden_root=garden_root,
        )
        if overhead_construction is not None
        else None,
    )
    return _result(subset, _subset_summary(subset), "Created DoorConstructionSet.")


def create_construction_set(
    *,
    identifier: str,
    base_construction_set: dict[str, Any] | str | None = None,
    wall_set: dict[str, Any] | str | None = None,
    floor_set: dict[str, Any] | str | None = None,
    roof_ceiling_set: dict[str, Any] | str | None = None,
    aperture_set: dict[str, Any] | str | None = None,
    door_set: dict[str, Any] | str | None = None,
    shade_construction: dict[str, Any] | str | None = None,
    air_boundary_construction: dict[str, Any] | str | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ConstructionSet object."""
    base = _construction_set_from_input(
        base_construction_set,
        field_name="base_construction_set",
        garden_root=garden_root,
    )
    construction_set = ConstructionSet(
        identifier,
        wall_set=_opaque_subset_from_input(
            wall_set,
            WallConstructionSet,
            field_name="wall_set",
            garden_root=garden_root,
            base_subset=base.wall_set if base else None,
        ),
        floor_set=_opaque_subset_from_input(
            floor_set,
            FloorConstructionSet,
            field_name="floor_set",
            garden_root=garden_root,
            base_subset=base.floor_set if base else None,
        ),
        roof_ceiling_set=_opaque_subset_from_input(
            roof_ceiling_set,
            RoofCeilingConstructionSet,
            field_name="roof_ceiling_set",
            garden_root=garden_root,
            base_subset=base.roof_ceiling_set if base else None,
        ),
        aperture_set=_aperture_set_from_input(
            aperture_set,
            garden_root=garden_root,
            base_subset=base.aperture_set if base else None,
        ),
        door_set=_door_set_from_input(
            door_set,
            garden_root=garden_root,
            base_subset=base.door_set if base else None,
        ),
        shade_construction=_construction_from_input(
            shade_construction,
            field_name="shade_construction",
            expected_types=(ShadeConstruction,),
            garden_root=garden_root,
        )
        if shade_construction is not None
        else (base.shade_construction.duplicate() if base else None),
        air_boundary_construction=_construction_from_input(
            air_boundary_construction,
            field_name="air_boundary_construction",
            expected_types=(AirBoundaryConstruction, OpaqueConstruction),
            garden_root=garden_root,
        )
        if air_boundary_construction is not None
        else (base.air_boundary_construction.duplicate() if base else None),
    )
    return _save_library_result(
        _result(
            construction_set,
            _construction_set_summary(construction_set, return_detail=return_detail),
            f"Created ConstructionSet: {identifier}",
        ),
        garden_root=garden_root,
        object_family="construction_set",
        ready_for="edit_honeybee_room.construction_set",
        return_object_dict=return_object_dict,
    )


_MATERIAL_CREATORS = {
    "opaque": create_opaque_material,
    "opaque_no_mass": create_opaque_no_mass_material,
    "vegetation": create_vegetation_material,
    "simple_glazing": create_simple_glazing_material,
    "window_glazing": create_window_glazing_material,
    "window_gas": create_window_gas_material,
    "window_gas_mixture": create_window_gas_mixture_material,
    "window_gas_custom": create_custom_window_gas_material,
    "window_shade": create_window_shade_material,
    "window_blind": create_window_blind_material,
    "window_frame": create_window_frame_material,
}


def create_material(
    *,
    material_type: str,
    identifier: str,
    params: dict[str, Any] | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create any Honeybee Energy material layer dispatched by material_type."""
    normalized = str(material_type or "").strip().lower().replace("-", "_")
    creator = _MATERIAL_CREATORS.get(normalized)
    if creator is None:
        allowed = ", ".join(sorted(_MATERIAL_CREATORS))
        raise ValueError(f"material_type must be one of: {allowed}.")
    validated_params = validate_material_params(normalized, params)
    return creator(
        identifier=identifier,
        return_detail=return_detail,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
        **validated_params,
    )


def create_construction(
    *,
    construction_type: str,
    identifier: str,
    materials: list[dict[str, Any] | str] | None = None,
    u_factor: float | None = None,
    shgc: float | None = None,
    vt: float = 0.6,
    frame: dict[str, Any] | str | None = None,
    params: dict[str, Any] | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create any Honeybee Energy construction dispatched by construction_type."""
    normalized = str(construction_type or "").strip().lower().replace("-", "_")
    if normalized not in {
        "opaque",
        "window",
        "window_shade",
        "window_dynamic",
        "shade",
        "air_boundary",
    }:
        raise ValueError(
            "construction_type must be one of: opaque, window, window_shade, window_dynamic, shade, air_boundary."
        )

    if normalized == "opaque":
        if u_factor is not None or shgc is not None or frame is not None:
            raise ValueError(
                "u_factor, shgc, and frame apply only to construction_type='window'."
            )
        validated = validate_construction_params(normalized, params)
        assert isinstance(validated, OpaqueConstructionParams)
        resolved_materials = materials if materials is not None else validated.materials
        if resolved_materials is None:
            raise ValueError("construction_type='opaque' requires materials.")
        return create_opaque_construction(
            identifier=identifier,
            materials=resolved_materials,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized == "window":
        validated = validate_construction_params(normalized, params)
        assert isinstance(validated, WindowConstructionParams)
        resolved_materials = materials if materials is not None else validated.materials
        resolved_u_factor = u_factor if u_factor is not None else validated.u_factor
        resolved_shgc = shgc if shgc is not None else validated.shgc
        resolved_vt = validated.vt if "vt" in validated.model_fields_set else vt
        resolved_frame = frame if frame is not None else validated.frame
        return create_window_construction(
            identifier=identifier,
            materials=resolved_materials,
            u_factor=resolved_u_factor,
            shgc=resolved_shgc,
            vt=resolved_vt,
            frame=resolved_frame,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if materials is not None or u_factor is not None or shgc is not None or frame is not None:
        if normalized == "window_shade":
            raise ValueError(
                "For construction_type='window_shade', pass window_construction and shade_material "
                "inside params rather than top-level materials, u_factor, shgc, or frame."
            )
        if normalized == "window_dynamic":
            raise ValueError(
                "For construction_type='window_dynamic', pass constructions and schedule "
                "inside params rather than top-level materials, u_factor, shgc, or frame."
            )
        raise ValueError(
            f"materials, u_factor, shgc, and frame are not supported for construction_type='{normalized}'."
        )

    validated = validate_construction_params(normalized, params)
    creators = {
        "window_shade": create_window_shade_construction,
        "window_dynamic": create_window_dynamic_construction,
        "shade": create_shade_construction,
        "air_boundary": create_air_boundary_construction,
    }
    return creators[normalized](
        identifier=identifier,
        return_detail=return_detail,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
        **validated.model_dump(),
    )
