"""Code Mode Web View automatic preview export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ladybug_display.visualization import VisualizationSet

from garden.paths import slugify_name
from garden.visualize.honeybee import honeybee_model_to_visualization_set
from web_view.session import (
    read_web_view_session,
    record_preview_failure,
    record_preview_file_step,
)


SIGNIFICANT_TOOL_NAMES = {
    "create_honeybee_model",
    "create_honeybee_room",
    "create_honeybee_face",
    "create_honeybee_aperture",
    "create_honeybee_apertures_by_parameters",
    "create_honeybee_door",
    "create_honeybee_shade",
    "create_honeybee_shades_by_parameters",
    "create_honeybee_shades_by_ratio",
    "edit_honeybee_model",
    "edit_honeybee_room",
    "edit_honeybee_face",
    "edit_honeybee_aperture",
    "edit_honeybee_door",
    "edit_honeybee_shade",
    "remove_honeybee_room",
    "remove_honeybee_face",
    "remove_honeybee_aperture",
    "remove_honeybee_door",
    "remove_honeybee_shade",
    "move_object",
    "rotate_object",
    "scale_object",
    "mirror_object",
    "relate_honeybee_model",
    "set_base_model",
    "save_base_model",
}
VISUALIZATION_EXPORT_TOOL_NAMES = {
    "visualization_set_to_vtkjs",
}
SKIPPED_TOOL_NAMES = {
    "start_web_view_mode",
    "stop_web_view_mode",
}


def _find_garden_root(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("garden_root", "root_dir"):
            item = value.get(key)
            if isinstance(item, str) and item:
                return item
        for item in value.values():
            found = _find_garden_root(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_garden_root(item)
            if found:
                return found
    return None


def _preview_kind(tool_name: str) -> str:
    if tool_name in {"create_honeybee_model", "set_base_model", "save_base_model"}:
        return "base_model"
    if tool_name in VISUALIZATION_EXPORT_TOOL_NAMES:
        return "analysis_overlay"
    return "object_edit"


def _is_significant_tool(tool_name: str) -> bool:
    return (
        tool_name in SIGNIFICANT_TOOL_NAMES
        or tool_name in VISUALIZATION_EXPORT_TOOL_NAMES
    )


def _active_session(garden_root: str) -> dict[str, Any] | None:
    session = read_web_view_session(garden_root=garden_root)
    if not session or not session.get("active", False):
        return None
    return session


def _session_preview_name(*, session: dict[str, Any], tool_name: str) -> str:
    step_index = len(session.get("steps", [])) + 1
    return slugify_name(f"{step_index:04d}_{tool_name}")


def _export_session_vtkjs(
    *,
    garden_root: str,
    visualization_set: dict[str, Any],
    name: str,
) -> str:
    root = Path(garden_root).expanduser().resolve()
    output_dir = root / "tmp" / "web_view" / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    vis_set = VisualizationSet.from_dict(visualization_set)
    vtkjs_path = Path(
        vis_set.to_vtkjs(
            output_folder=str(output_dir),
            file_name=name,
        )
    ).resolve()
    vtkjs_path.relative_to(root)
    return str(vtkjs_path)


def _record_existing_vtkjs_export(
    *,
    garden_root: str,
    tool_name: str,
    result: Any,
) -> None:
    if not isinstance(result, dict):
        return
    receipt = result.get("artifact_receipt")
    if not isinstance(receipt, dict):
        return
    absolute_path = receipt.get("absolute_path")
    if not isinstance(absolute_path, str) or not absolute_path:
        return
    record_preview_file_step(
        garden_root=garden_root,
        preview_kind=_preview_kind(tool_name),
        label="Exported vtk.js preview",
        vtkjs_file_path=absolute_path,
        source_tool=tool_name,
        summary={"artifact_path": receipt.get("artifact_path")},
    )


def maybe_record_code_mode_preview(
    *,
    tool_name: str,
    arguments: Any,
    result: Any,
) -> None:
    """Export and record a Web View preview after a significant Code Mode tool."""
    if tool_name in SKIPPED_TOOL_NAMES or not _is_significant_tool(tool_name):
        return
    garden_root = _find_garden_root(arguments) or _find_garden_root(result)
    if not garden_root:
        return
    session = _active_session(garden_root)
    if session is None:
        return

    preview_kind = _preview_kind(tool_name)
    try:
        if tool_name in VISUALIZATION_EXPORT_TOOL_NAMES:
            _record_existing_vtkjs_export(
                garden_root=garden_root,
                tool_name=tool_name,
                result=result,
            )
            return

        visualization = honeybee_model_to_visualization_set(
            garden_root=garden_root,
            color_by="type",
            include_wireframe=True,
            name=_session_preview_name(session=session, tool_name=tool_name),
            return_visualization_set=True,
        )
        vtkjs_path = _export_session_vtkjs(
            garden_root=garden_root,
            visualization_set=visualization["visualization_set"],
            name=_session_preview_name(session=session, tool_name=tool_name),
        )
        record_preview_file_step(
            garden_root=garden_root,
            preview_kind=preview_kind,
            label=f"Code Mode preview after {tool_name}",
            vtkjs_file_path=vtkjs_path,
            source_tool=tool_name,
            summary=visualization.get("summary_view", {}),
        )
    except Exception as exc:  # pragma: no cover - exercised through integration failures
        record_preview_failure(
            garden_root=garden_root,
            preview_kind=preview_kind,
            label=f"Code Mode preview failed after {tool_name}",
            source_tool=tool_name,
            error_message=str(exc),
        )
