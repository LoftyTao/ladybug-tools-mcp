# Dragonfly Skill Overview

Use this category when the Agent needs Dragonfly Model, Building, Story, Room2D, context shade, UWG, Dragonfly visualization, or Dragonfly-to-Honeybee handoff.

## Preconditions

- Treat Dragonfly as a core Ladybug Tools model family, parallel to Honeybee and Fairyfly.
- Use `base_dragonfly_model` and Dragonfly typed targets; do not mix them with Honeybee model targets unless a conversion tool is requested.
- Decide whether the user wants native Dragonfly authoring, UWG weather morphing, visualization, or downstream Honeybee/Energy handoff.

## Common Scenarios

- Author district/building massing with Room2D, Story, and Building hierarchy.
- Apply Dragonfly Energy, Radiance, window, shading, or UWG properties.
- Validate or summarize a Dragonfly Model.
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

- Stop before inventing URBANopt Energy, Electric Grid, or District Thermal behavior.
- Stop when a Honeybee-only operation would require conversion and the user has not authorized conversion.
- Stop when UWG is blocked or still running; return the run target and current status.

## References

- `dragonfly-authoring.md`
