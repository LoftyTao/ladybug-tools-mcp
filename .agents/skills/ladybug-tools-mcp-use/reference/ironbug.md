# Ironbug DetailedHVAC Overview & Loop Topology

Use the 8 `IB_*` tools when the user needs **custom OpenStudio/EnergyPlus HVAC topology** (plant loops, chillers, boilers, cooling towers, custom air loops, four-pipe FCUs, VRF systems, or explicit equipment curves/controls) rather than Honeybee Energy template HVAC (`EP_search_hvac_templates` / `EP_create_ideal_air_system`).

## External Runtime Boundary

- Ironbug authoring, schema introspection, and validation run through a thin `.NET 8` bridge (`IronbugBridge`) against the user's installed **`Ironbug.HVAC.dll`**, **`Ironbug.EPDoc.dll`**, and **`OpenStudio.dll`**.
- **Two-tier binary requirement**:
  - `IB_list_components` and `IB_describe_component` only require **`.NET 8`** + **`Ironbug.HVAC.dll`** (plus optional `Ironbug.EPDoc.dll`) and **work without `OpenStudio.dll`**.
  - `IB_validate_system` and `IB_apply_to_model` compile via official `IB_HVACSystem.SaveHVAC(OpenStudio.Model)` and **require `OpenStudio.dll`**.
- Energy simulation of models with `DetailedHVAC` uses native `honeybee-openstudio` calling external **`Ironbug.Console`** (no Python fallback translator).
- If `IB_*` or `EP_start_simulation` reports missing external Ironbug binaries, stop cleanly and guide the user to check `LB_get_runtime_config` and install Ladybug Tools / Ironbug + `.NET 8`.

## The 8 Ironbug Tools

1. **Discover & Inspect Official C# Classes** *(works without `OpenStudio.dll`)*
   - `IB_list_components`: Browse or search official `IB_*` classes by category (`zone_equipment`, `air_terminal`, `coil_cooling`, `coil_heating`, `coil_dx`, `fan`, `pump`, `plant_equipment`, `air_loop`, `plant_loop`, `vrf`, `setpoint_manager`, `curve`, `schedule`, `sizing`, `controller`, `ems`, `generator_electric`, etc.) or keyword (English or Chinese).
   - `IB_describe_component`: Inspect constructors, child wiring slots (`Set*`/`Add*`), and core fields with real EnergyPlus EPDoc descriptions, units, and valid enum choices (`include_advanced=True` for rare fields).
2. **Author Official `IB_HVACSystem` in Garden**
   - `IB_create_system`: Create (or import) a Garden-managed `IB_HVACSystem` JSON at `models/ironbug/<id>.json`. Importing via `specification=...` marks the system `imported_only`, guarding it against accidental overwrite by draft-based mutations (`IB_upsert_components` / `IB_configure_loops`).
   - `IB_upsert_components`: Add/update/remove typed components (`type`, `ctor_args`, `fields`, `wiring`, `output_variables`). `components` is optional when passing `remove_ids`. String values `"autosize"` / `"autocalculate"` on numeric C# fields are gracefully skipped so Ironbug/OpenStudio retains default autosizing. Every edit immediately validates against C# `*_FieldSet` and compiles via official `ToJson()`.
   - `IB_configure_loops`: Wire `thermal_zones`, `air_loops`, `plant_loops`, `vrf_systems`, and optional `energy_management_system` / `electric_load_center` component IDs.
   - `IB_inspect_system`: Inspect existing loops, zones, and component inventory.
3. **Validate & Apply** *(requires `OpenStudio.dll`)*
   - `IB_validate_system`: Compiles the system in-memory via official C# `IB_HVACSystem.SaveHVAC(OpenStudio.Model)`, runs static pre-checks (including `ironbug_fcu_cycling_fan_type_mismatch`, which requires `IB_FanOnOff` when `IB_ZoneHVACFourPipeFanCoil` has `CapacityControlMethod="CyclingFan"`), AND checks Honeybee `Room` (`model_family="honeybee"`) or Dragonfly `Room2D` (`model_family="dragonfly"`) preconditions (`ProgramType`, `Setpoint`, matching room/zone names).
   - `IB_apply_to_model`: Attaches `DetailedHVAC` to Honeybee Rooms (`model_family="honeybee"`) or Dragonfly Room2D/Story/Building hosts (`model_family="dragonfly"`), then simulate with `EP_start_simulation` + `EP_poll_simulation` + `EP_read_eui`.

## 1. Room Preconditions Before Applying Ironbug HVAC

Before validating or running EnergyPlus with an Ironbug `DetailedHVAC`:
- Target Honeybee Rooms (`model_family="honeybee"`) or Dragonfly Room2Ds (`model_family="dragonfly"`) must have both **`ProgramType`** and **`Setpoint`** assigned (use `HB_edit_room`, `HB_apply_room_energy_properties`, or `DF_apply_energy_properties`), so `properties.energy.is_conditioned` is `True`. Otherwise EnergyPlus simulates unconditioned free-floating zones with zero HVAC sizing/loads.
- `IB_validate_system(..., model_target=..., model_family="honeybee" | "dragonfly")` checks these room preconditions directly for both Honeybee `Room`s and Dragonfly `Room2D`s before `IB_apply_to_model`.
- Every `thermal_zones[i]["room_name"]` in `IB_configure_loops` must match the exact Room or Room2D `identifier` (for example `"Room1"`).

## 2. Discovering Exact Types and Fields

