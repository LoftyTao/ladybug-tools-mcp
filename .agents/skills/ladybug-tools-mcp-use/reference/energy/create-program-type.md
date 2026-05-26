# Create Program Type

Use this when the user needs a Honeybee Energy `ProgramType` for Room program assignment or Energy property editing.

## Preconditions

- If the ProgramType will be assigned later, save it in the Garden Properties Library.
- Use saved load targets for low-token handoff.
- Include Setpoint and conditioned-room assumptions separately before Energy simulation or HVAC workflows.

## MCP Route

1. Search standards identifiers with `energy_search_energy_library_objects` when a library base or schedule is needed.
2. Create needed loads, such as `energy_create_lighting`, `energy_create_people`, or `energy_create_setpoint`.
3. Call `energy_create_program_type` with a base ProgramType identifier or target and load targets.
4. Assign the resulting ProgramType target to Rooms with `honeybee_edit_room`.

## Code Mode Pattern

```python
lighting = await call_tool("energy_create_lighting", {
    "identifier": "agent_lighting",
    "watts_per_area": 5.0,
    "schedule": "Generic Office Lighting",
    "garden_root": garden_root,
    "return_object_dict": False
})

program = await call_tool("energy_create_program_type", {
    "identifier": "agent_program",
    "base_program_type": "Generic Office Program",
    "lighting": lighting["target"],
    "garden_root": garden_root,
    "return_object_dict": False
})
```

## Load Handoff

The same target-first pattern applies to `energy_create_people`, `energy_create_electric_equipment`, `energy_create_gas_equipment`, `energy_create_ventilation`, `energy_create_infiltration`, `energy_create_service_hot_water`, and `energy_create_setpoint`.

## Success Criteria

- `target` is a Garden Properties Library `program_type` target when `garden_root` is provided.
- `summary_view` lists active load slots and schedule counts.
- Room search after assignment shows expected Energy properties.

## Stop Conditions

- Do not ask Agents to copy full load dictionaries between tools when Garden targets are available.
- Do not treat ProgramType alone as proof that a Room is conditioned. Check Setpoint/HVAC or explicit conditioned assumptions for Energy workflows.
- Use library identifiers only when they match the user's intent.
