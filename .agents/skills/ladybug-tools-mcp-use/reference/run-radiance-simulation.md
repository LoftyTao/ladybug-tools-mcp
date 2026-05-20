# Run Radiance Simulation

Agent-verified paths for point-in-time grid illuminance, point-in-time view rendering, annual/matrix irradiance, dynamic-state grid simulation, and Luminaire/IES library coexistence plus daylight simulation from Garden-managed model, sky, WEA, SensorGrid, View, library, and Radiance parameter targets.

Use this path when the user asks for point-in-time daylight grids, point-in-time views/images, annual daylight, annual irradiance, cumulative radiation, or Radiance recipe setup. For completed visual outputs, use the postprocess tools below instead of moving result files through context.

## Tool Choice

- Runtime config: `get_ladybug_tools_config`
  - Use when Radiance/OpenStudio/EnergyPlus discovery is uncertain. The MCP service can apply the Ladybug Tools SDK config paths to process PATH before checking Radiance commands.
- Parameters: `create_radiance_parameters`
  - Inputs are `recipe_type`, `detail_level`, and `additional_par`.
  - Use `point-in-time-grid` / `daylight-factor` for rtrace, `point-in-time-view` for rpict, and `annual-daylight` / `annual-irradiance` / `cumulative-radiation` for rfluxmtx.
- Grid recipes: `start_radiance_grid_run`
  - Use for `point_in_time` and `daylight_factor`.
  - Point-in-time requires `sky_file_target` or inline `sky`.
- View recipes: `start_radiance_view_run`
  - Use for `point_in_time` views/images.
  - Requires `sky_file_target` or inline `sky`.
- Matrix recipes: `start_radiance_matrix_run`
  - Use for `annual_daylight`, `annual_irradiance`, or `cumulative_radiation`.
  - Requires `wea_target` or Garden-relative `wea_path`.
- Run ledger: `get_radiance_run`, `list_radiance_runs`, `list_radiance_run_outputs`.
- `get_radiance_run` can repair a stale `running` ledger when a background recipe has already written final outputs and the recipe progress log is complete.
  - Run ledgers are written through a locked atomic replace path. If an older or interrupted ledger file contains one valid JSON object followed by stale trailing bytes, run readers recover the first valid object instead of surfacing `JSONDecodeError: Extra data`.
  - When the user asks to wait or poll until completion, pass `wait_seconds` and a small `poll_interval` to a single `get_radiance_run` call. Do not issue many immediate one-status calls from separate `execute` blocks.
- Radiance artifact search: `search_radiance_sensor_grids`, `search_radiance_sky_files`, or `list_garden_artifacts`.
  - SensorGrids and sky files are Garden artifacts. Do not use Honeybee room/face/window search as the planned path for them, although `search_honeybee_model_objects(object_type="radiance_sensor_grid")` now redirects to compact artifact targets for recovery.
- View image postprocess: `list_radiance_hdr_images`, `radiance_hdr_to_falsecolor`, `radiance_hdr_to_gif`.
  - This MCP path only supports `.hdr` inputs. Do not request `.pic` or `.unf` tools.
- SensorGrid visual postprocess: `list_radiance_grid_results`, `radiance_grid_result_to_visualization_set`.
  - Stop at `visualization_set_target`; use `visualization_set_to_html` or `visualization_set_to_svg` as the generic downstream export.
  - For object-hosted grids created with `create_radiance_sensor_grid_from_object`, prefer `grid_data_display_mode="SurfaceWithEdges"` when the user wants surface/mesh coloring.
  - Use `compose_model_analysis_visualization_set` to overlay a saved model-context VisualizationSet with a saved analysis/result VisualizationSet. This avoids hand-editing VisualizationSet JSON for model + result scenes.

## Main Path

For daylight evidence, create at least one Room with a small exterior Aperture before attaching grids or views. A model with no window can still exercise parts of the toolchain, but it is a weak daylight simulation case.

