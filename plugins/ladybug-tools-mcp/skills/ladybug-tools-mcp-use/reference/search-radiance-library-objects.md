# Search Radiance Library Objects

Use this path when the user needs a Honeybee Radiance standards library identifier for modifiers or modifier sets.

## Shortest Verified Path

1. `search_tools`
   - Query: `search honeybee radiance library modifier identifiers`
2. `call_tool` -> `search_radiance_library_objects`
   - Required:
     - `query`: search text such as `generic wall`, `white glow`, or `generic exterior visible`
   - Optional:
     - `object_family_`: `modifier`, `modifier_set`, or `all`
     - `object_type`: deterministic fallback synonym for `object_family`
     - `limit_`
     - `garden_root`: accepted as an ignored context hint when an Agent is already operating in a Garden.
3. Use a returned `identifier` directly in a compatible radiance-related tool.

## Minimal Example

```json
{
  "name": "search_radiance_library_objects",
  "arguments": {
    "query": "generic wall",
    "object_family_": "modifier",
    "garden_root": "<garden root>",
    "limit_": 3
  }
}
```

Do not call this tool with `arguments: null` or `{}`. `query` is required and should be a short standards-library search phrase, not an empty object. If validation reports `query` missing, rebuild the full example shape instead of retrying the same empty call.

## Expected Output

- `matches[]`: each item includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families`: supported family filters.

## Notes

- This is a read-only SDK standards library search path, not Garden Properties Library management.
- The verified Agent smoke searched for `generic_wall_0.50`.
- A full agent regression previously exposed repeated empty calls to this tool; keep the `query` example visible in prompts that rely on lower-capability models.
- 2026-04-26 deterministic tests verify `object_type` as an Agent-friendly filter synonym. `object_family` remains the preferred documented field in hand-written calls.
- 2026-04-28 live Garden Round 18 verified the fixed Agent path: search visible Honeybee targets, call `search_radiance_library_objects` with the current `garden_root` hint, then pass returned modifier identifiers directly to `edit_honeybee_aperture`, `edit_honeybee_door`, or `edit_honeybee_shade` as `modifier`. The failed run cost `155,037` tokens; after this service-surface fix, retry closed at `11,797` tokens.
- 2026-04-30 supervised external Agent task 23 verified the read-only standards-library search path in the broad matrix, but the supervisor stopped a repeated `search_radiance_library_objects` loop at 7 calls. For simple modifier choice, search once or twice with short terms such as `glass`, `plastic`, or `generic wall`, choose a returned `identifier`, and stop; do not keep probing unrelated terms after matches are available.
