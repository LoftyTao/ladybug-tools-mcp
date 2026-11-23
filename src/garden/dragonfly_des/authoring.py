"""Dragonfly DES targets, persistence, geometry adapters, and authoring services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly_energy.des.connector import HorizontalPipeParameter, ThermalConnector
from dragonfly_energy.des.ghe import (
    BoreholeParameter,
    FluidParameter,
    GHEDesignParameter,
    GroundHeatExchanger,
    PipeParameter,
    SoilParameter,
)
from dragonfly_energy.des.loop import (
    FifthGenThermalLoop,
    FourthGenThermalLoop,
    GHEThermalLoop,
)

from garden.model_io import (
    load_typed_object,
    load_typed_objects,
    make_typed_object_target,
    normalize_typed_object_target,
    points2d_polygon,
    points2d_polyline,
    points3d_list,
    save_typed_object,
)
from ladybug_tools_mcp.contracts import make_report

DES_OBJECT_TARGET_TYPE = "dragonfly_des_object"
DES_DOMAIN = "dragonfly_des"
DES_DOMAIN_LABEL = "Dragonfly DES"

KIND_TO_CLASS = {
    "thermal_connector": ThermalConnector,
    "horizontal_pipe_parameter": HorizontalPipeParameter,
    "ghe_soil_parameter": SoilParameter,
    "ghe_fluid_parameter": FluidParameter,
    "ghe_pipe_parameter": PipeParameter,
    "ghe_borehole_parameter": BoreholeParameter,
    "ghe_design_parameter": GHEDesignParameter,
    "ground_heat_exchanger": GroundHeatExchanger,
    "fourth_gen_thermal_loop": FourthGenThermalLoop,
    "fifth_gen_thermal_loop": FifthGenThermalLoop,
    "ghe_thermal_loop": GHEThermalLoop,
}
DES_OBJECT_KINDS = set(KIND_TO_CLASS)


def make_des_object_target(
    *,
    garden_id: str,
    kind: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a Dragonfly DES object target."""
    return make_typed_object_target(
        target_type=DES_OBJECT_TARGET_TYPE,
        domain=DES_DOMAIN,
        garden_id=garden_id,
        kind=kind,
        identifier=identifier,
        path=path,
        allowed_kinds=DES_OBJECT_KINDS,
        domain_label=DES_DOMAIN_LABEL,
    )


