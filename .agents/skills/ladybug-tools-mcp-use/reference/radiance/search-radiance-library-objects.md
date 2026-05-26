# Search Radiance Library Objects

Use this when the user needs a Honeybee Radiance standards-library identifier for modifiers or modifier sets.

## Preconditions

- This is read-only standards-library search.
- Use Garden Properties Library search for project-specific saved modifiers or luminaires.
- `query` is required.

## MCP Route

1. Search for `radiance_search_library_objects`.
2. Call with `query`, optional `object_family`, and optional `limit`.
3. Pass the returned `identifier` directly to Radiance or Honeybee edit tools.

## Code Mode Pattern

```python
result = await call_tool("radiance_search_library_objects", {
    "query": "generic wall",
    "object_family": "modifier",
    "limit": 3
})
```

## Success Criteria

- `matches[]` includes `object_family`, `object_type`, `identifier`, `score`, and `use_as`.
- `summary_view.available_families` confirms valid filters.
- A selected identifier is passed directly to fields such as `modifier` or `modifier_set_identifier`.

## Stop Conditions

- Do not call this with `arguments: null` or `{}`.
- Do not keep probing unrelated terms after short searches such as `glass`, `plastic`, or `generic wall` return usable matches.
- Keep schema and live-run evidence in LLM-Wiki.
