# Ironbug EMS Storage Dispatch

Status: deterministic-contract-pass with Codex-direct MCP verification. This is
projected from
`docs/llm-wiki/evidence/ems-ice-storage-fcu-doas-python-only-2026-05-30.md`
and `docs/llm-wiki/workflows/ironbug-loop-topology-placement-guidance.md`.
Do not call it Agent-verified or a recommended natural-language Agent path until
a focused natural-language EMS storage Agent run passes.

Use this reference when the user asks for an Ironbug EMS ice-storage or
storage-dispatch demonstration and accepts an EMS proxy instead of native
EnergyPlus `ThermalStorage:Ice:*` plant equipment.

## Required Framing

- Say plainly that this is an EMS proxy for dispatch and tariff value, not a
  manufacturer-grade native ice tank.
- Build the room-serving HVAC first: real Rooms, matching Ironbug
  `IB_ThermalZone` objects, FCU/DOAS equipment, and water-loop demand tied to
  room coils.
- For multi-room water coils, pass one singleton branch per coil:
  `demand_branch_component_targets=[[coil_1], [coil_2], ...]`. A flat list is
  one serial branch and is wrong for separate room terminals.
- Use the Python Ironbug Console / OpenStudio OSM runtime for acceptance:
  `python_ironbug_console_runtime.status="translated"` and
  `simulation_input_kind="openstudio_osm"`.
- For direct Codex verification, use the active MCP Code Mode connection to
  reload the completed Energy run, poll it, then read ERR, EUI, SQL, and EMS
  custom output series through MCP tools instead of inspecting files by hand.

## EMS Authoring Pattern

- Put `IB_EnergyManagementSystem` on the `IB_Model` root so it is included in
  the DetailedHVAC specification.
- Put executable Erl under `ProgramClnManagers` through
  `IB_EnergyManagementSystemProgramCallingManager`; do not leave dispatch code
  as unattached root programs.
- Bind each ProgramCallingManager to concrete Program/Subroutine child objects
  so the translated OSM has populated `Program Name` fields.
- Bind actuators to named OpenStudio components and exact actuator/control
  pairs; verify the final ERR has `0 severe / 0 fatal`.
- For local Erl reporting, use
  `IB_EnergyManagementSystemMeteredOutputVariable` with
  `ems_program_or_subroutine_name` set to the owning Program/Subroutine name.
- For values that must persist between timesteps without an Ironbug
  GlobalVariable path, use a schedule-backed state register:
  ScheduleRuleset -> EMS Sensor `Schedule Value` -> EMS Actuator
  `Schedule:Year / Schedule Value`.
- Add custom output variables or metered output variables for SOC, mode,
  charge/discharge rate, and electricity adjustment so SQL post-processing can
  compare baseline and EMS runs.

## Comparison Outputs

Read SQL meters or EMS custom outputs, not only Honeybee EUI. The retained EMS
proxy case compared:

- `Electricity:Facility` annual kWh.
- Hourly peak kW.
- Peak-period and valley-period kWh under a toy TOU tariff.
- Calculated TOU cost.
- EMS SOC, charge, discharge, mode, and electric adjustment series.

## Stop Conditions

- Stop if the translated OSM lacks ProgramCallingManager program fields.
- Stop if a MeteredOutputVariable references a local Erl variable without
  `ems_program_or_subroutine_name`.
- Stop if ERR reports EMS local-variable output fatal errors.
- Stop if multi-room FCU/heating/reheat coils were passed as a flat demand list.
- Stop before claiming native ice tank physics unless the case uses
  `ThermalStorage:Ice:*`, `PlantComponent:UserDefined`, or an equivalent
  OpenStudio-backed storage component.

## Better Benchmark Direction

For storage physics and external comparison, prefer native EnergyPlus examples
when Ironbug/OpenStudio support exists:

- `ThermalStorage:Ice:Simple`.
- `ThermalStorage:Ice:Detailed`.
- `ThermalStorage:ChilledWater:Mixed`.
- Series chiller-upstream, series chiller-downstream, and parallel ice-storage
  configurations.
- Packaged unitary thermal storage OpenStudio Measure studies when the target
  system is packaged equipment instead of central chilled water.
