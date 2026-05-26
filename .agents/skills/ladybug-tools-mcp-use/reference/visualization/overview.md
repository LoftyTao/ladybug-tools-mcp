# Visualization Skill Overview

Use this category when the Agent needs VisualizationSet creation, composition, legend editing, chart generation, HTML export, SVG export, or user-facing preview artifacts.

## Preconditions

- Start from a real model, object, result, DataCollection, or existing VisualizationSet target.
- Decide whether the user needs a target handoff, an exported artifact, or a browser-openable preview.
- Use real model/result targets; do not fabricate analysis colors, values, or geometry.

## Common Scenarios

- Convert Honeybee models, Rooms, or Faces to VisualizationSet targets.
- Compose multiple VisualizationSets.
- Create/edit 2D LegendParameters.
- Export VisualizationSet targets to HTML or SVG.
- Convert DataCollection results to chart VisualizationSets.

## Usual MCP Route

1. Create or reuse the VisualizationSet target.
2. Compose or adjust legends only when needed.
3. Export to HTML/SVG when the user asks for an artifact.
4. Return target, artifact path, geometry counts, and summary views.

## Stop Conditions

- Stop when the requested visualization requires analysis results that do not exist yet.
- Stop before returning large VisualizationSet dictionaries unless explicitly requested for debug/export.
- Stop when export fails and return bounded artifact diagnostics.
- Do not use local plotting scripts for Energy/DataCollection charts unless the user explicitly asks for external plotting or MCP lacks the requested capability and you disclose it.

## References

- `visualize-honeybee-model.md`
- `visualize-honeybee-room-face.md`
- `visualize-honeybee-room-attribute-svg.md`
- `visualize-honeybee-face-attribute-svg.md`
- `compose-visualization-sets.md`
- `create-edit-2d-legend-parameter.md`
- `visualization-set-to-html.md`
- `visualization-set-to-svg.md`
- `visualize-data-collection-chart.md`
