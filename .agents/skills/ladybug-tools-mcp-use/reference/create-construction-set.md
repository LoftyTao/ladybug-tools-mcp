# Create Construction Set

Use this path when the user needs Honeybee Energy material, construction, or `ConstructionSet` objects for later room `construction_set` assignment, object-level construction overrides, or Garden Properties Library reuse.

## Shortest Verified Path

1. `search`
   - Query: `create honeybee energy construction set wall aperture construction`
2. `call_tool` -> `search_energy_library_objects`
   - Required:
     - `query`: `default generic construction set`
   - Optional:
     - `object_family`: `construction_set`
     - `limit`: `3`
3. `call_tool` -> `create_construction_set`
   - Required:
     - `identifier`
   - Optional:
     - `base_construction_set`: a Honeybee Energy ConstructionSet library identifier such as `Default Generic Construction Set`.
     - `return_detail`: `summary` or `full`.

## Authoring Chain

Use this path when custom materials and constructions are needed before the full set.

1. Create material objects.
   - Opaque example: `create_opaque_no_mass_material`
   - Window example: `create_simple_glazing_material`
   - Optional: `return_detail` can be `summary` or `full`.
   - With a Garden, pass `garden_root` and `return_object_dict=false`; use the returned material `target` downstream.
2. Create construction objects.
   - `create_opaque_construction`
   - `create_window_construction`
   - Material inputs may be standards identifiers, payload dicts, or Garden material targets.
   - For a user request like "make the windows low-U" with no exact material layers, call `create_window_construction` directly with `u_factor`, `shgc`, and optional `vt`; do not search and guess library material layer names.
   - With a Garden, pass `garden_root` and `return_object_dict=false`; use the returned construction `target` downstream.
3. Create subset objects.
   - `create_wall_construction_set`
   - `create_aperture_construction_set`
   - Subset objects remain payload authoring for now, but their construction slots can consume Garden construction targets when `garden_root` is provided.
   - If only the exterior window construction needs to change, skip `create_aperture_construction_set`: pass the `create_window_construction.target` directly as `create_construction_set.aperture_set`; the service wraps it as the aperture set.
   - `wall_set`, `floor_set`, and `roof_ceiling_set` can consume a single `OpaqueConstruction` target or identifier and wrap it as the exterior construction for that subset.
4. Create the full set.
   - `create_construction_set`
   - Required: `identifier`
   - Optional: `wall_set`, `aperture_set`, `floor_set`, `roof_ceiling_set`, `door_set`, `shade_construction`, `air_boundary_construction`

## Minimal Example

```json
{
  "name": "search_energy_library_objects",
  "arguments": {
    "query": "default generic construction set",
    "object_family": "construction_set",
    "limit": 3
  }
}
```

```json
{
  "name": "create_construction_set",
  "arguments": {
    "identifier": "agent_construction_set",
    "base_construction_set": "Default Generic Construction Set",
    "return_detail": "full"
  }
}
```

Authoring-chain example:

```json
{
  "name": "create_opaque_construction",
  "arguments": {
    "identifier": "exterior_wall",
    "materials": ["<create_opaque_no_mass_material.target>"],
    "return_detail": "full",
    "garden_root": "<garden root>",
    "return_object_dict": false
  }
}
```

Low-U simple window example:

```json
{
  "name": "create_window_construction",
  "arguments": {
    "identifier": "low_u_agent_window",
    "u_factor": 1.15,
    "shgc": 0.31,
    "vt": 0.58,
    "garden_root": "<garden root>",
    "return_object_dict": false
  }
}
```

For an existing Garden, keep the same pattern: pass `garden_root` and
`return_object_dict=false` on `create_window_construction` so the response has a
reusable `target`. Use that target directly in `create_construction_set.aperture_set`.
Use the returned target, not `save_to_library`, and not a handwritten `WindowConstruction` dict.

Low-U ConstructionSet handoff example:

```json
{
  "name": "create_construction_set",
  "arguments": {
    "identifier": "agent_envelope_set",
    "base_construction_set": "Default Generic Construction Set",
    "aperture_set": "<create_window_construction.target>",
    "garden_root": "<garden root>",
    "return_object_dict": false
  }
}
```

## Expected Output