### Point-In-Time Grid, Low-Replay Shape

Use this shape for vague "is this room bright enough right now?" or "small daylight grid proof" prompts. Keep setup and run as separate user-level checkpoints. If the setup checkpoint already exists, search and reuse it instead of rebuilding.

```python
model = await call_tool("create_honeybee_model", {
    "garden_root": garden_root,
    "identifier": "radiance_model",
})
room = await call_tool("create_honeybee_room", {
    "garden_root": garden_root,
    "identifier": "radiance_room",
    "x_dim": 4,
    "y_dim": 3,
    "height": 3,
    "return_object_dict": False,
})
faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "face_type": "wall",
    "boundary_condition": "outdoors",
    "children_scope": room["target"],
})
aperture = await call_tool("create_honeybee_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": faces["matches"][0]["target"],
    "generation_mode": "by_width_height",
    "aperture_width": 1.2,
    "aperture_height": 1.0,
    "sill_height": 0.9,
    "return_object_dict": False,
})
grid = await call_tool("create_radiance_sensor_grid", {
    "garden_root": garden_root,
    "identifier": "workplane_grid",
    "positions": [[0, 0, 0.8], [1, 0, 0.8]],
    "direction": [0, 0, 1],
    "model_target": model["target"],
    "attach_to_model": True,
    "return_object_dict": False,
})
sky = await call_tool("create_cie_standard_sky", {
    "garden_root": garden_root,
    "identifier": "summer_sunny_sky",
    "month": 6,
    "day": 21,
    "time": "12:00",
    "sky_type": "sunny",
})
params = await call_tool("create_radiance_parameters", {
    "recipe_type": "point-in-time-grid",
    "detail_level": "low",
})
started = await call_tool("start_radiance_grid_run", {
    "garden_root": garden_root,
    "model_target": model["target"],
    "sky_file_target": sky["target"],
    "sensor_grid_target": grid["target"],
    "radiance_parameters": params,
    "run_id": "grid_run",
    "workers": 1,
})
ledger = await call_tool("get_radiance_run", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2,
})
if ledger["status"] in {"queued", "running", "pending"}:
    ledger = await call_tool("get_radiance_run", {
        "garden_root": garden_root,
        "run_target": started["target"],
        "wait_seconds": 60,
        "poll_interval": 2,
    })
outputs = await call_tool("list_radiance_grid_results", {
    "garden_root": garden_root,
    "run_target": started["target"],
})
vis = await call_tool("radiance_grid_result_to_visualization_set", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "return_visualization_set": False,
})
context = await call_tool("honeybee_model_to_visualization_set", {
    "garden_root": garden_root,
    "model_target": model["target"],
    "wireframe_only": True,
    "name": "model_context",
    "return_visualization_set": False,
})
overlay = await call_tool("compose_model_analysis_visualization_set", {
    "garden_root": garden_root,
    "model_context_target": context["target"],
    "analysis_visualization_set_target": vis["target"],
    "name": "model_result_overlay",
    "return_visualization_set": False,
})
```

Stop after reporting the run status, grid result folder, and saved VisualizationSet target. Do not start a second grid run just because a result visualization or HTML export failed; first inspect `list_radiance_grid_results` and reuse the completed run target.

### Point-In-Time View, HDR To Falsecolor/GIF

Use this shape for "preview render", "see the interior", "falsecolor image", or "GIF export" prompts. Set up one simple room with daylight openings, one camera view, one sky, and one modest parameter set. Then do one render and at most one falsecolor plus one GIF from the first usable HDR.

