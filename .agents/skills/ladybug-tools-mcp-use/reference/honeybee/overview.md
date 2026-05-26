# Honeybee Skill Overview

Use this category when an Agent needs to author, search, edit, relate, validate, transform, or remove Honeybee Model objects through Ladybug Tools MCP.

## Preconditions

- Work from a Garden-backed Honeybee Model target or the current Garden base Honeybee Model.
- Use typed targets returned by MCP tools for Rooms, Faces, Apertures, Doors, Shades, and the Model.
- Keep geometry as SDK-compatible dictionaries or existing typed targets; do not patch HBJSON strings.
- After Room condition, program, construction, or HVAC-related edits, check that the Room is still suitable for the downstream Energy or Radiance workflow before running simulation.

## Common Scenarios

- Create a Honeybee Model, Room, Face, Aperture, Door, or Shade.
- Expand a live model with adjacent rooms, windows, shades, and interior doors.
- Search natural-language object references into typed targets before editing.
- Edit, transform, or remove existing model objects.
- Validate the model before Energy, Radiance, Visualization, or Ironbug workflows.

## Usual MCP Route

1. Confirm the Garden and Honeybee Model target.
2. Search existing host objects when the request edits, removes, or attaches to them.
3. Pass only `matches[i].target`, create result `target`, or model `target` into downstream tools.
4. Call the focused create/edit/remove/operate/relate tool in Code Mode.
5. Verify with narrow search, relationship inspection, or `honeybee_validate_model`.
6. Return compact targets, counts, validation status, and receipts.

## Stop Conditions

- Stop when the host object is ambiguous across object types or parent paths.
- Stop when validation exposes geometry or schema errors that the user did not ask you to repair.
- Stop after a successful stage summary in large staged workflows; do not create downstream simulation assets unless requested.
- Do not invent Honeybee search or save tools. Use the MCP tools in the referenced files.

## References

- `create-honeybee-model-and-confirm-base-model.md`
- `create-honeybee-room.md`
- `create-honeybee-face-and-shade.md`
- `create-honeybee-apertures-by-parameters.md`
- `create-honeybee-interior-door.md`
- `create-honeybee-shades-by-parameters.md`
- `search-honeybee-model-objects-natural-language.md`
- `edit-honeybee-model.md`
- `edit-honeybee-face-and-room.md`
- `edit-honeybee-subfaces-and-shade.md`
- `operate-honeybee-objects.md`
- `relate-honeybee-model.md`
- `validate-honeybee-model.md`
- `remove-honeybee-room.md`
- `remove-honeybee-face.md`
- `remove-honeybee-aperture.md`
- `remove-honeybee-door.md`
- `remove-honeybee-shade.md`
- `live-honeybee-model-expansion.md`
- `subface-shade-stage-short-path.md`
