# Ironbug Loop Topology Placement

Status: deterministic-contract-pass.

Use this before creating Ironbug hot-water, chilled-water, or condenser-water loops with pumps, bypasses, fans, or setpoint managers.

## Placement Rules

- Treat exactly one supply-side pump as the loop pump. Pass it with the supply equipment if needed; the semantic loop service places it directly on the loop supply side before the supply branch group.
- Use nested branch lists for parallel equipment. Each inner list is one serial branch: `[[coil_1], [coil_2, coil_3]]`.
- Do not flatten branch groups in Agent code. Preserve separate room/zone coils, towers, chillers, heat exchangers, and FCU coils as separate branches when they are parallel.
- If a loop has more than one pump, stop and choose intentionally: primary/secondary, headered, or branch-pump topology may need a more specific source-backed path.
- Put bypass intent in its own branch with only a pipe/bypass component. Do not mix bypass and active equipment on the same branch.
- Use `setpoint_c` for simple loop supply-temperature control. Only create explicit setpoint-manager objects when the public source-backed tool exposes the needed manager and target fields.
- Keep fans out of hydronic plant-loop branches. Fans belong inside air loops, terminal units, FCUs, unitary systems, or zone equipment.
- Do not use orientation words to describe component connection sides. For coils and terminal equipment, distinguish the Water Side connected to the Plant Loop from the Air Side connected to the Air Loop or zone/terminal air path.

## Public Tool Pattern

For semantic loop tools:

```python
loop = await call_tool('detailed_hvac_plant_loop_hot_water', {
    'garden_root': garden_root,
    'ironbug_model_target': ironbug_model_target,
    'identifier': 'hot_water_loop',
    'supply_branch_component_targets': [
        [pump_target, heat_pump_target, boiler_target],
    ],
    'demand_branch_component_targets': [
        [heating_water_coil_1_target],
        [heating_water_coil_2_target],
    ],
    'setpoint_c': 55.0,
})
```

Expected persisted topology: direct supply pump, one supply equipment branch containing heat pump then boiler, and two parallel demand branches.

## Stop Conditions

- Stop if the active MCP result still reports the single pump inside `supply_branch_lengths`; the server has not been restarted onto the deterministic-contract-pass code.
- Stop before inventing generic PlantLoop, Connector, BranchList, OperationScheme, or node payloads.
- Stop if a fan target appears in `supply_branch_component_targets` or `demand_branch_component_targets`; re-create the owning terminal or air-side equipment instead.
