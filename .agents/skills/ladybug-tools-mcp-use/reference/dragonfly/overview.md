# Dragonfly Skill Overview

Use this category for Dragonfly-facing workflows: `df_*`, `df_des_*`, `df_grid_*`, `df_uwg_*`, `df_urbanopt_*`, Dragonfly base-model Garden helpers, and Ironbug-to-Dragonfly bridge tools. The AX1 core authoring/search/attribute/visualization path is Agent-verified through Codex-native MCP. AX5 UWG local-weather morphing is Agent-verified through Codex-native MCP. AX6 URBANopt Energy completion is Agent-verified through Codex-native MCP; DES sys-param remains blocked until `config_get_runtime_config.summary_view.engines.des_gmt.available=true`. AX7 Electric Grid authoring and runtime-blocked ledger handling are Agent-verified through Codex-native MCP. The broader Dragonfly namespace remains deterministic-contract-pass until the remaining cross-test suite is retained.

## Preconditions

- Treat Dragonfly as a core Ladybug Tools model family, parallel to Honeybee and Fairyfly.
- Call Dragonfly tools inside Code Mode `execute` with `await call_tool(...)`, just like other domain tools.
- Use `base_dragonfly_model` and Dragonfly typed targets; do not mix them with Honeybee model targets unless a conversion tool is requested.
- Decide whether the user wants native Dragonfly authoring, UWG weather morphing, visualization, or downstream Honeybee/Energy handoff.

## Common Scenarios

- Author district/building massing with Room2D, Story, and Building hierarchy.
- Apply Dragonfly Energy, Radiance, window, shading, or UWG properties.
- Validate, search, filter, or visualize a Dragonfly Model.
- Convert Dragonfly to Honeybee for downstream Honeybee/Energy/Ironbug tools.
- Produce Dragonfly VisualizationSet, vtk.js, or UWG morphed weather targets.

## Usual MCP Route

1. Create or retrieve the Dragonfly Model target.
2. Build Room2D -> Story -> Building hierarchy.
3. Search existing Dragonfly objects before editing.
4. Apply Dragonfly-specific properties or run UWG only when requested.
5. Validate, visualize, convert, or hand off to Energy.
6. Return compact Dragonfly targets, summary views, and downstream handoff targets.

## Stop Conditions

- For URBANopt Energy, keep to the `df_urbanopt_*` path; for Electric Grid, keep to `df_grid_*`; stop before crossing these runtime families without a user request.
- Stop when a Honeybee-only operation would require conversion and the user has not authorized conversion.
- Stop when UWG is blocked or still running; return the run target and current status.

## References

- `dragonfly-authoring.md`
- `df-uwg-weather.md`
- `urbanopt-energy.md`
- `df-grid-electric.md`
