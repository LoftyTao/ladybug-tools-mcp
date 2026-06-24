"""Dragonfly Electric Grid authoring services."""

from __future__ import annotations

from typing import Any

from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.lib.powerlines import power_line_by_identifier
from dragonfly_energy.opendss.lib.transformers import transformer_prop_by_identifier
from dragonfly_energy.opendss.network import ElectricalNetwork, RoadNetwork
from dragonfly_energy.opendss.road import Road
from dragonfly_energy.opendss.substation import Substation
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.reopt import FinancialParameter, GroundMountPV

from .geometry import polygon_from_points, polyline_from_points
from .serialization import load_grid_object, load_grid_objects, save_grid_object


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
    geometry = polygon_from_points(footprint_points, field_name="substation footprint_points")
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
    transformer_properties_identifier: str,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS Transformer."""
    geometry = polygon_from_points(transformer_points := footprint_points, field_name="transformer footprint_points")
    properties = transformer_prop_by_identifier(transformer_properties_identifier)
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
            "footprint_point_count": len(transformer_points),
            "properties_identifier": transformer_properties_identifier,
            "nominal_voltage": getattr(obj, "nominal_voltage", None),
            "phase_count": getattr(obj, "phase_count", None),
        },
    )


def create_electrical_connector(
    *,
    garden_root: str,
    identifier: str,
    polyline_points: list[list[float]],
    power_line_identifier: str,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS ElectricalConnector."""
    geometry = polyline_from_points(polyline_points, field_name="electrical connector polyline_points")
    power_line = power_line_by_identifier(power_line_identifier)
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
            "power_line_identifier": power_line_identifier,
            "nominal_voltage": getattr(obj, "nominal_voltage", None),
            "phase_count": getattr(obj, "phase_count", None),
        },
    )


def create_electrical_network(
    *,
    garden_root: str,
    identifier: str,
    substation_target: dict[str, Any],
    transformer_targets: list[dict[str, Any]],
    connector_targets: list[dict[str, Any]],
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS ElectricalNetwork."""
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
            "substation_target": substation_target,
            "transformer_count": len(transformers),
            "connector_count": len(connectors),
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
            polyline_from_points(
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
    geometry = polygon_from_points(footprint_points, field_name="ground photovoltaics footprint_points")
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

