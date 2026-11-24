"""Local Web View session state, preview payloads, and Code Mode auto-preview."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
import zipfile

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    resolve_contained_path,
    slugify_name,
    to_posix_relative,
    windows_path_key,
)
from web_view.viewer import (
    POLL_INTERVAL_MS,
    VENDOR_VTKJS_PATH,
    fallback_viewer_html,
    start_preview_url_fallback,
    stop_preview_url_fallback,
)

SESSION_RELATIVE_PATH = "tmp/web_view/session.json"
VTKJS_ARTIFACT_TYPE = "visualization_vtkjs"
HTML_ARTIFACT_TYPE = "visualization_html"
SVG_ARTIFACT_TYPE = "visualization_svg"
SUPPORTED_PREVIEW_KINDS = (
    "base_honeybee_model",
    "base_dragonfly_model",
    "object_edit",
    "search_highlight",
    "analysis_overlay",
)
GEOMETRY_POLICY = "Use Ladybug Tools SDK/MCP exported vtkjs artifacts."
_MODEL_PREVIEW_KINDS = {
    "honeybee": "base_honeybee_model",
    "dragonfly": "base_dragonfly_model",
    "fairyfly": "object_edit",
}


def _resolve_garden(garden_root: str) -> tuple[Path, GardenManifest]:
    root = Path(garden_root).expanduser().resolve()
    return root, GardenManifest.read(root)


def _session_path(garden_root: Path) -> Path:
    return resolve_contained_path(garden_root, SESSION_RELATIVE_PATH, label="Web View session")


def _write_session(garden_root: Path, session: dict[str, Any]) -> None:
    path = _session_path(garden_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = utc_now_iso()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(session, handle, indent=2)
        handle.write("\n")


def _read_session(garden_root: Path) -> dict[str, Any] | None:
    path = _session_path(garden_root)
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _default_data_sources() -> dict[str, str]:
    return {
        "primary_geometry": VTKJS_ARTIFACT_TYPE,
        "geometry_policy": GEOMETRY_POLICY,
        "manifest": "garden.json",
        "session": SESSION_RELATIVE_PATH,
        "vtkjs_vendor": "/vendor/vtk.js",
    }


def read_web_view_session(*, garden_root: str) -> dict[str, Any] | None:
    """Return the stored Web View session without creating one."""
    root, _ = _resolve_garden(garden_root)
    return _read_session(root)


def start_web_view_session(
    *,
    garden_root: str,
    name: str = "Local Web View",
    preview_kinds: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Start or replace a Web View session for one Garden."""
    root, manifest = _resolve_garden(garden_root)
    kinds = tuple(preview_kinds or SUPPORTED_PREVIEW_KINDS)
    invalid = [kind for kind in kinds if kind not in SUPPORTED_PREVIEW_KINDS]
    if invalid:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview kind(s): {', '.join(invalid)}. Allowed values: {allowed}."
        )

    now = utc_now_iso()
    session = {
        "schema_version": "1",
        "session_id": f"web_view_{uuid4().hex[:12]}",
        "name": name,
        "active": True,
        "local_only": True,
        "created_at": now,
        "updated_at": now,
        "garden": {
            "garden_root": str(root),
            "garden_target": manifest.target(),
            "name": manifest.name,
        },
        "viewer": {
            "ui": "Local sidebar viewer",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
            "vendor_url": "/vendor/vtk.js",
        },
        "preview_kinds": list(kinds),
        "data_sources": _default_data_sources(),
        "steps": [],
        "active_step_id": None,
    }
    _write_session(root, session)
    return {
        "session": session,
        "session_path": str(_session_path(root)),
        "summary_view": {
            "garden_target": manifest.target(),
            "local_only": True,
            "preview_kinds": list(kinds),
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


def _vtkjs_artifacts(garden_root: Path, manifest: GardenManifest) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for artifact in manifest.artifacts:
        if artifact.get("artifact_type") != VTKJS_ARTIFACT_TYPE:
            continue
        relative_path = artifact.get("path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Garden artifact requires a non-empty path.")
        normalized_path = relative_path.strip().replace("\\", "/")
        absolute_path = (garden_root / normalized_path).resolve()
        absolute_path.relative_to(garden_root)
        if not absolute_path.is_file():
            raise ValueError(f"Garden artifact file was not found: {normalized_path}")
        item = dict(artifact)
        item["path"] = normalized_path
        item["absolute_path"] = str(absolute_path)
        artifacts.append(item)
    artifacts.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("path") or ""),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )
    return artifacts


