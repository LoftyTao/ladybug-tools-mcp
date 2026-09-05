"""Start native daylight compliance recipes using the Garden run ledger."""

from __future__ import annotations

from typing import Any

from honeybee_radiance.writer import _filter_by_pattern

from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.radiance.run import (
    _garden_root,
    _radiance_parameters_from_input,
    _resolve_wea_path,
    _start_radiance_run,
)
from garden.radiance.sky import _resolve_epw_path


def start_radiance_compliance_run(
    *,
    garden_root: str,
    recipe_name: str,
    model_target: dict[str, Any] | None = None,
    wea_target: dict[str, Any] | None = None,
    weather_file_target: dict[str, Any] | None = None,
    grid_filter: str = "*",
    north: float | None = None,
    min_sensor_count: int = 1,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    recipe_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve typed weather and model inputs before starting a compliance run."""
    if recipe_name not in {
        "leed-daylight-option-two", "annual-daylight-en17037",
        "leed-daylight-option-one", "well-daylight", "breeam-daylight-4b",
    }:
        raise ValueError(f"Unsupported daylight compliance recipe: {recipe_name}")
    if min_sensor_count < 1 or (workers is not None and workers < 1):
        raise ValueError("min_sensor_count and workers must be positive integers.")
    root = _garden_root(garden_root)
    manifest, model_target = resolve_model_target(root, model_target)
    model = load_honeybee_model(root, model_target)
    grids = _filter_by_pattern(model.properties.radiance.sensor_grids, grid_filter)
    if not grids:
        raise ValueError("The model must have attached SensorGrids matching grid_filter.")
    if len({grid.full_identifier for grid in grids}) != len(grids):
        raise ValueError(
            "Daylight compliance requires unique selected SensorGrid identifiers. "
            "Use distinct names and select only the intended workplanes."
        )
    if recipe_name in {
        "leed-daylight-option-two", "annual-daylight-en17037", "breeam-daylight-4b",
    } and any(grid.group_identifier for grid in grids):
        raise ValueError(
            f"{recipe_name} does not support grouped SensorGrids in the installed SDK. "
            "Use grids with an empty group_identifier."
        )
    if recipe_name == "breeam-daylight-4b":
        room_ids = {room.identifier for room in model.rooms}
        if any(grid.room_identifier not in room_ids or grid.mesh is None for grid in grids):
            raise ValueError(
                "BREEAM requires SensorGrids with meshes and valid room_identifier values. "
                "Create attached grids from room floor faces."
            )
    inputs = dict(recipe_options or {})
    inputs.update({"grid-filter": grid_filter, "min-sensor-count": min_sensor_count})
    if north is not None:
        inputs["north"] = north
    if recipe_name in {"annual-daylight-en17037", "well-daylight"}:
        if weather_file_target is None or wea_target is not None:
            raise ValueError("This recipe requires an EPW weather_file_target.")
        epw, _ = _resolve_epw_path(
            garden_root=root, manifest=manifest,
            weather_target=weather_file_target, epw_path=None,
        )
        inputs["epw"] = str(epw)
    else:
        if wea_target is None or weather_file_target is not None:
            raise ValueError("This recipe requires a wea_target.")
        inputs["wea"] = _resolve_wea_path(
            garden_root=root, manifest=manifest, wea_target=wea_target, wea_path=None,
        )
    result = _start_radiance_run(
        garden_root=garden_root,
        model_target=model_target,
        recipe_name=recipe_name,
        calculation_family="compliance",
        calculation_type=recipe_name.replace("-", "_"),
        command_name="rtrace" if recipe_name == "leed-daylight-option-two" else "rfluxmtx",
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
    )
    if recipe_name == "breeam-daylight-4b":
        from honeybee_radiance_postprocess.breeam.breeam import program_type_metrics

        rooms = model.rooms_by_identifier([grid.room_identifier for grid in grids])
        if any(
            room.properties.energy.program_type.identifier.replace("Creche", "Crèche")
            not in program_type_metrics for room in rooms
        ):
            result["report"]["warnings"].append(
                "The BREEAM recipe treats unrecognized room program types as office occupied spaces."
            )
    return result
