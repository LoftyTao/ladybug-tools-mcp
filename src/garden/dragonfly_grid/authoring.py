"""Dragonfly Electric Grid targets, persistence, catalog search, results, and authoring."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from dragonfly_energy.opendss.colorobj import ColorNetwork, ColorNetworkResults
from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.lib.powerlines import POWER_LINES, power_line_by_identifier
from dragonfly_energy.opendss.lib.transformers import (
    TRANSFORMER_PROPERTIES,
    transformer_prop_by_identifier,
)
from dragonfly_energy.opendss.lib.wires import WIRES, wire_by_identifier
from dragonfly_energy.opendss.network import ElectricalNetwork, RoadNetwork
from dragonfly_energy.opendss.powerline import PowerLine
from dragonfly_energy.opendss.result import OpenDSSResult
from dragonfly_energy.opendss.road import Road
from dragonfly_energy.opendss.substation import Substation
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.opendss.transformerprop import TransformerProperties
from dragonfly_energy.opendss.wire import ConcentricProperties, Wire
from dragonfly_energy.reopt import (
    FinancialParameter,
    GeneratorParameter,
    GroundMountPV,
    PVParameter,
    REoptParameter,
    StorageParameter,
    WindParameter,
)
from ladybug.datatype.base import DataTypeBase
from ladybug.datatype.generic import GenericType
from ladybug.location import Location
from ladybug_display.geometry3d import (
    DisplayFace3D,
    DisplayLineSegment3D,
    DisplayPolyline3D,
)
from ladybug_display.visualization import (
    AnalysisGeometry,
    ContextGeometry,
    VisualizationData,
    VisualizationSet,
)
from ladybug_geometry.geometry2d import LineSegment2D, Point2D, Polygon2D, Polyline2D
from ladybug_geometry.geometry3d import Face3D, LineSegment3D, Point3D, Polyline3D

from garden.manifest import GardenManifest
from garden.model_io import (
    load_typed_object,
    load_typed_objects,
    make_typed_object_target,
    normalize_typed_object_target,
    points2d_polygon,
    points2d_polyline,
    save_typed_object,
)
from garden.paths import require_garden_root, resolve_existing_garden_path, slugify_name
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts import make_report

GRID_OBJECT_TARGET_TYPE = "dragonfly_grid_object"
GRID_DOMAIN = "dragonfly_grid"
GRID_DOMAIN_LABEL = "Dragonfly Grid"
OPENDSS_RESULT_ARTIFACT_TYPE = "dragonfly_grid_opendss_result_csv"

KIND_TO_CLASS = {
    "substation": Substation,
    "transformer": Transformer,
    "electrical_connector": ElectricalConnector,
    "electrical_network": ElectricalNetwork,
    "road_network": RoadNetwork,
    "ground_photovoltaics": GroundMountPV,
    "financial_parameters": FinancialParameter,
    "wire": Wire,
    "power_line": PowerLine,
    "transformer_properties": TransformerProperties,
    "reopt_parameter": REoptParameter,
}
GRID_OBJECT_KINDS = set(KIND_TO_CLASS)

CATALOGS = {
    "transformer_properties": TRANSFORMER_PROPERTIES,
    "power_lines": POWER_LINES,
    "wires": WIRES,
}


def make_grid_object_target(
    *,
    garden_id: str,
    kind: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a Dragonfly Electric Grid object target."""
    return make_typed_object_target(
        target_type=GRID_OBJECT_TARGET_TYPE,
        domain=GRID_DOMAIN,
        garden_id=garden_id,
        kind=kind,
        identifier=identifier,
        path=path,
        allowed_kinds=GRID_OBJECT_KINDS,
        domain_label=GRID_DOMAIN_LABEL,
    )


