# Create Radiance Modifiers

Agent-verified path for creating a reusable project-specific Honeybee Radiance modifier and applying it to Honeybee objects through compact Garden targets.

Use these tools when the user needs a project-specific Radiance modifier instead of a standards-library identifier from `search_radiance_library_objects`.

## Tool Choice

- Opaque surface modifier: `create_radiance_opaque_modifier`
  - SDK object: `Plastic`
- Mirror modifier: `create_radiance_mirror_modifier`
  - SDK object: `Mirror`
- Metal modifier: `create_radiance_metal_modifier`
  - SDK object: `Metal`
- Translucent modifier: `create_radiance_trans_modifier`
  - SDK object: `Trans`
- Glass modifier: `create_radiance_glass_modifier`
  - SDK object: `Glass`

Prefer the specific create tool when you know the material kind. `create_radiance_modifier` is a bounded compatibility alias for common opaque/plastic and simple glass requests, but it is not a reason to skip the specific tools in planned calls.

## Compact Garden Target Path

For reusable project modifiers, pass:

```json
{
  "garden_root": "D:/path/to/Garden",
  "return_object_dict": false
}
```

The create result returns a `target` / `modifier_target` with:

- `target_type`: `garden_properties_library_object`
- `domain`: `honeybee_radiance`
- `object_family`: `modifier`

Use that target directly in `edit_honeybee_face`, `edit_honeybee_aperture`, `edit_honeybee_door`, or `edit_honeybee_shade` `modifier` / `modifier_blk` fields.
For apertures, `radiance_modifier` and `radiance_modifier_target` are accepted aliases, but the canonical parameter remains `modifier`.

## Input Shapes

For `opaque`, `mirror`, `metal`, and `trans`, use one of:

```json
{"rgb_reflectance": 0.45}
```

or:

```json
{
  "r_reflectance": 0.3,
  "g_reflectance": 0.35,
  "b_reflectance": 0.4
}
```

Do not mix `rgb_reflectance` with individual RGB reflectance channels.

For `glass`, the SDK uses transmittance or transmissivity rather than reflectance. Use one of:

```json
{"rgb_transmittance": 0.6}
```

```json
{
  "r_transmittance": 0.5,
  "g_transmittance": 0.55,
  "b_transmittance": 0.6
}
```

```json
{"rgb_transmissivity": 0.6}
```

```json
{
  "r_transmissivity": 0.5,
  "g_transmissivity": 0.55,
  "b_transmissivity": 0.6
}
```

Do not describe glass inputs as reflectance in user-facing output; say transmittance or transmissivity.
The tool also accepts natural Agent shapes such as `transmission`, `transmittance`, or `transmissivity`, and `[r, g, b]` lists for glass RGB values. Treat these as compatibility shapes; planned calls should still use the canonical examples above.

If you need to confirm an existing Garden before applying a modifier, call `get_garden` or `get_base_honeybee_model`. Do not use filesystem probes or Python imports inside Code Mode.

## Minimal Examples

Opaque modifier saved to Garden:

```json
{
  "name": "create_radiance_opaque_modifier",
  "arguments": {
    "garden_root": "D:/path/to/Garden",
    "identifier": "warm_matte_wall",
    "rgb_reflectance": 0.52,
    "return_object_dict": false
  }
}
```

Glass modifier saved to Garden:

```json
{
  "name": "create_radiance_glass_modifier",
  "arguments": {
    "garden_root": "D:/path/to/Garden",
    "identifier": "clear_visible_glass",
    "rgb_transmittance": 0.64,
    "refraction_index": 1.52,
    "return_object_dict": false
  }
}
```

## Evidence

- Deterministic MCP tests added 2026-04-29 verify simple and full RGB inputs for opaque/mirror/metal/trans, transmittance/transmissivity inputs for glass, Garden Properties Library target saving, and tool search discovery.
- 2026-04-30 external MiniMax supervised task 24 verified a project modifier apply workflow: existing Garden/model discovery, reusable modifier creation, aperture search, `edit_honeybee_aperture(modifier=<Garden Properties Library target>)`, and `validate_honeybee_model`. Latest retained run passed in `54.295s` with 8 outer tool calls and 6 inner MCP calls.
