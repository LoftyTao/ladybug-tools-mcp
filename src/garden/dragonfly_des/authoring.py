"""Dragonfly DES targets, persistence, geometry adapters, and authoring services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly_energy.des.connector import HorizontalPipeParameter, ThermalConnector
from dragonfly_energy.des.ets import HeatExchangerETS, HeatPumpETS
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
from dragonfly_energy.des.plant import CoolingPlant, HeatingPlant
from ladybug.location import Location
from ladybug_geometry.geometry2d.pointvector import Point2D

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
from garden.paths import require_garden_root, resolve_existing_garden_path
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
    "heating_plant": HeatingPlant,
    "cooling_plant": CoolingPlant,
    "heat_exchanger_ets": HeatExchangerETS,
    "heat_pump_ets": HeatPumpETS,
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


def create_heating_plant(
    *,
    garden_root: str,
    identifier: str,
    hw_setpoint: float = 55,
    heating_limit: float = 5000,
    hw_mass_flow: float = 1.0,
    hw_valve_pressure_drop: float = 6000,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a HeatingPlant."""
    obj = HeatingPlant(
        hw_setpoint=hw_setpoint,
        heating_limit=heating_limit,
        hw_mass_flow=hw_mass_flow,
        hw_valve_pressure_drop=hw_valve_pressure_drop,
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="heating_plant",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary={"hw_setpoint": obj.hw_setpoint, "heating_limit": obj.heating_limit})


def create_cooling_plant(
    *,
    garden_root: str,
    identifier: str,
    chw_setpoint: float = 6,
    cooling_limit: float = 8000,
    chw_mass_flow: float = 10,
    min_chw_mass_flow: float = 10,
    cw_mass_flow: float = 10,
    chw_pump_head: float = 250000,
    cw_pump_head: float = 175000,
    chw_pressure_drop: float = 55000,
    cw_pressure_drop: float = 80000,
    pressure_drop_setpoint: float = 50000,
    chw_valve_pressure_drop: float = 6000,
    cw_valve_pressure_drop: float = 6000,
    cooling_tower_fan_power: float = 5000,
    cooling_tower_delta_temperature: float = 7,
    approach_delta_temperature: float = 3,
    cw_inlet_temperature: float = 35,
    outdoor_wb_temperature: float = 25,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a CoolingPlant."""
    obj = CoolingPlant(
        chw_setpoint=chw_setpoint,
        cooling_limit=cooling_limit,
        chw_mass_flow=chw_mass_flow,
        min_chw_mass_flow=min_chw_mass_flow,
        cw_mass_flow=cw_mass_flow,
        chw_pump_head=chw_pump_head,
        cw_pump_head=cw_pump_head,
        chw_pressure_drop=chw_pressure_drop,
        cw_pressure_drop=cw_pressure_drop,
        pressure_drop_setpoint=pressure_drop_setpoint,
        chw_valve_pressure_drop=chw_valve_pressure_drop,
        cw_valve_pressure_drop=cw_valve_pressure_drop,
        cooling_tower_fan_power=cooling_tower_fan_power,
        cooling_tower_delta_temperature=cooling_tower_delta_temperature,
        approach_delta_temperature=approach_delta_temperature,
        cw_inlet_temperature=cw_inlet_temperature,
        outdoor_wb_temperature=outdoor_wb_temperature,
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="cooling_plant",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(saved, extra_summary={"chw_setpoint": obj.chw_setpoint, "cooling_limit": obj.cooling_limit})


def create_heat_exchanger_ets(
    *,
    garden_root: str,
    identifier: str,
    cooling_supply_temp: float = 7,
    heating_supply_temp: float = 50,
    exchanger_efficiency: float = 0.8,
    primary_pressure_drop: float = 500,
    secondary_pressure_drop: float = 500,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a HeatExchangerETS."""
    obj = HeatExchangerETS(
        cooling_supply_temp=cooling_supply_temp,
        heating_supply_temp=heating_supply_temp,
        exchanger_efficiency=exchanger_efficiency,
        primary_pressure_drop=primary_pressure_drop,
        secondary_pressure_drop=secondary_pressure_drop,
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="heat_exchanger_ets",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "cooling_supply_temp": obj.cooling_supply_temp,
            "heating_supply_temp": obj.heating_supply_temp,
            "exchanger_efficiency": obj.exchanger_efficiency,
        },
    )


