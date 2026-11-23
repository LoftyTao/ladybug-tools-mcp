# Ironbug Verified Code Mode Examples

All examples below use the 8 official-C#-backed `IB_*` tools inside Code Mode `execute`, assuming `garden_root` already contains conditioned Honeybee Room(s) (with `ProgramType` and `Setpoint`) and an imported `weather_target`.

## Example 1: Single-Zone PTAC (`IB_NoAirLoop` Auto-Wrapped)

```python
sys = await call_tool("IB_create_system", {
    "garden_root": garden_root,
    "identifier": "ptac_room1",
    "overwrite": True,
})
ib_target = sys["target"]

await call_tool("IB_upsert_components", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "components": {
        "ptac_fan": {"type": "IB_FanOnOff"},
        "ptac_hc": {"type": "IB_CoilHeatingElectric"},
        "ptac_cc": {"type": "IB_CoilCoolingDXSingleSpeed"},
        "ptac": {
            "type": "IB_ZoneHVACPackagedTerminalAirConditioner",
            "ctor_args": ["ptac_fan", "ptac_hc", "ptac_cc"],
        },
    },
})

await call_tool("IB_configure_loops", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "thermal_zones": [{"room_name": "Room1", "zone_equipments": ["ptac"]}],
})

val = await call_tool("IB_validate_system", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
applied = await call_tool("IB_apply_to_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
return {"valid": val["valid"], "ready": val["ready"], "os": val["openstudio_summary"], "applied": applied["summary_view"]}
```

## Example 2: Water-Cooled Chiller + Cooling Tower + Four-Pipe FCU (3 Plant Loops)

```python
sys = await call_tool("IB_create_system", {
    "garden_root": garden_root,
    "identifier": "chiller_tower_fcu",
    "overwrite": True,
})
ib_target = sys["target"]

await call_tool("IB_upsert_components", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "components": {
        "fcu_fan": {"type": "IB_FanOnOff"},
        "fcu_hc": {"type": "IB_CoilHeatingWater"},
        "fcu_cc": {"type": "IB_CoilCoolingWater"},
        "fcu": {
            "type": "IB_ZoneHVACFourPipeFanCoil",
            "wiring": {"fan": "fcu_fan", "heating_coil": "fcu_hc", "cooling_coil": "fcu_cc"},
        },
        "chiller": {
            "type": "IB_ChillerElectricEIR",
            "fields": {
                "ReferenceCOP": 5.5,
                "CondenserType": "WaterCooled",
                "ReferenceLeavingChilledWaterTemperature": 6.7,
            },
        },
        "tower": {"type": "IB_CoolingTowerVariableSpeed"},
        "chw_pump": {"type": "IB_PumpConstantSpeed"},
        "cw_pump": {"type": "IB_PumpConstantSpeed"},
        "hw_pump": {"type": "IB_PumpConstantSpeed"},
        "dh": {"type": "IB_DistrictHeatingWater"},
    },
})

await call_tool("IB_configure_loops", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "thermal_zones": [{"room_name": "Room1", "zone_equipments": ["fcu"]}],
    "plant_loops": [
        {
            "name": "ChilledWaterLoop",
            "loop_type": "Cooling",
            "design_loop_exit_temperature": 6.7,
            "loop_design_temperature_difference": 5.0,
            "supply": ["chw_pump"],
            "supply_branches": [["chiller"]],
            "supply_setpoint": 6.7,
            "demand_branches": [["fcu_cc"]],
        },
        {
            "name": "CondenserWaterLoop",
            "loop_type": "Condenser",
            "design_loop_exit_temperature": 29.4,
            "loop_design_temperature_difference": 5.6,
            "supply": ["cw_pump"],
            "supply_branches": [["tower"]],
            "supply_setpoint": 29.4,
            "demand_branches": [["chiller"]],
        },
        {
            "name": "HotWaterLoop",
            "loop_type": "Heating",
            "design_loop_exit_temperature": 60.0,
            "loop_design_temperature_difference": 11.0,
            "supply": ["hw_pump"],
            "supply_branches": [["dh"]],
            "supply_setpoint": 60.0,
            "demand_branches": [["fcu_hc"]],
        },
    ],
})

val = await call_tool("IB_validate_system", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
applied = await call_tool("IB_apply_to_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
return {"valid": val["valid"], "ready": val["ready"], "os": val["openstudio_summary"], "applied": applied["summary_view"]}
```

> **Note (`IB_CoolingTowerVariableSpeed`)**: The default `CoolToolsCrossFlow` empirical correlation enforces `DesignInletAirWetBulbTemperature` between `-1.0 °C` and `26.67 °C` (keep at or below `26.67 °C`, e.g. `25.5–26.0 °C`, even in humid climates when using this default correlation, or select an alternate correlation/model type for higher wet-bulb temperatures).

## Example 3: Central VAV with Hot-Water Reheat + Boiler Plant Loop

```python
sys = await call_tool("IB_create_system", {
    "garden_root": garden_root,
    "identifier": "vav_reheat",
    "overwrite": True,
})
ib_target = sys["target"]

await call_tool("IB_upsert_components", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "components": {
        "oa_ctrl": {"type": "IB_ControllerOutdoorAir"},
        "oa_sys": {"type": "IB_OutdoorAirSystem", "wiring": {"controller": "oa_ctrl"}},
        "ahu_cc": {"type": "IB_CoilCoolingDXSingleSpeed"},
        "ahu_hc": {"type": "IB_CoilHeatingGas"},
        "ahu_fan": {"type": "IB_FanVariableVolume"},
        "ahu_spm": {"type": "IB_SetpointManagerScheduled", "ctor_args": [12.8]},
        "reheat_coil": {"type": "IB_CoilHeatingWater"},
        "vav_box": {"type": "IB_AirTerminalSingleDuctVAVReheat", "wiring": {"reheat_coil": "reheat_coil"}},
        "hw_pump": {"type": "IB_PumpVariableSpeed"},
        "boiler": {"type": "IB_BoilerHotWater", "fields": {"NominalThermalEfficiency": 0.85}},
    },
})

await call_tool("IB_configure_loops", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
    "thermal_zones": [{"room_name": "Room1", "air_terminal": "vav_box"}],
    "air_loops": [
        {
            "name": "VAV_AHU",
            "supply": ["oa_sys", "ahu_cc", "ahu_hc", "ahu_fan", "ahu_spm"],
            "demand_zones": ["Room1"],
        }
    ],
    "plant_loops": [
        {
            "name": "HotWaterLoop",
            "loop_type": "Heating",
            "design_loop_exit_temperature": 82.0,
            "loop_design_temperature_difference": 11.0,
            "supply": ["hw_pump"],
            "supply_branches": [["boiler"]],
            "supply_setpoint": 82.0,
            "demand_branches": [["reheat_coil"]],
        }
    ],
})

val = await call_tool("IB_validate_system", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
applied = await call_tool("IB_apply_to_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ib_target,
})
return {"valid": val["valid"], "ready": val["ready"], "os": val["openstudio_summary"], "applied": applied["summary_view"]}
```