```python
view = await call_tool("create_radiance_view", {
    "garden_root": garden_root,
    "identifier": "preview_view",
    "position": [2, -6, 1.5],
    "direction": [0, 1, 0],
    "up_vector": [0, 0, 1],
    "view_type": "v",
    "h_size": 60,
    "v_size": 45,
    "model_target": model["target"],
    "attach_to_model": True,
    "return_object_dict": False,
})
sky = await call_tool("create_cie_standard_sky", {
    "garden_root": garden_root,
    "identifier": "preview_sky",
    "month": 6,
    "day": 21,
    "time": "12:00",
    "sky_type": "sunny",
})
params = await call_tool("create_radiance_parameters", {
    "recipe_type": "point-in-time-view",
    "detail_level": "low",
})
started = await call_tool("start_radiance_view_run", {
    "garden_root": garden_root,
    "model_target": model["target"],
    "view_target": view["target"],
    "sky_file_target": sky["target"],
    "radiance_parameters": params,
    "run_id": "preview_view_run",
    "workers": 1,
})
ledger = await call_tool("get_radiance_run", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2,
})
hdrs = await call_tool("list_radiance_hdr_images", {
    "garden_root": garden_root,
    "run_target": started["target"],
})
first_hdr = hdrs["matches"][0]["target"]
falsecolor = await call_tool("radiance_hdr_to_falsecolor", {
    "garden_root": garden_root,
    "hdr_image_target": first_hdr,
    "identifier": "preview_view_falsecolor",
})
gif = await call_tool("radiance_hdr_to_gif", {
    "garden_root": garden_root,
    "hdr_image_target": first_hdr,
    "identifier": "preview_view_gif",
})
```

Stop after reporting the HDR, falsecolor, and GIF artifact names. If `list_radiance_hdr_images` is empty immediately after completion, wait once with `get_radiance_run(wait_seconds=...)`; do not create a second view, sky, or run until you have clear failure evidence.

Annual/matrix path:

```python
wea = await call_tool("create_ashrae_clear_sky_wea", {
    "garden_root": garden_root,
    "identifier": "clear_sky_wea",
    "location": location,
})
params = await call_tool("create_radiance_parameters", {
    "recipe_type": "annual-daylight",
    "detail_level": "medium",
})
started = await call_tool("start_radiance_matrix_run", {
    "garden_root": garden_root,
    "model_target": model["target"],
    "wea_target": wea["target"],
    "calculation_type": "annual_daylight",
    "radiance_parameters": params,
    "run_id": "annual_daylight_run",
    "workers": 1,
})
```

## Annual Daylight, ASE, sDA, And Glare Metrics

For completed annual daylight runs, use `summarize_annual_daylight_metrics` after `get_radiance_run` reports `completed`. Keep `include_values=false` unless the user explicitly asks for raw values. Report sDA/ASE values with thresholds and provenance; do not declare pass/fail unless the user or selected rating system provides the rule.

For DGP/glare, use `summarize_radiance_glare_metrics` only on a completed glare-capable run. If the tool returns a blocked diagnostic because only HDR/GIF/falsecolor outputs exist, report the image as qualitative screening and do not call it DGP.

## Boundaries