def create_heat_pump_ets(
    *,
    garden_root: str,
    identifier: str,
    cooling_supply_temp: float = 5,
    heating_supply_temp: float = 50,
    shw_supply_temp: float = 50,
    cop_cooling: float = 3.5,
    cop_heating: float = 2.5,
    cop_shw: float = 2.5,
    pump_head: float = 10000,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a HeatPumpETS."""
    obj = HeatPumpETS(
        cooling_supply_temp=cooling_supply_temp,
        heating_supply_temp=heating_supply_temp,
        shw_supply_temp=shw_supply_temp,
        cop_cooling=cop_cooling,
        cop_heating=cop_heating,
        cop_shw=cop_shw,
        pump_head=pump_head,
    )
    saved = save_des_object(
        garden_root=garden_root,
        kind="heat_pump_ets",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "cop_cooling": obj.cop_cooling,
            "cop_heating": obj.cop_heating,
            "cop_shw": obj.cop_shw,
        },
    )


def _location_and_point(location: dict[str, Any] | None, point: list[float] | None) -> tuple[Location | None, Point2D]:
    loc = None
    if location is not None:
        loc = Location(
            city=location.get("city"),
            state=location.get("state"),
            country=location.get("country"),
            latitude=float(location.get("latitude", 0)),
            longitude=float(location.get("longitude", 0)),
            time_zone=location.get("time_zone"),
            elevation=float(location.get("elevation", 0)),
        )
    pt = Point2D(float(point[0]), float(point[1])) if point and len(point) >= 2 else Point2D(0, 0)
    return loc, pt


def create_fourth_gen_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    cooling_plant_target: dict[str, Any] | None = None,
    cooling_plant: dict[str, Any] | None = None,
    heating_plant_target: dict[str, Any] | None = None,
    heating_plant: dict[str, Any] | None = None,
    economizer_type: str = "None",
    heating_type: str = "NaturalGas",
    heat_recovery_chiller: bool = False,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a FourthGenThermalLoop with optional CoolingPlant and HeatingPlant."""
    c_plant = _coerce_des_parameter(
        garden_root,
        _pick_des_parameter_input(
            target_value=cooling_plant_target,
            inline_value=cooling_plant,
            target_name="cooling_plant_target",
            inline_name="cooling_plant",
        ),
        expected_kind="cooling_plant",
    )
    h_plant = _coerce_des_parameter(
        garden_root,
        _pick_des_parameter_input(
            target_value=heating_plant_target,
            inline_value=heating_plant,
            target_name="heating_plant_target",
            inline_name="heating_plant",
        ),
        expected_kind="heating_plant",
    )
    obj = FourthGenThermalLoop(
        identifier,
        cooling_plant=c_plant,
        heating_plant=h_plant,
        economizer_type=economizer_type,
        heating_type=heating_type,
        heat_recovery_chiller=heat_recovery_chiller,
    )
    _set_display_name(obj, display_name)
    saved = save_des_object(
        garden_root=garden_root,
        kind="fourth_gen_thermal_loop",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "economizer_type": economizer_type,
            "heating_type": heating_type,
            "heat_recovery_chiller": heat_recovery_chiller,
            "plant_targets_supported": True,
            "has_cooling_plant": c_plant is not None,
            "has_heating_plant": h_plant is not None,
        },
        report=make_report(
            status="ok",
            message=f"Saved fourth-generation thermal loop: {identifier}",
        ),
    )


def _coerce_des_parameter(
    garden_root: str,
    value: Any,
    *,
    expected_kind: str,
) -> Any:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{expected_kind} must be a target dict or inline parameter dict.")
    if value.get("target_type") == DES_OBJECT_TARGET_TYPE:
        return load_des_object(
            garden_root=garden_root,
            target=value,
            expected_kind=expected_kind,
        )
    cls = KIND_TO_CLASS[expected_kind]
    if "type" in value:
        if value.get("type") != cls.__name__:
            raise ValueError(
                f"Inline {expected_kind} dict type must be {cls.__name__!r}; "
                f"got {value.get('type')!r}."
            )
        return cls.from_dict(value)
    return cls(**_without_none(value))


def _pick_des_parameter_input(
    *,
    target_value: dict[str, Any] | None,
    inline_value: dict[str, Any] | None,
    target_name: str,
    inline_name: str,
) -> dict[str, Any] | None:
    if target_value is not None and inline_value is not None:
        raise ValueError(f"Provide either {target_name} or {inline_name}, not both.")
    return target_value if target_value is not None else inline_value


