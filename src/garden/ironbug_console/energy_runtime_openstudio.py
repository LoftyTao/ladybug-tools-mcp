"""OpenStudio compilation for the Python Ironbug Console Energy adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee_energy.hvac.detailed import DetailedHVAC

from ironbug.console_ir import (
    PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
    ConsoleDiagnostic,
)

from garden.ironbug_console.energy_runtime_reports import (
    _compiler_report_from_parts,
)
from garden.ironbug_console.energy_runtime_weather import (
    _simulation_parameter_for_openstudio,
)
from garden.ironbug_console.openstudio_postprocess import (
    apply_csharp_save_hvac_postprocess,
)
from garden.ironbug_console.openstudio_writer import (
    write_detailed_hvac_specification_to_openstudio_model,
)
from garden.paths import to_posix_relative


def _compile_honeybee_model_to_openstudio_runtime(
    *,
    model: Model,
    detailed_hvacs: list[DetailedHVAC],
    run_dir: Path,
    garden_root: Path,
    epw_path: str | Path | None,
    sim_par_path: str | Path | None,
) -> tuple[Path, list[dict[str, Any]]]:
    output_path = _runtime_osm_artifact_path(run_dir, model.identifier)
    try:
        from honeybee_openstudio.openstudio import OSModel, os_path
        from honeybee_openstudio.simulation import (
            assign_epw_to_model,
            simulation_parameter_to_openstudio,
        )
        from honeybee_openstudio.writer import model_to_openstudio
    except ImportError as exc:
        diagnostics = [
            ConsoleDiagnostic(
                code=PYCONSOLE_OPENSTUDIO_RUNTIME_UNAVAILABLE,
                message=f"Honeybee OpenStudio writer is unavailable: {exc}",
            ).to_dict()
        ]
        return output_path, [
            _compiler_report_from_parts(
                hvac_identifier=hvac.identifier,
                status="blocked",
                runtime_artifact=None,
                written_objects=[],
                diagnostics=diagnostics,
            )
            for hvac in detailed_hvacs
        ]

    openstudio_model = OSModel()
    sim_par = _simulation_parameter_for_openstudio(
        epw_path=epw_path,
        sim_par_path=sim_par_path,
    )
    if epw_path is not None:
        set_climate_zone = (
            sim_par is None or sim_par.sizing_parameter.climate_zone is None
        )
        assign_epw_to_model(str(epw_path), openstudio_model, set_climate_zone)
    if sim_par is not None:
        simulation_parameter_to_openstudio(sim_par, openstudio_model)

    openstudio_model = model_to_openstudio(
        model,
        openstudio_model,
        enforce_rooms=True,
    )
    compiler_reports: list[dict[str, Any]] = []
    for hvac in detailed_hvacs:
        write_result = write_detailed_hvac_specification_to_openstudio_model(
            model=openstudio_model,
            specification=hvac.specification,
            output_path=None,
        )
        runtime_artifact = (
            to_posix_relative(output_path, garden_root)
            if write_result.status == "written"
            else None
        )
        compiler_reports.append(
            _compiler_report_from_parts(
                hvac_identifier=hvac.identifier,
                status=write_result.status,
                runtime_artifact=runtime_artifact,
                written_objects=[
                    written_object.to_dict()
                    for written_object in write_result.written_objects
                ],
                diagnostics=[
                    diagnostic.to_dict() for diagnostic in write_result.diagnostics
                ],
            )
        )

    if all(report["status"] == "written" for report in compiler_reports):
        import openstudio

        apply_csharp_save_hvac_postprocess(openstudio, openstudio_model)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        openstudio_model.save(os_path(str(output_path)), overwrite=True)
    return output_path, compiler_reports


def _runtime_osm_artifact_path(run_dir: Path, model_identifier: str) -> Path:
    return run_dir / "pyironbug.osm"
