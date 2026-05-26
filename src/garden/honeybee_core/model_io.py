"""Honeybee model I/O inside a Garden."""

from __future__ import annotations

import json
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from honeybee.model import Model

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.honeybee_core.locate import iter_honeybee_objects
from garden.honeybee_core.targets import (
    is_honeybee_model_target,
    is_honeybee_object_target,
    normalize_honeybee_model_target,
    normalize_honeybee_target,
)

HONEYBEE_MODELS_DIR = Path("models") / "honeybee"
_MODEL_LOCKS_GUARD = Lock()
_MODEL_LOCKS: dict[tuple[str, str], RLock] = {}


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Honeybee model identifier."""
    return f"{model_identifier}.hbjson"


def honeybee_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the HBJSON path for a model identifier."""
    return garden_root / HONEYBEE_MODELS_DIR / model_filename(model_identifier)


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Honeybee model target with optional Garden-relative path."""
    target: dict[str, Any] = {
        "target_type": "honeybee_model",
        "id": model_identifier,
        "garden_id": garden_id,
        "domain": "honeybee",
        "model_identifier": model_identifier,
    }
    if path:
        target["path"] = path
    return target


def load_honeybee_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Honeybee model from a Garden model target."""
    model_target = normalize_honeybee_model_target(model_target)
    path_value = model_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("Honeybee model target requires a Garden-relative path.")
    model_path = garden_root / path_value
    return Model.from_hbjson(str(model_path), cleanup_irrational=False)


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit model target or the Garden base model."""
    manifest = GardenManifest.read(garden_root)
    model_target = model_target or manifest.base_honeybee_model
    if not model_target:
        raise ValueError(
            "Garden has no base Honeybee model. Create or set a Honeybee model first."
        )
    model_target = normalize_honeybee_model_target(model_target)
    if model_target.get("domain") != "honeybee":
        raise ValueError("Only Honeybee model targets are supported by this tool.")
    return manifest, model_target


@contextmanager
def honeybee_model_write_lock(
    garden_root: Path,
    *,
    model_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    target: dict[str, Any] | None = None,
    host_target: dict[str, Any] | None = None,
):
    """Serialize in-process writes against one Garden Honeybee model."""
    garden_root = garden_root.expanduser().resolve()
    identifier = _write_lock_model_identifier(
        garden_root,
        model_identifier=model_identifier,
        model_target=model_target,
        target=target,
        host_target=host_target,
    )
    lock = _model_lock(garden_root, identifier)
    with lock:
        yield


def with_honeybee_model_write_lock(func):
    """Decorate a Honeybee write service with a per Garden/model write lock."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        garden_root_value = kwargs.get("garden_root")
        if garden_root_value is None:
            return func(*args, **kwargs)
        garden_root = Path(str(garden_root_value)).expanduser().resolve()
        with honeybee_model_write_lock(
            garden_root,
            model_identifier=kwargs.get("identifier")
            if func.__name__ == "create_honeybee_model"
            else None,
            model_target=kwargs.get("model_target")
            or kwargs.get("honeybee_model_target"),
            target=kwargs.get("target"),
            host_target=kwargs.get("host_target"),
        ):
            return func(*args, **kwargs)

    return wrapper


def _write_lock_model_identifier(
    garden_root: Path,
    *,
    model_identifier: str | None,
    model_target: dict[str, Any] | None,
    target: dict[str, Any] | None,
    host_target: dict[str, Any] | None,
) -> str:
    if model_identifier:
        return str(model_identifier)
    for candidate in (model_target, target, host_target):
        identifier = _model_identifier_from_target_like(candidate)
        if identifier:
            return identifier
    manifest = GardenManifest.read(garden_root)
    if not manifest.base_honeybee_model:
        return "__no_base_honeybee_model__"
    return str(
        normalize_honeybee_model_target(manifest.base_honeybee_model)[
            "model_identifier"
        ]
    )


def _model_identifier_from_target_like(value: Any) -> str | None:
    if value is None:
        return None
    try:
        target = normalize_honeybee_target(value)
    except ValueError:
        return None
    if is_honeybee_model_target(target) or is_honeybee_object_target(target):
        return str(target["model_identifier"])
    return None


def _model_lock(garden_root: Path, model_identifier: str) -> RLock:
    key = (str(garden_root), model_identifier)
    with _MODEL_LOCKS_GUARD:
        lock = _MODEL_LOCKS.get(key)
        if lock is None:
            lock = RLock()
            _MODEL_LOCKS[key] = lock
        return lock


