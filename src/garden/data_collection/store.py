"""Garden-backed Ladybug DataCollection storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ladybug.datacollection import (
    DailyCollection,
    HourlyContinuousCollection,
    HourlyDiscontinuousCollection,
    MonthlyCollection,
    MonthlyPerHourCollection,
)
from ladybug.datautil import (
    collections_from_csv,
    collections_from_json,
    collections_to_csv,
    collections_to_json,
)

from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from garden.data_collection.summary import data_collection_summary
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative

DATA_COLLECTION_TARGET_TYPE = "ladybug_data_collection"
DATA_COLLECTION_ARTIFACT_TYPE = "data_collection_json"
DATA_COLLECTION_CSV_ARTIFACT_TYPE = "data_collection_csv"
DATA_COLLECTION_OUTPUT_SUBDIR = "artifacts/data_collections"
_DATA_COLLECTION_ARTIFACT_TYPES = {
    "json": DATA_COLLECTION_ARTIFACT_TYPE,
    "csv": DATA_COLLECTION_CSV_ARTIFACT_TYPE,
}

_COLLECTION_CLASSES = {
    "HourlyContinuous": HourlyContinuousCollection,
    "HourlyDiscontinuous": HourlyDiscontinuousCollection,
    "Daily": DailyCollection,
    "Monthly": MonthlyCollection,
    "MonthlyPerHour": MonthlyPerHourCollection,
}


def collection_from_dict(data: dict[str, Any]) -> Any:
    """Rebuild a Ladybug DataCollection from an SDK dictionary."""
    collection_type = str(data.get("type") or "")
    collection_cls = _COLLECTION_CLASSES.get(collection_type)
    if collection_cls is None:
        allowed = ", ".join(sorted(_COLLECTION_CLASSES))
        raise ValueError(
            f"Unsupported DataCollection type: {collection_type}. Allowed: {allowed}."
        )
    return collection_cls.from_dict(data)


def _target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    return {
        "target_type": DATA_COLLECTION_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": "ladybug",
        "identifier": identifier,
        "path": path,
    }


def _register_artifact(
    manifest: GardenManifest,
    *,
    name: str,
    path: str,
    source: dict[str, Any],
    artifact_type: str = DATA_COLLECTION_ARTIFACT_TYPE,
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact_type
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(record)
    return record


def _coerce_collection(data_collection: Any | dict[str, Any]) -> Any:
    collection = (
        collection_from_dict(data_collection)
        if isinstance(data_collection, dict)
        else data_collection
    )
    if not hasattr(collection, "to_dict"):
        raise ValueError("data_collection must be a Ladybug DataCollection object or dict.")
    return collection


def _write_collection_file(
    *,
    collection: Any,
    output_dir: Path,
    file_name: str,
    file_format: str,
) -> Path:
    file_format = file_format.lower()
    if file_format == "json":
        return Path(collections_to_json([collection], str(output_dir), file_name))
    if file_format == "csv":
        return Path(collections_to_csv([collection], str(output_dir), file_name))
    raise ValueError("file_format must be one of: json, csv.")


def _load_json_collection(data_path: Path) -> Any:
    with data_path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)
    if isinstance(raw_data, dict):
        return collection_from_dict(raw_data)

    collections = collections_from_json(str(data_path))
    if len(collections) != 1:
        raise ValueError(
            f"DataCollection JSON target must contain one collection; got {len(collections)}."
        )
    return collections[0]


def _load_csv_collection(data_path: Path) -> Any:
    collections = collections_from_csv(str(data_path))
    if len(collections) != 1:
        raise ValueError(
            f"DataCollection CSV target must contain one collection; got {len(collections)}."
        )
    return collections[0]


def save_data_collection(
    *,
    garden_root: str | Path,
    data_collection: Any | dict[str, Any],
    identifier: str,
    output_subdir: str = DATA_COLLECTION_OUTPUT_SUBDIR,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a Ladybug DataCollection and return a compact Garden target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    collection = _coerce_collection(data_collection)

    safe_identifier = slugify_name(identifier)
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = (output_dir / f"{safe_identifier}.json").resolve()
    data_path.relative_to(garden_root_path)
    data_dict = collection.to_dict()
    _write_collection_file(
        collection=collection,
        output_dir=output_dir,
        file_name=data_path.name,
        file_format="json",
    )

    artifact_path = to_posix_relative(data_path, garden_root_path)
    artifact_source = {
        "data_collection_type": data_dict.get("type"),
        **(source or {}),
    }
    artifact = _register_artifact(
        manifest,
        name=safe_identifier,
        path=artifact_path,
        source=artifact_source,
    )
    manifest.write(garden_root_path)
    target = _target(
        manifest=manifest,
        identifier=safe_identifier,
        path=artifact_path,
    )
    return {
        "target": target,
        "data_target": target,
        "summary_view": data_collection_summary(collection),
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=DATA_COLLECTION_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(data_path),
            source=artifact_source,
        ),
    }


def export_data_collection_file(
    *,
    garden_root: str | Path,
    data_collection: Any | dict[str, Any] | None = None,
    data_collection_target: dict[str, Any] | None = None,
    file_format: str = "json",
    name: str = "data_collection",
    output_subdir: str = DATA_COLLECTION_OUTPUT_SUBDIR,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export a Ladybug DataCollection to a native SDK JSON or CSV artifact."""
    has_dict = data_collection is not None
    has_target = data_collection_target is not None
    if has_dict == has_target:
        raise ValueError(
            "export_data_collection_file requires exactly one of "
            "data_collection or data_collection_target."
        )
    normalized_format = file_format.lower().strip()
    artifact_type = _DATA_COLLECTION_ARTIFACT_TYPES.get(normalized_format)
    if artifact_type is None:
        raise ValueError("file_format must be one of: json, csv.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    collection = (
        load_data_collection(
            garden_root=garden_root_path,
            data_collection_target=data_collection_target or {},
        )
        if has_target
        else _coerce_collection(data_collection)
    )

    safe_name = slugify_name(name)
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = (output_dir / f"{safe_name}.{normalized_format}").resolve()
    data_path.relative_to(garden_root_path)
    written_path = _write_collection_file(
        collection=collection,
        output_dir=output_dir,
        file_name=data_path.name,
        file_format=normalized_format,
    ).resolve()
    written_path.relative_to(garden_root_path)

    data_dict = collection.to_dict()
    artifact_path = to_posix_relative(written_path, garden_root_path)
    artifact_source = {
        "data_collection_type": data_dict.get("type"),
        "file_format": normalized_format,
        **(source or {}),
    }
    artifact = _register_artifact(
        manifest,
        name=safe_name,
        path=artifact_path,
        source=artifact_source,
        artifact_type=artifact_type,
    )
    manifest.write(garden_root_path)
    target = _target(
        manifest=manifest,
        identifier=safe_name,
        path=artifact_path,
    )
    return {
        "target": target,
        "data_collection_target": target,
        "summary_view": data_collection_summary(collection),
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            absolute_path=str(written_path),
            source=artifact_source,
        ),
    }


