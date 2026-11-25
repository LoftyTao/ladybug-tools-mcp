"""Local Rune 3D Web View session state, protocol coordination, and Code Mode auto-preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from garden.manifest import GardenManifest, utc_now_iso, write_json_file
from garden.paths import (
    resolve_contained_path,
    to_posix_relative,
    windows_path_key,
)
from web_view.launcher import (
    can_open_rune_window,
    discover_rune_viewer_binary,
    discover_rune_web_bundle_dir,
    is_rune_viewer_running,
    launch_rune_viewer,
    run_headless_snap,
    stop_rune_viewer,
)
from web_view.server import (
    get_rune_web_server_info,
    start_rune_web_server,
    stop_all_rune_web_servers,
    stop_rune_web_server,
)
from web_view.protocol import (
    CAPTURES_DIR_RELATIVE_PATH,
    CAPTURE_REQUEST_RELATIVE_PATH,
    INTERACTION_STATE_RELATIVE_PATH,
    PRESENT_RELATIVE_PATH,
    capture_output_paths,
    ensure_initial_interaction_state,
    ensure_initial_present,
    get_web_view_context,
    interaction_state_file_path,
    map_view_to_vtk,
    poll_capture_handshake,
    present_file_path,
    read_capture_receipt,
    read_interaction_state,
    read_present,
    update_present,
    write_capture_request,
    write_interaction_state,
    write_present,
)

SESSION_RELATIVE_PATH = "tmp/web_view/session.json"
SUPPORTED_PREVIEW_KINDS = (
    "base_honeybee_model",
    "base_dragonfly_model",
    "object_edit",
    "search_highlight",
    "analysis_overlay",
)
GEOMETRY_POLICY = (
    "Render Garden Honeybee (.hbjson) and Dragonfly-derived scenes natively "
    "in lbt-rune-viewer via tmp/web_view/present.json."
)
_MODEL_PREVIEW_KINDS = {
    "honeybee": "base_honeybee_model",
    "dragonfly": "base_dragonfly_model",
}
_CHART_TYPES = {
    "hourly_plot",
    "monthly_chart",
    "psychrometric_chart",
    "adaptive_chart",
    "windrose",
}
_CHART_PRODUCERS = {
    "LB_Chart_To_Visualization_Set",
    "data_collection_hourly_plot_to_visualization_set",
    "data_collection_monthly_chart_to_visualization_set",
    "psychrometric_chart_to_visualization_set",
    "adaptive_chart_to_visualization_set",
}


def _resolve_garden(garden_root: str) -> tuple[Path, GardenManifest]:
    root = Path(garden_root).expanduser().resolve()
    return root, GardenManifest.read(root)


def _session_path(garden_root: Path) -> Path:
    return resolve_contained_path(garden_root, SESSION_RELATIVE_PATH, label="Web View session")


def _write_session(garden_root: Path, session: dict[str, Any]) -> None:
    path = _session_path(garden_root)
    session["updated_at"] = utc_now_iso()
    write_json_file(path, session, ensure_ascii=False)


def _read_session(garden_root: Path) -> dict[str, Any] | None:
    path = _session_path(garden_root)
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _default_data_sources() -> dict[str, str]:
    return {
        "primary_geometry": "honeybee_hbjson",
        "geometry_policy": GEOMETRY_POLICY,
        "manifest": "garden.json",
        "session": SESSION_RELATIVE_PATH,
        "present": PRESENT_RELATIVE_PATH,
        "interaction_state": INTERACTION_STATE_RELATIVE_PATH,
        "capture_request": CAPTURE_REQUEST_RELATIVE_PATH,
        "captures_dir": CAPTURES_DIR_RELATIVE_PATH,
    }


def read_web_view_session(*, garden_root: str) -> dict[str, Any] | None:
    """Return the stored Web View session without creating one."""
    root, _ = _resolve_garden(garden_root)
    return _read_session(root)


def start_web_view_session(
    *,
    garden_root: str,
    name: str = "Rune 3D Preview",
    preview_kinds: list[str] | tuple[str, ...] | None = None,
    viewer_metadata: dict[str, Any] | None = None,
    preserve_history: bool = True,
) -> dict[str, Any]:
    """Start or refresh a Rune Web View session for one Garden."""
    root, manifest = _resolve_garden(garden_root)
    kinds = tuple(preview_kinds or SUPPORTED_PREVIEW_KINDS)
    invalid = [kind for kind in kinds if kind not in SUPPORTED_PREVIEW_KINDS]
    if invalid:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview kind(s): {', '.join(invalid)}. Allowed values: {allowed}."
        )

    existing = _read_session(root) if preserve_history else None
    now = utc_now_iso()
    steps = list(existing.get("steps") or []) if isinstance(existing, dict) else []
    active_step_id = existing.get("active_step_id") if isinstance(existing, dict) else None
    created_at = (
        existing.get("created_at") if isinstance(existing, dict) and existing.get("created_at") else now
    )
    session_id = (
        existing.get("session_id")
        if isinstance(existing, dict) and existing.get("session_id")
        else f"web_view_{uuid4().hex[:12]}"
    )
    default_viewer = {
        "ui": "Rune 3D Viewer",
        "library": "rune-wgpu",
        "mode": "rune_viewer",
        "backend": "rune",
        "local_only": True,
    }
    if isinstance(viewer_metadata, dict):
        viewer_info = {**default_viewer, **viewer_metadata}
    else:
        viewer_info = default_viewer

    session = {
        "schema_version": "1",
        "session_id": session_id,
        "name": name,
        "active": True,
        "local_only": True,
        "created_at": created_at,
        "updated_at": now,
        "garden": {
            "garden_root": str(root),
            "garden_target": manifest.target(),
            "name": manifest.name,
        },
        "viewer": viewer_info,
        "preview_kinds": list(kinds),
        "data_sources": _default_data_sources(),
        "steps": steps,
        "active_step_id": active_step_id,
    }
    _write_session(root, session)
    return {
        "session": session,
        "session_path": str(_session_path(root)),
        "summary_view": {
            "garden_target": manifest.target(),
            "local_only": True,
            "preview_kinds": list(kinds),
            "preserve_history": bool(preserve_history),
            "step_count": len(steps),
        },
    }


def stop_web_view_session(*, garden_root: str) -> dict[str, Any]:
    """Mark a Web View session as inactive without deleting its history."""
    root, _ = _resolve_garden(garden_root)
    session = _read_session(root)
    if session is None:
        session = start_web_view_session(garden_root=str(root))["session"]
    session["active"] = False
    _write_session(root, session)
    return {
        "session": session,
        "session_path": str(_session_path(root)),
        "summary_view": {"active": False, "local_only": True},
    }


def _resolve_active_session(garden_root: Path, preview_kind: str) -> dict[str, Any]:
    if preview_kind not in SUPPORTED_PREVIEW_KINDS:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview_kind: {preview_kind!r}. Allowed values: {allowed}."
        )
    session = _read_session(garden_root)
    if session is None or not session.get("active", False):
        session = start_web_view_session(garden_root=str(garden_root))["session"]
    if preview_kind not in session.get("preview_kinds", []):
        raise ValueError(
            f"Preview kind {preview_kind!r} is not enabled for this Web View session."
        )
    return session


def record_present_step(
    *,
    garden_root: str | Path,
    preview_kind: str,
    label: str,
    present: dict[str, Any],
    source_tool: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a local preview step backed by ``tmp/web_view/present.json``."""
    root, _ = _resolve_garden(str(garden_root))
    session = _resolve_active_session(root, preview_kind)
    viewer_source = {
        "kind": "rune_present",
        "present_revision": present.get("revision"),
        "view_type": present.get("view_type"),
        "model_path": present.get("model_path"),
        "color_by": present.get("color_by"),
        "highlight_count": len(present.get("highlight_targets") or []),
        "validation_issue_count": len(present.get("validation_issues") or []),
    }
    step = {
        "id": f"step_{len(session.get('steps', [])) + 1:04d}",
        "preview_kind": preview_kind,
        "label": label,
        "created_at": utc_now_iso(),
        "source_tool": source_tool,
        "summary": summary or {},
        "viewer_source": viewer_source,
    }
    session.setdefault("steps", []).append(step)
    session["active_step_id"] = step["id"]
    _write_session(root, session)
    return {
        "step": step,
        "session": session,
        "summary_view": {
            "active_step_id": step["id"],
            "preview_kind": preview_kind,
            "present_revision": present.get("revision"),
            "model_path": present.get("model_path"),
        },
    }


