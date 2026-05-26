# Create Radiance Sky And WEA

Use this when the user asks for Radiance sky setup, CIE standard sky, climate-based sky, WEA files, clear-sky studies, sky matrices, or sky inputs before incident radiation/daylight workflows.

## Preconditions

- WEA and SkyMatrix outputs are Garden artifacts, not Honeybee model properties.
- Single-timestep `.sky` outputs are `radiance_sky_file` targets.
- Pass returned targets downstream; do not copy WEA text or sky patch arrays through context.

## Tool Choice

- `radiance_create_wea_from_weather_file`: from Garden `weather_file` target.
- `radiance_create_ashrae_clear_sky_wea`: theoretical clear sky from a Ladybug `Location`.
- `radiance_create_cie_standard_sky`: single-timestep Radiance `gensky` CIE sky.
- `radiance_create_climate_based_sky`: single-timestep Radiance `gendaylit` sky from irradiance or illuminance.
- `radiance_create_sky_matrix`: WEA/weather/location to SkyMatrix.

## Code Mode Patterns

```python
wea = await call_tool("radiance_create_wea_from_weather_file", {
    "garden_root": garden_root,
    "identifier": "project_wea",
    "weather_target": weather_target
})
sky = await call_tool("radiance_create_sky_matrix", {
    "garden_root": garden_root,
    "identifier": "project_sky",
    "wea_target": wea["target"],
    "north": 0,
    "high_density": False,
    "ground_reflectance": 0.2,
    "compute": False
})
```

```python
cie = await call_tool("radiance_create_cie_standard_sky", {
    "garden_root": garden_root,
    "identifier": "summer_sunny_sky",
    "month": 6,
    "day": 21,
    "time": "12:00",
    "sky_type": "sunny",
    "latitude": 40,
    "longitude": -105,
    "ground_reflectance": 0.2
})
```

## Success Criteria

- WEA tools return a `wea_file` target under `artifacts/radiance/wea`.
- Single-timestep sky tools return a `radiance_sky_file` target under `artifacts/radiance/sky`.
- `radiance_create_sky_matrix` returns a `sky_matrix` target.
- `summary_view.patch_count` is `145` for default Tregenza or `577` for high-density Reinhart.

## Stop Conditions

- `radiance_create_sky_matrix` accepts exactly one source shape: `wea_target`, `weather_target`/`epw_path`, or `location`.
- Use `compute=false` unless the user needs stored patch values immediately.
- These tools do not run a complete Radiance recipe.
- Do not call `await call_tool("search", ...)` inside Code Mode.