def create_fifth_gen_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    connector_targets: list[dict[str, Any]] | None = None,
    geojson_file_path: str | None = None,
    location: dict[str, Any] | None = None,
    point: list[float] | None = None,
    units: str = "Meters",
    clockwise_flow: bool = False,
    soil_parameter_target: dict[str, Any] | None = None,
    soil_parameter: dict[str, Any] | None = None,
    horizontal_pipe_parameter_target: dict[str, Any] | None = None,
    horizontal_pipe_parameter: dict[str, Any] | None = None,
    heat_rejection_type: str = "CoolingTower",
    supplemental_heat_type: str = "Electricity",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a FifthGenThermalLoop from connectors or a GeoJSON file."""
    soil = _coerce_des_parameter(
        garden_root,
        _pick_des_parameter_input(
            target_value=soil_parameter_target,
            inline_value=soil_parameter,
            target_name="soil_parameter_target",
            inline_name="soil_parameter",
        ),
        expected_kind="ghe_soil_parameter",
    )
    hpipe = _coerce_des_parameter(
        garden_root,
        _pick_des_parameter_input(
            target_value=horizontal_pipe_parameter_target,
            inline_value=horizontal_pipe_parameter,
            target_name="horizontal_pipe_parameter_target",
            inline_name="horizontal_pipe_parameter",
        ),
        expected_kind="horizontal_pipe_parameter",
    )
    if geojson_file_path is not None:
        garden_root_path = require_garden_root(garden_root)
        geo_path = resolve_existing_garden_path(
            garden_root_path,
            geojson_file_path,
            kind="file",
            label="5G GeoJSON file",
        )
        loc, pt = _location_and_point(location, point)
        obj = FifthGenThermalLoop.from_geojson(
            str(geo_path),
            location=loc,
            point=pt,
            units=units,
            clockwise_flow=clockwise_flow,
        )
        obj.identifier = identifier
        if soil is not None:
            obj.soil_parameters = soil
        if hpipe is not None:
            obj.horizontal_pipe_parameters = hpipe
        obj.heat_rejection_type = heat_rejection_type
        obj.supplemental_heat_type = supplemental_heat_type
        connectors = list(obj.connectors)
    else:
        if not connector_targets:
            raise ValueError(
                "create_fifth_gen_thermal_loop requires connector_targets or geojson_file_path."
            )
        connectors = load_des_objects(
            garden_root=garden_root,
            targets=connector_targets,
            expected_kind="thermal_connector",
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
            "has_soil_parameters": obj.soil_parameters is not None,
            "has_horizontal_pipe_parameters": obj.horizontal_pipe_parameters is not None,
            "heat_rejection_type": heat_rejection_type,
            "supplemental_heat_type": supplemental_heat_type,
            "source": "geojson" if geojson_file_path is not None else "connectors",
        },
    )


def create_ghe_thermal_loop(
    *,
    garden_root: str,
    identifier: str,
    ground_heat_exchanger_targets: list[dict[str, Any]] | None = None,
    connector_targets: list[dict[str, Any]] | None = None,
    geojson_file_path: str | None = None,
    location: dict[str, Any] | None = None,
    point: list[float] | None = None,
    units: str = "Meters",
    clockwise_flow: bool = False,
    soil_parameter_target: dict[str, Any] | None = None,
    soil_parameter: dict[str, Any] | None = None,
    fluid_parameter_target: dict[str, Any] | None = None,
    fluid_parameter: dict[str, Any] | None = None,
    pipe_parameter_target: dict[str, Any] | None = None,
    pipe_parameter: dict[str, Any] | None = None,
    borehole_parameter_target: dict[str, Any] | None = None,
    borehole_parameter: dict[str, Any] | None = None,
    design_parameter_target: dict[str, Any] | None = None,
    design_parameter: dict[str, Any] | None = None,
    horizontal_pipe_parameter_target: dict[str, Any] | None = None,
    horizontal_pipe_parameter: dict[str, Any] | None = None,
    heat_rejection_type: str = "CoolingTower",
    supplemental_heat_type: str = "Electricity",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a GHEThermalLoop from targets or a GeoJSON file."""
    optional_targets = {
        "soil_parameters": (
            "ghe_soil_parameter",
            _pick_des_parameter_input(
                target_value=soil_parameter_target,
                inline_value=soil_parameter,
                target_name="soil_parameter_target",
                inline_name="soil_parameter",
            ),
        ),
        "fluid_parameters": (
            "ghe_fluid_parameter",
            _pick_des_parameter_input(
                target_value=fluid_parameter_target,
                inline_value=fluid_parameter,
                target_name="fluid_parameter_target",
                inline_name="fluid_parameter",
            ),
        ),
        "pipe_parameters": (
            "ghe_pipe_parameter",
            _pick_des_parameter_input(
                target_value=pipe_parameter_target,
                inline_value=pipe_parameter,
                target_name="pipe_parameter_target",
                inline_name="pipe_parameter",
            ),
        ),
        "borehole_parameters": (
            "ghe_borehole_parameter",
            _pick_des_parameter_input(
                target_value=borehole_parameter_target,
                inline_value=borehole_parameter,
                target_name="borehole_parameter_target",
                inline_name="borehole_parameter",
            ),
        ),
        "design_parameters": (
            "ghe_design_parameter",
            _pick_des_parameter_input(
                target_value=design_parameter_target,
                inline_value=design_parameter,
                target_name="design_parameter_target",
                inline_name="design_parameter",
            ),
        ),
        "horizontal_pipe_parameters": (
            "horizontal_pipe_parameter",
            _pick_des_parameter_input(
                target_value=horizontal_pipe_parameter_target,
                inline_value=horizontal_pipe_parameter,
                target_name="horizontal_pipe_parameter_target",
                inline_name="horizontal_pipe_parameter",
            ),
        ),
    }
    loaded = {
        field: _coerce_des_parameter(garden_root, target, expected_kind=kind)
        for field, (kind, target) in optional_targets.items()
    }
    if geojson_file_path is not None:
        garden_root_path = require_garden_root(garden_root)
        geo_path = resolve_existing_garden_path(
            garden_root_path,
            geojson_file_path,
            kind="file",
            label="GHE GeoJSON file",
        )
        loc, pt = _location_and_point(location, point)
        obj = GHEThermalLoop.from_geojson(
            str(geo_path),
            location=loc,
            point=pt,
            units=units,
            clockwise_flow=clockwise_flow,
        )
        obj.identifier = identifier
        for field, param_obj in loaded.items():
            if param_obj is not None:
                setattr(obj, field, param_obj)
        obj.heat_rejection_type = heat_rejection_type
        obj.supplemental_heat_type = supplemental_heat_type
        ghes = list(obj.ground_heat_exchangers)
        connectors = list(obj.connectors)
    else:
        if not ground_heat_exchanger_targets or not connector_targets:
            raise ValueError(
                "create_ghe_thermal_loop requires ground_heat_exchanger_targets and "
                "connector_targets, or geojson_file_path."
            )
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
            "source": "geojson" if geojson_file_path is not None else "targets",
        },
    )


