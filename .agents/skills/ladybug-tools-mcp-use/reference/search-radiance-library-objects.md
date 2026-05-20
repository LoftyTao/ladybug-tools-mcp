# Search Radiance Library Objects

Use this path when the user needs a Honeybee Radiance standards library identifier for modifiers or modifier sets.

## Code Mode Path

1. `search`
   - Query: `search honeybee radiance library modifier identifiers`
2. `get_schema`
   - Tool: `search_radiance_library_objects`
3. `execute`
   - Inside the code block, call `await call_tool("search_radiance_library_objects", arguments)`.
   - Required:
     - `query`: search text such as `generic wall`, `white glow`, or `generic exterior visible`
   - Optional:
     - `object_family`: `modifier`, `modifier_set`, or `all`
     - `limit`
4. Use a returned `identifier` directly in a radiance-related tool.

## Minimal Example

```python
result = await call_tool(
    "search_radiance_library_objects",
    {
        "query": "generic wall",
        "object_family": "modifier",
        "limit": 3,
    },
)
return result
```

Do not call this tool with `arguments: null` or `{}`. `query` is required and should be a short standards-library search phrase, not an empty object. If validation reports `query` missing, rebuild the full example shape instead of retrying the same empty call.

## Expected Output

- `matches[]`: each item includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families`: supported family filters.
- Public arguments are `query`, `object_family`, and `limit`.

## Notes

- This is a read-only SDK standards library search path, not Garden Properties Library management.
- The verified Agent smoke searched for `generic_wall_0.50`.
- A full agent regression previously exposed repeated empty calls to this tool; keep the `query` example visible in prompts that rely on lower-capability models.
- 2026-05-18 deterministic tests verify that the public schema exposes only canonical arguments for this standards-library search.
- A live Garden Round 18 run verified the standards-library handoff: search visible Honeybee targets, call `search_radiance_library_objects` with `query`, `object_family`, and `limit`, then pass returned modifier identifiers directly to `edit_honeybee_aperture`, `edit_honeybee_door`, or `edit_honeybee_shade` as `modifier`.
- 2026-04-30 supervised external Agent task 23 verified the read-only standards-library search path in the broad matrix, but the supervisor stopped a repeated `search_radiance_library_objects` loop at 7 calls. For simple modifier choice, search once or twice with short terms such as `glass`, `plastic`, or `generic wall`, choose a returned `identifier`, and stop; do not keep probing unrelated terms after matches are available.
