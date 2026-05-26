# Tool Disclosure And Namespace Runtime Guard

Use this reference only when maintaining Ladybug Tools MCP tool names, tags,
descriptions, or Skill references. This is not a normal modeling workflow.

## Current Runtime Rule

- Call only the tool names returned by Code Mode `search` or `get_schema`.
- Runtime public names now use FastMCP namespace prefixes, for example
  `honeybee_create_room`, `energyplus_start_simulation`,
  `radiance_create_sensor_grid`, and `detailed_hvac_zone_equipment_ptac`.
- Do not call old un-namespaced wrapper names such as `honeybee_create_room`,
  `energyplus_start_simulation`, `energyplus_poll_simulation`, or `create_ironbug_*` from Code Mode.
- There are no compatibility aliases for old public names; update playbooks,
  prompts, tests, and docs to the names returned by the current schema.

## Naming Direction

- Use tool names for the shortest clear callable identity.
- Use tags and descriptions for family context, backend context, and search
  terms.
- For Honeybee Energy template/simple HVAC tools, use `hvac-template` language.
- For Ironbug custom HVAC graphs, use `detailed-hvac` language.
- For Ironbug component names, prefer category phrase plus short class:
  `zone_equipment_ptac`, `zone_equipment_pthp`,
  `air_terminal_vav_reheat`, `fan_on_off`, `pump_constant_speed`,
  `coil_cooling_water`, and `chiller_electric_eir`.
- Keep `ironbug` in callable names for model/file/bridge operations where the
  backend object is user-facing, such as `.ibjson`, validation, search, and
  DetailedHVAC application.

## Skill Sync Checklist

When a runtime tool name actually changes:

1. Update all exact Code Mode snippets and case playbooks that call the tool.
2. Update category overviews only when the Agent's route or stop condition
   changes.
3. Keep candidate/evidence/history out of the Skill; link to LLM-Wiki pages only
   when the distinction changes Agent behavior.
4. Search the Skill tree for old callable names:

```powershell
rg -n "old_tool_name|old_tag|old_namespace" .agents\skills\ladybug-tools-mcp-use
```

5. Run the focused deterministic or Skill-boundary tests for the changed
   references before claiming the Skill is synced.

## LLM-Wiki First

Before changing Skill references for namespace or disclosure work, update the
LLM-Wiki concept and decision pages that define the mapping:

- `docs/llm-wiki/simulation-concept-mapping.md`
- the MCP tool disclosure namespace policy decision page under
  `docs/llm-wiki/decisions/`

Skill references should contain only the next operation an Agent should perform,
not raw evidence, long rationale, or full migration plans.
