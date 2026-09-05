# Dragonfly UWG Weather

Status: Agent-verified for local Ladybug Tools EPW reuse and UWG completion in AX5.

Use this reference when the user asks for Dragonfly UWG, Urban Weather Generator, alternative weather, urban microclimate EPW morphing, or a morphed EPW handoff to Energy.

## Tool Order

1. Create or select a Garden and a Dragonfly model target.
2. Prefer an existing Garden weather target via `EP_search_weather_files`.
3. If no existing target is available, read `weather://catalog`, select a station, and call `EP_import_local_weather` with the current `garden_root` and `source_path="weather://files/<station>"`.
4. Apply UWG properties with `DF_uwg_apply_dragonfly_properties` to model, Building, and ContextShade targets as needed.
5. Create parameters with `DF_uwg_create_simulation_parameter`.
6. Write a preview artifact with `DF_uwg_dragonfly_model_to_uwg`.
7. Start and poll with `DF_uwg_start_simulation` and `DF_uwg_poll_simulation`.
8. Inspect outputs with `DF_uwg_list_run_outputs`.
9. For charts or downstream checks, call `EP_read_weather_file_data` on the morphed `weather_file` target.

## Target Shapes

- `weather_target` must be a Garden `weather_file` target with Garden-relative `epw_path`.
- `model_target` must be a Dragonfly model target from the same Garden.
- `simulation_parameter_target` must have `target_type="uwg_simulation_parameter"` and `domain="dragonfly_uwg"`.
- The morphed output weather target is in `summary_view.run.outputs.weather_target`.

## Stop Conditions

- Stop on EPW preflight failure and return the failed `uwg_run` ledger.
- Stop if the run remains `running`; return `poll_next`.
- Do not continue into EnergyPlus until `DF_uwg_poll_simulation` reports `completed` and exposes a morphed `weather_file` target.

## Avoid

- If the catalog lacks the location, direct the user to `https://climate.onebuilding.org/`; after an extracted local EPW/DDY/STAT folder is available, import it with `EP_import_local_weather`.
- Do not pass absolute EPW paths directly to UWG tools; register or copy them into the Garden first.
- Do not describe UWG as URBANopt Energy, DES, RNM, OpenDSS, or REopt.
- Do not parse EPW text manually for visualization; use `EP_read_weather_file_data`.
