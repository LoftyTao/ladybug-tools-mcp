"""Result contracts for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ironbug.console_ir import ConsoleDiagnostic


@dataclass(frozen=True)
class OpenStudioWrittenObject:
    """Summary of one source node written to an OpenStudio model."""

    identifier: str
    source_class: str
    writer_family: str
    openstudio_type: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "source_class": self.source_class,
            "writer_family": self.writer_family,
            "openstudio_type": self.openstudio_type,
            "name": self.name,
        }


@dataclass(frozen=True)
class OpenStudioWriteResult:
    """Result of applying a writer slice to an OpenStudio model."""

    status: str
    written_objects: tuple[OpenStudioWrittenObject, ...] = ()
    diagnostics: tuple[ConsoleDiagnostic, ...] = ()
    output_path: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "written_objects", tuple(self.written_objects))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if self.output_path is not None:
            object.__setattr__(self, "output_path", Path(self.output_path))

    @property
    def written_object_count(self) -> int:
        return len(self.written_objects)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "written_object_count": self.written_object_count,
            "written_objects": [
                written_object.to_dict() for written_object in self.written_objects
            ],
            "diagnostics": [
                diagnostic.to_dict() for diagnostic in self.diagnostics
            ],
            "output_path": (
                self.output_path.as_posix() if self.output_path is not None else None
            ),
        }

