# Ironbug Room Energy Preconditions

Use this preflight before any Ironbug case skill or family workflow that will apply DetailedHVAC and run Energy.

## When To Use

Use this reference before building an Ironbug HVAC graph for Honeybee Rooms or
Dragonfly Room2Ds. The goal is to make sure the served spaces can become
conditioned simulation spaces before Ironbug DetailedHVAC is applied.

## Honeybee Rooms

Before creating `IB_ThermalZone` objects:

1. Search the served Rooms with `honeybee_search_model_objects(object_type="room")`.
2. Check each match's compact `energy_properties`.
3. If a Room has no `program_type`, call `honeybee_edit_room` with
   `program_type="Generic Office Program"` or a user/project-specific
   ProgramType.
4. If a Room has no `setpoint`, call `energy_create_setpoint` with `garden_root`,
   numeric `heating_setpoint` and `cooling_setpoint`, and
   `return_object_dict=False`; pass the returned `target` to
   `honeybee_edit_room.setpoint`.
5. Keep `exclude_floor_area=False` unless the user intentionally wants that
   Room excluded from floor-area accounting.
6. Re-search or validate the model after edits. Do not rely on memory of a
   prior write.

The public Honeybee Room edit tool does not expose a separate `conditioned` boolean. For current Ironbug Honeybee workflows, the practical precondition is that every served Room has a ProgramType and thermostat Setpoint before DetailedHVAC is applied. Also inspect compact room Energy properties for floor-area exclusion or other flags that can make the final Energy run behave like an unconditioned case. If a completed run reports `0.0` EUI or `conditioned_floor_area=0`, treat it as a Room energy-property blocker and repair ProgramType / Setpoint / floor-area flags before rerunning Energy.

## Dragonfly Room2Ds

Dragonfly-native Ironbug HVAC assignment uses `conditioned_only=True` by
default for Story and Building hosts.

Before calling `detailed_hvac_apply_to_dragonfly_energy_properties`:

1. Apply ProgramType to Room2D, Story, or Building hosts with
   `dragonfly_apply_energy_properties`.
2. Confirm the host has conditioned Room2Ds when `conditioned_only=True`.
3. Set `conditioned_only=False` only when the user intentionally wants HVAC
   assigned to all child Room2Ds, including spaces that are not yet marked
   conditioned.
4. Remember that Dragonfly Room2D setpoints are managed through ProgramType /
   program workflows; do not create Honeybee Room setpoints for a Dragonfly
   native path unless the workflow explicitly converts to Honeybee first.

## Ironbug Binding Check

After the space preflight:

- Create one `IB_ThermalZone` per served Room or Room2D.
- Match each `IB_ThermalZone.identifier` or `Name` to the exact Honeybee Room
  identifier for Honeybee DetailedHVAC application.
- For Dragonfly-native paths, keep the selected host and
  `conditioned_only` setting in the final evidence.
- If `detailed_hvac_apply_to_honeybee_model` reports a room-binding or
  simulation-readiness issue, repair that issue before starting Energy.

## Minimal Honeybee Pattern

```python
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
})
setpoint = await call_tool("energy_create_setpoint", {
    "garden_root": garden_root,
    "identifier": "ironbug_case_setpoint",
    "heating_setpoint": 20,
    "cooling_setpoint": 26,
    "return_object_dict": False,
})
await call_tool("honeybee_edit_room", {
    "garden_root": garden_root,
    "target": rooms["matches"][0]["target"],
    "program_type": "Generic Office Program",
    "setpoint_": setpoint["target"],
})
```
