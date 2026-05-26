# Source-Backed Energy Resources

Use this candidate path when a user asks to turn screenshots, cited standards, technical measures, prototype models, or datasheets into reusable Energy resources.

## Preconditions

- Treat this as conservative source-backed authoring, not compliance certification.
- Create or select a Garden before saving resources.
- Use the source to decide what can be created; do not fill missing fields with invented values.

## MCP Route

1. Classify the source as full layered assembly, performance target, schedule/program/load assumption, prototype/reference model concept, or incomplete evidence.
2. Choose an extraction level.
3. Create supported resources through Energy create tools.
4. Save reusable resources directly to the Garden Properties Library when create tools support `garden_root`.
5. Search the saved resources back from the Garden library.
6. Apply the resource pack to a small Honeybee model when useful.
7. Validate with `honeybee_validate_model`.
8. Create one Garden version after the resource-preparation task completes.

## Extraction Levels

- Level A: full layered construction from source-provided material properties.
- Level B: mostly source-backed construction with limited library-backed substitutions and explicit gaps.
- Level C: performance-target resource where only aggregate values are known.
- Level D: simplified draft resource for incomplete sources.

## Success Criteria

- Saved resources are traceable to source-backed fields or explicit assumptions.
- Missing fields and downgraded extraction level are reported.
- Resource targets can be reused from Garden library search.
- A small model validates after assignment when assignment is part of the task.

## Stop Conditions

- Do not treat a U-value limit as a complete construction.
- Do not invent density, specific heat, SHGC, VT, material type, or climate-zone mapping.
- Do not claim regulatory compliance from partial screenshots or source excerpts.
- Do not copy long copyrighted standards text into reports.
- For prototype models, do not say an original IDF was imported unless an actual source file was parsed.
