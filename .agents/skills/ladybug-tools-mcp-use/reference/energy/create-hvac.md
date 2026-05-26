# Create And Attach Honeybee Energy HVAC

Use this when the user needs a Honeybee Energy HVAC object or Setpoint attached to existing Honeybee Rooms.

This is an `hvac-template` path, not an Ironbug `detailed-hvac` path. Use it for
Honeybee Energy template HVAC, Ideal Air, simple ventilation/fans, and Setpoint
assignment. For source-backed custom HVAC components, loops, branches,
zone equipment, or DetailedHVAC application, use the Ironbug references.

## Preconditions

- Search Room targets explicitly and pass `matches[i].target` to `honeybee_edit_room`.
- Confirm Room ProgramType, Setpoint, and conditioned assumptions before simulation.
- Treat broad HVAC design selection as outside this stable MCP path unless the user names the system type.

## MCP Route

1. Create or find an HVAC target with `energy_search_hvac_templates` or `energy_create_ideal_air_system`.
2. Create a Setpoint with `energy_create_setpoint`.
3. Search Rooms with `honeybee_search_model_objects(object_type="room")`.
4. Attach HVAC and Setpoint with `honeybee_edit_room`.
5. Validate the model.

## Template HVAC Pattern

```python
hvac = await call_tool("energy_search_hvac_templates", {
    "query": "packaged single zone psz",
    "system_type": "PSZ",
    "identifier": "agent_psz_hvac",
    "equipment_type": "PSZAC_ElectricCoil",
    "garden_root": garden_root,
    "return_object_dict": False
})
setpoint = await call_tool("energy_create_setpoint", {
    "identifier": "agent_setpoint",
    "_heating_schedule": "Generic Office Heating",
    "_cooling_schedule": "Generic Office Cooling",
    "garden_root": garden_root,
    "return_object_dict": False
})
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})
edited = await call_tool("honeybee_edit_room", {
    "garden_root": garden_root,
    "target": rooms["matches"][0]["target"],
    "hvac": hvac["target"],
    "setpoint": setpoint["target"]
})
```

## Success Criteria

- HVAC and Setpoint creation return Garden targets.
- `honeybee_edit_room.summary_view.updated_fields` includes `hvac` and `setpoint`.
- Room search shows the edited Energy properties.
- `honeybee_validate_model.summary_view.is_valid == true`.

## Stop Conditions

- Do not invent `create_template_hvac`; `energy_search_hvac_templates` combines search and instantiation.
- Do not use this path for Ironbug source-backed custom HVAC graphs; switch to
  `reference/ironbug/ironbug-custom-hvac-agent-workflows.md`.
- Do not copy expanded Setpoint schedule JSON when a saved target exists.
- For `energy_create_ideal_air_system`, do not use room setpoint temperatures as supply air temperatures. Omit supply air temperatures unless the user means supply air.
- Keep HVAC smoke and run metrics in LLM-Wiki.
