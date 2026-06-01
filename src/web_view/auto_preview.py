"""Code Mode Web View automatic preview export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ladybug_display.visualization import VisualizationSet

from garden.dragonfly_core.display import dragonfly_model_to_visualization_set
from garden.paths import slugify_name
from garden.visualize.honeybee import honeybee_model_to_visualization_set
from garden.visualize.artifacts import load_visualization_set
from ladybug_tools_mcp.tool_namespaces import public_tool_name
from web_view.session import (
    read_web_view_session,
    record_preview_failure,
    record_preview_file_step,
)


def _tool_names(family: str, names: set[str]) -> set[str]:
    return {public_tool_name(name, family=family) for name in names}


HONEYBEE_AUTHORING_TOOL_NAMES = _tool_names(
    "honeybee_core",
    {
        "create_honeybee_model",
        "create_honeybee_room",
        "create_honeybee_face",
        "create_honeybee_aperture",
        "create_honeybee_apertures_by_parameters",
        "create_honeybee_door",
        "create_honeybee_shade",
        "create_honeybee_shades_by_parameters",
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
    },
)
DRAGONFLY_AUTHORING_TOOL_NAMES = _tool_names(
    "dragonfly_core",
    {
        "create_dragonfly_model",
        "create_dragonfly_room2d",
        "create_dragonfly_story",
        "create_dragonfly_building",
        "create_dragonfly_context_shade",
        "edit_dragonfly_model",
        "edit_dragonfly_room2d",
        "edit_dragonfly_story",
        "edit_dragonfly_building",
        "add_dragonfly_stories_to_building",
        "remove_dragonfly_stories_from_building",
        "solve_dragonfly_story_adjacency",
        "reset_dragonfly_story_adjacency",
        "clean_dragonfly_room2d_geometry",
        "apply_dragonfly_window_parameter",
        "apply_dragonfly_shading_parameter",
        "apply_dragonfly_energy_properties",
        "apply_dragonfly_radiance_properties",
    },
)
BASE_HONEYBEE_MODEL_TOOL_NAMES = _tool_names(
    "garden",
    {"set_base_honeybee_model", "save_base_honeybee_model"},
) | {public_tool_name("create_honeybee_model", family="honeybee_core")}
BASE_DRAGONFLY_MODEL_TOOL_NAMES = _tool_names(
    "garden",
    {"set_base_dragonfly_model", "save_base_dragonfly_model"},
) | {public_tool_name("create_dragonfly_model", family="dragonfly_core")}
SIGNIFICANT_TOOL_NAMES = (
    HONEYBEE_AUTHORING_TOOL_NAMES
    | DRAGONFLY_AUTHORING_TOOL_NAMES
    | BASE_HONEYBEE_MODEL_TOOL_NAMES
    | BASE_DRAGONFLY_MODEL_TOOL_NAMES
    | {
        public_tool_name("apply_dragonfly_uwg_properties", family="run_uwg"),
        public_tool_name("honeybee_model_to_dragonfly", family="dragonfly_core"),
        public_tool_name("dragonfly_model_to_honeybee", family="dragonfly_core"),
    }
)
FAIRYFLY_AUTHORING_TOOL_NAMES = _tool_names(
    "fairyfly",
    {
        "add_fairyfly_shape_to_model",
        "add_fairyfly_boundary_to_model",
        "set_base_fairyfly_model",
    },
)
VISUALIZATION_SET_RESULT_TOOL_NAMES = _tool_names(
    "dragonfly_core",
    {
        "dragonfly_model_to_visualization_set",
        "dragonfly_model_envelope_edges_to_visualization_set",
        "dragonfly_models_to_comparison_visualization_set",
    },
) | _tool_names(
    "fairyfly",
    {
        "fairyfly_model_to_visualization_set",
        "fairyfly_therm_result_to_visualization_set",
    },
)
VISUALIZATION_EXPORT_TOOL_NAMES = _tool_names(
    "visualize",
    {"visualization_set_to_vtkjs"},
)
DRAGONFLY_MODEL_PREVIEW_TOOL_NAMES = (
    DRAGONFLY_AUTHORING_TOOL_NAMES
    | BASE_DRAGONFLY_MODEL_TOOL_NAMES
    | {
        public_tool_name("apply_dragonfly_uwg_properties", family="run_uwg"),
        public_tool_name("honeybee_model_to_dragonfly", family="dragonfly_core"),
    }
)
HONEYBEE_MODEL_PREVIEW_TOOL_NAMES = (
    HONEYBEE_AUTHORING_TOOL_NAMES
    | BASE_HONEYBEE_MODEL_TOOL_NAMES
    | {public_tool_name("dragonfly_model_to_honeybee", family="dragonfly_core")}
)
SKIPPED_TOOL_NAMES = _tool_names(
    "web_view",
    {
        "start_web_view_mode",
        "stop_web_view_mode",
        "preview_state",
        "preview_artifact",
    },
)

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
    if tool_name in BASE_HONEYBEE_MODEL_TOOL_NAMES:
        return "base_honeybee_model"
    if tool_name in BASE_DRAGONFLY_MODEL_TOOL_NAMES:
        return "base_dragonfly_model"
    if tool_name in VISUALIZATION_EXPORT_TOOL_NAMES:
        return "analysis_overlay"
    if tool_name in VISUALIZATION_SET_RESULT_TOOL_NAMES:
        return "analysis_overlay"
    if tool_name == public_tool_name(
        "dragonfly_model_to_honeybee",
        family="dragonfly_core",
    ):
        return "base_honeybee_model"
    if tool_name == public_tool_name(
        "honeybee_model_to_dragonfly",
        family="dragonfly_core",
    ):
        return "base_dragonfly_model"
    return "object_edit"


def _is_significant_tool(tool_name: str) -> bool:
    return (
        tool_name in SIGNIFICANT_TOOL_NAMES
        or tool_name in FAIRYFLY_AUTHORING_TOOL_NAMES
        or tool_name in VISUALIZATION_SET_RESULT_TOOL_NAMES
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


def _visualization_set_from_result(
    *,
    garden_root: str,
    result: Any,
) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    visualization_set = result.get("visualization_set")
    if isinstance(visualization_set, dict):
        return visualization_set
    visualization_set_target = result.get("visualization_set_target")
    if not isinstance(visualization_set_target, dict):
        return None
    return load_visualization_set(
        garden_root=garden_root,
        visualization_set_target=visualization_set_target,
    )


def _model_target_from_result(*, result: Any, domain: str) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    plural_key = f"{domain}_model_targets"
    targets = result.get(plural_key)
    if isinstance(targets, list) and targets and isinstance(targets[0], dict):
        return targets[0]
    singular_key = f"{domain}_model_target"
    target = result.get(singular_key)
    if isinstance(target, dict):
        return target
    target = result.get("model_target")
    if isinstance(target, dict) and target.get("domain") == domain:
        return target
    return None


def _record_visualization_set_result_preview(
    *,
    garden_root: str,
    tool_name: str,
    result: Any,
    session: dict[str, Any],
) -> None:
    visualization_set = _visualization_set_from_result(
        garden_root=garden_root,
        result=result,
    )
    if visualization_set is None:
        return
    preview_name = _session_preview_name(session=session, tool_name=tool_name)
    vtkjs_path = _export_session_vtkjs(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=preview_name,
    )
    record_preview_file_step(
        garden_root=garden_root,
        preview_kind=_preview_kind(tool_name),
        label=f"Code Mode preview after {tool_name}",
        vtkjs_file_path=vtkjs_path,
        source_tool=tool_name,
        summary=result.get("summary_view", {}) if isinstance(result, dict) else {},
    )


def _record_fairyfly_authoring_preview(
    *,
    garden_root: str,
    tool_name: str,
    session: dict[str, Any],
) -> None:
    from garden.fairyfly.display import fairyfly_model_to_visualization_set

    preview_name = _session_preview_name(session=session, tool_name=tool_name)
    visualization = fairyfly_model_to_visualization_set(
        garden_root=garden_root,
        color_by="material",
        include_boundaries=True,
        name=preview_name,
        return_visualization_set=True,
    )
    vtkjs_path = _export_session_vtkjs(
        garden_root=garden_root,
        visualization_set=visualization["visualization_set"],
        name=preview_name,
    )
    record_preview_file_step(
        garden_root=garden_root,
        preview_kind=_preview_kind(tool_name),
        label=f"Code Mode preview after {tool_name}",
        vtkjs_file_path=vtkjs_path,
        source_tool=tool_name,
        summary=visualization.get("summary_view", {}),
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
        if tool_name in VISUALIZATION_SET_RESULT_TOOL_NAMES:
            _record_visualization_set_result_preview(
                garden_root=garden_root,
                tool_name=tool_name,
                result=result,
                session=session,
            )
            return
        if tool_name in FAIRYFLY_AUTHORING_TOOL_NAMES:
            _record_fairyfly_authoring_preview(
                garden_root=garden_root,
                tool_name=tool_name,
                session=session,
            )
            return

        preview_name = _session_preview_name(session=session, tool_name=tool_name)
        if tool_name in DRAGONFLY_MODEL_PREVIEW_TOOL_NAMES:
            visualization = dragonfly_model_to_visualization_set(
                garden_root=garden_root,
                model_target=_model_target_from_result(
                    result=result,
                    domain="dragonfly",
                ),
                color_by="type",
                include_wireframe=True,
                name=preview_name,
                return_visualization_set=True,
            )
        elif tool_name in HONEYBEE_MODEL_PREVIEW_TOOL_NAMES:
            visualization = honeybee_model_to_visualization_set(
                garden_root=garden_root,
                model_target=_model_target_from_result(
                    result=result,
                    domain="honeybee",
                ),
                color_by="type",
                include_wireframe=True,
                name=preview_name,
                return_visualization_set=True,
            )
        else:
            return
        vtkjs_path = _export_session_vtkjs(
            garden_root=garden_root,
            visualization_set=visualization["visualization_set"],
            name=preview_name,
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
