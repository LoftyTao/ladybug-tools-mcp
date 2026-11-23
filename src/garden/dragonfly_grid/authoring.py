"""Dragonfly Electric Grid targets, persistence, catalog search, results, and authoring."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.lib.powerlines import POWER_LINES, power_line_by_identifier
from dragonfly_energy.opendss.lib.transformers import (
    TRANSFORMER_PROPERTIES,
    transformer_prop_by_identifier,
)
from dragonfly_energy.opendss.lib.wires import WIRES
from dragonfly_energy.opendss.network import ElectricalNetwork, RoadNetwork
from dragonfly_energy.opendss.road import Road
from dragonfly_energy.opendss.substation import Substation
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.reopt import FinancialParameter, GroundMountPV

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


def _object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, FinancialParameter):
        return {
            "type": "FinancialParameter",
            "analysis_years": obj.analysis_years,
            "escalation_rate": obj.escalation_rate,
            "tax_rate": obj.tax_rate,
            "discount_rate": obj.discount_rate,
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
    transformer_properties_identifier: str,
    display_name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist a Dragonfly Energy OpenDSS Transformer."""
    geometry = points2d_polygon(footprint_points, field_name="transformer footprint_points")
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
            "footprint_point_count": len(footprint_points),
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
    geometry = points2d_polyline(polyline_points, field_name="electrical connector polyline_points")
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


def read_opendss_result(
    *,
    garden_root: str,
    result_target: dict[str, Any],
    max_rows: int = 25,
) -> dict[str, Any]:
    """Read a registered OpenDSS CSV result artifact into a compact preview."""
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    path = _resolve_result_path(root, manifest, result_target)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    preview = rows[:max_rows]
    return {
        "target": result_target,
        "result_target": result_target,
        "preview_rows": preview,
        "summary_view": {
            "garden_target": manifest.target(),
            "result_target": result_target,
            "columns": reader.fieldnames or [],
            "row_count": len(rows),
            "preview_count": len(preview),
            "body_returned": True,
        },
        "report": make_report(
            status="ok",
            message=f"Read OpenDSS result artifact: {result_target.get('identifier')}",
        ),
    }


def _resolve_result_path(root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    if not isinstance(target, dict):
        raise ValueError("result_target must be a dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("result_target must have target_type 'artifact'.")
    if target.get("domain") != "dragonfly_grid":
        raise ValueError("result_target must reference domain 'dragonfly_grid'.")
    if target.get("artifact_type") != OPENDSS_RESULT_ARTIFACT_TYPE:
        raise ValueError(f"result_target artifact_type must be '{OPENDSS_RESULT_ARTIFACT_TYPE}'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("result_target belongs to a different Garden.")
    raw_path = target.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("result_target requires a Garden-relative path.")
    return resolve_existing_garden_path(root, raw_path, kind="file", label="OpenDSS result artifact")


def _empty_visualization_set(identifier: str, display_name: str) -> dict[str, Any]:
    return {
        "type": "VisualizationSet",
        "identifier": slugify_name(identifier),
        "display_name": display_name,
        "geometry": [],
    }


def grid_network_to_visualization_set(
    *,
    garden_root: str,
    network_target: dict[str, Any],
    name: str | None = None,
    return_visualization_set: bool = False,
) -> dict[str, Any]:
    """Persist a compact VisualizationSet handoff for an electrical network."""
    network = load_grid_object(
        garden_root=garden_root,
        target=network_target,
        expected_kind="electrical_network",
    )
    vis_name = name or f"{network.identifier} Grid Network"
    visualization_set = _empty_visualization_set(network.identifier, vis_name)
    saved = save_visualization_set(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=vis_name,
        output_subdir="artifacts/dragonfly_grid/visualization_sets",
        source={"network_target": network_target},
    )
    result: dict[str, Any] = {
        "visualization_set_target": saved["visualization_set_target"],
        "summary_view": {
            "visualization_set_target": saved["visualization_set_target"],
            "network_target": network_target,
            "substation_identifier": network.substation.identifier,
            "transformer_count": len(network.transformers),
            "connector_count": len(network.connectors),
            "geometry_count": 0,
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
    name: str = "OpenDSS Results",
    return_visualization_set: bool = False,
) -> dict[str, Any]:
    """Persist a compact VisualizationSet handoff for OpenDSS result previews."""
    previews = [
        read_opendss_result(garden_root=garden_root, result_target=target, max_rows=1)
        for target in result_targets
    ]
    visualization_set = _empty_visualization_set(name, name)
    saved = save_visualization_set(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=name,
        output_subdir="artifacts/dragonfly_grid/visualization_sets",
        source={"result_targets": result_targets},
    )
    result: dict[str, Any] = {
        "visualization_set_target": saved["visualization_set_target"],
        "summary_view": {
            "visualization_set_target": saved["visualization_set_target"],
            "result_count": len(result_targets),
            "result_summaries": [preview["summary_view"] for preview in previews],
            "geometry_count": 0,
            "body_returned": return_visualization_set,
        },
        "persistence_receipt": saved["persistence_receipt"],
        "report": make_report(status="ok", message="Dragonfly Grid result VisualizationSet created."),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result
