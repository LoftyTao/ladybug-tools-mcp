# Search Energy Library Objects

Use this path when the user needs a Honeybee Energy standards library identifier for schedules, schedule type limits, program types, materials, constructions, or construction sets.

## Shortest Verified Path

1. `search_tools`
   - Query: `search honeybee energy library identifiers`
2. `call_tool` -> `search_energy_library_objects`
   - Required:
     - `query`: search text such as `generic office lighting`, `generic office program`, or `fractional`
   - Optional:
     - `object_family`: `schedule`, `schedule_type_limit`, `program_type`, `opaque_material`, `window_material`, `opaque_construction`, `window_construction`, `shade_construction`, `construction_set`, or `all`
     - `limit`
3. Use a returned `identifier` directly in a compatible energy foundation tool.

## Minimal Example

```json
{
  "name": "search_energy_library_objects",
  "arguments": {
    "query": "generic office lighting",
    "object_family": "schedule",
    "limit": 3
  }
}
```

## Expected Output

- `matches[]`: each item includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families`: supported family filters.

## Notes

- This is a read-only SDK standards library search path, not Garden Properties Library management.
- Do not pass `garden_root` in planned calls. If a low-intelligence Agent carries it over from a Garden-mode block, the service ignores it as a context hint and still searches built-in standards.
- The verified Agent smoke used this tool to find a schedule identifier before `create_lighting -> create_program_type`.
- 2026-04-26 staged MiniMax C initially repeated this tool 21 times after passing `garden_root`; after the no-op context hint fix, the same natural C stage closed with 3 standards-library searches.
