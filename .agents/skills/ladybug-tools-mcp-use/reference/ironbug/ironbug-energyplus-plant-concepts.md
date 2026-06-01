# Ironbug EnergyPlus Plant Concepts

Use this concept preflight for Ironbug hydronic, condenser, and air/water-loop requests. It explains tool relationships; it is not a case-specific recipe and does not replace the one-scenario case skills.

## Source Boundary

This guidance is aligned with EnergyPlus plant-loop concepts, but it must stay operational. Use the links for background when needed; do not copy long documentation text into the Skill.

- EnergyPlus Plant Application Guide nomenclature:
  https://bigladdersoftware.com/epx/docs/24-1/plant-application-guide/energyplus-nomenclature.html
- EnergyPlus Engineering Reference, Plant/Condenser Loops:
  https://bigladdersoftware.com/epx/docs/23-2/engineering-reference/plant-condenser-loops.html
- EnergyPlus Essentials, HVAC loops and controls:
  https://energyplus.readthedocs.io/en/stable/essentials/essentials.html
- For placement decisions around loop pumps, bypass branches, fans, and
  setpoint managers, also read `ironbug-loop-topology-placement.md`.

## Operational Mental Model

EnergyPlus plant and condenser loops are built from components, nodes,
branches, branch lists, connector pairs, and loop sides.

- The supply side half-loop contains equipment that prepares the working fluid,
  such as boilers, chillers, pumps, cooling towers, heat exchangers, district
  sources, or pipes.
- The demand side half-loop contains equipment that asks the loop for heating,
  cooling, or heat rejection, such as water coils, baseboard/radiant equipment,
  chiller condenser connections, and water-source heat-pump connections.
- Branches and connectors describe topology. Agents should not author these as
  generic public MCP payloads; current retained Ironbug paths use semantic loop
  tools and reviewed direct target parameters.
- Setpoint managers and plant/condenser control decide target temperatures and
  equipment availability. Public simple paths expose loop `setpoint_c` and
  reviewed parameters; explicit OperationScheme / operation-scheme authoring
  remains bottom-layer or candidate unless a retained Energy path proves it.

## Ironbug Public Tool Mapping

Use public Ironbug component tools for physical objects, then semantic loop
tools for topology:

| EnergyPlus concept | Ironbug MCP route |
|---|---|
| Chilled-water supply equipment | pumps, district cooling, chiller create tools |
| Hot-water supply equipment | pumps, district heating water, boiler create tools |
| Condenser supply equipment | condenser pumps, cooling tower / heat exchanger create tools |
| Room-serving demand | cooling/heating water coils, FCUs, unit ventilators, reheat coils, radiant/baseboard coils tied to `IB_ThermalZone` |
| Chilled-water loop topology | `detailed_hvac_plant_loop_chilled_water` |
| Hot-water loop topology | `detailed_hvac_plant_loop_hot_water` |
| Condenser-water loop topology | `detailed_hvac_plant_loop_condenser_water` |
| Loop temperature target | semantic loop `setpoint_c` or reviewed setpoint-manager parameters |
| Energy runtime | apply Ironbug DetailedHVAC, then standard Ladybug Tools MCP Energy run/readback tools |

Do not call or invent generic `create_ironbug_plant_loop`, relationship helper,
explicit PlantEquipmentOperation, or Ironbug-only simulation tools for retained
Agent workflows.

Local passed/candidate from
`docs/llm-wiki/evidence/ironbug-next-round-tool-tests-2026-05-31`:
air-cooled EIR chiller + FCU and repaired fluid-cooler condenser-water loop +
FCU passed next-round tool testing. The 2026-06-01 first-surface recovery also
closed PlantLoop EIR heat pump as a Codex-direct EnergyPlus pass with
cooling/heating `HeatPump:PlantLoop:EIR` writer evidence. Treat these as local
tool-test directions, not Agent-verified playbooks. Stop if the requested plant
path depends on headered/tertiary pump topology or cooled-beam coil EnergyPlus
validation; those records are blocked/partial. Compact branch-contained
`IB_NodeProbe` plus SystemNodeReset has Codex-direct EnergyPlus evidence only;
treat it as a local candidate path, not a retained Agent playbook.

## Branch Target Shape

This branch input shape is deterministic-contract-pass.

For `detailed_hvac_plant_loop_chilled_water`, `detailed_hvac_plant_loop_hot_water`, and
`detailed_hvac_plant_loop_condenser_water`, use the branch input shape to express
topology:

- A flat list creates one serial branch, for example
  `[pump_target, boiler_target]`.
- A nested list creates parallel branches, and each inner list is serial, for
  example `[[coil_1_target], [coil_2_target, coil_3_target]]`.
- If exactly one pump is present on the supply side, the service places it as a
  direct loop supply component before the supply branch group. The remaining
  supply equipment stays in branch groups.
- If an automatic pump is needed, the service creates a default
  `IB_PumpConstantSpeed` and treats it as the direct loop pump.
- If multiple pumps are present, do not assume they are interchangeable; decide
  whether the system needs primary/secondary, headered, or branch-pump topology.

Do not flatten nested branch lists in Agent code. Preserve the user's intended
parallel branch groups when a system has multiple coils, heat exchangers,
chillers, towers, or coupled source paths.

## Demand-Side Rule

`IB_LoadProfilePlant` is useful for plant-only debug graphs when a known load
schedule is the target. It is not accepted for current
custom-HVAC matrix or Codex subagent case passes. Accepted Energy cases need a
real room-serving demand path tied to `IB_ThermalZone` and Honeybee/Dragonfly
Rooms before Energy is run.

## Readiness Questions

Ask these before choosing a plant or air/water workflow:

1. Which Rooms or Room2Ds are served, and are they simulation-ready?
2. What is the demand object: water coil, FCU, unit ventilator, reheat coil,
   baseboard/radiant equipment, VRF terminal, or air terminal?
3. Which loop side is each object on: supply equipment or demand equipment?
4. Which public semantic loop tool maps the topology: chilled water, hot water,
   or condenser water?
5. Does the EnergyPlus result need ERR/SQL/EUI readback? If yes, stop after the
   first completed run with readable evidence; do not rebuild the graph.