def normalize_grid_object_target(
    value: Any,
    *,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly Electric Grid object target dict."""
    return normalize_typed_object_target(
        value,
        target_type=GRID_OBJECT_TARGET_TYPE,
        domain=GRID_DOMAIN,
        allowed_kinds=GRID_OBJECT_KINDS,
        domain_label=GRID_DOMAIN_LABEL,
        expected_kind=expected_kind,
    )


def _source_param_to_dict(obj: Any) -> dict[str, Any]:
    data = {
        "max_kw": obj.max_kw,
        "dollars_per_kw": obj.dollars_per_kw,
    }
    if isinstance(obj, PVParameter):
        data["max_kw_ground"] = obj.max_kw_ground
        data["dollars_per_kw_ground"] = obj.dollars_per_kw_ground
    return data


def _object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, FinancialParameter):
        return {
            "type": "FinancialParameter",
            "analysis_years": obj.analysis_years,
            "escalation_rate": obj.escalation_rate,
            "tax_rate": obj.tax_rate,
            "discount_rate": obj.discount_rate,
        }
    if isinstance(obj, REoptParameter):
        return {
            "type": "REoptParameter",
            "financial_parameter": _object_to_dict(obj.financial_parameter),
            "wind_parameter": _source_param_to_dict(obj.wind_parameter),
            "pv_parameter": _source_param_to_dict(obj.pv_parameter),
            "storage_parameter": _source_param_to_dict(obj.storage_parameter),
            "generator_parameter": _source_param_to_dict(obj.generator_parameter),
        }
    if not hasattr(obj, "to_dict"):
        raise ValueError("Dragonfly Grid object must expose to_dict().")
    return obj.to_dict()


def _object_from_dict(kind: str, record: dict[str, Any]) -> Any:
    cls = KIND_TO_CLASS[kind]
    if cls is FinancialParameter:
        return FinancialParameter(
            analysis_years=record.get("analysis_years", 25),
            escalation_rate=record.get("escalation_rate", 0.023),
            tax_rate=record.get("tax_rate", 0.26),
            discount_rate=record.get("discount_rate", 0.083),
        )
    if cls is REoptParameter:
        fp_raw = record.get("financial_parameter")
        fp = (
            _object_from_dict("financial_parameters", fp_raw)
            if isinstance(fp_raw, dict)
            else None
        )
        pv_raw = record.get("pv_parameter")
        st_raw = record.get("storage_parameter")
        wn_raw = record.get("wind_parameter")
        gn_raw = record.get("generator_parameter")
        return REoptParameter(
            financial_parameter=fp,
            wind_parameter=WindParameter(**wn_raw) if isinstance(wn_raw, dict) else None,
            pv_parameter=PVParameter(**pv_raw) if isinstance(pv_raw, dict) else None,
            storage_parameter=StorageParameter(**st_raw) if isinstance(st_raw, dict) else None,
            generator_parameter=GeneratorParameter(**gn_raw) if isinstance(gn_raw, dict) else None,
        )
    return cls.from_dict(record)


def save_grid_object(
    *,
    garden_root: str | Path,
    kind: str,
    identifier: str,
    obj: Any,
    include_body: bool = False,
) -> dict[str, Any]:
    """Save a Dragonfly Electric Grid object under the Garden."""
    return save_typed_object(
        garden_root=garden_root,
        domain=GRID_DOMAIN,
        target_type=GRID_OBJECT_TARGET_TYPE,
        domain_label=GRID_DOMAIN_LABEL,
        kind=kind,
        identifier=identifier,
        obj=obj,
        kind_to_class=KIND_TO_CLASS,
        serializer=_object_to_dict,
        include_body=include_body,
    )


def load_grid_object(
    *,
    garden_root: str | Path,
    target: dict[str, Any],
    expected_kind: str | None = None,
) -> Any:
    """Load one Dragonfly Electric Grid SDK object from a Garden target."""
    return load_typed_object(
        garden_root=garden_root,
        target=target,
        domain=GRID_DOMAIN,
        target_type=GRID_OBJECT_TARGET_TYPE,
        domain_label=GRID_DOMAIN_LABEL,
        kind_to_class=KIND_TO_CLASS,
        deserializer=_object_from_dict,
        expected_kind=expected_kind,
    )


def load_grid_objects(
    *,
    garden_root: str | Path,
    targets: list[dict[str, Any]],
    expected_kind: str,
) -> list[Any]:
    """Load a non-empty list of Dragonfly Grid objects of one kind."""
    return load_typed_objects(
        targets=targets,
        expected_kind=expected_kind,
        loader=load_grid_object,
        garden_root=garden_root,
    )


def _set_display_name(obj: Any, display_name: str | None) -> None:
    if display_name is not None and hasattr(obj, "display_name"):
        obj.display_name = display_name


def _finish(saved: dict[str, Any], *, extra_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    saved["summary_view"].update(extra_summary or {})
    return saved


def create_substation(
    *,
    garden_root: str,
    identifier: str,
    footprint_points: list[list[float]],
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS Substation."""
    geometry = points2d_polygon(footprint_points, field_name="substation footprint_points")
    obj = Substation(identifier, geometry)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="substation",
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
        },
    )