def normalize_des_object_target(
    value: Any,
    *,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly DES object target dict."""
    return normalize_typed_object_target(
        value,
        target_type=DES_OBJECT_TARGET_TYPE,
        domain=DES_DOMAIN,
        allowed_kinds=DES_OBJECT_KINDS,
        domain_label=DES_DOMAIN_LABEL,
        expected_kind=expected_kind,
    )


def save_des_object(
    *,
    garden_root: str | Path,
    kind: str,
    identifier: str,
    obj: Any,
    include_body: bool = False,
) -> dict[str, Any]:
    """Save a Dragonfly DES object as native SDK JSON under the Garden."""
    return save_typed_object(
        garden_root=garden_root,
        domain=DES_DOMAIN,
        target_type=DES_OBJECT_TARGET_TYPE,
        domain_label=DES_DOMAIN_LABEL,
        kind=kind,
        identifier=identifier,
        obj=obj,
        kind_to_class=KIND_TO_CLASS,
        include_body=include_body,
    )


def load_des_object(
    *,
    garden_root: str | Path,
    target: dict[str, Any],
    expected_kind: str | None = None,
) -> Any:
    """Load one Dragonfly DES SDK object from a Garden target."""
    return load_typed_object(
        garden_root=garden_root,
        target=target,
        domain=DES_DOMAIN,
        target_type=DES_OBJECT_TARGET_TYPE,
        domain_label=DES_DOMAIN_LABEL,
        kind_to_class=KIND_TO_CLASS,
        expected_kind=expected_kind,
    )


def load_des_objects(
    *,
    garden_root: str | Path,
    targets: list[dict[str, Any]],
    expected_kind: str,
) -> list[Any]:
    """Load a non-empty list of Dragonfly DES objects of one kind."""
    return load_typed_objects(
        targets=targets,
        expected_kind=expected_kind,
        loader=load_des_object,
        garden_root=garden_root,
    )


def connector_geometry_from_points(points: list[list[float]]) -> Any:
    """Create a ThermalConnector LineSegment2D or Polyline2D from 2D points."""
    return points2d_polyline(points, field_name="connector polyline_points")


def ghe_geometry_from_points(points: list[list[float]]) -> Any:
    """Create a GroundHeatExchanger Polygon2D footprint from 2D points."""
    return points2d_polygon(points, field_name="ground heat exchanger footprint_points")


def ghe_borehole_positions_from_points(points: list[list[float]] | None) -> list[Any] | None:
    """Create SDK-required Point3D borehole positions from coordinate lists."""
    return points3d_list(points, field_name="ground heat exchanger borehole_positions")


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _set_display_name(obj: Any, display_name: str | None) -> None:
    if display_name is not None and hasattr(obj, "display_name"):
        obj.display_name = display_name


def _finish(
    saved: dict[str, Any],
    *,
    extra_summary: dict[str, Any] | None = None,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    saved["summary_view"].update(extra_summary or {})
    if report is not None:
        saved["report"] = report
    return saved


def _geometry_length(geometry: Any) -> float | None:
    return float(geometry.length) if hasattr(geometry, "length") else None


def create_thermal_connector(
    *,
    garden_root: str,
    identifier: str,
    polyline_points: list[list[float]],
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy ThermalConnector."""
    geometry = connector_geometry_from_points(polyline_points)
    connector = ThermalConnector(identifier, geometry)
    _set_display_name(connector, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="thermal_connector",
        identifier=identifier,
        obj=connector,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(connector, "display_name", identifier),
            "geometry_type": geometry.__class__.__name__,
            "point_count": len(polyline_points),
            "length": _geometry_length(geometry),
        },
    )


