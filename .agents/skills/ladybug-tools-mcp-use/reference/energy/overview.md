# Energy Skill Overview

Use this category when the Agent needs Honeybee Energy resources, weather files, annual Energy simulation runs, result reading, or Energy-oriented staged workflows.

## Preconditions

- Work from a valid Garden and a simulation-ready Honeybee Model target.
- Before HVAC or Energy runs, confirm Room `ProgramType`, `Setpoint`, and whether Rooms are conditioned.
- Use Garden-managed EPW targets; do not create ad hoc weather folders or handwrite EPW paths outside the Garden.

## Common Scenarios

- Search or create ProgramType, ScheduleRuleset, ConstructionSet, HVAC, Setpoint, and reusable Garden library objects.
- Download EPW weather and start annual Energy simulation.
- Poll background Energy runs and read EUI, ERR, SQL, and available outputs.
- Diagnose suspicious Energy results from bounded evidence.
- Segment large geometry/properties/weather/simulation requests into stages.

## Usual MCP Route

1. Confirm required Honeybee Rooms and Energy properties.
2. Create or reuse Energy resources with Garden target handoff.
3. Attach resources through supported Honeybee edit tools.
4. Use `energyplus_search_epw_map` and `energyplus_download_epw` for weather.
5. Use `energyplus_start_simulation` and `energyplus_poll_simulation` for Agent workflows.
6. Read outputs only after completion and return compact result summaries.

## HVAC Boundary

- This category covers `hvac-template` workflows: Honeybee Energy template HVAC,
  Ideal Air, simple ventilation/fans, Setpoint, and reusable Energy resources.
- For source-backed custom HVAC graphs, loops, branches, zone equipment, or
  DetailedHVAC application, switch to the Ironbug references instead of trying
  to force the request through Energy template tools.

## Stop Conditions

- Stop when weather search or download is blocked after one clear recovery attempt.
- Stop when model validation or run status is `failed`; read bounded errors before proposing repair.
- Stop before using blocking `energyplus_run_simulation_wait` unless the user explicitly asks to wait for a local blocking run.
- Stop before claiming causality from a single run; describe hypotheses and next tests.

## References

- `search-energy-library-objects.md`
- `garden-properties-library.md`
- `create-program-type.md`
- `create-schedule-ruleset.md`
- `create-construction-set.md`
- `create-hvac.md`
- `source-backed-energy-resources.md`
- `staged-energy-agent-workflow.md`
- `source-backed-light-thermal-facade.md`
- `ventilation-pv-agent-workflow.md`
- `run-energy-simulation.md`
- `energy-result-diagnosis.md`