def _html_svg_artifacts(garden_root: Path, manifest: GardenManifest) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for artifact in manifest.artifacts:
        relative_path = artifact.get("path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            continue
        normalized = relative_path.strip().replace("\\", "/")
        suffix = Path(normalized).suffix.lower()
        atype = artifact.get("artifact_type")
        if atype not in {HTML_ARTIFACT_TYPE, SVG_ARTIFACT_TYPE} and suffix not in {".html", ".htm", ".svg"}:
            continue
        absolute_path = (garden_root / normalized).resolve()
        try:
            absolute_path.relative_to(garden_root)
        except ValueError:
            continue
        if not absolute_path.is_file():
            continue
        kind = "svg" if suffix == ".svg" or atype == SVG_ARTIFACT_TYPE else "html"
        items.append(
            {
                "name": artifact.get("name") or absolute_path.stem,
                "path": normalized,
                "artifact_type": atype or f"visualization_{kind}",
                "format": kind,
                "created_at": artifact.get("created_at"),
                "revision": _hash_file(absolute_path),
                "size_bytes": absolute_path.stat().st_size,
            }
        )
    items.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("path") or ""),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )
    return items


def _viewer_source(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "vtkjs_artifact",
        "artifact_type": VTKJS_ARTIFACT_TYPE,
        "artifact_name": artifact.get("name"),
        "artifact_path": artifact["path"],
        "absolute_path": artifact["absolute_path"],
        "source": artifact.get("source", {}),
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


def _append_preview_step(
    *,
    root: Path,
    session: dict[str, Any],
    preview_kind: str,
    label: str,
    viewer_source: dict[str, Any],
    source_tool: str | None,
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
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
            "artifact_path": viewer_source["artifact_path"],
        },
    }


