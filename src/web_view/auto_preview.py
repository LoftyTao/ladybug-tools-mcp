"""Code Mode Web View automatic preview export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.paths import slugify_name
from web_view.session import (
    read_web_view_session,
    record_preview_failure,
    record_preview_file_step,
)


_MODEL_PREVIEW_KINDS = {
    "honeybee": "base_honeybee_model",
    "dragonfly": "base_dragonfly_model",
    "fairyfly": "object_edit",
}
VTKJS_ARTIFACT_TYPE = "visualization_vtkjs"


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


def _is_visualization_result(result: Any) -> bool:
    return isinstance(result, dict) and any(
        isinstance(result.get(key), dict)
        for key in ("visualization_set", "visualization_set_target")
    )


def _vtkjs_artifact_receipt(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    receipt = result.get("artifact_receipt")
    if not isinstance(receipt, dict) or receipt.get("artifact_type") != VTKJS_ARTIFACT_TYPE:
        return None
    return receipt


def _model_target(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    domain = value.get("domain")
    if domain not in _MODEL_PREVIEW_KINDS:
        return None
    if value.get("target_type") != f"{domain}_model":
        return None
    return value


def _persisted_model_target(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    payloads = [result]
    nested = result.get("operation_result")
    if isinstance(nested, dict):
        payloads.append(nested)
    for payload in payloads:
        receipt = payload.get("persistence_receipt")
        if not isinstance(receipt, dict):
            continue
        target = _model_target(payload.get("model_target"))
        target = target or _model_target(receipt.get("model_target"))
        if target is not None:
            return target
    return None


def _preview_kind(*, result: Any, model_target: dict[str, Any] | None = None) -> str:
    if _is_visualization_result(result) or _vtkjs_artifact_receipt(result) is not None:
        return "analysis_overlay"
    if model_target is not None:
        return _MODEL_PREVIEW_KINDS.get(str(model_target.get("domain")), "object_edit")
    return "object_edit"


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
    from ladybug_display.visualization import VisualizationSet

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
        preview_kind="analysis_overlay",
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
    from garden.visualize.artifacts import load_visualization_set

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
        preview_kind="analysis_overlay",
        label=f"Code Mode preview after {tool_name}",
        vtkjs_file_path=vtkjs_path,
        source_tool=tool_name,
        summary=result.get("summary_view", {}) if isinstance(result, dict) else {},
    )


def _record_fairyfly_authoring_preview(
    *,
    garden_root: str,
    tool_name: str,
    model_target: dict[str, Any],
    session: dict[str, Any],
) -> None:
    from garden.fairyfly.display import fairyfly_model_to_visualization_set

    preview_name = _session_preview_name(session=session, tool_name=tool_name)
    visualization = fairyfly_model_to_visualization_set(
        garden_root=garden_root,
        model_target=model_target,
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
        preview_kind="object_edit",
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
    visualization_result = _is_visualization_result(result)
    vtkjs_receipt = _vtkjs_artifact_receipt(result)
    model_target = _persisted_model_target(result)
    if not visualization_result and vtkjs_receipt is None and model_target is None:
        return
    garden_root = _find_garden_root(arguments) or _find_garden_root(result)
    if not garden_root:
        return
    session = _active_session(garden_root)
    if session is None:
        return

    preview_kind = _preview_kind(result=result, model_target=model_target)
    try:
        if vtkjs_receipt is not None:
            _record_existing_vtkjs_export(
                garden_root=garden_root,
                tool_name=tool_name,
                result=result,
            )
            return
        if visualization_result:
            _record_visualization_set_result_preview(
                garden_root=garden_root,
                tool_name=tool_name,
                result=result,
                session=session,
            )
            return
        if model_target is not None and model_target.get("domain") == "fairyfly":
            _record_fairyfly_authoring_preview(
                garden_root=garden_root,
                tool_name=tool_name,
                model_target=model_target,
                session=session,
            )
            return

        preview_name = _session_preview_name(session=session, tool_name=tool_name)
        if model_target is not None and model_target.get("domain") == "dragonfly":
            from garden.dragonfly_core.display import (
                dragonfly_model_to_visualization_set,
            )

            visualization = dragonfly_model_to_visualization_set(
                garden_root=garden_root,
                model_target=model_target,
                color_by="type",
                include_wireframe=True,
                name=preview_name,
                return_visualization_set=True,
            )
        elif model_target is not None and model_target.get("domain") == "honeybee":
            from garden.visualize.honeybee import honeybee_model_to_visualization_set

            visualization = honeybee_model_to_visualization_set(
                garden_root=garden_root,
                model_target=model_target,
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
