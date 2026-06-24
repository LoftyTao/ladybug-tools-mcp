# Dragonfly UWG Weather

Status: Agent-verified for local Ladybug Tools EPW reuse and UWG completion in AX5.

Use this reference when the user asks for Dragonfly UWG, Urban Weather Generator, alternative weather, urban microclimate EPW morphing, or a morphed EPW handoff to Energy.

OKF source: `docs/llm-wiki/tools/uwg-tools.md`.

## Tool Order

1. Create or select a Garden and a Dragonfly model target.
2. Prefer an existing Garden weather target via `energyplus_search_weather_files`.
3. For workstation tests, seed Garden weather from `C:\Program Files\ladybug_tools\resources\weather` if the user allows local Ladybug Tools resources.
4. Apply UWG properties with `df_uwg_apply_dragonfly_properties` to model, Building, and ContextShade targets as needed.
5. Create parameters with `df_uwg_create_simulation_parameter`.
6. Write a preview artifact with `df_uwg_dragonfly_model_to_uwg`.
7. Start and poll with `df_uwg_start_simulation` and `df_uwg_poll_simulation`.
8. Inspect outputs with `df_uwg_list_run_outputs`.
9. For charts or downstream checks, call `energyplus_read_weather_file_data` on the morphed `weather_file` target.

## Target Shapes

- `weather_target` must be a Garden `weather_file` target with Garden-relative `epw_path`.
- `model_target` must be a Dragonfly model target from the same Garden.
- `simulation_parameter_target` must have `target_type="uwg_simulation_parameter"` and `domain="dragonfly_uwg"`.
- The morphed output weather target is in `summary_view.run.outputs.weather_target`.

## Stop Conditions

- Stop on EPW preflight failure and return the failed `uwg_run` ledger.
- Stop if the run remains `running`; return `poll_next`.
- Do not continue into EnergyPlus until `df_uwg_poll_simulation` reports `completed` and exposes a morphed `weather_file` target.

## Avoid

- Do not use remote `energyplus_search_epw_map` when a local Ladybug Tools EPW can be seeded for a regression test.
- Do not pass absolute EPW paths directly to UWG tools; register or copy them into the Garden first.
- Do not describe UWG as URBANopt Energy, DES, RNM, OpenDSS, or REopt.
- Do not parse EPW text manually for visualization; use `energyplus_read_weather_file_data`.
