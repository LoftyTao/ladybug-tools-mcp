"""Atomic Garden protocol state for Rune 3D viewer and MCP coordination."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from garden.manifest import GardenManifest, garden_lock, utc_now_iso, write_json_file
from garden.paths import resolve_contained_path, slugify_name
from ladybug_tools_mcp.contracts import BuildingObjectTargetRef

SCHEMA_VERSION = "1"
WEB_VIEW_DIR_RELATIVE_PATH = "tmp/web_view"
PRESENT_RELATIVE_PATH = "tmp/web_view/present.json"
INTERACTION_STATE_RELATIVE_PATH = "tmp/web_view/interaction_state.json"
CAPTURE_REQUEST_RELATIVE_PATH = "tmp/web_view/capture_request.json"
CAPTURES_DIR_RELATIVE_PATH = "tmp/web_view/captures"

SUPPORTED_VIEW_TYPES = (
    "model",
    "highlight",
    "validation",
    "analysis",
    "document",
    "diff",
    "split",
)
SUPPORTED_COLOR_BY = (
    "type",
    "boundary_condition",
    "story",
    "zone",
    "program_type",
    "construction_set",
    "hvac",
)
SUPPORTED_ISOLATION_MODES = ("highlight", "ghost_context", "isolate")
SUPPORTED_CAMERA_PRESETS = (
    "keep",
    "fit",
    "fit_highlights",
    "axon",
    "top",
    "north",
    "south",
    "east",
    "west",
)
SUPPORTED_SECTION_AXES = ("x", "y", "z")
SUPPORTED_ANNOTATION_STATUSES = ("open", "resolved")

_CAMERA_ALIASES = {
    "front": "south",
    "back": "north",
    "left": "west",
    "right": "east",
    "ne": "axon",
    "nw": "axon",
    "se": "axon",
    "sw": "axon",
}
_VTK_VIEW_MAP = {
    "keep": "NE",
    "fit": "NE",
    "fit_highlights": "NE",
    "axon": "NE",
    "top": "Top",
    "north": "Back",
    "south": "Front",
    "east": "Right",
    "west": "Left",
    "front": "Front",
    "back": "Back",
    "left": "Left",
    "right": "Right",
    "ne": "NE",
    "nw": "NW",
    "se": "SE",
    "sw": "SW",
}


def _resolve_garden(garden_root: str | Path) -> tuple[Path, GardenManifest]:
    root = Path(garden_root).expanduser().resolve()
    return root, GardenManifest.read(root)


def present_file_path(garden_root: Path) -> Path:
    """Return the contained ``tmp/web_view/present.json`` path."""
    return resolve_contained_path(garden_root, PRESENT_RELATIVE_PATH, label="Web View present")


def interaction_state_file_path(garden_root: Path) -> Path:
    """Return the contained ``tmp/web_view/interaction_state.json`` path."""
    return resolve_contained_path(
        garden_root, INTERACTION_STATE_RELATIVE_PATH, label="Web View interaction state"
    )


def capture_request_file_path(garden_root: Path) -> Path:
    """Return the contained ``tmp/web_view/capture_request.json`` path."""
    return resolve_contained_path(
        garden_root, CAPTURE_REQUEST_RELATIVE_PATH, label="Web View capture request"
    )


def capture_output_paths(garden_root: Path, request_id: str) -> tuple[Path, Path]:
    """Return contained ``captures/<request_id>.png`` and ``.json`` paths."""
    clean_id = str(request_id or "").strip()
    if not clean_id:
        raise ValueError("capture request_id must be a non-empty string.")
    png_path = resolve_contained_path(
        garden_root, f"{CAPTURES_DIR_RELATIVE_PATH}/{clean_id}.png", label="Web View capture PNG"
    )
    receipt_path = resolve_contained_path(
        garden_root,
        f"{CAPTURES_DIR_RELATIVE_PATH}/{clean_id}.json",
        label="Web View capture receipt",
    )
    return png_path, receipt_path


def _read_json_dict(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path.name}.")
    return data


def _read_json_dict_safe(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return _read_json_dict(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _normalize_enum(value: Any, allowed: tuple[str, ...], *, field_name: str) -> str:
    text = str(value or "").strip().lower()
    if text not in allowed:
        raise ValueError(f"Unsupported {field_name} {value!r}. Allowed values: {', '.join(allowed)}.")
    return text


def _normalize_vec3(value: Any, *, field_name: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{field_name} must be a 3-element [x, y, z] list.")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{field_name} coordinates must be numeric.")
        result.append(float(item))
    return result


def normalize_camera_spec(camera: Any, *, default: str | dict[str, Any] = "keep") -> str | dict[str, Any]:
    """Validate and normalize a camera preset string or explicit camera dictionary."""
    if camera is None:
        return default
    if isinstance(camera, str):
        key = camera.strip().lower()
        key = _CAMERA_ALIASES.get(key, key)
        if key not in SUPPORTED_CAMERA_PRESETS:
            allowed = ", ".join(SUPPORTED_CAMERA_PRESETS)
            raise ValueError(f"Unsupported camera preset {camera!r}. Allowed: {allowed}, or camera dict.")
        return key
    if isinstance(camera, dict):
        normalized: dict[str, Any] = {
            "position": _normalize_vec3(camera.get("position"), field_name="camera.position"),
            "target": _normalize_vec3(camera.get("target"), field_name="camera.target"),
        }
        if camera.get("up") is not None:
            normalized["up"] = _normalize_vec3(camera.get("up"), field_name="camera.up")
        if "orthographic" in camera and camera.get("orthographic") is not None:
            normalized["orthographic"] = bool(camera["orthographic"])
        return normalized
    raise ValueError("camera must be a camera preset string or {position, target, ...} dict.")


def map_view_to_vtk(view: str | dict[str, Any]) -> str | dict[str, Any]:
    """Map a viewer preset or camera/Plane dict to a view compatible with ``_render_png_vtk``."""
    if isinstance(view, dict):
        if "origin" in view or ("o" in view and "n" in view) or view.get("type") == "Plane":
            return dict(view)
        pos = view.get("position")
        tgt = view.get("target")
        if isinstance(pos, (list, tuple)) and isinstance(tgt, (list, tuple)) and len(pos) == 3 and len(tgt) == 3:
            dx = float(pos[0]) - float(tgt[0])
            dy = float(pos[1]) - float(tgt[1])
            dz = float(pos[2]) - float(tgt[2])
            if abs(dz) >= max(abs(dx), abs(dy)) * 2.0 and dz > 0:
                return "Top"
            if abs(dx) >= abs(dy) * 2.0:
                return "Right" if dx >= 0 else "Left"
            if abs(dy) >= abs(dx) * 2.0:
                return "Back" if dy >= 0 else "Front"
            return "NE"
        return "NE"
    key = str(view or "axon").strip().lower()
    return _VTK_VIEW_MAP.get(key, "NE")


def normalize_section_spec(section: Any) -> dict[str, Any] | None:
    """Validate and normalize a section cut specification."""
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("section must be a dictionary or None.")
    axis = _normalize_enum(section.get("axis", "z"), SUPPORTED_SECTION_AXES, field_name="section.axis")
    raw_value = section.get("value")
    if raw_value is not None:
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise ValueError("section.value must be a number or None.")
        value: float | None = float(raw_value)
    else:
        value = None
    story = section.get("story")
    if story is not None and not isinstance(story, str):
        raise ValueError("section.story must be a string or None.")
    return {
        "enabled": bool(section.get("enabled", True)),
        "axis": axis,
        "value": value,
        "story": story,
        "invert": bool(section.get("invert", False)),
    }


def _normalize_target_ref(item: Any, *, default_garden_id: str | None = None) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        raw = item.model_dump(exclude_none=True)
    elif isinstance(item, dict):
        raw = dict(item)
    else:
        raise ValueError("Target reference must be a dictionary.")
    if default_garden_id and not raw.get("garden_id"):
        raw["garden_id"] = default_garden_id
    if not raw.get("target_type") and raw.get("object_type") and raw.get("object_identifier"):
        raw["target_type"] = "honeybee_object"
    if not raw.get("domain") and raw.get("target_type") == "honeybee_object":
        raw["domain"] = "honeybee"
    validated = BuildingObjectTargetRef.model_validate(raw)
    return validated.model_dump(exclude_none=True)


def _normalize_dict_list(items: Any, *, field_name: str) -> list[dict[str, Any]]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError(f"{field_name} must be a list of dictionaries.")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if hasattr(item, "model_dump"):
            normalized.append(item.model_dump(exclude_none=True))
        elif isinstance(item, dict):
            normalized.append(dict(item))
        else:
            raise ValueError(f"{field_name}[{index}] must be a dictionary.")
    return normalized


def _export_dragonfly_preview_hbjson(root: Path, df_target: dict[str, Any]) -> str | None:
    """Convert a Dragonfly model into a Garden-contained preview HBJSON for Rune."""
    from garden.dragonfly_core.model_io import load_dragonfly_model

    df_model = load_dragonfly_model(root, df_target)
    if not getattr(df_model, "buildings", None):
        return None
    hb_models = df_model.to_honeybee(object_per_model="District", use_multiplier=False)
    if not hb_models:
        return None
    model_id = str(
        df_target.get("model_identifier") or getattr(df_model, "identifier", None) or "dragonfly"
    )
    rel_path = f"{WEB_VIEW_DIR_RELATIVE_PATH}/models/{slugify_name(model_id)}.hbjson"
    preview_path = resolve_contained_path(root, rel_path, label="Dragonfly preview HBJSON")
    write_json_file(preview_path, hb_models[0].to_dict(), ensure_ascii=False)
    return rel_path


def _resolve_present_model(
    root: Path,
    manifest: GardenManifest,
    model_target: dict[str, Any] | None = None,
    *,
    existing_model_path: str | None = None,
    refresh_derived: bool = True,
) -> tuple[str | None, dict[str, Any] | None]:
    if model_target is not None:
        raw_target = (
            model_target.model_dump(exclude_none=True)
            if hasattr(model_target, "model_dump")
            else dict(model_target)
        )
        domain = str(raw_target.get("domain") or "").strip().lower()
        target_type = str(raw_target.get("target_type") or "").strip().lower()
        if not domain and target_type.endswith("_model"):
            domain = target_type[: -len("_model")]
        if domain in {"", "honeybee"}:
            from garden.honeybee_core.model_io import resolve_model_target

            _, resolved = resolve_model_target(root, raw_target)
            return resolved.get("path"), resolved
        if domain == "dragonfly":
            from garden.dragonfly_core.model_io import resolve_model_target as resolve_df_target

            _, resolved = resolve_df_target(root, raw_target)
            if (
                not refresh_derived
                and isinstance(existing_model_path, str)
                and existing_model_path.endswith(".hbjson")
                and (root / existing_model_path).is_file()
            ):
                return existing_model_path, resolved
            return _export_dragonfly_preview_hbjson(root, resolved), resolved
        model_id = raw_target.get("model_identifier") or raw_target.get("id")
        for candidate in manifest.models:
            if (
                candidate.get("domain") == domain
                and (not model_id or candidate.get("model_identifier") == model_id)
            ):
                return candidate.get("path"), dict(candidate)
        return raw_target.get("path"), raw_target

    base = manifest.base_honeybee_model
    if isinstance(base, dict):
        path_val = base.get("path")
        if isinstance(path_val, str) and path_val.strip():
            return path_val.strip().replace("\\", "/"), dict(base)
        return None, dict(base)
    base_df = manifest.base_dragonfly_model
    if isinstance(base_df, dict):
        if (
            not refresh_derived
            and isinstance(existing_model_path, str)
            and existing_model_path.endswith(".hbjson")
            and (root / existing_model_path).is_file()
        ):
            return existing_model_path, dict(base_df)
        return _export_dragonfly_preview_hbjson(root, dict(base_df)), dict(base_df)
    return None, None


def read_present(garden_root: str | Path) -> dict[str, Any] | None:
    """Read ``tmp/web_view/present.json`` if it exists."""
    root, _ = _resolve_garden(garden_root)
    return _read_json_dict(present_file_path(root))


def write_present(
    *,
    garden_root: str | Path,
    view_type: str = "model",
    model_target: dict[str, Any] | None = None,
    color_by: str = "type",
    highlight_targets: list[dict[str, Any]] | None = None,
    isolation_mode: str = "highlight",
    validation_issues: list[dict[str, Any]] | None = None,
    camera: str | dict[str, Any] = "fit",
    section: dict[str, Any] | None = None,
    callouts: list[dict[str, Any]] | None = None,
    title: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Atomically write ``tmp/web_view/present.json`` with a monotonic revision."""
    root, manifest = _resolve_garden(garden_root)
    norm_view_type = _normalize_enum(view_type, SUPPORTED_VIEW_TYPES, field_name="view_type")
    norm_color_by = _normalize_enum(color_by, SUPPORTED_COLOR_BY, field_name="color_by")
    norm_isolation = _normalize_enum(isolation_mode, SUPPORTED_ISOLATION_MODES, field_name="isolation_mode")
    norm_camera = normalize_camera_spec(camera, default="fit")
    norm_section = normalize_section_spec(section)
    norm_highlights = [
        _normalize_target_ref(item, default_garden_id=manifest.garden_id)
        for item in _normalize_dict_list(highlight_targets, field_name="highlight_targets")
    ]
    norm_issues = _normalize_dict_list(validation_issues, field_name="validation_issues")
    norm_callouts = _normalize_dict_list(callouts, field_name="callouts")

    with garden_lock(root):
        manifest = GardenManifest.read(root)
        path = present_file_path(root)
        existing = _read_json_dict(path) or {}
        prev_rev = existing.get("revision")
        revision = (prev_rev if isinstance(prev_rev, int) and not isinstance(prev_rev, bool) and prev_rev >= 0 else 0) + 1
        model_path, resolved_model_target = _resolve_present_model(root, manifest, model_target)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "revision": revision,
            "garden_root": str(root),
            "garden_id": manifest.garden_id,
            "view_type": norm_view_type,
            "model_path": model_path,
            "model_target": resolved_model_target,
            "color_by": norm_color_by,
            "highlight_targets": norm_highlights,
            "isolation_mode": norm_isolation,
            "validation_issues": norm_issues,
            "camera": norm_camera,
            "section": norm_section,
            "callouts": norm_callouts,
            "title": title,
            "note": note,
            "updated_at": utc_now_iso(),
        }
        write_json_file(path, payload, ensure_ascii=False)
        return payload


