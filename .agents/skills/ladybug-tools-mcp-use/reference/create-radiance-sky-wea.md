# Create Radiance Sky / WEA

Agent-verified Code Mode path for creating Radiance single-timestep sky files, WEA files, and compact SkyMatrix targets in a Garden.

Use this path when the user asks for Radiance sky setup, CIE standard sky, climate-based sky, WEA files, clear-sky studies, sky matrices, or a pre-step before incident radiation / daylight workflows.

## Tool Choice

- EPW/weather target to WEA: `create_wea_from_weather_file`
  - Preferred when the Garden already has a `weather_file` target from `download_epw` or `search_weather_files`.
- ASHRAE clear sky to WEA: `create_ashrae_clear_sky_wea`
  - Use when the user wants theoretical clear sky from a Ladybug `Location`.
- Single-timestep CIE standard sky file: `create_cie_standard_sky`
  - Use for Radiance `gensky` CIE sky types: sunny, sunny without sun, cloudy, uniform cloudy, intermediate, or intermediate without sun.
- Single-timestep climate-based sky file: `create_climate_based_sky`
  - Use for Radiance `gendaylit` when the user provides direct normal plus diffuse horizontal irradiance or illuminance.
- WEA/weather/location to SkyMatrix: `create_sky_matrix`
  - Use `wea_target` when a WEA was just created.
  - Use `compute=false` unless the user explicitly needs stored patch values now.

## Main Paths

Weather-file path:

```python
wea = await call_tool("create_wea_from_weather_file", {
    "garden_root": garden_root,
    "identifier": "project_wea",
    "weather_target": weather_target,
})
sky = await call_tool("create_sky_matrix", {
    "garden_root": garden_root,
    "identifier": "project_sky",
    "wea_target": wea["target"],
    "north": 0,
    "high_density": False,
    "ground_reflectance": 0.2,
    "compute": False,
})
```

Clear-sky path:

```python
wea = await call_tool("create_ashrae_clear_sky_wea", {
    "garden_root": garden_root,
    "identifier": "clear_sky_wea",
    "location": {
        "type": "Location",
        "city": "Boulder",
        "latitude": 40.0,
        "longitude": -105.2,
        "time_zone": -7,
        "elevation": 1600,
    },
})
sky = await call_tool("create_sky_matrix", {
    "garden_root": garden_root,
    "identifier": "clear_sky_matrix",
    "wea_target": wea["target"],
    "compute": False,
})
```

Single-timestep CIE standard sky file:

```python
cie = await call_tool("create_cie_standard_sky", {
    "garden_root": garden_root,
    "identifier": "summer_sunny_sky",
    "month": 6,
    "day": 21,
    "time": "12:00",
    "sky_type": "sunny",
    "latitude": 40,
    "longitude": -105,
    "ground_reflectance": 0.2,
})
```

Single-timestep climate-based sky file:

```python
climate = await call_tool("create_climate_based_sky", {
    "garden_root": garden_root,
    "identifier": "summer_climate_sky",
    "month": 6,
    "day": 21,
    "time": "12:00",
    "direct_normal_irradiance": 800,
    "diffuse_horizontal_irradiance": 120,
    "output_mode": 0,
})
```

## Boundaries

- WEA and SkyMatrix outputs are Garden artifacts, not Honeybee model properties.
- Single-timestep `.sky` outputs are Garden artifacts with `radiance_sky_file` targets, not annual sky matrices.
- Pass returned targets downstream; do not copy WEA file text or sky patch arrays through Agent context.
- `create_sky_matrix` accepts exactly one source shape: `wea_target`, `weather_target` / `epw_path`, or `location`.
- `compute=false` stores compact setup parameters. Use `compute=true` only when the user needs persisted direct/diffuse patch values immediately.
- `create_cie_standard_sky` and `create_climate_based_sky` persist command-backed Radiance scene includes starting with `!gensky` or `!gendaylit`. They do not execute Radiance binaries.
- For simple natural requests like "clear summer noon", `create_cie_standard_sky` accepts `season="summer"`, `hour=12`, and `sky_condition="clear"`; planned calls may still use explicit `month=6`, `day=21`, and `time="12:00"`.
- Numeric `time_zone` offsets like `-5` / `-7` are accepted on single-timestep sky tools and normalized to common Radiance tokens such as `EST` / `MST`.
- Natural output folders such as `sky_files` are normalized to the Garden artifact path `artifacts/radiance/sky`.
- Natural WEA folder hints such as `wea` or `radiance/wea` are normalized to `artifacts/radiance/wea`.
- Natural SkyMatrix folder hints such as `imports/weather`, `radiance/sky_matrix`, or `sky_matrix` are normalized to `artifacts/radiance/sky`.
- Use outer Code Mode `search` / `get_schema` before `execute` if discovery is needed. Do not call `await call_tool("search", ...)` inside `execute`; it is a residual Agent cost smell, not the recommended path.
- This path does not run a complete Radiance recipe. Treat it as sky setup before the deterministic-pass `start_radiance_grid_run`, `start_radiance_view_run`, or `start_radiance_matrix_run` path.

## Success Criteria

- WEA tools return a `wea_file` target and create `artifacts/radiance/wea/<identifier>.wea`.
- Single-timestep sky tools return a `radiance_sky_file` target and create `artifacts/radiance/sky/<identifier>.sky`.
- `create_sky_matrix` returns a `sky_matrix` target and creates `artifacts/radiance/sky/<identifier>.json`.
- `summary_view.patch_count` is `145` for default Tregenza sky and `577` for high-density Reinhart sky.

## Evidence

- Agent integration smoke added 2026-04-29 verifies one Code Mode `execute` can create an ASHRAE clear-sky WEA, create a compact SkyMatrix target from it, and persist both Garden artifacts.
- Agent integration smoke added 2026-04-29 verifies one Code Mode `execute` can create both a CIE standard `!gensky` sky file and a climate-based `!gendaylit` sky file.
- Supervised external Matrix task 26 on 2026-04-30 verifies a natural MiniMax Agent can create a CIE `radiance_sky_file` artifact under `artifacts/radiance/sky` and return its compact target. The pre-fix run exposed numeric time-zone and `sky_files` output-path drift; after normalization, retained runtime dropped from about `64s` to `33.240s`.
- Supervised external Matrix task 27 on 2026-04-30 verifies a natural MiniMax Agent can create an ASHRAE clear-sky `wea_file` target and compact `sky_matrix` target without EPW search/download. Pre-fix runs exposed weather-folder/SkyMatrix-folder drift and unnecessary `compute=true`; after normalization and `compute=false` prompt tightening, the retained run passed at `39.056s` with 3 inner MCP calls and no repeated MCP tools.
