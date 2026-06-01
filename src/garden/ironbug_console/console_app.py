"""Python replacement for the C# Ironbug.Console file application role."""

from __future__ import annotations

from pathlib import Path

from garden.ironbug_console.console_contracts import PythonConsoleFileResult
from garden.ironbug_console.console_osm import (
    backup_osm_file,
    load_openstudio_model,
    save_openstudio_model,
    save_workflow_seed_file,
)
from garden.ironbug_console.console_model_payloads import (
    load_console_model_specification,
)
from garden.ironbug_console.openstudio_postprocess import (
    apply_csharp_save_hvac_postprocess,
)
from garden.ironbug_console.openstudio_writer import (
    write_console_model_specification_to_openstudio_model,
)


def save_hvac_to_osm(
    *,
    osm_path: str | Path,
    hvac_json_path: str | Path,
    backup: bool = True,
) -> PythonConsoleFileResult:
    """Apply Ironbug HVAC JSON to an existing OSM without C# Console fallback."""

    openstudio = _import_openstudio()
    osm = Path(osm_path)
    hvac_json = Path(hvac_json_path)
    specification = load_console_model_specification(hvac_json)
    model = load_openstudio_model(openstudio, osm)
    backup_path = backup_osm_file(osm) if backup else None

    write_result = write_console_model_specification_to_openstudio_model(
        model=model,
        specification=specification,
    )
    workflow_path = None
    if write_result.status == "written":
        apply_csharp_save_hvac_postprocess(openstudio, model)
        workflow_path = save_workflow_seed_file(openstudio, model, osm)
        save_openstudio_model(openstudio, model, osm)

    return PythonConsoleFileResult(
        status=write_result.status,
        osm_path=osm,
        hvac_json_path=hvac_json,
        backup_path=backup_path,
        workflow_path=workflow_path,
        write_result=write_result,
        csharp_ironbug_console_required=False,
    )


def _import_openstudio():
    import openstudio

    return openstudio
