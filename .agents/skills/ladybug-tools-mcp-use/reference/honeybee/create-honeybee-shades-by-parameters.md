# Create Honeybee Shades By Parameters

Use this when the user wants louvers or aperture extruded borders on an existing Honeybee Face or Aperture.

## Preconditions

- Search and pass a typed Face or Aperture target as `host_target`.
- Use `parameters` for geometry inputs; do not put depth/count/distance as top-level fields unless the tool schema requires it.
- Use explicit `honeybee_create_shade` only when the user provides shade `Face3D` geometry.

## MCP Route

1. Search the host Face or Aperture.
2. Call `honeybee_create_shades_by_parameters`.
3. Confirm with `children_scope=<host target>` or a narrow shade search.
4. Validate after larger staged modeling tasks.

## Code Mode Pattern

```python
shades = await call_tool("honeybee_create_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": aperture_target,
    "generation_mode": "louver_by_count",
    "parameters": {
        "depth": 0.45,
        "louver_count": 3,
        "offset": 0.15,
        "base_name": "office_louver"
    }
})
```

## Generation Modes

- `louver_by_count`: Face or Aperture host; requires `depth` and `louver_count`.
- `louver_by_distance_between`: Face or Aperture host; requires `depth` and `distance`.
- `extruded_border`: Aperture host only; requires `depth`.

## Success Criteria

- The result returns `targets` for the generated Shades.
- A child search under the host finds the new Shade identifiers.
- The target parent path matches the intended host.

## Stop Conditions

- Do not guess a host from natural language. Search the model first.
- Do not pass full search responses as `host_target`.
- This wrapper does not expose a parametric `overhang` mode. Use `honeybee_create_shade` only when explicit Face3D shade geometry is available, or record the overhang as a service capability gap.
- For room -> wall -> window -> shade workflows, use `subface-shade-stage-short-path.md` to keep the chain compact.
