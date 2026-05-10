# Create / Attach Honeybee Energy HVAC

Use this path when the user needs to create a Honeybee Energy HVAC object and attach it to an existing Honeybee `Room` in Garden mode.

## 当前证据分级

### 已验证内容

Deterministic MCP tests cover:

- `search_tools` can find `create_ideal_air_system` and `search_hvac_templates`.
- `search_hvac_templates` can search SDK template HVAC classes and instantiate a selected template when `identifier` is provided.
- `create_setpoint` returns a full SDK `Setpoint.to_dict(abridged=False)` object_dict.
- `search_hvac_templates` and `create_setpoint` can save created objects directly into Garden Properties Library when `garden_root` is provided.
- `search_hvac_templates -> create_setpoint -> search_honeybee_model_objects -> edit_honeybee_room -> validate_honeybee_model` persists HVAC and Setpoint as Garden library resources, then attaches them to a Garden room by target.
- Agent handoff avoids copying expanded SDK object dicts by passing Garden Properties Library targets into `edit_honeybee_room.hvac_` and `edit_honeybee_room.setpoint_`.

OpenAI Agents smoke passed on 2026-04-25 in `tests/agent_integration/test_agent_hvac_smoke.py`:

- `search_tools -> search_hvac_templates(garden_root_, return_object_dict_=false) -> create_setpoint(garden_root_, return_object_dict_=false) -> search_honeybee_model_objects -> edit_honeybee_room(targets) -> validate_honeybee_model`
- persisted room HVAC type: `PSZ`
- persisted room setpoint identifier: `agent_setpoint`

### 候选/未稳定内容

- Broad natural-language HVAC design decisions, such as choosing the best HVAC system for a building, are not yet a stable MCP decision workflow.
- Room-level HVAC attachment should still use explicit room search and typed target handoff.

## Shortest Agent Path

1. `search_tools`
   - Query: `search create honeybee energy hvac template setpoint edit room validate`
2. `call_tool` -> `search_hvac_templates`
   - Use `query` or `system_type_` to select an SDK HVAC template.
   - Provide `identifier`, `garden_root`, and `return_object_dict_=false` so the tool saves the HVAC to Garden Properties Library and returns a target.
3. `call_tool` -> `create_setpoint`
   - Use schedule library identifiers or full schedule dicts.
   - Provide `garden_root` and `return_object_dict_=false` so the tool saves the Setpoint to Garden Properties Library and returns a target.
4. `call_tool` -> `search_honeybee_model_objects`
   - Required:
     - `garden_root`
     - `object_type`: `room`
   - Use the returned `matches[i].target`.
5. `call_tool` -> `edit_honeybee_room`
   - Required:
     - `garden_root`
     - `target`: room typed target from search
   - Optional:
     - `hvac`: `search_hvac_templates.target`
     - `setpoint_`: `create_setpoint.target`
6. `call_tool` -> `validate_honeybee_model`
   - Required:
     - `garden_root`

## Minimal Example

```json
{
  "name": "search_hvac_templates",
  "arguments": {
    "query": "packaged single zone psz",
    "system_type_": "PSZ",
    "identifier": "agent_psz_hvac",
    "equipment_type_": "PSZAC_ElectricCoil",
    "garden_root": "<exact garden root>",
    "return_object_dict": false
  }
}
```

```json
{
  "name": "create_setpoint",
  "arguments": {
    "identifier": "agent_setpoint",
    "_heating_schedule": "Generic Office Heating",
    "_cooling_schedule": "Generic Office Cooling",
    "garden_root": "<exact garden root>",
    "return_object_dict": false
  }
}
```

```json
{
  "name": "search_honeybee_model_objects",
  "arguments": {
    "garden_root": "<exact garden root>",
    "object_type": "room"
  }
}
```

```json
{
  "name": "edit_honeybee_room",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": "<search_honeybee_model_objects.matches[0].target>",
    "hvac": "<search_hvac_templates.target>",
    "setpoint_": "<create_setpoint.target>"
  }
}
```

```json
{
  "name": "validate_honeybee_model",
  "arguments": {
    "garden_root": "<exact garden root>"
  }
}
```

## Expected Output

- `search_hvac_templates.target`: Garden Properties Library `hvac` target ready for `edit_honeybee_room.hvac_`.
- `create_setpoint.target`: Garden Properties Library `load` target ready for `edit_honeybee_room.setpoint_`.
- If `return_object_dict` is left as `true`, `create_setpoint.object_dict` remains the full Honeybee Energy `Setpoint` SDK dict from `Setpoint.to_dict(abridged=False)`.
- `edit_honeybee_room.summary_view.updated_fields`: includes `hvac` and `setpoint` when both were updated.
- `validate_honeybee_model.summary_view.is_valid`: `true` for a valid model.

## Notes

- `search_hvac_templates` intentionally combines search and instantiate. Do not call a separate `create_template_hvac`; that tool is not part of the public path.
- Use `create_ideal_air_system` when the user explicitly asks for Ideal Air, quick early-stage conditioning, or a simple non-template HVAC object.
- For simple `create_ideal_air_system` calls, omit `heating_air_temperature_` and `cooling_air_temperature_`. They are supply air temperatures, not room heating/cooling setpoints. If an Agent passes a setpoint-like pair such as 21/26 C, the tool now ignores the pair with a warning and uses SDK defaults.
- For template HVAC, keep the SDK `type` in the returned dict; `edit_honeybee_room` reconstructs the SDK HVAC object from the dict.
- Do not ask Agents to copy expanded Setpoint schedule JSON or full HVAC object dicts between tools. In Garden mode, prefer `garden_root_ + return_object_dict_=false`, then pass the returned Garden Properties Library target.
- A low-intelligence Agent run initially retried `edit_honeybee_room` after passing expanded `Setpoint` schedule JSON. Treat repeated `edit_honeybee_room` calls as a prompt/tool-description optimization signal.
- 2026-04-28 live Garden Round 17 verified the compact path on the Grasshopper-followed model: `create_ideal_air_system(garden_root, return_object_dict=false) -> create_setpoint(garden_root, return_object_dict=false) -> create_zone_ventilation_fan(garden_root, return_object_dict=false) -> edit_honeybee_room` assigned IdealAir and setpoint to `north_office` / `north_meeting`, attached a corridor exhaust fan to `east_corridor`, and validated at `11,779` tokens.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch C Task 11 verified the natural replacement path: create a simple `IdealAir` HVAC and distinct Setpoints for two rooms, save a Garden version, instantiate a higher-efficiency template HVAC through `search_hvac_templates(identifier, garden_root, return_object_dict=false)`, reassign both rooms, validate, and save a second Garden version. Treat selected template HVAC as a simplified modeling assumption, not vendor-grade equipment selection.