def update_present(
    *,
    garden_root: str | Path,
    view_type: str | None = None,
    model_target: dict[str, Any] | None = None,
    color_by: str | None = None,
    highlight_targets: list[dict[str, Any]] | None = None,
    isolation_mode: str | None = None,
    validation_issues: list[dict[str, Any]] | None = None,
    camera: str | dict[str, Any] | None = None,
    section: dict[str, Any] | None = None,
    callouts: list[dict[str, Any]] | None = None,
    title: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Atomically patch ``tmp/web_view/present.json``, preserving unspecified fields."""
    root, _ = _resolve_garden(garden_root)
    with garden_lock(root):
        manifest = GardenManifest.read(root)
        path = present_file_path(root)
        existing = _read_json_dict(path)
        has_existing = existing is not None
        base = existing or {}

        effective_model_target = model_target if model_target is not None else base.get("model_target")
        model_path, resolved_model_target = _resolve_present_model(
            root,
            manifest,
            effective_model_target,
            existing_model_path=base.get("model_path"),
            refresh_derived=(model_target is not None),
        )
        if model_path is None and model_target is None and (
            manifest.base_honeybee_model is not None or manifest.base_dragonfly_model is not None
        ):
            model_path, resolved_model_target = _resolve_present_model(
                root,
                manifest,
                None,
                existing_model_path=base.get("model_path"),
                refresh_derived=True,
            )

        eff_view_type = _normalize_enum(
            view_type if view_type is not None else base.get("view_type", "model"),
            SUPPORTED_VIEW_TYPES,
            field_name="view_type",
        )
        eff_color_by = _normalize_enum(
            color_by if color_by is not None else base.get("color_by", "type"),
            SUPPORTED_COLOR_BY,
            field_name="color_by",
        )
        eff_isolation = _normalize_enum(
            isolation_mode if isolation_mode is not None else base.get("isolation_mode", "highlight"),
            SUPPORTED_ISOLATION_MODES,
            field_name="isolation_mode",
        )
        if highlight_targets is not None:
            eff_highlights = [
                _normalize_target_ref(item, default_garden_id=manifest.garden_id)
                for item in _normalize_dict_list(highlight_targets, field_name="highlight_targets")
            ]
        elif view_type == "model" and base.get("view_type") == "highlight":
            eff_highlights = []
        else:
            eff_highlights = [
                _normalize_target_ref(item, default_garden_id=manifest.garden_id)
                for item in _normalize_dict_list(base.get("highlight_targets"), field_name="highlight_targets")
            ]

        if validation_issues is not None:
            eff_issues = _normalize_dict_list(validation_issues, field_name="validation_issues")
        elif view_type == "model" and base.get("view_type") == "validation":
            eff_issues = []
        else:
            eff_issues = _normalize_dict_list(
                base.get("validation_issues"),
                field_name="validation_issues",
            )
        eff_callouts = _normalize_dict_list(
            callouts if callouts is not None else base.get("callouts"),
            field_name="callouts",
        )
        eff_camera = normalize_camera_spec(
            camera,
            default="keep" if has_existing else "fit",
        )
        eff_section = normalize_section_spec(section) if section is not None else base.get("section")
        eff_title = title if title is not None else base.get("title")
        eff_note = note if note is not None else base.get("note")

        prev_rev = base.get("revision")
        revision = (
            prev_rev if isinstance(prev_rev, int) and not isinstance(prev_rev, bool) and prev_rev >= 0 else 0
        ) + 1
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "revision": revision,
            "garden_root": str(root),
            "garden_id": manifest.garden_id,
            "view_type": eff_view_type,
            "model_path": model_path,
            "model_target": resolved_model_target,
            "color_by": eff_color_by,
            "highlight_targets": eff_highlights,
            "isolation_mode": eff_isolation,
            "validation_issues": eff_issues,
            "camera": eff_camera,
            "section": eff_section,
            "callouts": eff_callouts,
            "title": eff_title,
            "note": eff_note,
            "updated_at": utc_now_iso(),
        }
        write_json_file(path, payload, ensure_ascii=False)
        return payload


def ensure_initial_present(
    *,
    garden_root: str | Path,
    force_reset: bool = False,
    title: str | None = None,
) -> dict[str, Any]:
    """Ensure ``tmp/web_view/present.json`` is populated from ``manifest.base_honeybee_model`` if available."""
    root, _ = _resolve_garden(garden_root)
    with garden_lock(root):
        manifest = GardenManifest.read(root)
        path = present_file_path(root)
        existing = _read_json_dict(path)
        model_path, model_target = _resolve_present_model(root, manifest, None)
        if existing is not None and not force_reset:
            existing_model_path = existing.get("model_path")
            if model_path is not None and existing_model_path != model_path:
                return update_present(
                    garden_root=root,
                    model_target=model_target,
                    camera="fit" if existing_model_path is None else "keep",
                    title=existing.get("title") or title or manifest.name,
                )
            return existing
        return write_present(
            garden_root=root,
            view_type="model",
            model_target=model_target,
            color_by="type",
            highlight_targets=[],
            isolation_mode="highlight",
            validation_issues=[],
            camera="fit",
            section=None,
            callouts=[],
            title=title or manifest.name,
            note=None,
        )


def _default_interaction_state(
    manifest: GardenManifest,
    *,
    model_path: str | None = None,
) -> dict[str, Any]:
    resolved_model_path = model_path
    if resolved_model_path is None and isinstance(manifest.base_honeybee_model, dict):
        raw = manifest.base_honeybee_model.get("path")
        if isinstance(raw, str) and raw.strip():
            resolved_model_path = raw.strip().replace("\\", "/")
    return {
        "schema_version": SCHEMA_VERSION,
        "garden_id": manifest.garden_id,
        "selected_targets": [],
        "annotations": [],
        "viewport": {
            "model_path": resolved_model_path,
            "color_by": "type",
            "camera": "fit",
            "section": None,
        },
        "pending_intents": [],
        "viewer_pid": None,
        "updated_at": utc_now_iso(),
    }


def _normalize_annotation(entry: dict[str, Any], *, default_garden_id: str, now: str) -> dict[str, Any]:
    ann = dict(entry)
    ann_id = str(ann.get("id") or f"ann_{uuid4().hex[:8]}").strip()
    status = _normalize_enum(ann.get("status", "open"), SUPPORTED_ANNOTATION_STATUSES, field_name="annotation.status")
    target = ann.get("target")
    if isinstance(target, dict):
        target = _normalize_target_ref(target, default_garden_id=default_garden_id)
    return {
        "id": ann_id,
        "status": status,
        "target": target,
        "world_point": ann.get("world_point"),
        "comment": ann.get("comment", ""),
        "resolution_note": ann.get("resolution_note"),
        "camera_bookmark": ann.get("camera_bookmark"),
        "created_at": ann.get("created_at") or now,
        "updated_at": ann.get("updated_at") or now,
    }


def read_interaction_state(garden_root: str | Path) -> dict[str, Any]:
    """Read ``tmp/web_view/interaction_state.json`` or return an empty default state."""
    root, manifest = _resolve_garden(garden_root)
    path = interaction_state_file_path(root)
    data = _read_json_dict(path)
    if data is None:
        return _default_interaction_state(manifest)
    now = utc_now_iso()
    selected = [
        _normalize_target_ref(item, default_garden_id=manifest.garden_id)
        for item in _normalize_dict_list(data.get("selected_targets"), field_name="selected_targets")
    ]
    annotations = [
        _normalize_annotation(item, default_garden_id=manifest.garden_id, now=now)
        for item in _normalize_dict_list(data.get("annotations"), field_name="annotations")
    ]
    viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {}
    pending_intents = _normalize_dict_list(data.get("pending_intents"), field_name="pending_intents")
    viewer_pid = data.get("viewer_pid")
    if isinstance(viewer_pid, bool) or (viewer_pid is not None and not isinstance(viewer_pid, int)):
        viewer_pid = None
    return {
        "schema_version": str(data.get("schema_version") or SCHEMA_VERSION),
        "garden_id": str(data.get("garden_id") or manifest.garden_id),
        "selected_targets": selected,
        "annotations": annotations,
        "viewport": {
            "model_path": viewport.get("model_path"),
            "color_by": viewport.get("color_by", "type"),
            "camera": viewport.get("camera", "fit"),
            "section": viewport.get("section"),
        },
        "pending_intents": pending_intents,
        "viewer_pid": viewer_pid,
        "updated_at": str(data.get("updated_at") or now),
    }


def write_interaction_state(garden_root: str | Path, state: dict[str, Any]) -> dict[str, Any]:
    """Atomically validate and write ``tmp/web_view/interaction_state.json``."""
    root, manifest = _resolve_garden(garden_root)
    now = utc_now_iso()
    selected = [
        _normalize_target_ref(item, default_garden_id=manifest.garden_id)
        for item in _normalize_dict_list(state.get("selected_targets"), field_name="selected_targets")
    ]
    annotations = [
        _normalize_annotation(item, default_garden_id=manifest.garden_id, now=now)
        for item in _normalize_dict_list(state.get("annotations"), field_name="annotations")
    ]
    viewport = state.get("viewport") if isinstance(state.get("viewport"), dict) else {}
    pending_intents = _normalize_dict_list(state.get("pending_intents"), field_name="pending_intents")
    viewer_pid = state.get("viewer_pid")
    if isinstance(viewer_pid, bool) or (viewer_pid is not None and not isinstance(viewer_pid, int)):
        raise ValueError("interaction_state.viewer_pid must be an integer or None.")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "garden_id": str(state.get("garden_id") or manifest.garden_id),
        "selected_targets": selected,
        "annotations": annotations,
        "viewport": {
            "model_path": viewport.get("model_path"),
            "color_by": viewport.get("color_by", "type"),
            "camera": viewport.get("camera", "fit"),
            "section": viewport.get("section"),
        },
        "pending_intents": pending_intents,
        "viewer_pid": viewer_pid,
        "updated_at": now,
    }
    with garden_lock(root):
        write_json_file(interaction_state_file_path(root), payload, ensure_ascii=False)
    return payload


def ensure_initial_interaction_state(
    garden_root: str | Path,
    *,
    model_path: str | None = None,
) -> dict[str, Any]:
    """Ensure ``tmp/web_view/interaction_state.json`` exists on disk."""
    root, _ = _resolve_garden(garden_root)
    with garden_lock(root):
        manifest = GardenManifest.read(root)
        path = interaction_state_file_path(root)
        if not path.is_file():
            payload = _default_interaction_state(manifest, model_path=model_path)
            write_json_file(path, payload, ensure_ascii=False)
            return payload
        state = read_interaction_state(root)
        if model_path is not None and state["viewport"].get("model_path") is None:
            state["viewport"]["model_path"] = model_path
            return write_interaction_state(root, state)
        return state


def get_web_view_context(
    *,
    garden_root: str | Path,
    only_open_annotations: bool = True,
    resolve_annotations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read viewer interaction context and atomically resolve requested annotations."""
    root, _ = _resolve_garden(garden_root)
    resolved_ids: list[str] = []
    with garden_lock(root):
        state = read_interaction_state(root)
        if resolve_annotations:
            if not isinstance(resolve_annotations, list):
                raise ValueError("resolve_annotations must be a list of {id, resolution_note} dicts.")
            by_id = {str(ann["id"]): ann for ann in state["annotations"]}
            now = utc_now_iso()
            for index, req in enumerate(resolve_annotations):
                if not isinstance(req, dict):
                    raise ValueError(f"resolve_annotations[{index}] must be a dictionary.")
                ann_id = str(req.get("id") or req.get("annotation_id") or "").strip()
                if not ann_id:
                    raise ValueError(f"resolve_annotations[{index}] requires a non-empty 'id'.")
                if ann_id not in by_id:
                    raise ValueError(f"Annotation not found in interaction_state.json: {ann_id!r}.")
                ann = by_id[ann_id]
                ann["status"] = "resolved"
                note = req.get("resolution_note")
                if note is None:
                    note = req.get("note")
                if note is not None:
                    ann["resolution_note"] = str(note)
                ann["updated_at"] = now
                resolved_ids.append(ann_id)
            state = write_interaction_state(root, state)

    all_annotations = state["annotations"]
    open_count = sum(1 for ann in all_annotations if ann.get("status") == "open")
    resolved_count = sum(1 for ann in all_annotations if ann.get("status") == "resolved")
    filtered_annotations = (
        [ann for ann in all_annotations if ann.get("status") == "open"]
        if only_open_annotations
        else list(all_annotations)
    )
    return {
        "schema_version": state["schema_version"],
        "garden_id": state["garden_id"],
        "garden_root": str(root),
        "selected_targets": state["selected_targets"],
        "annotations": filtered_annotations,
        "open_annotation_count": open_count,
        "resolved_annotation_count": resolved_count,
        "resolved_ids": resolved_ids,
        "viewport": state["viewport"],
        "pending_intents": state["pending_intents"],
        "viewer_pid": state["viewer_pid"],
        "updated_at": state["updated_at"],
    }


def write_capture_request(
    *,
    garden_root: str | Path,
    view: str | dict[str, Any] = "fit",
    width: int = 1280,
    height: int = 720,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Atomically write ``tmp/web_view/capture_request.json`` for the live Rune viewer."""
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError("capture width must be a positive integer.")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ValueError("capture height must be a positive integer.")

    root, manifest = _resolve_garden(garden_root)
    req_id = (request_id or f"cap_{uuid4().hex[:12]}").strip()
    png_path, receipt_path = capture_output_paths(root, req_id)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(view, dict) and ("origin" in view or ("o" in view and "n" in view)):
        normalized_view: str | dict[str, Any] = dict(view)
    else:
        normalized_view = normalize_camera_spec(view, default="fit")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "request_id": req_id,
        "garden_root": str(root),
        "garden_id": manifest.garden_id,
        "view": normalized_view,
        "width": width,
        "height": height,
        "output_png_path": png_path.relative_to(root).as_posix(),
        "receipt_path": receipt_path.relative_to(root).as_posix(),
        "requested_at": utc_now_iso(),
    }
    with garden_lock(root):
        write_json_file(capture_request_file_path(root), payload, ensure_ascii=False)
    return payload


def read_capture_receipt(garden_root: str | Path, request_id: str) -> dict[str, Any] | None:
    """Read ``tmp/web_view/captures/<request_id>.json`` if present."""
    root, _ = _resolve_garden(garden_root)
    _, receipt_path = capture_output_paths(root, request_id)
    return _read_json_dict_safe(receipt_path)


def clear_capture_request(garden_root: str | Path, *, request_id: str | None = None) -> None:
    """Remove ``tmp/web_view/capture_request.json`` if it matches ``request_id`` (or unconditionally)."""
    root, _ = _resolve_garden(garden_root)
    with garden_lock(root):
        req_path = capture_request_file_path(root)
        if not req_path.is_file():
            return
        if request_id is not None:
            current = _read_json_dict_safe(req_path)
            if isinstance(current, dict) and current.get("request_id") != request_id:
                return
        req_path.unlink(missing_ok=True)


def poll_capture_handshake(
    *,
    garden_root: str | Path,
    view: str | dict[str, Any] = "fit",
    width: int = 1280,
    height: int = 720,
    timeout_secs: float = 5.0,
    poll_interval: float = 0.05,
    request_id: str | None = None,
) -> dict[str, Any] | None:
    """Submit ``capture_request.json`` and wait for ``captures/<id>.json`` + ``.png``."""
    root, _ = _resolve_garden(garden_root)
    req = write_capture_request(
        garden_root=root,
        view=view,
        width=width,
        height=height,
        request_id=request_id,
    )
    req_id = req["request_id"]
    png_path, _ = capture_output_paths(root, req_id)
    deadline = time.monotonic() + max(0.05, float(timeout_secs))
    try:
        while time.monotonic() <= deadline:
            receipt = read_capture_receipt(root, req_id)
            if isinstance(receipt, dict):
                status = str(receipt.get("status") or "").lower()
                if status == "ok" and png_path.is_file() and png_path.stat().st_size > 0:
                    return {
                        "request": req,
                        "receipt": receipt,
                        "png_path": png_path,
                    }
                if status in {"error", "failed"}:
                    return None
            time.sleep(poll_interval)
    finally:
        clear_capture_request(root, request_id=req_id)
    return None
