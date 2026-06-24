"""Dragonfly Electric Grid VisualizationSet services."""

from __future__ import annotations

from typing import Any

from garden.paths import slugify_name
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts.report import make_report

from .results import read_opendss_result
from .serialization import load_grid_object


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
    result = {
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
        "report": make_report(
            status="ok",
            message="Dragonfly Grid network VisualizationSet created.",
        ),
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
    result = {
        "visualization_set_target": saved["visualization_set_target"],
        "summary_view": {
            "visualization_set_target": saved["visualization_set_target"],
            "result_count": len(result_targets),
            "result_summaries": [preview["summary_view"] for preview in previews],
            "geometry_count": 0,
            "body_returned": return_visualization_set,
        },
        "persistence_receipt": saved["persistence_receipt"],
        "report": make_report(
            status="ok",
            message="Dragonfly Grid result VisualizationSet created.",
        ),
    }
    if return_visualization_set:
        result["visualization_set"] = visualization_set
    return result