def record_preview_failure(
    *,
    garden_root: str,
    preview_kind: str,
    label: str,
    source_tool: str,
    error_message: str,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append a failed preview event without changing the active viewer source."""
    if preview_kind not in SUPPORTED_PREVIEW_KINDS:
        preview_kind = "object_edit"
    root, _ = _resolve_garden(garden_root)
    session = _read_session(root)
    if session is None or not session.get("active", False):
        return None
    step = {
        "id": f"step_{len(session.get('steps', [])) + 1:04d}",
        "preview_kind": preview_kind,
        "label": label,
        "created_at": utc_now_iso(),
        "source_tool": source_tool,
        "summary": summary or {},
        "status": "failed",
        "error": error_message,
    }
    session.setdefault("steps", []).append(step)
    _write_session(root, session)
    return {
        "step": step,
        "session": session,
        "summary_view": {
            "preview_kind": preview_kind,
            "source_tool": source_tool,
            "status": "failed",
        },
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


def _persisted_model_target(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    if result.get("runtime_status") == "no_change":
        return None
    receipt = result.get("persistence_receipt")
    if not isinstance(receipt, dict) or receipt.get("status") == "no_change":
        return None
    for candidate in (result.get("model_target"), receipt.get("model_target")):
        if isinstance(candidate, dict):
            domain = candidate.get("domain")
            if domain in _MODEL_PREVIEW_KINDS and candidate.get("target_type") == f"{domain}_model":
                return candidate
    return None


def _is_2d_chart_visualization(
    *,
    tool_name: str = "",
    arguments: Any = None,
    result: Any = None,
) -> bool:
    """Return True for 2D chart VisualizationSets that must not hijack the 3D Rune viewport."""
    if tool_name == "LB_Chart_To_Visualization_Set":
        return True
    if isinstance(arguments, dict):
        chart_type = str(arguments.get("chart_type") or "").strip().lower()
        if chart_type in _CHART_TYPES:
            return True
    if isinstance(result, dict):
        summary = result.get("summary_view")
        if isinstance(summary, dict):
            if any(
                k in summary
                for k in ("chart_dimensions", "comfort_polygon", "comfort_percentages", "windrose")
            ):
                return True
            src = summary.get("source")
            if isinstance(src, dict) and src.get("producer") in _CHART_PRODUCERS:
                return True
        for receipt_key in ("visualization_set_persistence_receipt", "persistence_receipt"):
            rec = result.get(receipt_key)
            if isinstance(rec, dict):
                src = rec.get("source")
                if isinstance(src, dict) and src.get("producer") in _CHART_PRODUCERS:
                    return True
        artifact = result.get("artifact")
        if isinstance(artifact, dict):
            src = artifact.get("source")
            if isinstance(src, dict) and src.get("producer") in _CHART_PRODUCERS:
                return True
    return False


def _is_object_target_dict(candidate: Any) -> bool:
    return (
        isinstance(candidate, dict)
        and (
            candidate.get("target_type") == "honeybee_object"
            or (
                candidate.get("domain") == "honeybee"
                and isinstance(candidate.get("object_type"), str)
                and isinstance(candidate.get("object_identifier"), str)
            )
        )
    )


def extract_changed_targets(*, result: Any, arguments: Any = None) -> list[dict[str, Any]]:
    """Extract created or edited Honeybee object targets from a tool result."""
    if not isinstance(result, dict):
        return []
    if result.get("runtime_status") == "no_change":
        return []
    receipt = result.get("persistence_receipt")
    if isinstance(receipt, dict) and receipt.get("status") == "no_change":
        return []

    collected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(item: Any) -> None:
        if not _is_object_target_dict(item):
            return
        key = (
            str(item.get("model_identifier") or ""),
            str(item.get("object_type") or ""),
            str(item.get("object_identifier") or item.get("identifier") or ""),
        )
        if key not in seen:
            seen.add(key)
            collected.append(dict(item))

    for list_key in ("created_targets", "targets"):
        items = result.get(list_key)
        if isinstance(items, list):
            for item in items:
                _add(item)
    for single_key in ("target", "object_target", "adjacent_target"):
        _add(result.get(single_key))

    if not collected and isinstance(receipt, dict):
        cs = receipt.get("change_summary")
        if isinstance(cs, dict):
            for list_key in ("created_targets", "targets"):
                items = cs.get(list_key)
                if isinstance(items, list):
                    for item in items:
                        _add(item)
            _add(cs.get("target"))

    return collected


def preview_event_garden_root(
    *,
    arguments: Any,
    result: Any,
    tool_name: str = "",
) -> str | None:
    """Return a normalized Garden key when a tool call produced a 3D Rune preview update."""
    if _is_2d_chart_visualization(tool_name=tool_name, arguments=arguments, result=result):
        return None
    model_target = _persisted_model_target(result)
    has_supported_model = (
        model_target is not None and model_target.get("domain") in {"honeybee", "dragonfly"}
    )
    is_hb_validation = (
        tool_name == "HB_Validate_Model"
        and isinstance(result, dict)
        and "issues" in result
    )
    if not has_supported_model and not is_hb_validation:
        return None
    garden_root = _find_garden_root(arguments) or _find_garden_root(result)
    if not garden_root:
        return None
    return windows_path_key(Path(garden_root).expanduser().resolve())


def maybe_record_code_mode_preview(
    *,
    tool_name: str,
    arguments: Any,
    result: Any,
    changed_targets: list[dict[str, Any]] | None = None,
) -> None:
    """Update ``present.json`` and record a Rune Web View step after a Code Mode tool."""
    if _is_2d_chart_visualization(tool_name=tool_name, arguments=arguments, result=result):
        return

    is_hb_validation = (
        tool_name == "HB_Validate_Model"
        and isinstance(result, dict)
        and "issues" in result
    )
    model_target = _persisted_model_target(result)
    if not is_hb_validation and (
        model_target is None or model_target.get("domain") not in {"honeybee", "dragonfly"}
    ):
        return

    garden_root = _find_garden_root(arguments) or _find_garden_root(result)
    if not garden_root:
        return
    session = read_web_view_session(garden_root=garden_root)
    if not session or not session.get("active", False):
        return

    preview_kind = (
        "analysis_overlay"
        if is_hb_validation
        else _MODEL_PREVIEW_KINDS.get(str((model_target or {}).get("domain")), "object_edit")
    )

    try:
        if is_hb_validation:
            issues = [item for item in (result.get("issues") or []) if isinstance(item, dict)]
            summary_view = (
                result.get("summary_view") if isinstance(result.get("summary_view"), dict) else {}
            )
            val_model_target = (
                summary_view.get("model_target")
                if isinstance(summary_view.get("model_target"), dict)
                else None
            )
            if issues:
                present = update_present(
                    garden_root=garden_root,
                    view_type="validation",
                    model_target=val_model_target,
                    validation_issues=issues,
                    highlight_targets=[],
                    camera=None,
                    title=f"Validation: {len(issues)} issue(s)",
                )
                record_present_step(
                    garden_root=garden_root,
                    preview_kind="analysis_overlay",
                    label=f"Validation overlay after {tool_name}",
                    present=present,
                    source_tool=tool_name,
                    summary=summary_view,
                )
            else:
                effective_targets = list(changed_targets) if changed_targets else []
                present = update_present(
                    garden_root=garden_root,
                    view_type="highlight" if effective_targets else "model",
                    model_target=val_model_target,
                    highlight_targets=effective_targets,
                    isolation_mode="highlight",
                    validation_issues=[],
                    camera=None,
                    title=f"Code Mode: {tool_name}",
                )
                record_present_step(
                    garden_root=garden_root,
                    preview_kind="object_edit" if effective_targets else "base_honeybee_model",
                    label=f"Rune preview after {tool_name}",
                    present=present,
                    source_tool=tool_name,
                    summary=summary_view,
                )
            return

        domain = (model_target or {}).get("domain")
        summary_view = (
            result.get("summary_view")
            if isinstance(result, dict) and isinstance(result.get("summary_view"), dict)
            else {}
        )
        if domain == "honeybee":
            effective_targets = (
                list(changed_targets)
                if changed_targets
                else extract_changed_targets(result=result, arguments=arguments)
            )
            step_kind = "object_edit" if effective_targets else "base_honeybee_model"
            preview_kind = step_kind
            present = update_present(
                garden_root=garden_root,
                view_type="highlight" if effective_targets else "model",
                model_target=model_target,
                highlight_targets=effective_targets,
                isolation_mode="highlight",
                camera=None,
                title=f"Code Mode: {tool_name}",
            )
            record_present_step(
                garden_root=garden_root,
                preview_kind=step_kind,
                label=f"Rune preview after {tool_name}",
                present=present,
                source_tool=tool_name,
                summary=summary_view,
            )
        elif domain == "dragonfly":
            present = update_present(
                garden_root=garden_root,
                view_type="model",
                model_target=model_target,
                highlight_targets=[],
                isolation_mode="highlight",
                camera=None,
                title=f"Code Mode: {tool_name}",
            )
            record_present_step(
                garden_root=garden_root,
                preview_kind="base_dragonfly_model",
                label=f"Rune preview after {tool_name}",
                present=present,
                source_tool=tool_name,
                summary=summary_view,
            )
    except Exception as exc:  # pragma: no cover - exercised through integration failures
        record_preview_failure(
            garden_root=garden_root,
            preview_kind=preview_kind,
            label=f"Code Mode preview failed after {tool_name}",
            source_tool=tool_name,
            error_message=str(exc),
        )


def _read_png_dimensions(png_path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(png_path) as img:
        w, h = img.size
    return int(w), int(h)


def _load_capture_visualization_set(
    *,
    root: Path,
    manifest: GardenManifest,
    present: dict[str, Any] | None,
) -> Any:
    from ladybug_display.visualization import VisualizationSet

    model_target = present.get("model_target") if isinstance(present, dict) else None
    if model_target is None and isinstance(manifest.base_honeybee_model, dict):
        model_target = dict(manifest.base_honeybee_model)
    if isinstance(model_target, dict) and model_target.get("domain") == "honeybee":
        from garden.visualize.honeybee import honeybee_model_to_visualization_set

        raw_color_by = str((present or {}).get("color_by") or "type").lower()
        vtk_color_by = raw_color_by if raw_color_by in {"type", "boundary_condition"} else "type"
        vis_res = honeybee_model_to_visualization_set(
            garden_root=str(root),
            model_target=model_target,
            color_by=vtk_color_by,
            include_wireframe=True,
            return_visualization_set=True,
        )
        return VisualizationSet.from_dict(vis_res["visualization_set"])

    if isinstance(manifest.base_dragonfly_model, dict):
        from garden.dragonfly_core.display import dragonfly_model_to_visualization_set

        vis_res = dragonfly_model_to_visualization_set(
            garden_root=str(root),
            model_target=dict(manifest.base_dragonfly_model),
            color_by="type",
            include_wireframe=True,
            return_visualization_set=True,
        )
        return VisualizationSet.from_dict(vis_res["visualization_set"])

    from garden.visualize.artifacts import VISUALIZATION_SET_ARTIFACT_TYPE, load_visualization_set

    for artifact in reversed(manifest.artifacts):
        if artifact.get("artifact_type") == VISUALIZATION_SET_ARTIFACT_TYPE:
            vis_dict = load_visualization_set(
                garden_root=str(root),
                visualization_set_target={
                    "target_type": "visualization_set",
                    "garden_id": manifest.garden_id,
                    "path": artifact.get("path"),
                },
            )
            return VisualizationSet.from_dict(vis_dict)

    raise ValueError(
        "No Honeybee, Dragonfly, or VisualizationSet model is available to capture in this Garden."
    )


def capture_web_view(
    *,
    garden_root: str,
    view: str | dict[str, Any] = "fit",
    width: int = 1280,
    height: int = 720,
    timeout_secs: float = 5.0,
) -> dict[str, Any]:
    """Capture a viewport PNG via live Rune handshake, headless Rune ``--snap``, or VTK fallback."""
    from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

    root, manifest = _resolve_garden(garden_root)
    request_id = f"cap_{uuid4().hex[:12]}"
    out_png, _ = capture_output_paths(root, request_id)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    # 1. Live Rune viewer capture handshake.
    if is_rune_viewer_running(root):
        live = poll_capture_handshake(
            garden_root=root,
            view=view,
            width=width,
            height=height,
            timeout_secs=timeout_secs,
            request_id=request_id,
        )
        if live is not None:
            png_path = Path(live["png_path"])
            actual_w, actual_h = _read_png_dimensions(png_path)
            rel_path = to_posix_relative(png_path, root)
            receipt_data = live.get("receipt") or {}
            source = {
                "renderer": "rune_live",
                "view": receipt_data.get("camera", view),
                "width": actual_w,
                "height": actual_h,
                "request_id": request_id,
            }
            return {
                "artifact_path": rel_path,
                "absolute_path": str(png_path),
                "width": actual_w,
                "height": actual_h,
                "renderer": "rune_live",
                "view": view,
                "request_id": request_id,
                "artifact_receipt": make_artifact_receipt(
                    status="persisted",
                    garden_id=manifest.garden_id,
                    artifact_type="web_view_capture_png",
                    artifact_path=rel_path,
                    absolute_path=str(png_path),
                    source=source,
                ),
                "summary_view": {
                    "garden_target": manifest.target(),
                    "artifact_path": rel_path,
                    "absolute_path": str(png_path),
                    "width": actual_w,
                    "height": actual_h,
                    "renderer": "rune_live",
                    "view": view,
                    "request_id": request_id,
                    "exists": png_path.is_file(),
                },
                "report": make_report(
                    status="ok",
                    message=f"Captured live Rune viewport PNG ({actual_w}x{actual_h}).",
                ),
            }
        warnings.append("Live Rune capture handshake timed out or failed; falling back.")

    present = read_present(root)
    hbjson_abs: Path | None = None
    if isinstance(present, dict) and isinstance(present.get("model_path"), str) and present["model_path"]:
        candidate = (root / present["model_path"]).resolve()
        if candidate.is_file():
            hbjson_abs = candidate
    elif isinstance(manifest.base_honeybee_model, dict):
        raw_path = manifest.base_honeybee_model.get("path")
        if isinstance(raw_path, str) and raw_path:
            candidate = (root / raw_path).resolve()
            if candidate.is_file():
                hbjson_abs = candidate

    # 2. Headless Rune --snap fallback.
    rune_bin = discover_rune_viewer_binary()
    if rune_bin is not None and (hbjson_abs is not None or present is not None):
        snap_res = run_headless_snap(
            garden_root=root,
            output_png_path=out_png,
            hbjson_path=None if present is not None else hbjson_abs,
            view=view,
            color_by=(present or {}).get("color_by") if isinstance(present, dict) else None,
            width=width,
            height=height,
            timeout_secs=max(5.0, float(timeout_secs)),
            binary_path=rune_bin,
        )
        if snap_res.get("status") == "ok":
            actual_w, actual_h = _read_png_dimensions(out_png)
            rel_path = to_posix_relative(out_png, root)
            source = {
                "renderer": "rune_headless",
                "view": view,
                "width": actual_w,
                "height": actual_h,
                "request_id": request_id,
            }
            return {
                "artifact_path": rel_path,
                "absolute_path": str(out_png),
                "width": actual_w,
                "height": actual_h,
                "renderer": "rune_headless",
                "view": view,
                "request_id": request_id,
                "artifact_receipt": make_artifact_receipt(
                    status="persisted",
                    garden_id=manifest.garden_id,
                    artifact_type="web_view_capture_png",
                    artifact_path=rel_path,
                    absolute_path=str(out_png),
                    source=source,
                    warnings=warnings,
                ),
                "summary_view": {
                    "garden_target": manifest.target(),
                    "artifact_path": rel_path,
                    "absolute_path": str(out_png),
                    "width": actual_w,
                    "height": actual_h,
                    "renderer": "rune_headless",
                    "view": view,
                    "request_id": request_id,
                    "exists": out_png.is_file(),
                },
                "report": make_report(
                    status="ok",
                    message=f"Captured headless Rune PNG ({actual_w}x{actual_h}).",
                    warnings=warnings,
                ),
            }
        warnings.append(
            f"Headless Rune snap failed ({snap_res.get('reason') or snap_res.get('returncode')}); falling back to VTK."
        )

    # 3. _render_png_vtk fallback from garden.visualize.artifacts.
    from garden.visualize.artifacts import _render_png_matplotlib_fallback, _render_png_vtk

    vis_set = _load_capture_visualization_set(root=root, manifest=manifest, present=present)
    vtk_view = map_view_to_vtk(view)
    renderer_used = "vtk_offscreen"
    try:
        image = _render_png_vtk(
            vis_set,
            width=width,
            height=height,
            view=vtk_view,
            render_2d_legend=True,
        )
    except Exception as exc:
        warnings.append(f"Offscreen VTK capture failed ({exc}); used matplotlib fallback.")
        renderer_used = "matplotlib_fallback"
        image = _render_png_matplotlib_fallback(
            vis_set,
            width=width,
            height=height,
            view=vtk_view,
        )
    image.save(out_png, format="PNG")
    actual_w, actual_h = _read_png_dimensions(out_png)
    rel_path = to_posix_relative(out_png, root)
    source = {
        "renderer": renderer_used,
        "view": vtk_view,
        "width": actual_w,
        "height": actual_h,
        "request_id": request_id,
    }
    return {
        "artifact_path": rel_path,
        "absolute_path": str(out_png),
        "width": actual_w,
        "height": actual_h,
        "renderer": renderer_used,
        "view": view,
        "request_id": request_id,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type="web_view_capture_png",
            artifact_path=rel_path,
            absolute_path=str(out_png),
            source=source,
            warnings=warnings,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact_path": rel_path,
            "absolute_path": str(out_png),
            "width": actual_w,
            "height": actual_h,
            "renderer": renderer_used,
            "view": view,
            "request_id": request_id,
            "exists": out_png.is_file(),
        },
        "report": make_report(
            status="ok",
            message=f"Captured Web View PNG ({actual_w}x{actual_h}) via {renderer_used}.",
            warnings=warnings,
        ),
    }


__all__ = [
    "CAPTURES_DIR_RELATIVE_PATH",
    "CAPTURE_REQUEST_RELATIVE_PATH",
    "INTERACTION_STATE_RELATIVE_PATH",
    "PRESENT_RELATIVE_PATH",
    "SUPPORTED_PREVIEW_KINDS",
    "can_open_rune_window",
    "capture_output_paths",
    "capture_web_view",
    "discover_rune_viewer_binary",
    "discover_rune_web_bundle_dir",
    "ensure_initial_interaction_state",
    "ensure_initial_present",
    "extract_changed_targets",
    "get_rune_web_server_info",
    "get_web_view_context",
    "interaction_state_file_path",
    "is_rune_viewer_running",
    "launch_rune_viewer",
    "map_view_to_vtk",
    "maybe_record_code_mode_preview",
    "poll_capture_handshake",
    "present_file_path",
    "preview_event_garden_root",
    "read_capture_receipt",
    "read_interaction_state",
    "read_present",
    "read_web_view_session",
    "record_present_step",
    "record_preview_failure",
    "run_headless_snap",
    "start_rune_web_server",
    "start_web_view_session",
    "stop_all_rune_web_servers",
    "stop_rune_viewer",
    "stop_rune_web_server",
    "stop_web_view_session",
    "update_present",
    "write_capture_request",
    "write_interaction_state",
    "write_present",
]
