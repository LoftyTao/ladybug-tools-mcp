"""Garden manifest model and file I/O."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ladybug_tools_mcp.contracts.targets import make_garden_target


def utc_now_iso() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(slots=True)
class GardenManifest:
    """Minimal Garden manifest for the first implementation slice."""

    garden_id: str
    name: str
    description: str = ""
    schema_version: str = "1"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    base_model: dict[str, Any] | None = None
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
        return cls(
            garden_id=str(data["garden_id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            schema_version=str(data.get("schema_version", "1")),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            base_model=data.get("base_model"),
            models=list(data.get("models", [])),
            weather_files=list(data.get("weather_files", [])),
            artifacts=list(data.get("artifacts", [])),
        )

    @classmethod
    def read(cls, garden_root: Path) -> "GardenManifest":
        """Read `garden.json` from a Garden root."""
        with (garden_root / "garden.json").open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest."""
        return {
            "schema_version": self.schema_version,
            "garden_id": self.garden_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "base_model": self.base_model,
            "models": self.models,
            "weather_files": self.weather_files,
            "artifacts": self.artifacts,
        }

    def write(self, garden_root: Path) -> Path:
        """Write `garden.json` into a Garden root."""
        self.updated_at = utc_now_iso()
        manifest_path = garden_root / "garden.json"
        with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")
        return manifest_path

    def target(self) -> dict[str, str]:
        """Return this Garden's public target."""
        return make_garden_target(self.garden_id)
