"""VisualizationSet artifact services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ladybug_vtk._extend_visualization_set  # noqa: F401
from ladybug_display.visualization import VisualizationSet

from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative

HTML_ARTIFACT_TYPE = "visualization_html"
SVG_ARTIFACT_TYPE = "visualization_svg"
VTKJS_ARTIFACT_TYPE = "visualization_vtkjs"
VISUALIZATION_SET_TARGET_TYPE = "visualization_set"
VISUALIZATION_SET_ARTIFACT_TYPE = "visualization_set_json"
SVG_VIEWS = {"Top", "Left", "Right", "Front", "Back", "NE", "NW", "SE", "SW"}


def _resolve_output_dir(garden_root: Path, output_subdir: str) -> Path:
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact_type
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(record)
    return record


def _visualization_set_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    return {
        "target_type": VISUALIZATION_SET_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": "visualize",
        "identifier": identifier,
        "path": path,
    }


def save_visualization_set(
    *,
    garden_root: str,
    visualization_set: dict[str, Any],
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization_sets",
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a VisualizationSet dict and return a compact Garden target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    VisualizationSet.from_dict(visualization_set)
    vis_set_path = (output_dir / f"{safe_name}.json").resolve()
    vis_set_path.relative_to(garden_root_path)
    with vis_set_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(visualization_set, handle)
        handle.write("\n")

    artifact_path = to_posix_relative(vis_set_path, garden_root_path)
    artifact_source = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        **(source or {}),
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=VISUALIZATION_SET_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=artifact_source,
    )
    manifest.write(garden_root_path)
    target = _visualization_set_target(
        manifest=manifest,
        identifier=safe_name,
        path=artifact_path,
    )
    return {
        "target": target,
        "visualization_set_target": target,
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=VISUALIZATION_SET_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(vis_set_path),
            source=artifact_source,
        ),
    }


def load_visualization_set(
    *,
    garden_root: str,
    visualization_set_target: dict[str, Any],
) -> dict[str, Any]:
    """Load a Garden-backed VisualizationSet target."""
    if not isinstance(visualization_set_target, dict):
        raise ValueError("visualization_set_target must be a dictionary.")
    target_type = visualization_set_target.get("target_type")
    if target_type != VISUALIZATION_SET_TARGET_TYPE:
        raise ValueError(
            "visualization_set_target target_type must be "
            f"{VISUALIZATION_SET_TARGET_TYPE!r}; got {target_type!r}."
        )
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    garden_id = visualization_set_target.get("garden_id")
    if garden_id and garden_id != manifest.garden_id:
        raise ValueError("visualization_set_target garden_id does not match the Garden root.")
    target_path = visualization_set_target.get("path")
    if not isinstance(target_path, str) or not target_path:
        raise ValueError("visualization_set_target requires a Garden-relative path.")
    vis_set_path = (garden_root_path / target_path).resolve()
    vis_set_path.relative_to(garden_root_path)
    if not vis_set_path.is_file():
        raise ValueError(f"VisualizationSet target file was not found: {target_path}")
    with vis_set_path.open("r", encoding="utf-8") as handle:
        visualization_set = json.load(handle)
    VisualizationSet.from_dict(visualization_set)
    return visualization_set


def _resolve_visualization_set_input(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None,
    visualization_set_target: dict[str, Any] | None,
) -> dict[str, Any]:
    has_dict = visualization_set is not None
    has_target = visualization_set_target is not None
    if has_dict == has_target:
        raise ValueError(
            "Provide exactly one of visualization_set or visualization_set_target."
        )
    if has_dict:
        if not isinstance(visualization_set, dict):
            raise ValueError("visualization_set must be a dictionary.")
        return visualization_set
    return load_visualization_set(
        garden_root=garden_root,
        visualization_set_target=visualization_set_target or {},
    )


def visualization_set_to_html(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/html",
    open: bool = False,
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden HTML artifact."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set = _resolve_visualization_set_input(
        garden_root=garden_root,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    vis_set = VisualizationSet.from_dict(visualization_set)
    html_path = Path(
        vis_set.to_html(
            output_folder=str(output_dir),
            file_name=safe_name,
            open=open,
        )
    ).resolve()
    html_path.relative_to(garden_root_path)
    artifact_path = to_posix_relative(html_path, garden_root_path)
    source = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=HTML_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)

    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=HTML_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(html_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": html_path.is_file(),
        },
        "report": make_report(
            status="ok",
            message="VisualizationSet HTML artifact exported.",
            details={"artifact_path": artifact_path},
        ),
    }


def visualization_set_to_vtkjs(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/vtkjs",
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden vtkjs artifact."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set = _resolve_visualization_set_input(
        garden_root=garden_root,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    vis_set = VisualizationSet.from_dict(visualization_set)
    vtkjs_path = Path(
        vis_set.to_vtkjs(
            output_folder=str(output_dir),
            file_name=safe_name,
        )
    ).resolve()
    vtkjs_path.relative_to(garden_root_path)
    artifact_path = to_posix_relative(vtkjs_path, garden_root_path)
    source = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=VTKJS_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)

    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=VTKJS_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(vtkjs_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": vtkjs_path.is_file(),
        },
        "report": make_report(
            status="ok",
            message="VisualizationSet vtkjs artifact exported.",
            details={"artifact_path": artifact_path},
        ),
    }


def visualization_set_to_svg(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    width: int = 1600,
    height: int = 900,
    view: str = "Top",
    interactive: bool = False,
    render_2d_legend: bool = True,
    render_3d_legend: bool = False,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/svg",
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden SVG artifact."""
    if width <= 0 or height <= 0:
        raise ValueError("SVG width and height must be positive integers.")
    if view not in SVG_VIEWS:
        allowed = ", ".join(sorted(SVG_VIEWS))
        raise ValueError(f"Unsupported SVG view: {view}. Allowed values: {allowed}.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set = _resolve_visualization_set_input(
        garden_root=garden_root,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    vis_set = VisualizationSet.from_dict(visualization_set)
    svg = vis_set.to_svg(
        width=width,
        height=height,
        interactive=interactive,
        render_3d_legend=render_3d_legend,
        render_2d_legend=render_2d_legend,
        view=view,
    )
    svg_path = (output_dir / f"{safe_name}.svg").resolve()
    svg_path.relative_to(garden_root_path)
    svg_path.write_text(svg.as_str(), encoding="utf-8")

    artifact_path = to_posix_relative(svg_path, garden_root_path)
    source = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        "view": view,
        "width": width,
        "height": height,
        "interactive": interactive,
        "render_2d_legend": render_2d_legend,
        "render_3d_legend": render_3d_legend,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=SVG_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)

    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=SVG_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(svg_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": svg_path.is_file(),
            "view": view,
            "width": width,
            "height": height,
        },
        "report": make_report(
            status="ok",
            message="VisualizationSet SVG artifact exported.",
            details={"artifact_path": artifact_path},
        ),
    }