_CREATE_BY_KIND = {
    "thermal_connector": create_thermal_connector,
    "horizontal_pipe_parameter": create_horizontal_pipe_parameter,
    "ghe_soil_parameter": create_ghe_soil_parameter,
    "ghe_fluid_parameter": create_ghe_fluid_parameter,
    "ghe_pipe_parameter": create_ghe_pipe_parameter,
    "ghe_borehole_parameter": create_ghe_borehole_parameter,
    "ghe_design_parameter": create_ghe_design_parameter,
    "ground_heat_exchanger": create_ground_heat_exchanger,
    "heating_plant": create_heating_plant,
    "cooling_plant": create_cooling_plant,
    "heat_exchanger_ets": create_heat_exchanger_ets,
    "heat_pump_ets": create_heat_pump_ets,
    "fourth_gen_thermal_loop": create_fourth_gen_thermal_loop,
    "fifth_gen_thermal_loop": create_fifth_gen_thermal_loop,
    "ghe_thermal_loop": create_ghe_thermal_loop,
}


def create_des_object(
    *,
    garden_root: str,
    kind: str,
    identifier: str,
    params: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create and persist any Dragonfly DES authoring object by kind."""
    normalized_kind = kind.strip().lower().replace("-", "_")
    creator = _CREATE_BY_KIND.get(normalized_kind)
    if creator is None:
        allowed = ", ".join(sorted(_CREATE_BY_KIND))
        raise ValueError(f"Unsupported DES object kind: {kind}. Allowed: {allowed}.")
    merged: dict[str, Any] = {}
    if params is not None:
        if not isinstance(params, dict):
            raise ValueError("params must be a dictionary.")
        merged.update(params)
    for key, val in kwargs.items():
        if val is not None and key not in merged:
            merged[key] = val
    return creator(garden_root=garden_root, identifier=identifier, **merged)
