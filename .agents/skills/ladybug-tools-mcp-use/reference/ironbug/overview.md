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
- Treat OpenStudio translation as diagnostic only. For Ironbug tool testing,
  EnergyPlus completion with ERR/SQL/EUI evidence is the acceptance target.
- Current callable tool names remain the names returned by `search` or
  `get_schema`, including existing `create_ironbug_*` names. Category short
  names such as `zone_equipment_ptac` are migration targets until the MCP schema
  exposes them.

## Common Scenarios

- Create, validate, and search a Garden-managed Ironbug model.
- Check Room ProgramType, Setpoint, and conditioned status before HVAC work.
- Map EnergyPlus plant concepts to public Ironbug semantic loop tools.
- Apply loop-topology placement rules for pumps, bypasses, fans, and setpoints.
- Decide when Ironbug native controls are enough and when EMS should be used as
  a supervisory operation-strategy layer.
- Author deterministic-pass EMS storage-dispatch proxy cases and compare
  baseline vs EMS SQL outputs.
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
- Stop before calling Ironbug PVWatts or ElectricLoadCenter Energy results accepted unless the Python Console compiler report includes the relevant generator / electric-load-center writer coverage, the runtime OSM contains matching OpenStudio generator/load-center objects, and SQL exposes PV/generator or purchased-electricity outputs. A run that only writes `thermal_zone` / `sizing` is not valid renewable-generation evidence.
- Stop before presenting Ironbug flat-plate solar thermal DHW as a savings path unless SQL shows nonzero `Solar Collector Heat Transfer Energy`, nonzero plant hot-water demand from the DHW load path, and a baseline/variant auxiliary-heater reduction. Current Phase 3 Codex-direct evidence satisfies these checks for a high-DHW-load probe, but it is not OpenAI Agent SDK evidence and should not be reused as a polished design template without warning, sizing, and control refinement.
- Stop before accepting Ironbug PVT collector evidence unless the final EnergyPlus IDF, not only the OSM, shows `SolarCollector:FlatPlate:PhotovoltaicThermal` with non-empty `Surface Name` and `Photovoltaic Name`, plus a matching `Generator:Photovoltaic` and ElectricLoadCenter generator list. PVT should bind to a real Honeybee roof/building `OS:Surface`; shading surfaces or unattached surfaces can survive in OSM but be dropped during IDF translation. Current Phase 4 Codex-direct evidence is component-boundary evidence only, not OpenAI Agent SDK evidence or a design template.
- Stop before accepting Ironbug WSHP/GSHP evidence unless the source loop connects both water-to-air heat pump equation-fit coils, EnergyPlus completes with SQL/EUI/ERR, and SQL exposes WSHP electricity plus ground heat exchanger temperature/flow/heat-transfer outputs. Plant-loop EIR heat pump authoring alone is not runtime-retained evidence until it is connected to room demand.
- Stop before accepting Ironbug small-wind ElectricLoadCenter evidence unless a matching `IB_ThermalZone` exists for the served Honeybee Room, the final run writes `Generator:WindTurbine` through ElectricLoadCenter, and SQL exposes wind generation, ElectricLoadCenter production, and net purchased electricity. Do not trust `simulation_ready=true` alone for renewable ElectricLoadCenter cases without the thermal-zone match.
- Stop before treating `IB_ControllerWaterCoil` as a standalone runtime object. It is a water-coil child/configuration object: attach it through `IB_CoilCoolingWater` or `IB_CoilHeatingWater` so the Python Console writer applies its fields to the real coil controller after plant-loop connection. A controller-only write is not valid Energy evidence.
- For Sandia PV + ElectricLoadCenter, require the full chain before treating it
  as local MCP pass evidence: final IDF has `Generator:Photovoltaic`,
  `PhotovoltaicPerformance:Sandia`, and `ElectricLoadCenter:Generators`;
  EnergyPlus completes with SQL/EUI/ERR; ERR has no severe/fatal; and SQL reads
  nonzero PV / ElectricLoadCenter production. Current evidence is Codex-direct
  MCP EnergyPlus evidence, not OpenAI Agent SDK evidence.

## References

- `ironbug-room-energy-preconditions.md`
- `ironbug-core-ibjson.md`
- `ironbug-energyplus-plant-concepts.md`
- `ironbug-loop-topology-placement.md`
- `ironbug-ems-operation-strategy.md`
- `ironbug-ems-storage-dispatch.md`
- `ironbug-custom-hvac-agent-workflows.md`
- `custom-hvac-cases/index.md`
