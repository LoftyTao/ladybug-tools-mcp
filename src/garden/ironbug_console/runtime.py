"""Runtime boundary reports for the Python Ironbug Console."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Any, Mapping

from ironbug.console_ir import (
    PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
    ConsoleDiagnostic,
)


_SURROGATE_OUTPUT_KINDS = frozenset(
    {
        "honeybee_template_hvac",
        "template_hvac",
        "honeybee_surrogate",
        "surrogate_honeybee_template",
    }
)


@dataclass(frozen=True)
class OpenStudioRuntimeStatus:
    """Availability report for Python bindings used by writer stages."""

    available: bool
    import_name: str = "openstudio"
    version: str | None = None
    diagnostic: ConsoleDiagnostic | None = None

    def __post_init__(self) -> None:
        if self.available and self.diagnostic is not None:
            raise ValueError("Available runtime status cannot carry a diagnostic.")
        if not self.available and self.diagnostic is None:
            object.__setattr__(
                self,
                "diagnostic",
                ConsoleDiagnostic(
                    code=PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
                    message=(
                        "Python OpenStudio bindings are unavailable for the "
                        f"Python Ironbug Console runtime: {self.import_name}"
                    ),
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "import_name": self.import_name,
            "version": self.version,
            "diagnostic": (
                self.diagnostic.to_dict() if self.diagnostic is not None else None
            ),
        }


@dataclass(frozen=True)
class PythonConsoleRuntimeReport:
    """Structured runtime boundary report before writer-family implementation."""

    status: str
    ironbug_model_target: Mapping[str, Any]
    honeybee_model_target: Mapping[str, Any]
    openstudio_runtime: OpenStudioRuntimeStatus
    diagnostics: tuple[ConsoleDiagnostic, ...] = ()
    stage: str = "runtime-boundary"
    compiler_output_kind: str | None = None
    runtime_artifact: str | None = None
    writer_family: str | None = None
    csharp_ironbug_console_required: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"blocked", "accepted"}:
            raise ValueError(f"Unknown Python Console runtime status: {self.status}")
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(
            self, "ironbug_model_target", dict(self.ironbug_model_target)
        )
        object.__setattr__(
            self, "honeybee_model_target", dict(self.honeybee_model_target)
        )
        if self.status == "accepted" and self.csharp_ironbug_console_required:
            raise ValueError(
                "An accepted Python Console report cannot require C# Ironbug Console."
            )
        if self.status == "accepted" and not self.openstudio_runtime.available:
            raise ValueError(
                "An accepted Python Console report requires available Python "
                "OpenStudio bindings."
            )
        if (
            self.status == "accepted"
            and self.compiler_output_kind in _SURROGATE_OUTPUT_KINDS
        ):
            raise ValueError(
                "Honeybee template surrogate output cannot be accepted as Python "
                "Console compiler evidence."
            )

    @classmethod
    def blocked(
        cls,
        *,
        ironbug_model_target: Mapping[str, Any],
        honeybee_model_target: Mapping[str, Any],
        openstudio_runtime: OpenStudioRuntimeStatus,
        diagnostics: tuple[ConsoleDiagnostic, ...],
    ) -> "PythonConsoleRuntimeReport":
        return cls(
            status="blocked",
            ironbug_model_target=ironbug_model_target,
            honeybee_model_target=honeybee_model_target,
            openstudio_runtime=openstudio_runtime,
            diagnostics=diagnostics,
        )

    @classmethod
    def accepted(
        cls,
        *,
        ironbug_model_target: Mapping[str, Any],
        honeybee_model_target: Mapping[str, Any],
        openstudio_runtime: OpenStudioRuntimeStatus,
        compiler_output_kind: str,
        runtime_artifact: str,
        writer_family: str,
        csharp_ironbug_console_required: bool = False,
    ) -> "PythonConsoleRuntimeReport":
        return cls(
            status="accepted",
            ironbug_model_target=ironbug_model_target,
            honeybee_model_target=honeybee_model_target,
            openstudio_runtime=openstudio_runtime,
            compiler_output_kind=compiler_output_kind,
            runtime_artifact=runtime_artifact,
            writer_family=writer_family,
            csharp_ironbug_console_required=csharp_ironbug_console_required,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stage": self.stage,
            "ironbug_model_target": dict(self.ironbug_model_target),
            "honeybee_model_target": dict(self.honeybee_model_target),
            "openstudio_runtime": self.openstudio_runtime.to_dict(),
            "diagnostics": [
                diagnostic.to_dict() for diagnostic in self.diagnostics
            ],
            "compiler_output_kind": self.compiler_output_kind,
            "runtime_artifact": self.runtime_artifact,
            "writer_family": self.writer_family,
            "csharp_ironbug_console_required": self.csharp_ironbug_console_required,
        }


def check_openstudio_runtime(import_name: str = "openstudio") -> OpenStudioRuntimeStatus:
    """Check whether the Python binding package can be imported."""

    if importlib.util.find_spec(import_name) is None:
        return OpenStudioRuntimeStatus(available=False, import_name=import_name)
    return OpenStudioRuntimeStatus(available=True, import_name=import_name)