def create_transformer(
    *,
    garden_root: str,
    identifier: str,
    footprint_points: list[list[float]],
    transformer_properties_identifier: str | None = None,
    transformer_properties_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS Transformer."""
    geometry = points2d_polygon(footprint_points, field_name="transformer footprint_points")
    if transformer_properties_target is not None:
        properties = load_grid_object(
            garden_root=garden_root,
            target=transformer_properties_target,
            expected_kind="transformer_properties",
        )
        resolved_prop_id = str(getattr(properties, "identifier", None) or "custom")
    elif transformer_properties_identifier:
        properties = transformer_prop_by_identifier(transformer_properties_identifier)
        resolved_prop_id = transformer_properties_identifier
    else:
        raise ValueError(
            "Provide transformer_properties_identifier or transformer_properties_target."
        )
    obj = Transformer(identifier, geometry, properties)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="transformer",
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
            "properties_identifier": resolved_prop_id,
            "nominal_voltage": getattr(obj, "nominal_voltage", None),
            "phase_count": getattr(obj, "phase_count", None),
        },
    )


def create_electrical_connector(
    *,
    garden_root: str,
    identifier: str,
    polyline_points: list[list[float]],
    power_line_identifier: str | None = None,
    power_line_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS ElectricalConnector."""
    geometry = points2d_polyline(polyline_points, field_name="electrical connector polyline_points")
    if power_line_target is not None:
        power_line = load_grid_object(
            garden_root=garden_root,
            target=power_line_target,
            expected_kind="power_line",
        )
        resolved_line_id = str(getattr(power_line, "identifier", None) or "custom")
    elif power_line_identifier:
        power_line = power_line_by_identifier(power_line_identifier)
        resolved_line_id = power_line_identifier
    else:
        raise ValueError("Provide power_line_identifier or power_line_target.")
    obj = ElectricalConnector(identifier, geometry, power_line)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="electrical_connector",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "geometry_type": geometry.__class__.__name__,
            "point_count": len(polyline_points),
            "power_line_identifier": resolved_line_id,
            "nominal_voltage": getattr(obj, "nominal_voltage", None),
            "phase_count": getattr(obj, "phase_count", None),
        },
    )


def _location_from_dict(value: dict[str, Any] | None) -> Location | None:
    if value is None:
        return None
    return Location(
        city=value.get("city"),
        state=value.get("state"),
        country=value.get("country"),
        latitude=float(value.get("latitude", 0)),
        longitude=float(value.get("longitude", 0)),
        time_zone=value.get("time_zone"),
        elevation=float(value.get("elevation", 0)),
    )


def create_electrical_network(
    *,
    garden_root: str,
    identifier: str,
    substation_target: dict[str, Any] | None = None,
    transformer_targets: list[dict[str, Any]] | None = None,
    connector_targets: list[dict[str, Any]] | None = None,
    geojson_file_path: str | None = None,
    location: dict[str, Any] | None = None,
    point: list[float] | None = None,
    units: str = "Meters",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an ElectricalNetwork from components or an RNM GeoJSON file."""
    if geojson_file_path is not None:
        root = require_garden_root(garden_root)
        geo_path = resolve_existing_garden_path(
            root,
            geojson_file_path,
            kind="file",
            label="RNM GeoJSON file",
        )
        loc = _location_from_dict(location)
        pt = Point2D(float(point[0]), float(point[1])) if point and len(point) >= 2 else None
        obj = ElectricalNetwork.from_rnm_geojson(
            str(geo_path),
            location=loc,
            point=pt,
            units=units,
        )
        obj.identifier = identifier
    else:
        if substation_target is None or transformer_targets is None or connector_targets is None:
            raise ValueError(
                "create_electrical_network requires substation_target, transformer_targets, "
                "and connector_targets, or geojson_file_path."
            )
        substation = load_grid_object(
            garden_root=garden_root,
            target=substation_target,
            expected_kind="substation",
        )
        transformers = load_grid_objects(
            garden_root=garden_root,
            targets=transformer_targets,
            expected_kind="transformer",
        )
        connectors = load_grid_objects(
            garden_root=garden_root,
            targets=connector_targets,
            expected_kind="electrical_connector",
        )
        obj = ElectricalNetwork(identifier, substation, transformers, connectors)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="electrical_network",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "substation_identifier": obj.substation.identifier,
            "transformer_count": len(obj.transformers),
            "connector_count": len(obj.connectors),
            "source": "rnm_geojson" if geojson_file_path is not None else "targets",
        },
    )


def create_road_network(
    *,
    garden_root: str,
    identifier: str,
    substation_target: dict[str, Any],
    road_segments: list[dict[str, Any]],
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy RNM RoadNetwork."""
    substation = load_grid_object(
        garden_root=garden_root,
        target=substation_target,
        expected_kind="substation",
    )
    roads = [
        Road(
            str(segment["identifier"]),
            points2d_polyline(
                segment["polyline_points"],
                field_name=f"road_segments[{index}].polyline_points",
            ),
        )
        for index, segment in enumerate(road_segments)
    ]
    obj = RoadNetwork(identifier, substation, roads)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="road_network",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "display_name": getattr(obj, "display_name", identifier),
            "substation_target": substation_target,
            "road_count": len(roads),
        },
    )


