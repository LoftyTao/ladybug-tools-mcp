# Create Radiance Luminaires

Use this path when the user provides IES LM-63 content or an IES file path and wants a reusable Honeybee Radiance Luminaire resource.

## Shortest Verified Path

Use Code Mode and keep the IES text inside one `execute` block:

```python
garden = await call_tool("create_garden", {"name": "IES Project", "root_dir": garden_root})
luminaire = await call_tool("create_radiance_luminaire", {
    "garden_root": garden_root,
    "ies_content": ies_text,
    "identifier": "sample_luminaire",
    "instances": [{"point": [0, 0, 3], "aiming_point": [0, 0, 0]}],
    "custom_lamp": {"mode": "color_temperature", "name": "warm_lamp", "color_temperature": 3000},
    "return_object_dict": False
})
found = await call_tool("search_garden_properties_library_objects", {
    "garden_root": garden_root,
    "query": "sample",
    "domain": "honeybee_radiance",
    "object_family": "luminaire"
})
```

The create result returns a `target` / `luminaire_target` with:

- `target_type`: `garden_properties_library_object`
- `domain`: `honeybee_radiance`
- `object_family`: `luminaire`

## Inputs

- Provide exactly one of `ies_content` or `ies_path`.
- `instances` is optional. Each item uses `point` plus optional `spin`, `tilt`, `rotation`, or `aiming_point`.
- `custom_lamp` can be an SDK `CustomLamp` dict or simple settings:
  - `{"mode": "color_temperature", "color_temperature": 3000}`
  - `{"mode": "rgb", "rgb": [1, 0.85, 0.65]}`
  - `{"mode": "xy", "x": 0.43, "y": 0.40}`

## Evidence

- 2026-04-29 Agent Code Mode smoke verified `create_garden -> create_radiance_luminaire(return_object_dict=false) -> search_garden_properties_library_objects` with one `execute`, 3 MCP calls, no repeated tools, and 8,428 total tokens.