- If a long Radiance setup fails after writes have succeeded, search the current Garden and resume from the existing targets. Do not replay Garden/model/library setup from the top.
- For existing setup, use `get_base_honeybee_model`, `search_radiance_sensor_grids`, and `search_radiance_sky_files` to recover compact targets before calling `start_radiance_grid_run`.
- For broad Agent-style multi-turn tasks, separate "explain workflow", "setup checkpoint", and "run/postprocess" turns. The setup turn should end after assets exist; the run turn should not create geometry, grids, skies, views, or parameters again.
- `create_radiance_parameters` accepts raw Radiance flags such as `ab`, `ad`, `as`, `ar`, and `aa`; prefer the readable `recipe_type` / `detail_level` path unless the user asks for specific flags.
- SensorGrids and Views must be attached to the Honeybee model with `attach_to_model=true`; standalone `.pts` and `.vf` artifacts are useful evidence but are not enough for current recipe inputs.
- If the requested output is surface mesh coloring, create the SensorGrid from a Honeybee object surface instead of explicit points so the attached model carries `SensorGrid.mesh`.
- Point-in-time recipes pass the text inside the `.sky` file to the recipe input named `sky`.
- Annual/matrix recipes pass the resolved `.wea` file path to the recipe input named `wea`.
- `start_radiance_*_run` returns a compact `radiance_run` target and writes a run ledger under `runs/radiance/`.
- Use `list_radiance_run_outputs` or the more specific `list_radiance_hdr_images` / `list_radiance_grid_results` before postprocess tools. Do not move full result files through Agent context.
- If `get_radiance_run` keeps reporting `running`, keep polling through the returned `poll_next` target; do not start a second run unless the user explicitly asks for a fresh `run_id`.
- View image postprocess V1 is intentionally `.hdr -> .hdr/.gif` only.
- SensorGrid visual postprocess V1 intentionally stops at `VisualizationSet`; do not invent Radiance-owned HTML/SVG export tools.
- Radiance grid result VisualizationSet defaults to `use_mesh=false` for model context, matching the project-wide preference for `DisplayFace3D`; pass `use_mesh=true` only when a mesh context is explicitly needed.
- Mixed model/result visualization should use `compose_model_analysis_visualization_set` with saved VisualizationSet targets; do not handwrite a report HTML or hand-merge JSON in Agent space.
- Direct sun hours and advanced recipe-specific postprocessing remain future slices.
- If `get_radiance_run` reports `failed`, treat postprocess as blocked until an output-specific listing such as `list_radiance_grid_results` or `list_radiance_hdr_images` shows real input files. A failed run with `outputs[].path = null` is valid failure evidence, not a VisualizationSet input.
- For view renders, inspect the resulting GIF/HDR preview before calling the task complete. A non-empty image can still be unusable when the camera is aimed at a blank wall, floor, or overexposed surface. If the preview is mostly blank, create a corrected view from inside the room looking toward the aperture and rerun with a new `run_id`.
- After a view run completes, `list_radiance_hdr_images` can be briefly empty while the HDR is still being merged/written. Wait once with `get_radiance_run(wait_seconds=...)` or delay before postprocess; do not immediately start a duplicate view run.
- `radiance_hdr_to_falsecolor` now rejects header-only or otherwise tiny HDR outputs instead of registering them as successful artifacts. If falsecolor fails but `radiance_hdr_to_gif` produces a useful preview, report falsecolor as a failed postprocess and keep the GIF as the usable preview.

## Success Criteria

- `create_radiance_parameters.summary_view.command_name` is `rtrace`, `rpict`, or `rfluxmtx`.
- `start_radiance_*_run` returns `target.target_type == "radiance_run"` and `summary_view.poll_next.tool == "get_radiance_run"`.
- `list_radiance_runs(status="running")` can see the newly queued run.
- `list_radiance_run_outputs` returns known output names even before the background recipe completes.
- `list_radiance_hdr_images` returns only `.hdr` entries and reports `.pic/.unf` as unsupported.
- `radiance_grid_result_to_visualization_set(return_visualization_set=false)` returns a compact `visualization_set_target` for generic export tools.
- Default result summary reports `summary_view.use_mesh == false` unless the caller explicitly opted into mesh context geometry.
- `compose_model_analysis_visualization_set(return_visualization_set=false)` returns a compact overlay `visualization_set_target` that can be passed to `visualization_set_to_html` / `visualization_set_to_svg`.
- View GIF/HDR artifacts are large enough and visually plausible for the stated purpose; do not rely on file existence alone.

## Evidence

