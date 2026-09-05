"""Shared model-file persistence helpers for Garden model domains."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest
from garden.operations import commit_manifest
from garden.paths import reject_windows_alias, validate_portable_file_name

_MODEL_SUFFIXES = {
    "honeybee": ".hbjson",
    "dragonfly": ".dfjson",
    "fairyfly": ".ffjson",
}


def _model_filename(identifier: str, domain: str) -> str:
    model_kind = f"{domain.title()} model"
    if not identifier.strip():
        raise ValueError(f"{model_kind} identifier must not be empty.")
    return validate_portable_file_name(
        f"{identifier}{_MODEL_SUFFIXES[domain]}", label=f"{model_kind} file name"
    )


def _model_target_for_manifest(
    garden_id: str, model_identifier: str, domain: str, path: str | None = None
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": f"{domain}_model",
        "id": model_identifier,
        "garden_id": garden_id,
        "domain": domain,
        "model_identifier": model_identifier,
    }
    if path:
        target["path"] = path
    return target


def _resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None,
    *,
    domain: str,
    normalize_target: Callable[[Any], dict[str, Any]],
) -> tuple[GardenManifest, dict[str, Any]]:
    model_kind = f"{domain.title()} model"
    manifest = GardenManifest.read(garden_root)
    model_target = model_target or getattr(manifest, f"base_{domain}_model")
    if not model_target:
        raise ValueError(
            f"Garden has no base {model_kind}. Create or set a {model_kind} first."
        )
    model_target = normalize_target(model_target)
    if model_target.get("domain") != domain:
        raise ValueError(f"Only {model_kind} targets are supported by this tool.")
    return manifest, model_target


def _load_model(
    garden_root: Path,
    model_target: dict[str, Any],
    *,
    normalize_target: Callable[[Any], dict[str, Any]],
    target_kind: str,
    loader: Callable[[Path], Any],
) -> Any:
    model_kind = f"{target_kind.title()} model"
    target = normalize_target(model_target)
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError(f"{model_kind} target requires a Garden-relative path.")
    path = Path(path_value)
    if path.is_absolute():
        raise ValueError(f"{model_kind} target path must be Garden-relative.")
    root = garden_root.expanduser().resolve()
    path = (root / path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{model_kind} target path must stay inside the Garden.") from exc
    return loader(path)


def _save_model(
    garden_root: Path,
    manifest: GardenManifest,
    *,
    domain: str,
    output_name: str,
    content: bytes,
    set_base: bool,
    set_default_base: bool = True,
    operation_id: str | None = None,
    staged_writes: Mapping[str, bytes] | None = None,
) -> tuple[dict[str, Any], str]:
    model_kind = f"{domain.title()} model"
    expected_revision = manifest.revision
    persisted_path = (
        Path("models") / domain / _model_filename(output_name, domain)
    ).as_posix()
    other_models = [item for item in manifest.models if item.get("domain") == domain and item.get("model_identifier") != output_name]
    reject_windows_alias(output_name, (item.get("model_identifier") for item in other_models), label=f"{model_kind} identifier")
    reject_windows_alias(persisted_path, (item.get("path") for item in other_models), label=f"{model_kind} path")
    target = _model_target_for_manifest(
        manifest.garden_id, output_name, domain, persisted_path
    )
    manifest.models = [
        item
        for item in manifest.models
        if not (
            item.get("domain") == domain
            and item.get("model_identifier") == output_name
        )
    ]
    manifest.models.append(target)
    if set_base or (
        set_default_base and getattr(manifest, f"base_{domain}_model") is None
    ):
        setattr(manifest, f"base_{domain}_model", target)
    commit_manifest(
        garden_root,
        manifest,
        operation_type=f"{domain}_model_save",
        operation_id=operation_id,
        expected_revision=expected_revision,
        staged_writes={**(staged_writes or {}), persisted_path: content},
    )
    return target, persisted_path
