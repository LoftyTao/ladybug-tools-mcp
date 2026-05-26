# Garden Properties Library

Use this when a reusable Honeybee Energy or Honeybee Radiance SDK object should persist as a Garden resource instead of being passed only as an inline dictionary.

## Preconditions

- Prefer direct Garden-saving create tools when they exist.
- Use `garden_root` and `return_object_dict=false` for low-token target handoff.
- For schedules, set `include_data=false` unless the user needs time-series data.

## MCP Route

1. Create the final reusable object with a direct create tool when possible.
2. Reuse the returned `target`.
3. Confirm or discover later with `library_get_garden_properties_object` or `library_search_garden_properties_objects`.
4. Use `library_save_garden_properties_object` only when the object already exists as a complete SDK `object_dict` and no direct saving create tool is available.

## Code Mode Pattern

```python
schedule = await call_tool("energy_create_schedule_ruleset", {
    "garden_root": garden_root,
    "identifier": "Office Occupancy",
    "default_day_schedule": schedule_day["object_dict"],
    "include_data": False,
    "return_object_dict": False
})
```

Fallback save path:

```python
saved = await call_tool("library_save_garden_properties_object", {
    "garden_root": garden_root,
    "domain": "honeybee_energy",
    "object_family": "schedule",
    "object_dict": full_schedule_dict
})
```

## Success Criteria

- Saved resources return a `garden_properties_library_object` target.
- `persistence_receipt.persisted_path` points under `libraries/...`.
- Later searches return reusable targets for assignment workflows.

## Stop Conditions

- Do not call this `Garden-local`; Garden already implies locality.
- Do not store Room, Face, Aperture, Door, or Shade here; they live in model files.
- Do not use standards-library search for saved Garden resources.
- Prefer `object_family`; `object_type` is only an Agent-friendly synonym for search.
