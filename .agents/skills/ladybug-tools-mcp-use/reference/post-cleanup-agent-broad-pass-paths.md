# Post-Cleanup Agent Broad Pass Paths

Use this reference when a natural-language Agent task resembles the 2026-05-18 post-cleanup production sweep. These paths passed with `mimo-v2.5-pro` after compatibility surfaces, old fields, old tool names, and automatic fallback behavior were removed.

## Reusable Rules

- Work in Garden mode and keep each turn to one stage: explain, create or inspect, then verify or report.
- After a write succeeds, resume from persisted Garden state. Search compact targets and validate once instead of replaying the whole setup.
- Do not add aliases, old fields, or fallback wrappers to smooth Agent behavior. Improve tool search text, schema descriptions, or this reference instead.
- When a run may still be executing, report the run ledger state. Do not force EUI, Radiance images, UWG morphed weather, or THERM results unless the ledger shows completed outputs.

## Verified Scenario Patterns

| Scenario | Passed path |
| --- | --- |
| `honeybee_adjacent_rooms_openings` | Create one compact two-room model, set adjacency, create one parameterized exterior window, one interior door, one simple shade, then validate and inspect counts. |
| `honeybee_geometry_transform_repair` | Create or reuse one simple room, apply one move and one vertical rotation, then validate the transformed model without rebuilding. |
| `energy_envelope_low_u_window` | Create or reuse one room, call `create_window_construction` with U-factor/SHGC/VT, pass its target directly to `create_construction_set`, assign to the room, then validate. |
| `energy_start_poll_eui` | Prepare one model and one Garden-managed weather file, call `start_energy_run` once, poll `get_energy_run`, and read EUI only if already completed. |
| `energy_ventilation_pv_fan` | Create one room with one aperture, set simple ventilation properties on the aperture, create one ZoneVentilation fan and attach it to the room, create one Shade plus `create_pv_properties(mounting_type="FixedRoofMounted")`, attach PV properties to the Shade, then validate and inspect compact room/shade `energy_properties` summaries. |
| `dragonfly_massing_visualization` | Create compact Dragonfly Room2D/Story/Building/Model, validate, then export model and envelope-edge VisualizationSets; use vtk.js only for reusable asset export. |
| `dragonfly_story_adjacency_cleanup` | Create Room2Ds, Story, Building, solve Story adjacency, inspect summary, then validate. |
| `dragonfly_web_view_slot_split` | Create one Garden, call `start_web_view_mode` once, then create Dragonfly and Honeybee models in their separate base slots with `set_base`; use `get_base_dragonfly_model`, `get_base_honeybee_model`, Dragonfly summary, Honeybee object search, and validation to prove the split. |
| `fairyfly_boundary_visualization` | Create Fairyfly model/material/shape/boundary, validate, then convert to VisualizationSet. If THERM runtime is unavailable, keep authoring evidence separate from execution claims. |
| `flowerpot_active_context_handoff` | Create a Flowerpot for a Garden model/version, then use `get_active_flowerpot_context`; keep Flowerpot opaque. |
| `web_view_live_preview_handoff` | Start Web View Mode once, do normal Garden modeling or visualization work, then stop Web View Mode. Do not invent preview-refresh tools. |

## Boundaries

- `radiance_grid_point_in_time` and `radiance_view_falsecolor_gif` have focused prior passes, but the 2026-05-18 broad pressure run still replayed setup. Keep those workflows staged and high-cost until a retained low-replay rerun passes.
- `energy_ventilation_pv_fan` still needed repeated Honeybee object searches in the focused rerun. Treat the compact room/shade `energy_properties` summaries as the reuse path; do not add fan/PV aliases or wrapper tools.
- `dragonfly_web_view_slot_split` is a retained pass, but it remains high-cost. Use `set_base`, not `set_as_base`, and keep Honeybee and Dragonfly slots separate instead of adding a generic model slot.
- UWG broad runs in this sweep were blocked or failed under provider/runtime pressure. Use the UWG reference for deterministic tool shape, but do not describe the latest broad UWG path as retained-pass.