Never guess Ironbug class names, constructor arguments, or field names:
1. Call `IB_list_components(query=..., category=...)` to find the exact `IB_*` class name (e.g., `IB_ChillerElectricEIR`, `IB_ZoneHVACFourPipeFanCoil`).
2. Call `IB_describe_component(type_names=[...])` to see:
   - `constructors`: Some components (e.g. `IB_ScheduleRuleset(value)`, `IB_SetpointManagerScheduled(value)`, `IB_ZoneHVACPackagedTerminalAirConditioner(SupplyFan, HeatingCoil, CoolingCoil)`) take constructor arguments in `ctor_args`.
   - `wiring_methods`: Child slots such as `fan`, `heating_coil`, `cooling_coil`, `reheat_coil`, `controller`, `heat_exchanger`, `sizing_zone`, `sizing_system`.
   - `core_fields` (and `advanced_fields` when `include_advanced=True`): Exact EnergyPlus/Ironbug `FullName` keys, units, and enum `choices`.

## 3. Shared Component IDs (Automatic `TrackingID` Linking)

When a water coil, chiller, or heat-recovery object belongs to **two loops/objects** (for example: a cooling coil inside a Four-Pipe FCU AND on the chilled-water plant loop demand side, or a water-cooled chiller on the chilled-water supply side AND the condenser-water demand side):
- Define that component **once** in `IB_upsert_components` with a single component ID (e.g., `"fcu_cc"`, `"chiller"`).
- Reference that **exact same ID** in both places (e.g., inside `fcu.wiring.cooling_coil` AND `CHW_Loop.demand_branches`, or `CHW_Loop.supply_branches` AND `CW_Loop.demand_branches`).
- The C# bridge reuses the identical C# object instance and `TrackingID`, so `IB_HVACSystem.SaveHVAC` links both loops to one OpenStudio object rather than duplicating it.

## 4. Serial vs Parallel Branches in `IB_configure_loops`

- **`air_loops`**:
  - `supply`: Ordered list of component IDs from outdoor air / coils / fan / setpoint manager (e.g., `["oa_sys", "cc", "hc", "fan", "sa_spm"]`).
  - `demand_zones`: List of room names served by the air loop (e.g., `["Room1", "Room2"]`). Each zone must have its `air_terminal` set in `thermal_zones` if using VAV/CAV/PIU terminals.
  - Any zone in `thermal_zones` NOT placed in an `air_loop` is automatically wrapped in `IB_NoAirLoop` (the standard path for PTAC, PTHP, FCU, or zone equipment without a central air loop).
- **`plant_loops`**:
  - `loop_type`: `"Cooling"`, `"Heating"`, `"Condenser"`, or `"Both"` (automatically creates `IB_SizingPlant`).
  - `supply` / `demand`: Ordered serial items placed directly on the loop header (typically the circulation `pump` in `supply`).
  - `supply_branches` / `demand_branches`: **Nested lists `list[list[str]]`**, where each inner list is one parallel branch:
    - Single chiller branch: `supply_branches: [["chiller"]]`
    - Two parallel room coils: `demand_branches: [["room1_cc"], ["room2_cc"]]`
    - Two components in series on one branch: `demand_branches: [["pipe1", "coil1"]]`
  - `supply_setpoint`: Numeric °C setpoint (automatically adds `IB_SetpointManagerScheduled(value)` at the supply outlet). Use `supply_setpoint_manager` for custom setpoint managers (such as `IB_SetpointManagerOutdoorAirReset`).
- **System-level EMS & Electric Load Center (`IB_configure_loops`)**:
  - `energy_management_system`: Optional component ID (defined in `IB_upsert_components`, e.g., an `IB_EnergyManagementSystem` instance) attached to `IB_HVACSystem.EnergyManagementSystem`.
  - `electric_load_center`: Optional component ID (e.g., an `IB_ElectricLoadCenterDistribution` instance) attached to `IB_HVACSystem.ElectricLoadCenter`.
- **`imported_only` Overwrite Guard on Imported Systems**:
  - Systems created via `IB_create_system(specification=...)` hold raw imported official `IB_HVACSystem` JSON without a reconstructible authoring draft (`imported_only`).
  - Calling `IB_upsert_components` or `IB_configure_loops` against an `imported_only` system raises a guard error instead of silently overwriting imported loops/components. Use `IB_inspect_system`, `IB_validate_system`, and `IB_apply_to_model` directly, or re-create with `IB_create_system(..., overwrite=True)` if switching to draft-based authoring.

## 5. Validation, Application & Examples

1. Always call `IB_validate_system(garden_root=..., ironbug_model_target=..., model_target=..., model_family=...)` before `IB_apply_to_model` (pass `model_family="dragonfly"` when checking Dragonfly `Room2D` preconditions). Confirm `valid == True`, `ready == True`, and inspect `openstudio_summary` counts (e.g. `chillers_electric_eir`, `plant_loops`, `pumps_constant_speed`, `pumps_variable_speed`, `fans_on_off`, `fans_constant_volume`, `fans_variable_volume`).
2. Call `IB_apply_to_model(garden_root=..., ironbug_model_target=...)` (for Dragonfly hosts, set `model_family="dragonfly"` and `host_target=...`).
3. Run standard Energy simulation: `EP_start_simulation` -> `EP_poll_simulation` -> `EP_list_run_outputs` -> `EP_read_eui` / `EP_read_errors`.

See [reference/ironbug-examples.md](ironbug-examples.md) for complete verified Code Mode examples (PTAC, Chiller + Cooling Tower + Four-Pipe FCU, and VAV Reheat).