- Natural Agent cross test added 2026-04-29 verifies a real point-in-time grid illuminance run from a one-room Garden through SensorGrid, CIE sky, `start_radiance_grid_run`, polling, grid result listing, and VisualizationSet target creation. The pass is real but cost-heavy: `593,955` total tokens, `54` inner MCP calls, `32` Code Mode executes, and `38s` Radiance run time.
- Natural Agent cross test added 2026-04-30 verifies a real point-in-time view render through View, CIE sky, `start_radiance_view_run`, HDR discovery, and image postprocess. The pass recorded `673,093` total tokens, `133` inner MCP calls, and `49s` Radiance run time.
- Supervised external Agent matrix task 30 added 2026-04-30 verifies a fresh point-in-time view render through `start_radiance_view_run`, `get_radiance_run`, `list_radiance_hdr_images`, `radiance_hdr_to_falsecolor`, and `radiance_hdr_to_gif`. The retained run passed at `110.610s`, with `13` outer tool calls, `11` inner MCP calls, and about `38s` Radiance run time; MiniMax streaming token usage was unavailable, so cost is tracked by wall time and tool counts for this run.
- MCP-wide focused MiMo repair on 2026-05-17 verified the point-in-time view HDR -> falsecolor -> GIF path with stricter stop conditions. `radiance_view_falsecolor_gif` moved from `425,147` tokens / `MaxTurnsExceeded` to a functional pass at `305,363` tokens with one completed view run, one HDR, one falsecolor HDR, and one GIF. This is functional evidence, not a low-cost path.
- MCP-wide focused MiMo repair on 2026-05-17 verified the point-in-time grid path after bounded Radiance schema tolerance and equivalent SensorGrid expected-tool handling. `radiance_grid_point_in_time` moved from `366,166` tokens / failed replay to a functional pass at `299,106` tokens with one completed grid run and a saved VisualizationSet artifact. Remaining cost is state replay; do not solve it by adding new Radiance wrappers.
- Natural Agent cross test added 2026-04-30 verifies a real annual/matrix irradiance workflow through WEA and matrix run targets. The pass recorded `311,596` total tokens, `22` inner MCP calls, and `39s` Radiance run time.
- Natural Agent cross test added 2026-04-30 verifies dynamic Radiance properties and shade states flowing into a real grid simulation. The pass recorded `602,661` total tokens, `72` inner MCP calls, and `26s` Radiance run time.
- 2026-05-01 Codex `ladybug_mcp_tester` 20-Task Batch D verified the Honeybee visualization matrix in Task 16: model/room/face VisualizationSets, legend create/edit, `compose_visualization_sets(conflict_strategy=rename)`, HTML export, SVG export, and artifact listing. Task 14 exposed a corrupt `runs/radiance/index.json` with `JSONDecodeError: Extra data` after concurrent grid/view runs; deterministic regression now covers trailing-stale-ledger recovery and atomic index writes. Task 15 confirmed failed Radiance runs should stop postprocess when result folders or HDR files are absent.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 16 verified a fresh point-in-time daylight grid from a windowed office: 9 sensors, CIE sky, `start_radiance_grid_run`, completed `rtrace`, grid result listing, VisualizationSet target, and HTML export. The Agent correctly scoped the result as point-in-time, not annual daylight autonomy.
- 2026-05-01 deterministic regression verifies object-hosted SensorGrid mesh preservation, Radiance grid result `Mesh3D` VisualizationSet output, and target-based `compose_model_analysis_visualization_set` overlay export.
- 2026-05-01 Batch D Task 17 first closed PARTIAL: view run and GIF completed, but the preview framing was mostly blank and falsecolor produced a 65-byte header-only HDR. Main-process correction created `task17_corrected_window_view`, reran a fresh point-in-time view, produced a visually useful GIF preview, and added deterministic coverage so header-only falsecolor output fails instead of being persisted as success.
- Deterministic MCP test added 2026-04-29 verifies parameter creation, grid/view/matrix start scheduling, run ledger polling, output listing, and Tool Search discoverability.
- Agent integration smoke added 2026-04-29 verifies one Code Mode `execute` can prepare model-attached SensorGrid, CIE sky file, and Radiance parameters for a future run without starting a long recipe.
- Deterministic MCP test added 2026-04-29 verifies `.hdr` listing, falsecolor `.hdr` artifact persistence, `.gif` artifact persistence, SDK-style grid result folder discovery, and SensorGrid result `VisualizationSet` target handoff.
