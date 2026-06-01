"""Weather and SimulationParameter helpers for Python Console Energy runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _simulation_parameter_for_openstudio(
    *,
    epw_path: str | Path | None,
    sim_par_path: str | Path | None,
) -> Any:
    if sim_par_path is None and epw_path is None:
        return None

    from honeybee_energy.simulation.parameter import SimulationParameter

    if sim_par_path is None:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use()
        sim_par.output.add_hvac_energy_use()
        sim_par.output.add_electricity_generation()
        sim_par.output.reporting_frequency = "Monthly"
    else:
        sim_par_data = json.loads(Path(sim_par_path).read_text(encoding="utf-8"))
        sim_par = SimulationParameter.from_dict(sim_par_data)

    if epw_path is not None:
        _complete_simulation_parameter_from_weather(sim_par, Path(epw_path))
    return sim_par


def _complete_simulation_parameter_from_weather(
    sim_par: Any,
    epw_path: Path,
) -> None:
    from ladybug.epw import EPW
    from ladybug.stat import STAT

    ddy_path = epw_path.with_suffix(".ddy")
    stat_path = epw_path.with_suffix(".stat")

    def _add_approximate_design_days() -> None:
        epw = EPW(str(epw_path))
        sim_par.sizing_parameter.design_days = [
            epw.approximate_design_day("WinterDesignDay"),
            epw.approximate_design_day("SummerDesignDay"),
        ]

    if len(sim_par.sizing_parameter.design_days) == 0 and ddy_path.is_file():
        try:
            sim_par.sizing_parameter.add_from_ddy_996_004(str(ddy_path))
        except AssertionError:
            _add_approximate_design_days()
    elif len(sim_par.sizing_parameter.design_days) == 0:
        _add_approximate_design_days()

    if sim_par.sizing_parameter.climate_zone is None and stat_path.is_file():
        stat = STAT(str(stat_path))
        sim_par.sizing_parameter.climate_zone = stat.ashrae_climate_zone