def load_data_collection(
    *,
    garden_root: str | Path,
    data_collection_target: dict[str, Any],
) -> Any:
    """Load a Garden-backed Ladybug DataCollection target."""
    if not isinstance(data_collection_target, dict):
        raise ValueError("data_collection_target must be a dictionary.")
    target_type = data_collection_target.get("target_type")
    if target_type == "data_collection":
        target_type = DATA_COLLECTION_TARGET_TYPE
    if target_type != DATA_COLLECTION_TARGET_TYPE:
        raise ValueError(
            "data_collection_target target_type must be "
            f"{DATA_COLLECTION_TARGET_TYPE!r}; got {target_type!r}."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    garden_id = data_collection_target.get("garden_id")
    if garden_id and garden_id != manifest.garden_id:
        raise ValueError(
            "data_collection_target garden_id does not match the Garden root."
        )
    target_path = data_collection_target.get("path")
    if not target_path:
        artifact_name = data_collection_target.get("artifact_name") or data_collection_target.get(
            "identifier"
        )
        if isinstance(artifact_name, str) and artifact_name.strip():
            artifact_path = artifact_name.strip().replace("\\", "/")
            if "/" not in artifact_path:
                artifact_path = f"artifacts/data_collections/{artifact_path}"
            target_path = artifact_path
    if not isinstance(target_path, str) or not target_path:
        raise ValueError("data_collection_target requires a Garden-relative path.")
    data_path = (garden_root_path / target_path).resolve()
    data_path.relative_to(garden_root_path)
    if not data_path.suffix:
        for suffix in (".json", ".csv"):
            candidate = data_path.with_suffix(suffix)
            if candidate.is_file():
                data_path = candidate
                target_path = to_posix_relative(data_path, garden_root_path)
                break
    if not data_path.is_file():
        raise ValueError(f"DataCollection target file was not found: {target_path}")
    suffix = data_path.suffix.lower()
    if suffix == ".json":
        return _load_json_collection(data_path)
    if suffix == ".csv":
        return _load_csv_collection(data_path)
    raise ValueError(
        f"DataCollection target must point to a .json or .csv file: {target_path}"
    )
