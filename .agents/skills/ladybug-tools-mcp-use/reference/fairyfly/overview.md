# Fairyfly Skill Overview

Use this category when the Agent needs Fairyfly 2D heat-transfer authoring, THERM export, THERM runtime execution, or Fairyfly result visualization.

## Preconditions

- Treat Fairyfly as a core Ladybug Tools model family, parallel to Honeybee and Dragonfly.
- Confirm Fairyfly tools are registered; they are Windows/runtime dependent.
- Confirm THERM runtime availability before promising completed results.
- Use Fairyfly model targets and inline material dictionaries according to each tool schema.

## Common Scenarios

- Create a Fairyfly Model, material, shape, and boundary.
- Validate 2D geometry and boundary setup.
- Write a `.thmz` package.
- Start and poll a THERM run.
- Read temperature, heat-flux, or U-Factor summaries.
- Convert Fairyfly models or THERM results to VisualizationSet targets.

## Usual MCP Route

1. Create or retrieve the Fairyfly Model target.
2. Add materials, shapes, and boundaries.
3. Validate before THERM export.
4. For runtime work, write THMZ, start THERM, then poll.
5. Read result targets only after the run completes.
6. Export VisualizationSet artifacts only when the user asks for visual output.

## Stop Conditions

- Stop when THERM runtime is unavailable and report `blocked`.
- Stop before inventing heat-transfer results from geometry alone.
- Stop when a requested result is not present in completed outputs.

## References

- `fairyfly-authoring.md`
