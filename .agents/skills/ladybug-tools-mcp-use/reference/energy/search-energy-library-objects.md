# Search Energy Library Objects

Use this when the user needs a Honeybee Energy standards-library identifier for schedules, schedule type limits, program types, materials, constructions, or construction sets.

## Preconditions

- Use this for read-only standards library lookup.
- Use Garden Properties Library search when the object was created and saved inside a Garden.
- Do not pass Garden context to standards-library search.

## MCP Route

1. Search for `energy_search_energy_library_objects`.
2. Call it with `query` and optional `object_family` and `limit`.
3. Use the returned `identifier` directly in Energy foundation tools.

## Code Mode Pattern

```python
result = await call_tool("energy_search_energy_library_objects", {
    "query": "generic office lighting",
    "object_family": "schedule",
    "limit": 3
})
```

## Supported Families

`schedule`, `schedule_type_limit`, `program_type`, `opaque_material`, `window_material`, `opaque_construction`, `window_construction`, `shade_construction`, `construction_set`, and `all`.

## Success Criteria

- `matches[]` includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families` confirms valid filters.
- The selected identifier is passed to a create/assignment tool without copying standards objects through chat.

## Stop Conditions

- Do not use this to find Garden-saved custom resources.
- Do not invent broader Energy library families when a filter returns no match.
- Keep schema evidence in LLM-Wiki.