def create_ground_photovoltaics(
    *,
    garden_root: str,
    identifier: str,
    footprint_points: list[list[float]],
    building_identifier: str | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy REopt GroundMountPV object."""
    geometry = points2d_polygon(footprint_points, field_name="ground photovoltaics footprint_points")
    obj = GroundMountPV(identifier, geometry, building_identifier=building_identifier)
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="ground_photovoltaics",
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
            "building_identifier": building_identifier,
        },
    )


def create_financial_parameters(
    *,
    garden_root: str,
    identifier: str,
    analysis_years: int = 25,
    escalation_rate: float = 0.023,
    tax_rate: float = 0.26,
    discount_rate: float = 0.083,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist Dragonfly Energy REopt FinancialParameter settings."""
    obj = FinancialParameter(
        analysis_years=analysis_years,
        escalation_rate=escalation_rate,
        tax_rate=tax_rate,
        discount_rate=discount_rate,
    )
    saved = save_grid_object(
        garden_root=garden_root,
        kind="financial_parameters",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "analysis_years": obj.analysis_years,
            "escalation_rate": obj.escalation_rate,
            "tax_rate": obj.tax_rate,
            "discount_rate": obj.discount_rate,
        },
    )


def create_wire(
    *,
    garden_root: str,
    identifier: str,
    ampacity: float = 220,
    geometrical_mean_radius: float = 3.9,
    resistance: float = 0.3937,
    diameter: float = 10,
    voltage_level: str = "MV",
    wire_type: str = "OH",
    concentric_properties: dict[str, Any] | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an OpenDSS Wire specification."""
    conc = (
        ConcentricProperties(**concentric_properties)
        if isinstance(concentric_properties, dict)
        else None
    )
    obj = Wire(
        identifier,
        ampacity=ampacity,
        geometrical_mean_radius=geometrical_mean_radius,
        resistance=resistance,
        diameter=diameter,
        voltage_level=voltage_level,
        wire_type=wire_type,
        concentric_properties=conc,
    )
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="wire",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "ampacity": obj.ampacity,
            "voltage_level": obj.voltage_level,
            "wire_type": obj.wire_type,
        },
    )


def _resolve_wire_object(garden_root: str, item: Any) -> Wire:
    if isinstance(item, dict) and item.get("target_type") == GRID_OBJECT_TARGET_TYPE:
        return load_grid_object(garden_root=garden_root, target=item, expected_kind="wire")
    if isinstance(item, dict):
        return Wire.from_dict(item)
    if isinstance(item, str):
        return wire_by_identifier(item)
    raise ValueError("wires entries must be wire targets, Wire dicts, or OpenDSS Wire identifiers.")


def create_power_line(
    *,
    garden_root: str,
    identifier: str,
    wires: list[Any],
    heights: list[float],
    relative_xs: list[float],
    phases: list[str],
    phase_count: int | None = None,
    nominal_voltage: float | None = None,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an OpenDSS PowerLine geometry/wire assembly."""
    wire_objs = [_resolve_wire_object(garden_root, w) for w in wires]
    obj = PowerLine(
        identifier,
        wire_objs,
        [float(h) for h in heights],
        [float(x) for x in relative_xs],
        list(phases),
        phase_count=phase_count,
        nominal_voltage=nominal_voltage,
    )
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="power_line",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "wire_count": len(wire_objs),
            "phases": list(phases),
            "nominal_voltage": getattr(obj, "nominal_voltage", None),
        },
    )


