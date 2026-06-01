"""Diagnostic contract for Python Ironbug Console compiler stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PYCONSOLE_UNSUPPORTED_SOURCE_CLASS = "PYCONSOLE_UNSUPPORTED_SOURCE_CLASS"
PYCONSOLE_MISSING_REQUIRED_CHILD = "PYCONSOLE_MISSING_REQUIRED_CHILD"
PYCONSOLE_UNRESOLVED_REFERENCE = "PYCONSOLE_UNRESOLVED_REFERENCE"
PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE = (
    "PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE"
)
PYCONSOLE_WRITER_NOT_IMPLEMENTED = "PYCONSOLE_WRITER_NOT_IMPLEMENTED"

CONSOLE_DIAGNOSTIC_CODES = frozenset(
    {
        PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
        PYCONSOLE_MISSING_REQUIRED_CHILD,
        PYCONSOLE_UNRESOLVED_REFERENCE,
        PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
        PYCONSOLE_WRITER_NOT_IMPLEMENTED,
    }
)

_SEVERITIES = frozenset({"error", "warning", "info"})


@dataclass(frozen=True)
class ConsoleDiagnostic:
    """A stable compiler diagnostic that can be persisted in reports."""

    code: str
    message: str
    severity: str = "error"
    source_class: str | None = None
    identifier: str | None = None
    path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.code not in CONSOLE_DIAGNOSTIC_CODES:
            raise ValueError(f"Unknown Python Console diagnostic code: {self.code}")
        if self.severity not in _SEVERITIES:
            raise ValueError(f"Unknown Python Console diagnostic severity: {self.severity}")
        object.__setattr__(self, "path", tuple(self.path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "source_class": self.source_class,
            "identifier": self.identifier,
            "path": list(self.path),
        }
