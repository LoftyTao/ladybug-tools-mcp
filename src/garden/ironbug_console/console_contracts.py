"""Contracts for Python Ironbug Console file entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWriteResult


@dataclass(frozen=True)
class PythonConsoleFileResult:
    """Result from applying an Ironbug HVAC JSON payload to an OSM file."""

    status: str
    osm_path: Path
    hvac_json_path: Path
    write_result: OpenStudioWriteResult
    backup_path: Path | None = None
    workflow_path: Path | None = None
    csharp_ironbug_console_required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "osm_path", Path(self.osm_path))
        object.__setattr__(self, "hvac_json_path", Path(self.hvac_json_path))
        if self.backup_path is not None:
            object.__setattr__(self, "backup_path", Path(self.backup_path))
        if self.workflow_path is not None:
            object.__setattr__(self, "workflow_path", Path(self.workflow_path))
        if self.status == "written" and self.csharp_ironbug_console_required:
            raise ValueError("Python Console file result cannot require C# Console.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "osm_path": self.osm_path.as_posix(),
            "hvac_json_path": self.hvac_json_path.as_posix(),
            "backup_path": (
                self.backup_path.as_posix() if self.backup_path is not None else None
            ),
            "workflow_path": (
                self.workflow_path.as_posix()
                if self.workflow_path is not None
                else None
            ),
            "csharp_ironbug_console_required": self.csharp_ironbug_console_required,
            "write_result": self.write_result.to_dict(),
        }
