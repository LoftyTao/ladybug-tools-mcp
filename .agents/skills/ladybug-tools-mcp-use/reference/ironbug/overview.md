# Ironbug Skill Overview

Use this category when the Agent needs Ironbug `.ibjson` custom HVAC authoring, Room energy preflight, EnergyPlus plant concept mapping, DetailedHVAC application, or retained one-case custom HVAC playbooks.

This is the `detailed-hvac` path, not the Honeybee Energy `hvac-template` path.
Use Energy references for template HVAC, Ideal Air, simple ventilation/fans, and
reusable HVAC resources. Use this category for source-backed custom HVAC
components, loops, branches, zone equipment, and DetailedHVAC application.

## Preconditions

- Confirm served Honeybee Rooms or Dragonfly Room2Ds are simulation-ready before applying custom HVAC.
- For Honeybee, check ProgramType, Setpoint, and conditioned-floor-area assumptions before Ironbug authoring.
- Use Ironbug MCP tools and typed targets; do not hand-author `.ibjson`.
- Run Energy simulation through the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied.
- Current callable tool names remain the names returned by `search` or
  `get_schema`, including existing `create_ironbug_*` names. Category short
  names such as `zone_equipment_ptac` are migration targets until the MCP schema
  exposes them.

## Common Scenarios

- Create, validate, and search a Garden-managed Ironbug model.
- Check Room ProgramType, Setpoint, and conditioned status before HVAC work.
- Map EnergyPlus plant concepts to public Ironbug semantic loop tools.
- Apply loop-topology placement rules for pumps, bypasses, fans, and setpoints.
- Use a retained one-case HVAC playbook for exact short prompts.
- Use the family workflow for near variants or repair work.

## Usual MCP Route

1. Load Room energy preconditions before case or family workflows.
2. Create Ironbug components in dependency order through MCP tools.
3. Apply DetailedHVAC to the Honeybee or Dragonfly model.
4. Run standard Energy simulation and read EUI, ERR, and SQL outputs.
5. Keep case files focused on reusable execution guidance; put run records in
   LLM-Wiki.

## Stop Conditions

- Stop when a required Ironbug source-backed component tool is missing.
- Stop before inventing EnergyPlus plant topology or generic payload fields.
- Stop when Rooms are unconditioned or lack compatible ProgramType/Setpoint, unless the user explicitly asks for an unconditioned path.

## References

- `ironbug-room-energy-preconditions.md`
- `ironbug-core-ibjson.md`
- `ironbug-energyplus-plant-concepts.md`
- `ironbug-loop-topology-placement.md`
- `ironbug-custom-hvac-agent-workflows.md`
- `custom-hvac-cases/index.md`
