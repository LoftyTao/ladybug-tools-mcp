# Dragonfly Skill Overview

Use this category for Dragonfly-facing workflows: `DF_*`, `DF_des_*`, `DF_grid_*`, `DF_uwg_*`, `DF_urbanopt_*`, Dragonfly base-model Garden helpers, and Ironbug-to-Dragonfly bridge tools. Core authoring/search/attribute/visualization, UWG local-weather morphing, URBANopt Energy completion, and Electric Grid authoring have direct MCP evidence. DES sys-param and Modelica numeric completion remain blocked until `LB_get_runtime_config.summary_view.engines.des_gmt.available=true`.

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

- For URBANopt Energy, keep to the `DF_urbanopt_*` path; for Electric Grid, keep to `DF_grid_*`; stop before crossing these runtime families without a user request.
- Stop when a Honeybee-only operation would require conversion and the user has not authorized conversion.
- Stop when UWG is blocked or still running; return the run target and current status.
- Before rerunning AX6/AX7 numeric runtime branches, use `LB_get_runtime_config` and the retained completion/preflight summaries to inspect Energy output health, local-bundle log evidence, and runtime diagnostics. Start DES/GMT, OpenDSS, RNM, REopt, Modelica, or fully offline branches only when their reported prerequisites are ready; otherwise return the blocked status and missing conditions.
- Before claiming the full Dragonfly cross-test suite is closed, inspect `overall_status` and each passing axis's retained reports, worker status, and terminal next action. For AX6/AX7, require healthy Energy outputs, local-bundle simulation-log evidence, empty online-fetch markers, and ready runtime diagnostics; otherwise return `partial` with the missing conditions.

## References

- `dragonfly-authoring.md`
- `df-uwg-weather.md`
- `urbanopt-energy.md`
- `df-grid-electric.md`
