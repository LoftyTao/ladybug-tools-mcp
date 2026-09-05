"""Garden-backed data access for the local vtk.js preview viewer."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

from web_view.session import get_web_view_config

POLL_INTERVAL_MS = 1500


def _resolve_garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_file(*, garden_root: Path, artifact_path: str) -> Path:
    normalized = artifact_path.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Preview artifact path must be a non-empty Garden-relative path.")
    path = (garden_root / normalized).resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("Preview artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() != ".vtkjs":
        raise ValueError(f"Preview artifact must be a .vtkjs file; got {normalized!r}.")
    if not path.is_file():
        raise ValueError(f"Preview artifact file was not found: {normalized}.")
    return path


def _artifact_from_source(*, garden_root: Path, source: dict[str, Any] | None) -> dict[str, Any] | None:
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


def _active_artifact(config: dict[str, Any], garden_root: Path) -> dict[str, Any] | None:
    active_step = config.get("active_step")
    if isinstance(active_step, dict):
        artifact = _artifact_from_source(garden_root=garden_root, source=active_step.get("viewer_source"))
        if artifact:
            return artifact
    latest = config.get("latest_vtkjs_artifact")
    if isinstance(latest, dict):
        return _artifact_from_source(garden_root=garden_root, source=latest)
    return None


def read_preview_state(*, garden_root: str) -> dict[str, Any]:
    """Return compact state for the local vtk.js preview viewer."""
    root = _resolve_garden_root(garden_root)
    config = get_web_view_config(garden_root=str(root))
    artifact = _active_artifact(config, root)
    return {
        "schema_version": "1",
        "active": bool(config.get("active", False)),
        "garden": config.get("garden", {}),
        "viewer": {"ui": "Local sidebar viewer", "library": "vtk.js", "mode": "local_url_preview"},
        "poll_interval_ms": POLL_INTERVAL_MS,
        "preview_kinds": config.get("preview_kinds", []),
        "active_step": config.get("active_step"),
        "artifact": artifact,
        "report": {"status": "ready" if artifact else "waiting_for_vtkjs", "message": "A vtk.js preview is available." if artifact else "No vtk.js preview has been recorded for this Garden yet."},
    }


def read_preview_artifact(*, garden_root: str, artifact_path: str, revision: str | None = None) -> dict[str, Any]:
    """Return a Garden-local `.vtkjs` preview payload for the sidebar viewer."""
    root = _resolve_garden_root(garden_root)
    path = _resolve_artifact_file(garden_root=root, artifact_path=artifact_path)
    actual_revision = _hash_file(path)
    if revision and revision != actual_revision:
        raise ValueError("Preview artifact revision changed; refresh preview state before loading it.")
    return {
        "schema_version": "1",
        "path": artifact_path.replace("\\", "/"),
        "revision": actual_revision,
        "size_bytes": path.stat().st_size,
        "mime_type": "application/vnd.vtkjs",
        "encoding": "base64",
        "payload_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
    }
