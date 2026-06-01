"""Web View session state for FastMCP App vtk.js previews.

This module only coordinates Garden-backed preview state. Geometry and result
visuals must come from Ladybug Tools SDK/MCP artifacts such as `.vtkjs` files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import to_posix_relative


SESSION_RELATIVE_PATH = "tmp/web_view/session.json"
VTKJS_ARTIFACT_TYPE = "visualization_vtkjs"
SUPPORTED_PREVIEW_KINDS = (
    "base_honeybee_model",
    "base_dragonfly_model",
    "object_edit",
    "search_highlight",
    "analysis_overlay",
)
GEOMETRY_POLICY = (
    "Use Ladybug Tools SDK/MCP exported vtkjs artifacts; do not invent geometry."
)


def _resolve_garden_root(garden_root: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    GardenManifest.read(root)
    return root


def _session_path(garden_root: Path) -> Path:
    path = (garden_root / SESSION_RELATIVE_PATH).resolve()
    path.relative_to(garden_root)
    return path


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


def read_web_view_session(*, garden_root: str) -> dict[str, Any] | None:
    """Return the stored Web View session without creating one."""
    root = _resolve_garden_root(garden_root)
    return _read_session(root)


def _default_data_sources() -> dict[str, str]:
    return {
        "primary_geometry": VTKJS_ARTIFACT_TYPE,
        "geometry_policy": GEOMETRY_POLICY,
        "manifest": "garden.json",
        "session": SESSION_RELATIVE_PATH,
    }


def start_web_view_session(
    *,
    garden_root: str,
    name: str = "Local Web View",
    preview_kinds: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Start or replace a Web View session for one Garden."""
    root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    kinds = tuple(preview_kinds or SUPPORTED_PREVIEW_KINDS)
    invalid = [kind for kind in kinds if kind not in SUPPORTED_PREVIEW_KINDS]
    if invalid:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview kind(s): {', '.join(invalid)}. "
            f"Allowed values: {allowed}."
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
            "ui": "FastMCP App",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
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
    root = _resolve_garden_root(garden_root)
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


def _normalize_relative_path(value: str) -> str:
    return value.strip().replace("\\", "/")


def _artifact_with_absolute_path(
    *,
    garden_root: Path,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    relative_path = artifact.get("path")
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("Garden artifact requires a non-empty path.")
    normalized_path = _normalize_relative_path(relative_path)
    absolute_path = (garden_root / normalized_path).resolve()
    absolute_path.relative_to(garden_root)
    if not absolute_path.is_file():
        raise ValueError(f"Garden artifact file was not found: {normalized_path}")
    item = dict(artifact)
    item["path"] = normalized_path
    item["absolute_path"] = str(absolute_path)
    return item


def _vtkjs_artifacts(garden_root: Path) -> list[dict[str, Any]]:
    manifest = GardenManifest.read(garden_root)
    artifacts = [
        _artifact_with_absolute_path(garden_root=garden_root, artifact=artifact)
        for artifact in manifest.artifacts
        if artifact.get("artifact_type") == VTKJS_ARTIFACT_TYPE
    ]
    artifacts.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("path") or ""),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )
    return artifacts


def _resolve_vtkjs_artifact(
    *,
    garden_root: Path,
    vtkjs_artifact_path: str | None,
) -> dict[str, Any]:
    artifacts = _vtkjs_artifacts(garden_root)
    if vtkjs_artifact_path is None:
        if not artifacts:
            raise ValueError(
                "No visualization_vtkjs artifact is registered in this Garden. "
                "Export a VisualizationSet with visualization_set_to_vtkjs first."
            )
        return artifacts[0]

    requested = _normalize_relative_path(vtkjs_artifact_path)
    for artifact in artifacts:
        if artifact.get("path") == requested:
            return artifact
    raise ValueError(
        f"Web View previews require a Garden-registered {VTKJS_ARTIFACT_TYPE} "
        f"artifact; got {requested!r}."
    )


def _viewer_source(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "vtkjs_artifact",
        "artifact_type": VTKJS_ARTIFACT_TYPE,
        "artifact_name": artifact.get("name"),
        "artifact_path": artifact["path"],
        "absolute_path": artifact["absolute_path"],
        "source": artifact.get("source", {}),
    }


def _session_file_viewer_source(
    *,
    garden_root: Path,
    vtkjs_file_path: str,
) -> dict[str, Any]:
    path = Path(vtkjs_file_path).expanduser().resolve()
    path.relative_to(garden_root)
    if path.suffix.lower() != ".vtkjs":
        raise ValueError(f"Web View preview file must be a .vtkjs file; got {path}")
    if not path.is_file():
        raise ValueError(f"Web View preview file was not found: {path}")
    relative_path = to_posix_relative(path, garden_root)
    return {
        "kind": "session_vtkjs_file",
        "artifact_type": VTKJS_ARTIFACT_TYPE,
        "artifact_name": path.stem,
        "artifact_path": relative_path,
        "absolute_path": str(path),
        "source": {"storage": "web_view_session"},
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
    """Append a local preview step backed by a Garden `.vtkjs` artifact."""
    if preview_kind not in SUPPORTED_PREVIEW_KINDS:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview_kind: {preview_kind!r}. Allowed values: {allowed}."
        )

    root = _resolve_garden_root(garden_root)
    session = _read_session(root)
    if session is None or not session.get("active", False):
        session = start_web_view_session(garden_root=str(root))["session"]
    if preview_kind not in session.get("preview_kinds", []):
        raise ValueError(
            f"Preview kind {preview_kind!r} is not enabled for this Web View session."
        )

    artifact = _resolve_vtkjs_artifact(
        garden_root=root,
        vtkjs_artifact_path=vtkjs_artifact_path,
    )
    step = {
        "id": f"step_{len(session.get('steps', [])) + 1:04d}",
        "preview_kind": preview_kind,
        "label": label,
        "created_at": utc_now_iso(),
        "source_tool": source_tool,
        "summary": summary or {},
        "viewer_source": _viewer_source(artifact),
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
            "artifact_path": artifact["path"],
        },
    }


def record_preview_file_step(
    *,
    garden_root: str,
    preview_kind: str,
    label: str,
    vtkjs_file_path: str,
    source_tool: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a local preview step backed by a session-managed `.vtkjs` file."""
    if preview_kind not in SUPPORTED_PREVIEW_KINDS:
        allowed = ", ".join(SUPPORTED_PREVIEW_KINDS)
        raise ValueError(
            f"Unsupported preview_kind: {preview_kind!r}. Allowed values: {allowed}."
        )

    root = _resolve_garden_root(garden_root)
    session = _read_session(root)
    if session is None or not session.get("active", False):
        session = start_web_view_session(garden_root=str(root))["session"]
    if preview_kind not in session.get("preview_kinds", []):
        raise ValueError(
            f"Preview kind {preview_kind!r} is not enabled for this Web View session."
        )

    viewer_source = _session_file_viewer_source(
        garden_root=root,
        vtkjs_file_path=vtkjs_file_path,
    )
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
    root = _resolve_garden_root(garden_root)
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
    """Return the Web View config that the FastMCP App can consume."""
    root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    session = _read_session(root)
    if session is None:
        session = start_web_view_session(garden_root=str(root))["session"]

    steps = list(session.get("steps", []))
    active_step_id = session.get("active_step_id")
    active_step = next(
        (step for step in steps if step.get("id") == active_step_id),
        steps[-1] if steps else None,
    )
    latest_artifact = None
    artifacts = _vtkjs_artifacts(root)
    if artifacts:
        latest_artifact = _viewer_source(artifacts[0])

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
    }
