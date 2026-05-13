"""Garden-managed Dragonfly UWG Alternative Weather services."""

from __future__ import annotations

from pathlib import Path

UWG_DOMAIN = "dragonfly_uwg"
UWG_ARTIFACT_DIR = Path("artifacts") / "uwg"
UWG_PARAMETER_TARGET_TYPE = "uwg_simulation_parameter"
UWG_JSON_ARTIFACT_TYPE = "uwg_json"
UWG_RUN_TARGET_TYPE = "uwg_run"
UWG_RUN_RECIPE = "urban_weather_generator"