def create_horizontal_pipe_parameter(
    *,
    garden_root: str,
    identifier: str,
    buried_depth: float | None = None,
    diameter_ratio: float | None = None,
    pressure_drop_per_meter: float | None = None,
    insulation_conductivity: float | None = None,
    insulation_thickness: float | None = None,
    heat_capacity: float | None = None,
    roughness: float | None = None,
    hydraulic_diameter: float | None = None,
    pump_design_head: float | None = None,
    pump_flow_rate: float | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist HorizontalPipeParameter."""
    obj = HorizontalPipeParameter(
        **_without_none(
            {
                "buried_depth": buried_depth,
                "diameter_ratio": diameter_ratio,
                "pressure_drop_per_meter": pressure_drop_per_meter,
                "insulation_conductivity": insulation_conductivity,
                "insulation_thickness": insulation_thickness,
                "heat_capacity": heat_capacity,
                "roughness": roughness,
                "hydraulic_diameter": hydraulic_diameter,
                "pump_design_head": pump_design_head,
                "pump_flow_rate": pump_flow_rate,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="horizontal_pipe_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ghe_soil_parameter(
    *,
    garden_root: str,
    identifier: str,
    conductivity: float | None = None,
    heat_capacity: float | None = None,
    undisturbed_temperature: float | None = None,
    grout_conductivity: float | None = None,
    grout_heat_capacity: float | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist SoilParameter."""
    obj = SoilParameter(
        **_without_none(
            {
                "conductivity": conductivity,
                "heat_capacity": heat_capacity,
                "undisturbed_temperature": undisturbed_temperature,
                "grout_conductivity": grout_conductivity,
                "grout_heat_capacity": grout_heat_capacity,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_soil_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ghe_fluid_parameter(
    *,
    garden_root: str,
    identifier: str,
    fluid_type: str | None = None,
    concentration: float | None = None,
    temperature: float | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist FluidParameter."""
    obj = FluidParameter(
        **_without_none(
            {
                "fluid_type": fluid_type,
                "concentration": concentration,
                "temperature": temperature,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_fluid_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ghe_pipe_parameter(
    *,
    garden_root: str,
    identifier: str,
    inner_diameter: float | None = None,
    outer_diameter: float | None = None,
    shank_spacing: float | None = None,
    roughness: float | None = None,
    conductivity: float | None = None,
    heat_capacity: float | None = None,
    arrangement: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist PipeParameter."""
    obj = PipeParameter(
        **_without_none(
            {
                "inner_diameter": inner_diameter,
                "outer_diameter": outer_diameter,
                "shank_spacing": shank_spacing,
                "roughness": roughness,
                "conductivity": conductivity,
                "heat_capacity": heat_capacity,
                "arrangement": arrangement,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_pipe_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ghe_borehole_parameter(
    *,
    garden_root: str,
    identifier: str,
    min_depth: float | None = None,
    max_depth: float | None = None,
    min_spacing: float | None = None,
    max_spacing: float | None = None,
    buried_depth: float | None = None,
    diameter: float | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist BoreholeParameter."""
    obj = BoreholeParameter(
        **_without_none(
            {
                "min_depth": min_depth,
                "max_depth": max_depth,
                "min_spacing": min_spacing,
                "max_spacing": max_spacing,
                "buried_depth": buried_depth,
                "diameter": diameter,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_borehole_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ghe_design_parameter(
    *,
    garden_root: str,
    identifier: str,
    flow_rate: float | None = None,
    flow_type: str | None = None,
    max_eft: float | None = None,
    min_eft: float | None = None,
    month_count: int | None = None,
    method: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist GHEDesignParameter."""
    obj = GHEDesignParameter(
        **_without_none(
            {
                "flow_rate": flow_rate,
                "flow_type": flow_type,
                "max_eft": max_eft,
                "min_eft": min_eft,
                "month_count": month_count,
                "method": method,
            }
        )
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_design_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary=_without_none(obj.to_dict()))


def create_ground_heat_exchanger(
    *,
    garden_root: str,
    identifier: str,
    footprint_points: list[list[float]],
    borehole_positions: list[list[float]] | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a GroundHeatExchanger."""
    geometry = ghe_geometry_from_points(footprint_points)
    boreholes = ghe_borehole_positions_from_points(borehole_positions)
    obj = GroundHeatExchanger(identifier, geometry, borehole_positions=boreholes)
    _set_display_name(obj, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="ground_heat_exchanger",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "geometry_type": geometry.__class__.__name__,
            "footprint_point_count": len(footprint_points),
            "borehole_position_count": len(boreholes or []),
        },
    )


def create_fourth_gen_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    economizer_type: str = "None",
    heating_type: str = "NaturalGas",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a FourthGenThermalLoop without plant target binding."""
    obj = FourthGenThermalLoop(
        identifier,
        economizer_type=economizer_type,
        heating_type=heating_type,
    )
    _set_display_name(obj, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="fourth_gen_thermal_loop",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    warnings = ["Cooling/heating plant targets are not yet implemented for DES authoring Slice 1."]
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "economizer_type": economizer_type,
            "heating_type": heating_type,
            "plant_targets_supported": False,
        },
        report=make_report(
            status="ok",
            message=f"Saved fourth-generation thermal loop: {identifier}",
            warnings=warnings,
        ),
    )


def create_fifth_gen_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    connector_targets: list[dict[str, Any]],
    clockwise_flow: bool = False,
    soil_parameter_target: dict[str, Any] | None = None,
    horizontal_pipe_parameter_target: dict[str, Any] | None = None,
    heat_rejection_type: str = "CoolingTower",
    supplemental_heat_type: str = "Electricity",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a FifthGenThermalLoop."""
    connectors = load_des_objects(
        garden_root=garden_root,
        targets=connector_targets,
        expected_kind="thermal_connector",
    )
    soil = (
        load_des_object(
            garden_root=garden_root,
            target=soil_parameter_target,
            expected_kind="ghe_soil_parameter",
        )
        if soil_parameter_target
        else None
    )
    hpipe = (
        load_des_object(
            garden_root=garden_root,
            target=horizontal_pipe_parameter_target,
            expected_kind="horizontal_pipe_parameter",
        )
        if horizontal_pipe_parameter_target
        else None
    )
    obj = FifthGenThermalLoop(
        identifier,
        connectors,
        clockwise_flow=clockwise_flow,
        soil_parameters=soil,
        horizontal_pipe_parameters=hpipe,
        heat_rejection_type=heat_rejection_type,
        supplemental_heat_type=supplemental_heat_type,
    )
    _set_display_name(obj, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="fifth_gen_thermal_loop",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "connector_count": len(connectors),
            "clockwise_flow": clockwise_flow,
            "has_soil_parameters": soil is not None,
            "has_horizontal_pipe_parameters": hpipe is not None,
            "heat_rejection_type": heat_rejection_type,
            "supplemental_heat_type": supplemental_heat_type,
        },
    )


def create_ghe_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    ground_heat_exchanger_targets: list[dict[str, Any]],
    connector_targets: list[dict[str, Any]],
    clockwise_flow: bool = False,
    soil_parameter_target: dict[str, Any] | None = None,
    fluid_parameter_target: dict[str, Any] | None = None,
    pipe_parameter_target: dict[str, Any] | None = None,
    borehole_parameter_target: dict[str, Any] | None = None,
    design_parameter_target: dict[str, Any] | None = None,
    horizontal_pipe_parameter_target: dict[str, Any] | None = None,
    heat_rejection_type: str = "CoolingTower",
    supplemental_heat_type: str = "Electricity",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a GHEThermalLoop."""
    ghes = load_des_objects(
        garden_root=garden_root,
        targets=ground_heat_exchanger_targets,
        expected_kind="ground_heat_exchanger",
    )
    connectors = load_des_objects(
        garden_root=garden_root,
        targets=connector_targets,
        expected_kind="thermal_connector",
    )
    optional_targets = {
        "soil_parameters": ("ghe_soil_parameter", soil_parameter_target),
        "fluid_parameters": ("ghe_fluid_parameter", fluid_parameter_target),
        "pipe_parameters": ("ghe_pipe_parameter", pipe_parameter_target),
        "borehole_parameters": ("ghe_borehole_parameter", borehole_parameter_target),
        "design_parameters": ("ghe_design_parameter", design_parameter_target),
        "horizontal_pipe_parameters": (
            "horizontal_pipe_parameter",
            horizontal_pipe_parameter_target,
        ),
    }
    loaded = {
        field: (
            load_des_object(
                garden_root=garden_root,
                target=target,
                expected_kind=kind,
            )
            if target
            else None
        )
        for field, (kind, target) in optional_targets.items()
    }
    obj = GHEThermalLoop(
        identifier,
        ghes,
        connectors,
        clockwise_flow=clockwise_flow,
        heat_rejection_type=heat_rejection_type,
        supplemental_heat_type=supplemental_heat_type,
        **loaded,
    )
    _set_display_name(obj, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="ghe_thermal_loop",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "ground_heat_exchanger_count": len(ghes),
            "connector_count": len(connectors),
            "clockwise_flow": clockwise_flow,
            "has_soil_parameters": loaded["soil_parameters"] is not None,
            "has_fluid_parameters": loaded["fluid_parameters"] is not None,
            "has_pipe_parameters": loaded["pipe_parameters"] is not None,
            "has_borehole_parameters": loaded["borehole_parameters"] is not None,
            "has_design_parameters": loaded["design_parameters"] is not None,
            "has_horizontal_pipe_parameters": loaded["horizontal_pipe_parameters"] is not None,
            "heat_rejection_type": heat_rejection_type,
            "supplemental_heat_type": supplemental_heat_type,
        },
    )
