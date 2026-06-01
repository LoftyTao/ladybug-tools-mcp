"""Pure Python IR for the Python Ironbug Console compiler."""

from __future__ import annotations

from ironbug.console_ir.diagnostics import (
    CONSOLE_DIAGNOSTIC_CODES,
    PYCONSOLE_MISSING_REQUIRED_CHILD,
    PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
    PYCONSOLE_UNRESOLVED_REFERENCE,
    PYCONSOLE_UNSUPPORTED_SOURCE_CLASS,
    PYCONSOLE_WRITER_NOT_IMPLEMENTED,
    ConsoleDiagnostic,
)
from ironbug.console_ir.graph import (
    ConsoleCompilePlan,
    ConsoleGraph,
    ConsoleGraphNode,
)

__all__ = [
    "CONSOLE_DIAGNOSTIC_CODES",
    "PYCONSOLE_MISSING_REQUIRED_CHILD",
    "PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE",
    "PYCONSOLE_UNRESOLVED_REFERENCE",
    "PYCONSOLE_UNSUPPORTED_SOURCE_CLASS",
    "PYCONSOLE_WRITER_NOT_IMPLEMENTED",
    "ConsoleCompilePlan",
    "ConsoleDiagnostic",
    "ConsoleGraph",
    "ConsoleGraphNode",
]
