"""Garden manifest model and file I/O."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ladybug_tools_mcp.contracts.targets import make_garden_target


CURRENT_SCHEMA_VERSION = "1"


def utc_now_iso() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json_file(
    path: Path,
    data: dict[str, Any],
    *,
    ensure_ascii: bool = True,
) -> None:
    """Write a UTF-8 JSON object with a stable trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=ensure_ascii)
        handle.write("\n")


@dataclass(slots=True)
class GardenManifest:
    """Minimal Garden manifest for the first implementation slice."""

    garden_id: str
    name: str
    description: str = ""
    schema_version: str = CURRENT_SCHEMA_VERSION
    revision: int = 0
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    base_honeybee_model: dict[str, Any] | None = None
    base_dragonfly_model: dict[str, Any] | None = None
    base_fairyfly_model: dict[str, Any] | None = None
    models: list[dict[str, Any]] = field(default_factory=list)
    weather_files: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def new(cls, name: str, description: str = "") -> "GardenManifest":
        """Create a new manifest with a generated Garden id."""
        return cls(
            garden_id=f"garden_{uuid4().hex[:12]}",
            name=name,
            description=description,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GardenManifest":
        """Load a manifest from a JSON-compatible dict."""
        try:
            json.dumps(data, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Garden manifest must contain JSON-compatible values: {exc}"
            ) from exc
        schema_version = data.get("schema_version")
        if not isinstance(schema_version, str) or not schema_version:
            raise ValueError("Garden manifest schema_version must be a non-empty string.")
        if schema_version != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported Garden manifest schema_version: "
                f"{schema_version!r}; supported version is {CURRENT_SCHEMA_VERSION!r}."
            )
        revision = data.get("revision", 0)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("Garden manifest revision must be a non-negative integer.")
        garden_id = data.get("garden_id")
        if not isinstance(garden_id, str) or not garden_id.strip():
            raise ValueError("Garden manifest garden_id must be a non-empty string.")
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Garden manifest name must be a non-empty string.")
        description = data.get("description", "")
        if not isinstance(description, str):
            raise ValueError("Garden manifest description must be a string.")
        created_at = data.get("created_at", utc_now_iso())
        updated_at = data.get("updated_at", utc_now_iso())
        if not isinstance(created_at, str) or not created_at:
            raise ValueError("Garden manifest created_at must be a non-empty string.")
        if not isinstance(updated_at, str) or not updated_at:
            raise ValueError("Garden manifest updated_at must be a non-empty string.")
        base_models: dict[str, dict[str, Any] | None] = {}
        for field_name in (
            "base_honeybee_model",
            "base_dragonfly_model",
            "base_fairyfly_model",
        ):
            value = data.get(field_name)
            if value is not None and not isinstance(value, dict):
                raise ValueError(
                    f"Garden manifest {field_name} must be an object or null."
                )
            base_models[field_name] = value
        collections: dict[str, list[dict[str, Any]]] = {}
        for field_name in ("models", "weather_files", "artifacts"):
            value = data.get(field_name, [])
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise ValueError(
                    f"Garden manifest {field_name} must be a list of objects."
                )
            collections[field_name] = list(value)
        return cls(
            garden_id=garden_id,
            name=name,
            description=description,
            schema_version=schema_version,
            revision=revision,
            created_at=created_at,
            updated_at=updated_at,
            base_honeybee_model=base_models["base_honeybee_model"],
            base_dragonfly_model=base_models["base_dragonfly_model"],
            base_fairyfly_model=base_models["base_fairyfly_model"],
            models=collections["models"],
            weather_files=collections["weather_files"],
            artifacts=collections["artifacts"],
        )

    @classmethod
    def read(cls, garden_root: Path) -> "GardenManifest":
        """Read `garden.json` from a Garden root."""
        from garden.operations import (
            garden_authoring_lock,
            recover_interrupted_operations,
        )

        garden_root = garden_root.expanduser().resolve()
        with garden_authoring_lock(garden_root):
            recover_interrupted_operations(garden_root)
            return cls._read_unlocked(garden_root)

    @classmethod
    def _read_unlocked(cls, garden_root: Path) -> "GardenManifest":
        """Read the manifest while the caller owns the Garden authoring lock."""
        with (garden_root / "garden.json").open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Garden manifest must be a JSON object.")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest."""
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "garden_id": self.garden_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "base_honeybee_model": self.base_honeybee_model,
            "base_dragonfly_model": self.base_dragonfly_model,
            "base_fairyfly_model": self.base_fairyfly_model,
            "models": self.models,
            "weather_files": self.weather_files,
            "artifacts": self.artifacts,
        }

    def validate(self) -> None:
        """Validate the complete in-memory manifest before persistence."""
        self.from_dict(self.to_dict())

    def upsert_artifact(
        self,
        artifact: dict[str, Any],
        *,
        key_fields: tuple[str, ...] = ("artifact_type", "path"),
    ) -> dict[str, Any]:
        """Replace an artifact matching its identity fields and append the new record."""
        if not key_fields:
            raise ValueError("Artifact key_fields must not be empty.")
        self.artifacts = [
            item
            for item in self.artifacts
            if any(item.get(field) != artifact.get(field) for field in key_fields)
        ]
        self.artifacts.append(artifact)
        return artifact

    def write(
        self,
        garden_root: Path,
        *,
        expected_revision: int | None = None,
        operation_id: str | None = None,
        operation_type: str = "manifest_write",
    ) -> Path:
        """Atomically commit `garden.json` with revision conflict detection."""
        from garden.operations import commit_manifest

        garden_root = garden_root.expanduser().resolve()
        commit_manifest(
            garden_root,
            self,
            operation_type=operation_type,
            operation_id=operation_id,
            expected_revision=expected_revision,
        )
        return garden_root / "garden.json"

    def target(self) -> dict[str, str]:
        """Return this Garden's public target."""
        return make_garden_target(self.garden_id)
