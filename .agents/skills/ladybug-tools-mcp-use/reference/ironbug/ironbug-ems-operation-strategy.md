# Ironbug EMS Operation Strategy

Status: deterministic-contract-pass with Codex-direct MCP practice. This is
projected from
`docs/llm-wiki/workflows/ironbug-ems-operation-strategy.md`.
Do not call it Agent-verified until a focused natural-language EMS
operation-strategy Agent run passes.

Use this reference when the user asks whether to use Ironbug EMS for an HVAC
control or operation strategy.

## Native First

Before authoring EMS, check whether native Ironbug controls already express the
strategy:

- Schedules, on/off availability, optimum start, night cycle, and night
  ventilation: use schedules and AvailabilityManagers.
- Supply-air, plant-loop, or zone reset: use SetpointManagers when the logic is
  schedule, outdoor-air, zone, multi-zone, follow-node, or warmest/coldest
  based.
- Economizer, high humidity, mechanical ventilation, or heat-recovery bypass:
  use ControllerOutdoorAir and OutdoorAirSystem fields.
- Load-range plant staging: use PlantLoop OperationScheme and source-backed
  plant equipment.
- Room-serving demand: use real terminals, coils, air terminals, or zone
  equipment tied to `IB_ThermalZone` and Honeybee/Dragonfly Rooms.

Stop here if the native object can represent the requested behavior. EMS is for
supervisory logic, not ordinary schedule or reset setup.

Local passed/candidate from
`docs/llm-wiki/evidence/ironbug-next-round-tool-tests-2026-05-31`:
AvailabilityManager suites for air-loop and plant-loop use passed next-round
tool testing. Use them first for ordinary availability behavior; do not move to
EMS just to express availability.

Minimal EMS occupied demand limit has Codex-direct EnergyPlus pass evidence
with EMS Program, Actuator, ProgramCallingManager, MeteredOutputVariable, and
SQL `EMS Demand Limit Flag` readback. Treat it as a local tool-test direction,
not an Agent-verified EMS playbook.

## Use EMS When Needed

Use Ironbug EMS when the strategy needs one or more of these:

- Cross-system supervision, such as plant dispatch depending on DOAS state,
  terminal load, loop condition, tariff period, or peak demand.
- Timestep memory, such as storage state of charge, timers, hysteresis,
  accumulated runtime, or rolling peak.
- Direct actuator override that native Ironbug fields cannot express.
- Custom EMS output or metered output variables for SQL comparison.
- `PlantComponent:UserDefined` or another EMS-backed component pattern.
- An unsupported-equipment proxy, as long as the final claim says proxy/value
  demonstration and not native equipment physics.

## Codex MCP Validation Route

For a first-practice EMS strategy case, use the active MCP Code Mode connection:

1. Build or reuse the Garden-managed native baseline model.
2. Build an EMS variant as a separate DetailedHVAC/Ironbug model or run.
3. Apply DetailedHVAC, then run Energy with `energyplus_start_simulation` and
   polling. DetailedHVAC runs should report Python Ironbug Console runtime
   translation; otherwise root EMS objects may not reach the OSM/IDF.
4. For retained comparisons, reload completed runs with
   `energyplus_start_simulation(reload_old=true)`.
5. Read ERR, EUI, SQL meters, and EMS custom outputs through MCP Energy result
   tools.
6. Compare the baseline and EMS variant on the intended strategy metric, not
   only whole-building EUI.

For EMS schedule actuators, target the EnergyPlus-side actuator exactly. If the
authored schedule is translated to a default object such as `Always On
Discrete`, use the translated unique name and the matching component type such
as `Schedule:Constant`; do not assume the authored Ironbug schedule wrapper name
or `Schedule:Year` will be the valid EMS actuator target.

For EMS Program tools, put Erl source text in `body`. Do not pass a scalar
string to `lines`; in current practice this can be written one character per
EnergyPlus line and fail with EMS parser errors such as `Unknown keyword [S]`.

For Energy output requests, do not use an `end_uses` preset. Use allowed
presets such as `hvac_energy_use` and `zone_energy_use`; read annual end-use
breakdown from `energyplus_read_eui`.

For data-center PUE probes, use a clearly labeled IT proxy such as always-on
Honeybee `ElectricEquipment` when native `ElectricEquipment:ITE:AirCooled` is
not part of the MCP workflow. Calculate:
`PUE = total_energy / (end_uses["Electric Equipment"] * conditioned_floor_area)`.

Keep one compact returned dictionary from each `execute` block with run ids,
ERR severe/fatal counts, EUI, relevant meter totals, and EMS output-series
names/counts.

When several variants share one Honeybee Model, run them one at a time:
`apply DetailedHVAC -> start Energy -> poll completed -> read results`. Do not
queue several background runs after several applies against the same model.

## Preferred Scenario Ladder

- Native baseline vs EMS supervisory chiller-plant dispatch.
- Native FCU + DOAS vs EMS cross-system coordination.
- EMS ice-storage or storage-like plant dispatch proxy.
- EMS-backed `PlantComponent:UserDefined` plant component.

Each case needs a paired baseline and EMS variant so the comparison shows why
EMS was introduced.

For supply-side `PlantComponent:UserDefined`, require a Python runtime path
that treats `IB_PlantComponentUserDefined` as cooling equipment for PlantLoop
sizing and operation setup. If a native support chiller is present only as a
temporary simulation scaffold, record that boundary and do not claim a pure
PCUD-only plant.

## Stop Conditions

- Stop before EMS if the request is only schedule, reset, economizer,
  availability, or load-range staging.
- Treat compact FollowSystemNode / MixedAir as Codex-direct local pass only,
  not an Agent-verified EMS playbook. The passed topology places
  `IB_SetpointManagerMixedAir` on the next supply fan inlet and uses the fan
  outlet as the reference node; stop if EnergyPlus reports the MixedAir
  reference node and setpoint node are the same.
- Treat compact PlantLoop NodeProbe / SystemNodeReset as Codex-direct local
  pass only, not an Agent-verified EMS playbook. Broader EMS follow-on paths
  remain unverified beyond the minimal occupied demand-limit pass.
- Stop if the EMS actuator target/control pair, ProgramCallingManager, or EMS
  output variable cannot be confirmed through ERR/SQL/readback.
- Stop if a schedule actuator compiles but EnergyPlus reports the
  actuator/object/control combination is unavailable. Repair the target name and
  component type from the translated EnergyPlus object before rerunning.
- Stop if a DetailedHVAC EMS root exists in the Ironbug/Honeybee model but the
  Energy run lacks Python Ironbug runtime evidence or SQL custom-output
  inventory.
- Stop if the comparison does not expose the strategy's value metric.
- Stop before claiming native thermal-storage or equipment physics for an EMS
  proxy.
- Stop if parallel plant components were passed as a flat serial branch list.
  Use nested branch groups for independent terminal loads, heat exchangers,
  tanks, chillers, boilers, heat rejection, and user-defined plant components.