def save_honeybee_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: Model,
    *,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
    triangulate_sub_faces: bool = False,
    set_base: bool = False,
) -> tuple[dict[str, Any], str]:
    """Save a Honeybee model into Garden authoring truth and update manifest."""
    model_dir = garden_root / HONEYBEE_MODELS_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    output_name = name or model.identifier
    model.to_hbjson(
        name=output_name,
        folder=str(model_dir),
        indent=indent,
        included_prop=included_prop,
        triangulate_sub_faces=triangulate_sub_faces,
    )
    output_path = model_dir / model_filename(output_name)
    _patch_hbjson_extension_resources(output_path, model)
    persisted_path = to_posix_relative(
        output_path,
        garden_root,
    )
    target = model_target_for_manifest(
        manifest.garden_id,
        output_name,
        path=persisted_path,
    )
    manifest.models = [
        item
        for item in manifest.models
        if not (
            item.get("domain") == "honeybee"
            and item.get("model_identifier") == output_name
        )
    ]
    manifest.models.append(target)
    if set_base or manifest.base_honeybee_model is None:
        manifest.base_honeybee_model = target
    manifest.write(garden_root)
    return target, persisted_path


def _patch_hbjson_extension_resources(model_path: Path, model: Model) -> None:
    """Patch missing extension resources in saved HBJSON for reliable round-tripping."""
    data = json.loads(model_path.read_text(encoding="utf-8"))
    properties = data.setdefault("properties", {})
    energy = properties.setdefault("energy", {"type": "ModelEnergyProperties"})
    radiance = properties.setdefault("radiance", {"type": "ModelRadianceProperties"})

    energy_schedules = energy.setdefault("schedules", [])
    energy_type_limits = energy.setdefault("schedule_type_limits", [])
    radiance_modifiers = radiance.setdefault("modifiers", [])

    schedule_ids = {
        item.get("identifier")
        for item in energy_schedules
        if isinstance(item, dict)
    }
    type_limit_ids = {
        item.get("identifier")
        for item in energy_type_limits
        if isinstance(item, dict)
    }
    modifier_ids = {
        item.get("identifier")
        for item in radiance_modifiers
        if isinstance(item, dict)
    }

    for obj, _ in iter_honeybee_objects(
        model,
        garden_id="",
        model_identifier=str(model.identifier),
    ):
        _append_missing_energy_schedule_resources(
            obj,
            schedules=energy_schedules,
            schedule_ids=schedule_ids,
            type_limits=energy_type_limits,
            type_limit_ids=type_limit_ids,
        )
        _append_missing_radiance_modifier_resources(
            obj,
            modifiers=radiance_modifiers,
            modifier_ids=modifier_ids,
        )

    model_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _append_missing_energy_schedule_resources(
    obj: Any,
    *,
    schedules: list[dict[str, Any]],
    schedule_ids: set[str | None],
    type_limits: list[dict[str, Any]],
    type_limit_ids: set[str | None],
) -> None:
    schedule = getattr(getattr(obj.properties, "energy", None), "transmittance_schedule", None)
    if schedule is None:
        return
    if schedule.identifier not in schedule_ids:
        schedules.append(schedule.to_dict(abridged=True))
        schedule_ids.add(schedule.identifier)
    type_limit = getattr(schedule, "schedule_type_limit", None)
    if type_limit is not None and type_limit.identifier not in type_limit_ids:
        type_limits.append(type_limit.to_dict())
        type_limit_ids.add(type_limit.identifier)


def _append_missing_radiance_modifier_resources(
    obj: Any,
    *,
    modifiers: list[dict[str, Any]],
    modifier_ids: set[str | None],
) -> None:
    radiance = getattr(obj.properties, "radiance", None)
    if radiance is None:
        return

    for modifier in (
        getattr(radiance, "_modifier", None),
        getattr(radiance, "_modifier_blk", None),
    ):
        _append_modifier(modifier, modifiers, modifier_ids)

    for state in getattr(radiance, "_states", []):
        for modifier in (
            getattr(state, "_modifier", None),
            getattr(state, "_modifier_direct", None),
        ):
            _append_modifier(modifier, modifiers, modifier_ids)
        for shade in getattr(state, "_shades", []):
            for modifier in (
                getattr(shade, "_modifier", None),
                getattr(shade, "_modifier_direct", None),
            ):
                _append_modifier(modifier, modifiers, modifier_ids)


def _append_modifier(
    modifier: Any,
    modifiers: list[dict[str, Any]],
    modifier_ids: set[str | None],
) -> None:
    if modifier is None or modifier.identifier in modifier_ids:
        return
    modifiers.append(modifier.to_dict())
    modifier_ids.add(modifier.identifier)