- `target`: Garden Properties Library target when `garden_root` is provided for material, construction, or final `ConstructionSet` create tools.
- `object_dict`: full Honeybee Energy SDK object dictionary for downstream handoff, omitted when `return_object_dict` is `false`.
- `summary_view`: property values, not only an object dict.
- `return_detail = "summary"`: compact identifiers and key thermal/optical values such as U-value, R-value, thickness, SHGC, and visible transmittance.
- `return_detail = "full"`: includes matrix-style structures such as material `property_matrix`, construction `layer_matrix`, ConstructionSet `slot_matrix`, and ConstructionSet `material_matrix` using `columns + rows`.

## Notes

- The verified Agent smoke covered `search_energy_library_objects -> create_construction_set` using `Default Generic Construction Set` as the base and `return_detail = "full"`.
- A longer custom authoring chain is covered by deterministic tests. Prefer Garden targets over nested `object_dict` values for material -> construction -> object edit handoff.
- `create_window_construction` simple-parameter creation uses the Honeybee Energy SDK `WindowConstruction.from_simple_parameters` path. It is appropriate for compact Agent workflows and avoids repeated library searches for guessed glazing layer identifiers.
- `ConstructionSet` without a base uses Honeybee Energy generic defaults for unspecified slots.
- `WallConstructionSet`, `FloorConstructionSet`, `RoofCeilingConstructionSet`, `ApertureConstructionSet`, and `DoorConstructionSet` are intermediate dict objects and do not have standalone Garden Properties Library targets.
- Low-intelligence Agent runs have repeatedly assumed `create_aperture_construction_set` returns a reusable `target`; it does not. For the common low-U window override, use the direct `create_window_construction.target -> create_construction_set.aperture_set` path.
- 2026-04-25 deterministic MCP cross-test verified `create_opaque_material(return_object_dict=false) -> create_opaque_construction(return_object_dict=false) -> create_wall_construction_set -> create_construction_set(return_object_dict=false)` with Garden targets.
- 2026-04-26 MiniMax Code Mode smoke verified a natural create/edit workflow where a low-U window construction was saved to the Garden library, wrapped into a custom `ConstructionSet`, and assigned to a room without returning expanded construction-set JSON. The same investigation showed lower token cost when tools accept Garden targets, full upstream result envelopes, and standards-library identifiers directly.
- 2026-04-26 deterministic MCP tests verified simple-parameter `create_window_construction` and Agent-style material/ConstructionSet target dictionaries.
- 2026-04-26 MiniMax v16 closed the focused custom model-edit-simulate path to simulation start with a custom low-U window construction and `ConstructionSet`. v17 then failed after trying to pass hand-written `thickness / conductivity` material dicts directly to `create_opaque_construction`, so low-intelligence Agents should prefer `create_window_construction`, `create_opaque_material` targets, standards identifiers, or generic defaults instead of inventing material dicts.
- 2026-04-27 disclosure 推广：工具描述和 tags 已补充官方 HB-Energy Primer /
  论坛常见说法，包括 `Window Construction`、`Window Material`、`U-factor`、
  `U-value`、`SHGC`、`visible transmittance`、`simple glazing system`、
  `ConstructionSet`、`aperture_set` 和 `exterior window slot`。同轮
  deterministic search probes 显示 low-U / U-factor / SHGC 查询会优先命中
  `create_window_construction`，ConstructionSet handoff 查询会优先命中
  `create_construction_set`；这属于 `deterministic-pass`，不是新的
  real-Agent 推荐路径证据。
- 2026-04-27 focused MiniMax C-stage rerun verified the low-U handoff in a
  real Agent path: `create_window_construction.target ->
  create_construction_set.aperture_set -> edit_honeybee_room`. Artifact:
  `tests/.artifacts/agent_integration/manual_staged_metrics_c_low_u_window_disclosure_v1`.
  The run closed at `55,937` tokens and deterministic inspection confirmed both
  rooms used `stage_c_envelope_set`. Residual drift: the Agent used
  `get_base_honeybee_model` as a validation stand-in, so validation flags still need
  explicit `validate_honeybee_model` guidance.
- 2026-04-28 live Garden Round 13 verified the same low-U target handoff on the
  Grasshopper-followed `grasshopper_live_model`: `create_window_construction.target
  -> create_construction_set.aperture_set -> edit_honeybee_room` assigned
  `live_round_13_low_u_envelope` to `north_office` and `north_meeting`.
- 2026-04-28 live Garden Round 14 verified a longer opaque chain on the same
  model: material/opaque construction targets can feed wall/floor/roof subset
  inputs, and the final `ConstructionSet` target can be assigned to rooms. The
  run was high-cost (`92,497` tokens) because intermediate subset tools do not
  return Garden targets and should not be treated like persisted library objects.