def record_preview_step(
    *,
    garden_root: str,
    preview_kind: str,
    label: str,
    vtkjs_artifact_path: str | None = None,
    source_tool: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a local preview step backed by a Garden ``.vtkjs`` artifact."""
    root, manifest = _resolve_garden(garden_root)
    session = _resolve_active_session(root, preview_kind)
    artifacts = _vtkjs_artifacts(root, manifest)
    if vtkjs_artifact_path is None:
        if not artifacts:
            raise ValueError(
                "No visualization_vtkjs artifact is registered in this Garden. "
                "Export a VisualizationSet with LB_Export_Visualization_Set first."
            )
        artifact = artifacts[0]
    else:
        requested = vtkjs_artifact_path.strip().replace("\\", "/")
        artifact = next((item for item in artifacts if item.get("path") == requested), None)
        if artifact is None:
            raise ValueError(
                f"Web View previews require a Garden-registered {VTKJS_ARTIFACT_TYPE} "
                f"artifact; got {requested!r}."
            )
    return _append_preview_step(
        root=root,
        session=session,
        preview_kind=preview_kind,
        label=label,
        viewer_source=_viewer_source(artifact),
        source_tool=source_tool,
        summary=summary,
    )


def record_preview_file_step(
    *,
    garden_root: str,
    preview_kind: str,
    label: str,
    vtkjs_file_path: str,
    source_tool: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a local preview step backed by a session-managed ``.vtkjs`` file."""
    root, _ = _resolve_garden(garden_root)
    session = _resolve_active_session(root, preview_kind)
    path = Path(vtkjs_file_path).expanduser().resolve()
    path.relative_to(root)
    if path.suffix.lower() != ".vtkjs":
        raise ValueError(f"Web View preview file must be a .vtkjs file; got {path}")
    if not path.is_file():
        raise ValueError(f"Web View preview file was not found: {path}")
    viewer_source = {
        "kind": "session_vtkjs_file",
        "artifact_type": VTKJS_ARTIFACT_TYPE,
        "artifact_name": path.stem,
        "artifact_path": to_posix_relative(path, root),
        "absolute_path": str(path),
        "source": {"storage": "web_view_session"},
    }
    return _append_preview_step(
        root=root,
        session=session,
        preview_kind=preview_kind,
        label=label,
        viewer_source=viewer_source,
        source_tool=source_tool,
        summary=summary,
    )


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


def get_web_view_config(*, garden_root: str) -> dict[str, Any]:
    """Return the Web View config consumed by the local viewer."""
    root, manifest = _resolve_garden(garden_root)
    session = _read_session(root)
    if session is None:
        session = start_web_view_session(garden_root=str(root))["session"]
    steps = list(session.get("steps", []))
    active_step_id = session.get("active_step_id")
    active_step = next(
        (step for step in steps if step.get("id") == active_step_id),
        steps[-1] if steps else None,
    )
    artifacts = _vtkjs_artifacts(root, manifest)
    latest_artifact = _viewer_source(artifacts[0]) if artifacts else None
    return {
        "schema_version": "1",
        "active": bool(session.get("active", False)),
        "local_only": True,
        "garden": {
            "garden_root": str(root),
            "garden_target": manifest.target(),
            "name": manifest.name,
        },
        "viewer": session.get("viewer", {}),
        "data_sources": session.get("data_sources", _default_data_sources()),
        "preview_kinds": session.get("preview_kinds", list(SUPPORTED_PREVIEW_KINDS)),
        "steps": steps,
        "active_step": active_step,
        "latest_vtkjs_artifact": latest_artifact,
        "html_svg_artifacts": _html_svg_artifacts(root, manifest),
    }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_file(
    *,
    garden_root: Path,
    artifact_path: str,
    allowed_suffixes: tuple[str, ...] = (".vtkjs",),
) -> Path:
    normalized = artifact_path.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Preview artifact path must be a non-empty Garden-relative path.")
    path = (garden_root / normalized).resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("Preview artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() not in allowed_suffixes:
        allowed = ", ".join(allowed_suffixes)
        raise ValueError(f"Preview artifact must end with ({allowed}); got {normalized!r}.")
    if not path.is_file():
        raise ValueError(f"Preview artifact file was not found: {normalized}.")
    return path


def _artifact_from_source(
    *, garden_root: Path, source: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not source:
        return None
    artifact_path = source.get("artifact_path")
    if not isinstance(artifact_path, str) or not artifact_path:
        return None
    path = _resolve_artifact_file(garden_root=garden_root, artifact_path=artifact_path)
    return {
        "name": source.get("artifact_name") or path.stem,
        "path": artifact_path.replace("\\", "/"),
        "kind": source.get("kind") or "vtkjs_artifact",
        "artifact_type": source.get("artifact_type"),
        "source": source.get("source", {}),
        "revision": _hash_file(path),
        "size_bytes": path.stat().st_size,
    }


def _extract_vtkjs_scene_metadata(path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "index.json" not in zf.namelist():
                return None
            index_data = json.loads(zf.read("index.json").decode("utf-8"))
    except Exception:
        return None
    scene = index_data.get("scene") if isinstance(index_data, dict) else None
    if not isinstance(scene, list):
        return None
    scene_items: list[dict[str, Any]] = []
    legends: list[dict[str, Any]] = []
    for entry in scene:
        if not isinstance(entry, dict):
            continue
        prop = entry.get("property") if isinstance(entry.get("property"), dict) else {}
        scene_items.append(
            {
                "name": entry.get("name") or "Layer",
                "hidden": bool(entry.get("hidden", False)),
                "diffuseColor": prop.get("diffuseColor"),
            }
        )
        metadata_list = entry.get("metadata")
        if isinstance(metadata_list, list):
            for meta in metadata_list:
                if not isinstance(meta, dict):
                    continue
                lpar = meta.get("legend_parameters")
                if isinstance(lpar, dict):
                    legends.append(
                        {
                            "layer": entry.get("name"),
                            "unit": meta.get("unit"),
                            "title": lpar.get("title") or meta.get("unit") or entry.get("name"),
                            "min": lpar.get("min"),
                            "max": lpar.get("max"),
                            "decimal_count": lpar.get("decimal_count", 2),
                            "segment_count": lpar.get("segment_count"),
                            "colors": lpar.get("colors"),
                            "continuous_legend": lpar.get("continuous_legend", False),
                        }
                    )
    return {
        "scene_items": scene_items,
        "legends": legends,
        "lookup_tables": index_data.get("lookupTables") or {},
    }


def read_preview_state(*, garden_root: str) -> dict[str, Any]:
    """Return compact state for the local vtk.js preview workbench."""
    root = Path(garden_root).expanduser().resolve()
    config = get_web_view_config(garden_root=str(root))
    steps = list(config.get("steps", []))
    active_step = config.get("active_step")
    artifact = (
        _artifact_from_source(garden_root=root, source=active_step.get("viewer_source"))
        if isinstance(active_step, dict)
        else None
    )
    if artifact is None and isinstance(config.get("latest_vtkjs_artifact"), dict):
        artifact = _artifact_from_source(
            garden_root=root, source=config["latest_vtkjs_artifact"]
        )
    hydrated_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        item = dict(step)
        vs = step.get("viewer_source")
        if isinstance(vs, dict) and isinstance(vs.get("artifact_path"), str):
            try:
                item["artifact"] = _artifact_from_source(garden_root=root, source=vs)
            except Exception:
                item["artifact"] = None
        hydrated_steps.append(item)

    return {
        "schema_version": "1",
        "active": bool(config.get("active", False)),
        "garden": config.get("garden", {}),
        "viewer": {
            "ui": "Local sidebar viewer",
            "library": "vtk.js",
            "mode": "local_url_preview",
            "vendor_url": "/vendor/vtk.js",
            "offline_bundled": VENDOR_VTKJS_PATH.is_file(),
        },
        "poll_interval_ms": POLL_INTERVAL_MS,
        "preview_kinds": config.get("preview_kinds", []),
        "steps": hydrated_steps,
        "active_step": active_step,
        "artifact": artifact,
        "html_svg_artifacts": config.get("html_svg_artifacts", []),
        "report": {
            "status": "ready" if artifact else "waiting_for_vtkjs",
            "message": (
                "A vtk.js preview is available."
                if artifact
                else "No vtk.js preview has been recorded for this Garden yet."
            ),
        },
    }


def read_preview_artifact(
    *,
    garden_root: str,
    artifact_path: str,
    revision: str | None = None,
) -> dict[str, Any]:
    """Return a Garden-local ``.vtkjs`` preview payload for the sidebar viewer."""
    root = Path(garden_root).expanduser().resolve()
    path = _resolve_artifact_file(garden_root=root, artifact_path=artifact_path)
    actual_revision = _hash_file(path)
    if revision and revision != actual_revision:
        raise ValueError(
            "Preview artifact revision changed; refresh preview state before loading it."
        )
    payload: dict[str, Any] = {
        "schema_version": "1",
        "path": artifact_path.replace("\\", "/"),
        "revision": actual_revision,
        "size_bytes": path.stat().st_size,
        "mime_type": "application/vnd.vtkjs",
        "encoding": "base64",
        "payload_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
    }
    scene_meta = _extract_vtkjs_scene_metadata(path)
    if scene_meta is not None:
        payload["scene_metadata"] = scene_meta
    return payload


def read_preview_document(*, garden_root: str, artifact_path: str) -> dict[str, Any]:
    """Read a Garden-local HTML or SVG visualization artifact for inline workbench preview."""
    root = Path(garden_root).expanduser().resolve()
    path = _resolve_artifact_file(
        garden_root=root,
        artifact_path=artifact_path,
        allowed_suffixes=(".html", ".htm", ".svg"),
    )
    mime = (
        "image/svg+xml; charset=utf-8"
        if path.suffix.lower() == ".svg"
        else "text/html; charset=utf-8"
    )
    return {
        "schema_version": "1",
        "path": artifact_path.replace("\\", "/"),
        "mime_type": mime,
        "body": path.read_bytes(),
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
    if not isinstance(result.get("persistence_receipt"), dict):
        return None
    receipt = result["persistence_receipt"]
    for candidate in (result.get("model_target"), receipt.get("model_target")):
        if isinstance(candidate, dict):
            domain = candidate.get("domain")
            if domain in _MODEL_PREVIEW_KINDS and candidate.get("target_type") == f"{domain}_model":
                return candidate
    return None


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
        vis_set.to_vtkjs(output_folder=str(output_dir), file_name=name)
    ).resolve()
    vtkjs_path.relative_to(root)
    return str(vtkjs_path)


def preview_event_garden_root(*, arguments: Any, result: Any) -> str | None:
    """Return a normalized Garden key when a tool call produced a preview-worthy result."""
    visualization_result = isinstance(result, dict) and any(
        isinstance(result.get(key), dict)
        for key in ("visualization_set", "visualization_set_target")
    )
    receipt = result.get("artifact_receipt") if isinstance(result, dict) else None
    vtkjs_receipt = (
        receipt
        if isinstance(receipt, dict) and receipt.get("artifact_type") == VTKJS_ARTIFACT_TYPE
        else None
    )
    model_target = _persisted_model_target(result)
    if not visualization_result and vtkjs_receipt is None and model_target is None:
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
) -> None:
    """Export and record a Web View preview after a significant Code Mode tool."""
    visualization_result = isinstance(result, dict) and any(
        isinstance(result.get(key), dict)
        for key in ("visualization_set", "visualization_set_target")
    )
    receipt = result.get("artifact_receipt") if isinstance(result, dict) else None
    vtkjs_receipt = (
        receipt
        if isinstance(receipt, dict) and receipt.get("artifact_type") == VTKJS_ARTIFACT_TYPE
        else None
    )
    model_target = _persisted_model_target(result)
    if not visualization_result and vtkjs_receipt is None and model_target is None:
        return
    garden_root = _find_garden_root(arguments) or _find_garden_root(result)
    if not garden_root:
        return
    session = read_web_view_session(garden_root=garden_root)
    if not session or not session.get("active", False):
        return

    preview_kind = (
        "analysis_overlay"
        if (visualization_result or vtkjs_receipt is not None)
        else _MODEL_PREVIEW_KINDS.get(str((model_target or {}).get("domain")), "object_edit")
    )
    try:
        if vtkjs_receipt is not None:
            absolute_path = vtkjs_receipt.get("absolute_path")
            if isinstance(absolute_path, str) and absolute_path:
                record_preview_file_step(
                    garden_root=garden_root,
                    preview_kind="analysis_overlay",
                    label="Exported vtk.js preview",
                    vtkjs_file_path=absolute_path,
                    source_tool=tool_name,
                    summary={"artifact_path": vtkjs_receipt.get("artifact_path")},
                )
            return

        preview_name = slugify_name(f"{len(session.get('steps', [])) + 1:04d}_{tool_name}")
        if visualization_result:
            vis_set = result.get("visualization_set")
            if not isinstance(vis_set, dict):
                from garden.visualize.artifacts import load_visualization_set

                vis_set = load_visualization_set(
                    garden_root=garden_root,
                    visualization_set_target=result["visualization_set_target"],
                )
            vtkjs_path = _export_session_vtkjs(
                garden_root=garden_root,
                visualization_set=vis_set,
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
            return

        domain = (model_target or {}).get("domain")
        if domain == "fairyfly":
            from garden.fairyfly.model import fairyfly_model_to_visualization_set

            visualization = fairyfly_model_to_visualization_set(
                garden_root=garden_root,
                model_target=model_target,
                color_by="material",
                include_boundaries=True,
                name=preview_name,
                return_visualization_set=True,
            )
        elif domain == "dragonfly":
            from garden.dragonfly_core.display import dragonfly_model_to_visualization_set

            visualization = dragonfly_model_to_visualization_set(
                garden_root=garden_root,
                model_target=model_target,
                color_by="type",
                include_wireframe=True,
                name=preview_name,
                return_visualization_set=True,
            )
        elif domain == "honeybee":
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


__all__ = [
    "POLL_INTERVAL_MS",
    "SUPPORTED_PREVIEW_KINDS",
    "VENDOR_VTKJS_PATH",
    "fallback_viewer_html",
    "get_web_view_config",
    "maybe_record_code_mode_preview",
    "preview_event_garden_root",
    "read_preview_artifact",
    "read_preview_document",
    "read_preview_state",
    "read_web_view_session",
    "record_preview_failure",
    "record_preview_file_step",
    "record_preview_step",
    "start_preview_url_fallback",
    "start_web_view_session",
    "stop_preview_url_fallback",
    "stop_web_view_session",
]
