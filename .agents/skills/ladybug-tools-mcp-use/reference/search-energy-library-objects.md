# Search Energy Library Objects

Use this path when the user needs a Honeybee Energy standards library identifier for schedules, schedule type limits, program types, materials, constructions, or construction sets.

## Code Mode Path

1. `search`
   - Query: `search honeybee energy library identifiers`
2. `get_schema`
   - Tool: `search_energy_library_objects`
3. `execute`
   - Inside the code block, call `await call_tool("search_energy_library_objects", arguments)`.
   - Required:
     - `query`: search text such as `generic office lighting`, `generic office program`, or `fractional`
   - Optional:
     - `object_family`: `schedule`, `schedule_type_limit`, `program_type`, `opaque_material`, `window_material`, `opaque_construction`, `window_construction`, `shade_construction`, `construction_set`, or `all`
     - `limit`
4. Use a returned `identifier` directly in an energy foundation tool.

## Minimal Example

```python
result = await call_tool(
    "search_energy_library_objects",
    {
        "query": "generic office lighting",
        "object_family": "schedule",
        "limit": 3,
    },
)
return result
```

## Expected Output

- `matches[]`: each item includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families`: supported family filters.
- Public arguments are `query`, `object_family`, and `limit`.

## Notes

- This is a read-only SDK standards library search path, not Garden Properties Library management.
- Do not pass Garden context to this standards-library search. Use `search_garden_properties_library_objects` for saved Garden objects.
- The verified Agent smoke used this tool to find a schedule identifier before `create_lighting -> create_program_type`.
- 2026-05-18 deterministic tests verify that the public schema exposes only canonical arguments for this standards-library search.
