# Create Construction Set

Use this when the user needs Honeybee Energy material, construction, or `ConstructionSet` objects for Room construction assignment, object-level overrides, or Garden reuse.

## Preconditions

- Use standards identifiers for generic baseline sets.
- Use custom material/construction tools only when the user provides enough data or asks for a performance target.
- Save reusable materials, constructions, and final ConstructionSets with `garden_root` and compact returns.

## MCP Route

1. Optionally search standards with `energy_search_energy_library_objects`.
2. Create materials when source data supports layers.
3. Create constructions from material targets or simple performance parameters.
4. Create the full ConstructionSet.
5. Pass the ConstructionSet target to `honeybee_edit_room.construction_set`.

## Baseline Pattern

```python
construction_set = await call_tool("energy_create_construction_set", {
    "identifier": "agent_construction_set",
    "base_construction_set": "Default Generic Construction Set",
    "garden_root": garden_root,
    "return_object_dict": False
})
```

## Low-U Window Pattern

```python
window = await call_tool("energy_create_window_construction", {
    "identifier": "low_u_agent_window",
    "u_factor": 1.15,
    "shgc": 0.31,
    "vt": 0.58,
    "garden_root": garden_root,
    "return_object_dict": False
})

construction_set = await call_tool("energy_create_construction_set", {
    "identifier": "agent_envelope_set",
    "base_construction_set": "Default Generic Construction Set",
    "aperture_set": window["target"],
    "garden_root": garden_root,
    "return_object_dict": False
})
```

## Success Criteria

- Saved create tools return Garden Properties Library targets.
- `summary_view` includes key thermal/optical values.
- `return_detail="full"` can expose matrices such as layer, slot, and material matrices when detailed inspection is requested.

## Stop Conditions

- Do not treat a U-value target as a full layered construction.
- Do not use `save_to_library`; use `garden_root` and returned targets.
- Do not assume `energy_create_aperture_construction_set` returns a reusable target. For common low-U overrides, pass `energy_create_window_construction.target` directly to `energy_create_construction_set.aperture_set`.
- Keep construction-set evidence in LLM-Wiki.
