# Source-Backed Energy Resources

Status: agent-observed candidate after Codex `ladybug_mcp_tester` Batch A on 2026-05-01.

Use this path when a user asks to turn screenshots, cited standards, technical measures, prototype models, or datasheets into reusable Energy resources. Keep the path conservative: create what the source supports, record uncertainty, and avoid claiming compliance.

## Stable Candidate Path

1. Enter the Garden gate first. Create or select a Garden before saving resources.
2. Classify the source:
   - complete layered assembly
   - performance limit such as U-value / SHGC / VT
   - schedule/program/load assumption
   - prototype/reference model concept
   - incomplete or cropped evidence
3. Prefer full layered materials and constructions when the source provides enough fields.
4. If fields are missing, record missing fields and downgrade the extraction level instead of inventing values.
5. Save reusable resources directly to the Garden Properties Library when create tools support `garden_root` and compact returns.
6. Search the saved resources back from the Garden library to prove reuse.
7. Apply the resource pack to a small Honeybee model and call `validate_honeybee_model`.
8. Create one Garden version after the user-level resource-preparation task is complete.

## Extraction Levels

- Level A: full layered construction from source-provided material properties.
- Level B: mostly source-backed construction with limited library-backed substitutions and explicit gaps.
- Level C: performance-target resource where only aggregate values are known.
- Level D: simplified draft resource for incomplete sources.

## Boundaries

- Do not treat a U-value limit as a complete construction.
- Do not invent density, specific heat, SHGC, VT, material type, or climate-zone mapping.
- Do not claim regulatory compliance from partial screenshots or source excerpts.
- Do not copy full copyrighted standards or long table text into reports.
- Distinguish `source-derived` resources from `inferred mapping` resources.
- For prototype models, do not say an original IDF was imported unless an actual source file was parsed.

## Observed Batch A Evidence

Task 01 used a mock envelope screenshot and closed as PARTIAL:

- Created reusable Garden materials/constructions/construction set.
- Applied the construction set to a small Honeybee model.
- `validate_honeybee_model` returned valid with zero issues.
- Missing layer properties were recorded instead of fabricated.
- Some library-backed substitutions were needed for incomplete layers, so the extraction level was recorded as Level B.

Task 02 used a cropped mock screenshot and closed as PARTIAL:

- Created a Level D draft construction set.
- Did not create window resources because SHGC and VT were missing.
- Used `NoMass` only for unreadable insulation portions.
- Proved reuse with Garden library search and object readback.

Task 03 used DOE / PNNL prototype-model concepts and closed as PASS:

- Created reusable schedules, program type, construction set, setpoint, and HVAC mapping resources.
- Applied them to a small Honeybee model and validated successfully.
- Clearly separated source-derived library concepts from inferred Garden mappings.

## Cost Notes

- Material-name mismatch causes repeated standards-library searches, especially for plaster, mortar, and concrete terms.
- Search by functional prototype terms like `OfficeMedium`, `MediumOffice`, or `Generic Office` is more effective than searching only `DOE` or `prototype`.
- Prefer compact provenance and resource targets over returning full object bodies.
