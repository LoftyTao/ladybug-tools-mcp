"""Energy runtime adapter for the Python Ironbug Console."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee_energy.hvac.detailed import DetailedHVAC

from garden.ironbug_console.energy_runtime_openstudio import (
    _compile_honeybee_model_to_openstudio_runtime,
)
from garden.ironbug_console.energy_runtime_reports import (
    PythonIronbugRuntimeUnsupported,
)
from garden.ironbug_console.energy_runtime_room_mapping import (
    _detailed_hvac_room_mapping_issues,
)
from garden.paths import to_posix_relative


PYTHON_ONLY_ENV = "LBT_REQUIRE_PYTHON_IRONBUG_CONSOLE_ONLY"


def prepare_python_only_energy_model(
    *,
    model_path: Path,
    run_dir: Path,
    garden_root: Path,
    epw_path: str | Path | None = None,
    sim_par_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any] | None]:
    """Return a runtime OSM path that avoids C# Ironbug Console when possible.

    The Garden authoring model remains Ironbug-backed DetailedHVAC; only the
    transient Energy run input is rewritten as an OpenStudio model compiled by
    the Python Console path.
    """

    model = Model.from_hbjson(str(model_path), cleanup_irrational=False)
    unsupported: list[dict[str, Any]] = []
    graph_unsupported_by_hvac: dict[str, list[dict[str, Any]]] = {}
    reported_unsupported_hvacs: set[str] = set()
    assigned_room_ids_by_hvac: dict[str, set[str]] = {}
    detailed_hvacs_by_id: dict[str, DetailedHVAC] = {}
    for room in model.rooms:
        hvac = room.properties.energy.hvac
        if isinstance(hvac, DetailedHVAC):
            assigned_room_ids_by_hvac.setdefault(hvac.identifier, set()).add(
                room.identifier
            )
            detailed_hvacs_by_id.setdefault(hvac.identifier, hvac)

    if not detailed_hvacs_by_id:
        return model_path, None

    for hvac in detailed_hvacs_by_id.values():
        graph_unsupported = graph_unsupported_by_hvac.setdefault(
            hvac.identifier,
            _detailed_hvac_room_mapping_issues(
                hvac,
                assigned_room_ids=assigned_room_ids_by_hvac[hvac.identifier],
            ),
        )
        if graph_unsupported:
            if hvac.identifier not in reported_unsupported_hvacs:
                unsupported.extend(graph_unsupported)
                reported_unsupported_hvacs.add(hvac.identifier)
            continue

    if unsupported:
        raise PythonIronbugRuntimeUnsupported(unsupported)

    for room in model.rooms:
        if isinstance(room.properties.energy.hvac, DetailedHVAC):
            room.properties.energy.hvac = None

    output_path, compiler_reports = _compile_honeybee_model_to_openstudio_runtime(
        model=model,
        detailed_hvacs=list(detailed_hvacs_by_id.values()),
        run_dir=run_dir,
        garden_root=garden_root,
        epw_path=epw_path,
        sim_par_path=sim_par_path,
    )
    for compiler_report in compiler_reports:
        if compiler_report["status"] != "written":
            hvac_identifier = str(compiler_report["detailed_hvac_identifier"])
            if hvac_identifier not in reported_unsupported_hvacs:
                unsupported.append(
                    {
                        "room_identifier": None,
                        "detailed_hvac_identifier": hvac_identifier,
                        "reason": "python_console_writer_blocked",
                        "diagnostics": compiler_report["diagnostics"],
                    }
                )
                reported_unsupported_hvacs.add(hvac_identifier)

    if unsupported:
        raise PythonIronbugRuntimeUnsupported(unsupported)

    writer_families = sorted(
        {
            writer_family
            for report in compiler_reports
            for writer_family in report["writer_families"]
        }
    )
    writer_diagnostics = [
        diagnostic
        for report in compiler_reports
        for diagnostic in report["diagnostics"]
    ]
    compiled_room_count = sum(len(rooms) for rooms in assigned_room_ids_by_hvac.values())
    return output_path, {
        "status": "translated",
        "source_model_path": to_posix_relative(model_path, garden_root),
        "runtime_model_path": to_posix_relative(output_path, garden_root),
        "compiler_stage": "detailed_hvac_specification_to_openstudio_model",
        "compiler_output_kind": "openstudio_model",
        "simulation_input_kind": "openstudio_osm",
        "compiler_report_count": len(compiler_reports),
        "compiler_reports": compiler_reports,
        "writer_families": writer_families,
        "writer_diagnostics": writer_diagnostics,
        "compiled_detailed_hvac_count": len(detailed_hvacs_by_id),
        "compiled_room_count": compiled_room_count,
        "csharp_ironbug_console_required": False,
    }
