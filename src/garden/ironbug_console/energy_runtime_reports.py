"""Runtime report helpers for the Python Ironbug Console Energy adapter."""

from __future__ import annotations

from typing import Any


class PythonIronbugRuntimeUnsupported(ValueError):
    """Raised when a DetailedHVAC graph cannot be translated without C#."""

    def __init__(self, unsupported_graphs: list[dict[str, Any]]) -> None:
        self.unsupported_graphs = unsupported_graphs
        super().__init__(
            "Python Ironbug Console could not translate all DetailedHVAC "
            f"graphs: {unsupported_graphs}"
        )


def _compiler_report_from_parts(
    *,
    hvac_identifier: str,
    status: str,
    runtime_artifact: str | None,
    written_objects: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    writer_families = sorted(
        {str(written_object["writer_family"]) for written_object in written_objects}
    )
    return {
        "detailed_hvac_identifier": hvac_identifier,
        "status": status,
        "compiler_stage": "detailed_hvac_specification_to_openstudio_model",
        "compiler_output_kind": "openstudio_model",
        "runtime_artifact": runtime_artifact,
        "writer_families": writer_families,
        "written_object_count": len(written_objects),
        "written_objects": written_objects,
        "diagnostics": diagnostics,
    }