def create_transformer_properties(
    *,
    garden_root: str,
    identifier: str,
    kva: float,
    resistance: float = 0.1,
    reactance: float = 0.1,
    phase_count: int = 3,
    high_voltage: float = 13.2,
    low_voltage: float = 0.48,
    is_center_tap: bool = False,
    connection: str = "Wye-Wye",
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an OpenDSS TransformerProperties specification."""
    obj = TransformerProperties(
        identifier,
        kva,
        resistance=resistance,
        reactance=reactance,
        phase_count=phase_count,
        high_voltage=high_voltage,
        low_voltage=low_voltage,
        is_center_tap=is_center_tap,
        connection=connection,
    )
    _set_display_name(obj, display_name)
    saved = save_grid_object(
        garden_root=garden_root,
        kind="transformer_properties",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "kva": obj.kva,
            "high_voltage": obj.high_voltage,
            "low_voltage": obj.low_voltage,
            "connection": obj.connection,
        },
    )


def create_reopt_parameter(
    *,
    garden_root: str,
    identifier: str,
    financial_parameters_target: dict[str, Any] | None = None,
    financial_parameter: dict[str, Any] | None = None,
    pv_parameter: dict[str, Any] | None = None,
    storage_parameter: dict[str, Any] | None = None,
    wind_parameter: dict[str, Any] | None = None,
    generator_parameter: dict[str, Any] | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a complete REoptParameter configuration."""
    if financial_parameters_target is not None:
        fp = load_grid_object(
            garden_root=garden_root,
            target=financial_parameters_target,
            expected_kind="financial_parameters",
        )
    elif isinstance(financial_parameter, dict):
        fp = FinancialParameter(**financial_parameter)
    else:
        fp = FinancialParameter()

    pv = PVParameter(**pv_parameter) if isinstance(pv_parameter, dict) else PVParameter()
    storage = (
        StorageParameter(**storage_parameter)
        if isinstance(storage_parameter, dict)
        else StorageParameter()
    )
    wind = WindParameter(**wind_parameter) if isinstance(wind_parameter, dict) else WindParameter()
    generator = (
        GeneratorParameter(**generator_parameter)
        if isinstance(generator_parameter, dict)
        else GeneratorParameter()
    )
    obj = REoptParameter(
        financial_parameter=fp,
        wind_parameter=wind,
        pv_parameter=pv,
        storage_parameter=storage,
        generator_parameter=generator,
    )
    saved = save_grid_object(
        garden_root=garden_root,
        kind="reopt_parameter",
        identifier=identifier,
        obj=obj,
        include_body=include_body,
    )
    return _finish(
        saved,
        extra_summary={
            "analysis_years": obj.financial_parameter.analysis_years,
            "pv_max_kw": obj.pv_parameter.max_kw,
            "storage_max_kw": obj.storage_parameter.max_kw,
            "wind_max_kw": obj.wind_parameter.max_kw,
            "generator_max_kw": obj.generator_parameter.max_kw,
        },
    )


def search_opendss(
    *,
    keywords: list[str] | None = None,
    catalogs: list[str] | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search compact OpenDSS catalog identifiers."""
    if limit <= 0:
        raise ValueError("limit must be a positive integer.")
    selected = catalogs or list(CATALOGS)
    unknown = [catalog for catalog in selected if catalog not in CATALOGS]
    if unknown:
        allowed = ", ".join(sorted(CATALOGS))
        raise ValueError(f"Unknown OpenDSS catalog(s): {unknown}. Allowed: {allowed}.")
    terms = [term.strip().lower() for term in (keywords or []) if term.strip()]
    matches: list[dict[str, Any]] = []
    for catalog in selected:
        for identifier in CATALOGS[catalog]:
            text = identifier.lower()
            if terms and not all(term in text for term in terms):
                continue
            matches.append({"catalog": catalog, "identifier": identifier})
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    return {
        "matches": matches,
        "summary_view": {
            "keywords": keywords or [],
            "catalogs": selected,
            "returned_count": len(matches),
            "total_count": sum(len(CATALOGS[catalog]) for catalog in selected),
            "limit": limit,
            "body_returned": False,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} OpenDSS catalog records.",
        ),
    }


def _resolve_result_path(
    root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    if not isinstance(target, dict):
        raise ValueError("OpenDSS result target must be a dictionary.")
    target_garden = target.get("garden_id")
    if target_garden and target_garden != manifest.garden_id:
        raise ValueError("OpenDSS result target belongs to a different Garden.")
    path_value = target.get("path") or target.get("path_relative")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("OpenDSS result target requires a path.")
    return resolve_existing_garden_path(
        root, path_value, kind="file", label="OpenDSS result file"
    )


def _opendss_metrics_for_paths(paths: list[Path]) -> dict[str, Any]:
    res = OpenDSSResult([str(p) for p in paths])
    elements: list[dict[str, Any]] = []
    overloaded_elements = 0
    voltage_violation_elements = 0
    for f_col, c_col in zip(res.factor_data, res.condition_data, strict=False):
        meta = dict(f_col.header.metadata or {})
        cond_vals = list(c_col.values)
        is_voltage = "voltage" in str(meta.get("type", "")).lower()
        violation_hours = sum(1 for v in cond_vals if v != 0)
        if is_voltage and violation_hours > 0:
            voltage_violation_elements += 1
        elif not is_voltage and violation_hours > 0:
            overloaded_elements += 1
        elements.append(
            {
                "name": meta.get("name"),
                "type": meta.get("type"),
                "peak_factor": round(float(f_col.max), 6),
                "average_factor": round(float(f_col.average), 6),
                "min_factor": round(float(f_col.min), 6),
                "violation_hours": violation_hours,
                "overvoltage_hours": sum(1 for v in cond_vals if v > 0) if is_voltage else 0,
                "undervoltage_hours": sum(1 for v in cond_vals if v < 0) if is_voltage else 0,
            }
        )
    peak_max = round(max(res.peak_factors), 6) if res.peak_factors else None
    avg_mean = (
        round(sum(res.average_factors) / len(res.average_factors), 6)
        if res.average_factors
        else None
    )
    return {
        "elements": elements,
        "peak_factor_max": peak_max,
        "average_factor_mean": avg_mean,
        "overloaded_elements": overloaded_elements,
        "voltage_violation_elements": voltage_violation_elements,
        "result": res,
    }


def read_opendss_result(
    *,
    garden_root: str,
    result_target: dict[str, Any] | None = None,
    result_targets: list[dict[str, Any]] | None = None,
    max_rows: int = 25,
) -> dict[str, Any]:
    """Read registered OpenDSS CSV result artifact(s) with OpenDSSResult loading & voltage summaries."""
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")
    targets = list(result_targets or ([] if result_target is None else [result_target]))
    if not targets:
        raise ValueError("Provide result_target or result_targets.")
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    paths = [_resolve_result_path(root, manifest, t) for t in targets]
    first_path = paths[0]
    with first_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    preview = rows[:max_rows]
    opendss_summary: dict[str, Any] = {}
    try:
        parsed = _opendss_metrics_for_paths(paths)
        opendss_summary = {
            "elements": parsed["elements"],
            "peak_factor_max": parsed["peak_factor_max"],
            "average_factor_mean": parsed["average_factor_mean"],
            "overloaded_elements": parsed["overloaded_elements"],
            "voltage_violation_elements": parsed["voltage_violation_elements"],
        }
    except Exception:
        opendss_summary = {}

    return {
        "target": targets[0],
        "result_target": targets[0],
        "preview_rows": preview,
        "summary_view": {
            "garden_target": manifest.target(),
            "result_target": targets[0],
            "columns": reader.fieldnames or [],
            "row_count": len(rows),
            "preview_count": len(preview),
            "body_returned": True,
            **opendss_summary,
        },
        "report": make_report(
            status="ok",
            message=f"Read OpenDSS result artifact(s): {len(targets)} file(s)",
        ),
    }


def read_reopt_result(
    *,
    garden_root: str,
    report_json_path: str | None = None,
    report_csv_path: str | None = None,
    run_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read REopt scenario_optimization.json / .csv outputs into a compact techno-economic summary."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    json_path: Path | None = None
    csv_path: Path | None = None
    if run_target is not None:
        from garden.dragonfly_grid.runs import get_grid_run

        run_info = get_grid_run(garden_root=garden_root, run_target=run_target)
        for out in run_info.get("summary_view", {}).get("outputs") or []:
            p = out.get("path") if isinstance(out, dict) else None
            if isinstance(p, str):
                candidate = resolve_existing_garden_path(root, p, kind="file", label="REopt output")
                if candidate.suffix.lower() == ".json":
                    json_path = candidate
                elif candidate.suffix.lower() == ".csv":
                    csv_path = candidate
    if report_json_path is not None:
        json_path = resolve_existing_garden_path(
            root, report_json_path, kind="file", suffix=".json", label="REopt JSON output"
        )
    if report_csv_path is not None:
        csv_path = resolve_existing_garden_path(
            root, report_csv_path, kind="file", suffix=".csv", label="REopt CSV output"
        )
    if json_path is None and csv_path is None:
        raise ValueError(
            "Provide report_json_path, report_csv_path, or a completed REopt run_target."
        )

    reopt_json: dict[str, Any] | None = (
        json.loads(json_path.read_text(encoding="utf-8")) if json_path is not None else None
    )
    csv_rows: list[dict[str, Any]] = []
    if csv_path is not None:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))

    metrics: dict[str, Any] = {}
    if isinstance(reopt_json, dict):
        outputs_block = reopt_json.get("outputs") or {}
        if isinstance(outputs_block, dict) and isinstance(outputs_block.get("Scenario"), dict):
            site = outputs_block["Scenario"].get("Site") or {}
        elif isinstance(reopt_json.get("Scenario"), dict):
            site = reopt_json["Scenario"].get("Site") or {}
        else:
            site = outputs_block if isinstance(outputs_block, dict) else {}

        financial = site.get("Financial") or {}
        pv_block = site.get("PV")
        pv_items = pv_block if isinstance(pv_block, list) else ([pv_block] if isinstance(pv_block, dict) else [])
        pv_kw = sum(float(p.get("size_kw") or 0.0) for p in pv_items if isinstance(p, dict))
        storage = site.get("ElectricStorage") or site.get("Storage") or {}
        wind = site.get("Wind") or {}
        gen = site.get("Generator") or {}
        tariff = site.get("ElectricTariff") or {}
        metrics = {
            "lcc_us_dollars": financial.get("lcc_us_dollars"),
            "npv_us_dollars": financial.get("npv_us_dollars"),
            "net_capital_costs_plus_om": financial.get("net_capital_costs_plus_om_us_dollars"),
            "simple_payback_years": financial.get("simple_payback_years"),
            "pv_size_kw": round(pv_kw, 4),
            "storage_size_kw": storage.get("size_kw"),
            "storage_size_kwh": storage.get("size_kwh"),
            "wind_size_kw": wind.get("size_kw"),
            "generator_size_kw": gen.get("size_kw"),
            "year_one_energy_supplied_kwh": (site.get("ElectricLoad") or {}).get("year_one_electric_load_series_kw"),
            "year_one_bill_savings_us_dollars": tariff.get("total_energy_cost_us_dollars"),
        }

    return {
        "metrics": metrics,
        "csv_rows": csv_rows,
        "summary_view": {
            "garden_target": manifest.target(),
            "metrics": metrics,
            "csv_row_count": len(csv_rows),
        },
        "report": make_report(status="ok", message="Read REopt optimization results."),
    }


def _to_geometry_3d(geo: Any) -> Any:
    if isinstance(geo, Polygon2D):
        return Face3D([Point3D(pt.x, pt.y, 0.0) for pt in geo.vertices])
    if isinstance(geo, LineSegment2D):
        return LineSegment3D.from_end_points(
            Point3D(geo.p1.x, geo.p1.y, 0.0),
            Point3D(geo.p2.x, geo.p2.y, 0.0),
        )
    if isinstance(geo, Polyline2D):
        return Polyline3D([Point3D(pt.x, pt.y, 0.0) for pt in geo.vertices])
    return geo


def _to_display_3d(geo: Any) -> Any:
    if isinstance(geo, Polygon2D):
        return DisplayFace3D(Face3D([Point3D(pt.x, pt.y, 0.0) for pt in geo.vertices]))
    if isinstance(geo, LineSegment2D):
        return DisplayLineSegment3D(
            LineSegment3D.from_end_points(
                Point3D(geo.p1.x, geo.p1.y, 0.0),
                Point3D(geo.p2.x, geo.p2.y, 0.0),
            )
        )
    if isinstance(geo, Polyline2D):
        return DisplayPolyline3D(Polyline3D([Point3D(pt.x, pt.y, 0.0) for pt in geo.vertices]))
    return geo


def _vis_data_type(value: Any, unit: str = "") -> DataTypeBase | None:
    if isinstance(value, DataTypeBase):
        return value
    if value is None:
        return None
    return GenericType(str(value), str(unit or ""))


def grid_network_to_visualization_set(
    *,
    garden_root: str,
    network_target: dict[str, Any],
    attr_name: str = "identifier",
    name: str | None = None,
    return_visualization_set: bool = False,
) -> dict[str, Any]:
    """Build a real ColorNetwork VisualizationSet handoff for an ElectricalNetwork."""
    network = load_grid_object(
        garden_root=garden_root,
        target=network_target,
        expected_kind="electrical_network",
    )
    vis_name = name or f"{network.identifier} Grid Network"
    color_net = ColorNetwork(network, attr_name)
    gc = color_net.graphic_container
    raw_geoms = [_to_geometry_3d(geo) for geo in color_net.geometries]
    vis_data = VisualizationData(
        list(gc.values),
        legend_parameters=gc.legend_parameters,
        data_type=_vis_data_type(
            getattr(gc, "data_type", None) or color_net.attr_name_end.replace("_", " ").title()
        ),
    )
    analysis_geo = AnalysisGeometry(slugify_name(network.identifier), raw_geoms, [vis_data])
    vis_set = VisualizationSet(slugify_name(network.identifier), [analysis_geo])
    vis_set.display_name = vis_name
    visualization_set = vis_set.to_dict()

    saved = save_visualization_set(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=vis_name,
        output_subdir="artifacts/dragonfly_grid/visualization_sets",
        source={"network_target": network_target, "attr_name": attr_name},
    )
    result: dict[str, Any] = {
        "visualization_set_target": saved["visualization_set_target"],
        "summary_view": {
            "visualization_set_target": saved["visualization_set_target"],
            "network_target": network_target,
            "attr_name": attr_name,
            "substation_identifier": network.substation.identifier,
            "transformer_count": len(network.transformers),
            "connector_count": len(network.connectors),
            "geometry_count": len(visualization_set.get("geometry", [])),
            "body_returned": return_visualization_set,
        },
        "persistence_receipt": saved["persistence_receipt"],
        "report": make_report(status="ok", message="Dragonfly Grid network VisualizationSet created."),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result


def grid_results_to_visualization_set(
    *,
    garden_root: str,
    result_targets: list[dict[str, Any]],
    network_target: dict[str, Any] | None = None,
    attribute: str | int = "max",
    name: str = "OpenDSS Results",
    return_visualization_set: bool = False,
) -> dict[str, Any]:
    """Build a real ColorNetworkResults + OpenDSSResult VisualizationSet."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    paths = [_resolve_result_path(root, manifest, t) for t in result_targets]
    parsed = _opendss_metrics_for_paths(paths)
    opendss_result = parsed["result"]

    geometries: list[Any] = []
    if network_target is not None:
        network = load_grid_object(
            garden_root=garden_root,
            target=network_target,
            expected_kind="electrical_network",
        )
        color_res = ColorNetworkResults(
            list(opendss_result.factor_data),
            network,
            attribute=attribute,
        )
        if color_res.matched_geometries:
            gc = color_res.graphic_container
            raw_geoms = [_to_geometry_3d(geo) for geo in color_res.matched_geometries]
            unit_str = str(color_res.unit or "")
            vis_data = VisualizationData(
                list(color_res.matched_values),
                legend_parameters=gc.legend_parameters,
                data_type=_vis_data_type(getattr(gc, "data_type", None) or color_res.data_type, unit_str),
                unit=unit_str or None,
            )
            geometries.append(
                AnalysisGeometry(slugify_name(name), raw_geoms, [vis_data])
            )
        else:
            color_net = ColorNetwork(network, "identifier")
            geometries.append(
                ContextGeometry(
                    slugify_name(network.identifier),
                    [_to_display_3d(geo) for geo in color_net.geometries],
                )
            )

    if not geometries and parsed["elements"]:
        raw_segs = []
        values = []
        for idx, elem in enumerate(parsed["elements"]):
            val = float(
                elem["average_factor"]
                if str(attribute).lower() == "average"
                else elem["peak_factor"]
            )
            raw_segs.append(
                LineSegment3D.from_end_points(
                    Point3D(float(idx) * 2.0, 0.0, 0.0),
                    Point3D(float(idx) * 2.0, max(val, 0.01) * 10.0, 0.0),
                )
            )
            values.append(val)
        geometries.append(
            AnalysisGeometry(
                slugify_name(name),
                raw_segs,
                [VisualizationData(values, data_type=GenericType("OpenDSS Loading Factor", "fraction"), unit="fraction")],
            )
        )

    vis_set = VisualizationSet(slugify_name(name), geometries)
    vis_set.display_name = name
    visualization_set = vis_set.to_dict()
    saved = save_visualization_set(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=name,
        output_subdir="artifacts/dragonfly_grid/visualization_sets",
        source={"result_targets": result_targets, "network_target": network_target},
    )
    result: dict[str, Any] = {
        "visualization_set_target": saved["visualization_set_target"],
        "summary_view": {
            "visualization_set_target": saved["visualization_set_target"],
            "result_count": len(result_targets),
            "elements": parsed["elements"],
            "peak_factor_max": parsed["peak_factor_max"],
            "average_factor_mean": parsed["average_factor_mean"],
            "overloaded_elements": parsed["overloaded_elements"],
            "voltage_violation_elements": parsed["voltage_violation_elements"],
            "geometry_count": len(visualization_set.get("geometry", [])),
            "body_returned": return_visualization_set,
        },
        "persistence_receipt": saved["persistence_receipt"],
        "report": make_report(status="ok", message="Dragonfly Grid result VisualizationSet created."),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result
