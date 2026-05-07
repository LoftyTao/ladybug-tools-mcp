# Create Program Type

Use this path when the user needs a Honeybee Energy `ProgramType` object for room program assignment or later energy-property editing.

## Shortest Verified Path

1. `search_tools`
   - Query: `create honeybee energy program type lighting override`
2. `call_tool` -> `search_energy_library_objects`
   - Required:
     - `query`: `generic office lighting`
   - Optional:
     - `object_family_`: `schedule`
     - `limit_`: `3`
   - Use the returned `identifier` as schedule input when it matches the intended library object.
3. `call_tool` -> `create_lighting`
   - Required:
     - `identifier`
     - `_watts_per_area`
   - Optional:
     - `schedule_`: full schedule dict or Honeybee Energy schedule library identifier such as `Generic Office Lighting`.
     - `garden_root`: when a Garden exists, save the load into Garden Properties Library.
     - `return_object_dict`: use `false` with `garden_root` for low-token handoff.
4. `call_tool` -> `create_program_type`
   - Required:
     - `identifier`
   - Optional:
     - `base_program_type`: full ProgramType dict, Garden Properties Library target, or Honeybee Energy ProgramType library identifier such as `Generic Office Program`.
     - `lighting_`: prefer `create_lighting.target`; `object_dict` still works for payload-only authoring.
     - `garden_root`: required when consuming Garden targets; also saves the ProgramType when provided.
     - `return_object_dict`: use `false` with `garden_root` to return only target/summary/receipt.

## Minimal Example

```json
{
  "name": "search_energy_library_objects",
  "arguments": {
    "query": "generic office lighting",
    "object_family_": "schedule",
    "limit_": 3
  }
}
```

```json
{
  "name": "create_lighting",
  "arguments": {
    "identifier": "agent_lighting",
    "_watts_per_area": 5.0,
    "schedule_": "Generic Office Lighting",
    "garden_root": "<garden root>",
    "return_object_dict": false
  }
}
```

```json
{
  "name": "create_program_type",
  "arguments": {
    "identifier": "agent_program",
    "base_program_type": "Generic Office Program",
    "lighting_": "<create_lighting.target>",
    "garden_root": "<garden root>",
    "return_object_dict": false
  }
}
```

## Expected Output

- `target`: Garden Properties Library `program_type` target when `garden_root` is provided.
- `object_dict`: Honeybee Energy `ProgramType` dict, omitted when `return_object_dict` is `false`.
- `summary_view`: compact identifiers for the active load slots and `schedule_count`.

## Notes

- The verified Agent smoke covered `search_energy_library_objects -> create_lighting -> create_program_type` with a library schedule and library ProgramType base.
- 2026-04-25 deterministic MCP cross-test verified low-token Garden handoff: `create_lighting(return_object_dict_=false) -> create_setpoint(return_object_dict_=false) -> create_program_type(return_object_dict_=false)` using load targets and fetching the saved ProgramType back from Garden.
- Other foundation load tools follow the same target handoff pattern and are covered by deterministic tests: `create_people`, `create_electric_equipment`, `create_gas_equipment`, `create_ventilation`, `create_infiltration`, `create_service_hot_water`, and `create_setpoint`.
- Schedule inputs on load tools may use schedule library identifiers or Garden schedule targets when `garden_root` is supplied.
- 2026-04-26 deterministic tests also cover simple Agent-written load shorthands inside `create_program_type`: people density, lighting/equipment watts per area, gas equipment, service hot water, infiltration, ventilation flow fields, and numeric heating/cooling setpoints. Prefer saved load targets for low-token handoff, but these shorthands prevent late-chain natural calls from failing immediately.
