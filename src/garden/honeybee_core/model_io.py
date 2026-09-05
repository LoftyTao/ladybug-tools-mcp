"""Honeybee model I/O inside a Garden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee.model import Model

from garden.honeybee_core.locate import iter_honeybee_objects
from garden.honeybee_core.targets import normalize_honeybee_model_target
from garden.manifest import GardenManifest
from garden.model_io import (
    _load_model,
    _model_filename,
    _model_target_for_manifest,
    _resolve_model_target,
    _save_model,
)

HONEYBEE_MODELS_DIR = Path("models") / "honeybee"


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Honeybee model identifier."""
    return _model_filename(model_identifier, "honeybee")


def honeybee_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the HBJSON path for a model identifier."""
    return garden_root / HONEYBEE_MODELS_DIR / _model_filename(model_identifier, "honeybee")


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Honeybee model target with optional Garden-relative path."""
    return _model_target_for_manifest(garden_id, model_identifier, "honeybee", path)


def load_honeybee_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Honeybee model from a Garden model target."""
    return _load_model(
        garden_root,
        model_target,
        normalize_target=normalize_honeybee_model_target,
        target_kind="honeybee",
        loader=lambda path: Model.from_hbjson(str(path), cleanup_irrational=False),
    )


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit model target or the Garden base model."""
    return _resolve_model_target(
        garden_root,
        model_target,
        domain="honeybee",
        normalize_target=normalize_honeybee_model_target,
    )


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
    set_default_base: bool = True,
    operation_id: str | None = None,
    staged_writes: dict[str, bytes] | None = None,
) -> tuple[dict[str, Any], str]:
    """Save a Honeybee model into Garden authoring truth and update manifest."""
    output_name = name or model.identifier
    data = json.loads(
        json.dumps(
            model.to_dict(
                included_prop=included_prop,
                triangulate_sub_faces=triangulate_sub_faces,
            ),
            indent=indent,
        )
    )
    _patch_hbjson_extension_resources(data, model)
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    return _save_model(
        garden_root,
        manifest,
        domain="honeybee",
        output_name=output_name,
        content=content,
        set_base=set_base,
        set_default_base=set_default_base,
        operation_id=operation_id,
        staged_writes=staged_writes,
    )


def _patch_hbjson_extension_resources(data: dict[str, Any], model: Model) -> None:
    """Patch missing extension resources in saved HBJSON for reliable round-tripping."""
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
