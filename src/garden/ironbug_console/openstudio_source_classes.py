"""Source-class groups for the Python Ironbug OpenStudio writer."""

from __future__ import annotations


SETPOINT_MANAGER_SOURCE_CLASSES = frozenset(
    {
        "IB_SetpointManagerColdest",
        "IB_SetpointManagerFollowGroundTemperature",
        "IB_SetpointManagerFollowOutdoorAirTemperature",
        "IB_SetpointManagerFollowSystemNodeTemperature",
        "IB_SetpointManagerMixedAir",
        "IB_SetpointManagerMultiZoneCoolingAverage",
        "IB_SetpointManagerMultiZoneHeatingAverage",
        "IB_SetpointManagerMultiZoneHumidityMaximum",
        "IB_SetpointManagerMultiZoneHumidityMinimum",
        "IB_SetpointManagerMultiZoneMaximumHumidityAverage",
        "IB_SetpointManagerMultiZoneMinimumHumidityAverage",
        "IB_SetpointManagerOutdoorAirPretreat",
        "IB_SetpointManagerOutdoorAirReset",
        "IB_SetpointManagerScheduled",
        "IB_SetpointManagerScheduledDualSetpoint",
        "IB_SetpointManagerSingleZoneCooling",
        "IB_SetpointManagerSingleZoneHeating",
        "IB_SetpointManagerSingleZoneHumidityMaximum",
        "IB_SetpointManagerSingleZoneHumidityMinimum",
        "IB_SetpointManagerSingleZoneReheat",
        "IB_SetpointManagerSystemNodeResetHumidity",
        "IB_SetpointManagerSystemNodeResetTemperature",
        "IB_SetpointManagerWarmest",
        "IB_SetpointManagerWarmestTemperatureFlow",
    }
)

SETPOINT_MANAGER_OPENSTUDIO_CLASSES = {
    source_class: source_class.removeprefix("IB_")
    for source_class in SETPOINT_MANAGER_SOURCE_CLASSES
    if source_class != "IB_SetpointManagerScheduled"
}

SINGLE_ZONE_SETPOINT_MANAGER_SOURCE_CLASSES = frozenset(
    {
        "IB_SetpointManagerSingleZoneCooling",
        "IB_SetpointManagerSingleZoneHeating",
        "IB_SetpointManagerSingleZoneHumidityMaximum",
        "IB_SetpointManagerSingleZoneHumidityMinimum",
        "IB_SetpointManagerSingleZoneReheat",
    }
)

SETPOINT_MANAGER_STRING_FIELDS = frozenset(
    {
        "ControlVariable",
        "ReferenceGroundTemperatureObjectType",
        "ReferenceTemperatureType",
        "Strategy",
    }
)

GENERIC_OPENSTUDIO_CLASS_NAMES = {
    "IB_AvailabilityManagerDifferentialThermostat": (
        "AvailabilityManagerDifferentialThermostat"
    ),
    "IB_AvailabilityManagerHighTemperatureTurnOff": (
        "AvailabilityManagerHighTemperatureTurnOff"
    ),
    "IB_AvailabilityManagerHighTemperatureTurnOn": (
        "AvailabilityManagerHighTemperatureTurnOn"
    ),
    "IB_AvailabilityManagerHybridVentilation": "AvailabilityManagerHybridVentilation",
    "IB_AvailabilityManagerLowTemperatureTurnOff": (
        "AvailabilityManagerLowTemperatureTurnOff"
    ),
    "IB_AvailabilityManagerLowTemperatureTurnOn": (
        "AvailabilityManagerLowTemperatureTurnOn"
    ),
    "IB_AvailabilityManagerNightCycle": "AvailabilityManagerNightCycle",
    "IB_AvailabilityManagerNightVentilation": "AvailabilityManagerNightVentilation",
    "IB_AvailabilityManagerOptimumStart": "AvailabilityManagerOptimumStart",
    "IB_AvailabilityManagerScheduled": "AvailabilityManagerScheduled",
    "IB_AvailabilityManagerScheduledOff": "AvailabilityManagerScheduledOff",
    "IB_AvailabilityManagerScheduledOn": "AvailabilityManagerScheduledOn",
    "IB_CentralHeatPumpSystem": "CentralHeatPumpSystem",
    "IB_CentralHeatPumpSystemModule": "CentralHeatPumpSystemModule",
    "IB_ChillerAbsorptionIndirect": "ChillerAbsorptionIndirect",
    "IB_ChillerHeaterPerformanceElectricEIR": (
        "ChillerHeaterPerformanceElectricEIR"
    ),
    "IB_CoilCoolingDXMultiSpeed": "CoilCoolingDXMultiSpeed",
    "IB_CoilCoolingDXMultiSpeedStageData": "CoilCoolingDXMultiSpeedStageData",
    "IB_CoilCoolingDXTwoSpeed": "CoilCoolingDXTwoSpeed",
    "IB_CoilCoolingDXTwoStageWithHumidityControlMode": (
        "CoilCoolingDXTwoStageWithHumidityControlMode"
    ),
    "IB_CoilCoolingWaterToAirHeatPumpEquationFit": (
        "CoilCoolingWaterToAirHeatPumpEquationFit"
    ),
    "IB_CoilHeatingDXMultiSpeed": "CoilHeatingDXMultiSpeed",
    "IB_CoilHeatingDXMultiSpeedStageData": "CoilHeatingDXMultiSpeedStageData",
    "IB_CoilHeatingDesuperheater": "CoilHeatingDesuperheater",
    "IB_CoilHeatingGas": "CoilHeatingGas",
    "IB_CoilHeatingGasMultiStage": "CoilHeatingGasMultiStage",
    "IB_CoilHeatingGasMultiStageStageData": "CoilHeatingGasMultiStageStageData",
    "IB_CoilHeatingWaterBaseboard": "CoilHeatingWaterBaseboard",
    "IB_CoilHeatingWaterToAirHeatPumpEquationFit": (
        "CoilHeatingWaterToAirHeatPumpEquationFit"
    ),
    "IB_CoilPerformanceDXCooling": "CoilPerformanceDXCooling",
    "IB_CoilWaterHeatingAirToWaterHeatPump": (
        "CoilWaterHeatingAirToWaterHeatPump"
    ),
    "IB_CoolingTowerSingleSpeed": "CoolingTowerSingleSpeed",
    "IB_CoolingTowerTwoSpeed": "CoolingTowerTwoSpeed",
    "IB_DistrictHeating": "DistrictHeating",
    "IB_DistrictHeatingSteam": "DistrictHeatingSteam",
    "IB_Duct": "Duct",
    "IB_ElectricLoadCenter": "ElectricLoadCenterDistribution",
    "IB_ElectricLoadCenterDistribution": "ElectricLoadCenterDistribution",
    "IB_ElectricLoadCenterInverterLookUpTable": (
        "ElectricLoadCenterInverterLookUpTable"
    ),
    "IB_ElectricLoadCenterInverterPVWatts": "ElectricLoadCenterInverterPVWatts",
    "IB_ElectricLoadCenterInverterSimple": "ElectricLoadCenterInverterSimple",
    "IB_ElectricLoadCenterStorageConverter": "ElectricLoadCenterStorageConverter",
    "IB_ElectricLoadCenterStorageLiIonNMCBattery": (
        "ElectricLoadCenterStorageLiIonNMCBattery"
    ),
    "IB_ElectricLoadCenterStorageSimple": "ElectricLoadCenterStorageSimple",
    "IB_ElectricLoadCenterTransformer": "ElectricLoadCenterTransformer",
    "IB_EnergyManagementSystemConstructionIndexVariable": (
        "EnergyManagementSystemConstructionIndexVariable"
    ),
    "IB_EnergyManagementSystemProgram": "EnergyManagementSystemProgram",
    "IB_EnergyManagementSystemProgramCallingManager": (
        "EnergyManagementSystemProgramCallingManager"
    ),
    "IB_EvaporativeCoolerIndirectResearchSpecial": (
        "EvaporativeCoolerIndirectResearchSpecial"
    ),
    "IB_EvaporativeFluidCoolerSingleSpeed": "EvaporativeFluidCoolerSingleSpeed",
    "IB_EvaporativeFluidCoolerTwoSpeed": "EvaporativeFluidCoolerTwoSpeed",
    "IB_FanSystemModel": "FanSystemModel",
    "IB_FanZoneExhaust": "FanZoneExhaust",
    "IB_FluidCoolerSingleSpeed": "FluidCoolerSingleSpeed",
    "IB_FluidCoolerTwoSpeed": "FluidCoolerTwoSpeed",
    "IB_GeneratorMicroTurbine": "GeneratorMicroTurbine",
    "IB_GeneratorWindTurbine": "GeneratorWindTurbine",
    "IB_GroundHeatExchangerHorizontalTrench": (
        "GroundHeatExchangerHorizontalTrench"
    ),
    "IB_GroundHeatExchangerVertical": "GroundHeatExchangerVertical",
    "IB_HeaderedPumpsConstantSpeed": "HeaderedPumpsConstantSpeed",
    "IB_HeaderedPumpsVariableSpeed": "HeaderedPumpsVariableSpeed",
    "IB_HeatExchangerAirToAirSensibleAndLatent": (
        "HeatExchangerAirToAirSensibleAndLatent"
    ),
    "IB_HeatExchangerDesiccantBalancedFlow": "HeatExchangerDesiccantBalancedFlow",
    "IB_HeatPumpPlantLoopEIRCooling": "HeatPumpPlantLoopEIRCooling",
    "IB_HeatPumpPlantLoopEIRHeating": "HeatPumpPlantLoopEIRHeating",
    "IB_HeatPumpWaterToWaterEquationFitCooling": (
        "HeatPumpWaterToWaterEquationFitCooling"
    ),
    "IB_HeatPumpWaterToWaterEquationFitHeating": (
        "HeatPumpWaterToWaterEquationFitHeating"
    ),
    "IB_HumidifierSteamElectric": "HumidifierSteamElectric",
    "IB_LoadProfilePlant": "LoadProfilePlant",
    "IB_PhotovoltaicPerformanceEquivalentOneDiode": (
        "PhotovoltaicPerformanceEquivalentOneDiode"
    ),
    "IB_PhotovoltaicPerformanceSandia": "PhotovoltaicPerformanceSandia",
    "IB_PhotovoltaicPerformanceSimple": "PhotovoltaicPerformanceSimple",
    "IB_PipeAdiabatic": "PipeAdiabatic",
    "IB_PipeIndoor": "PipeIndoor",
    "IB_PipeOutdoor": "PipeOutdoor",
    "IB_PlantComponentTemperatureSource": "PlantComponentTemperatureSource",
    "IB_PlantComponentUserDefined": "PlantComponentUserDefined",
    "IB_SolarCollectorFlatPlatePhotovoltaicThermal": (
        "SolarCollectorFlatPlatePhotovoltaicThermal"
    ),
    "IB_SolarCollectorFlatPlateWater": "SolarCollectorFlatPlateWater",
    "IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT": (
        "SolarCollectorPerformancePhotovoltaicThermalBIPVT"
    ),
    "IB_SolarCollectorPerformancePhotovoltaicThermalSimple": (
        "SolarCollectorPerformancePhotovoltaicThermalSimple"
    ),
    "IB_WaterHeaterHeatPump": "WaterHeaterHeatPump",
    "IB_WaterHeaterMixed": "WaterHeaterMixed",
    "IB_WaterUseConnections": "WaterUseConnections",
    "IB_WaterUseEquipmentDefinition": "WaterUseEquipmentDefinition",
    "IB_ZoneHVACBaseboardConvectiveElectric": "ZoneHVACBaseboardConvectiveElectric",
    "IB_ZoneHVACBaseboardRadiantConvectiveElectric": (
        "ZoneHVACBaseboardRadiantConvectiveElectric"
    ),
    "IB_ZoneHVACEnergyRecoveryVentilator": "ZoneHVACEnergyRecoveryVentilator",
    "IB_ZoneHVACHighTemperatureRadiant": "ZoneHVACHighTemperatureRadiant",
    "IB_ZoneHVACIdealLoadsAirSystem": "ZoneHVACIdealLoadsAirSystem",
    "IB_ZoneHVACLowTempRadiantVarFlow": "ZoneHVACLowTempRadiantVarFlow",
    "IB_ZoneHVACUnitVentilator": "ZoneHVACUnitVentilator",
    "IB_ZoneHVACUnitVentilator_CoolingOnly": "ZoneHVACUnitVentilator",
    "IB_ZoneHVACUnitVentilator_HeatingOnly": "ZoneHVACUnitVentilator",
}

GENERIC_OPENSTUDIO_SOURCE_CLASSES = frozenset(GENERIC_OPENSTUDIO_CLASS_NAMES)

GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES = frozenset(
    {
        "IB_CoilCoolingDXMultiSpeed",
        "IB_CoilCoolingDXTwoSpeed",
        "IB_CoilCoolingDXTwoStageWithHumidityControlMode",
        "IB_CoilHeatingDXMultiSpeed",
        "IB_CoilHeatingGas",
        "IB_CoilHeatingGasMultiStage",
        "IB_Duct",
        "IB_EvaporativeCoolerIndirectResearchSpecial",
        "IB_FanSystemModel",
        "IB_HeatExchangerAirToAirSensibleAndLatent",
        "IB_HeatExchangerDesiccantBalancedFlow",
        "IB_HumidifierSteamElectric",
    }
)

GENERIC_PLANT_COMPONENT_SOURCE_CLASSES = frozenset(
    {
        "IB_CentralHeatPumpSystem",
        "IB_CentralHeatPumpSystemModule",
        "IB_ChillerAbsorptionIndirect",
        "IB_CoilCoolingWaterToAirHeatPumpEquationFit",
        "IB_CoilHeatingWaterToAirHeatPumpEquationFit",
        "IB_CoolingTowerSingleSpeed",
        "IB_CoolingTowerTwoSpeed",
        "IB_DistrictHeating",
        "IB_DistrictHeatingSteam",
        "IB_EvaporativeFluidCoolerSingleSpeed",
        "IB_EvaporativeFluidCoolerTwoSpeed",
        "IB_FluidCoolerSingleSpeed",
        "IB_FluidCoolerTwoSpeed",
        "IB_GroundHeatExchangerHorizontalTrench",
        "IB_GroundHeatExchangerVertical",
        "IB_HeaderedPumpsConstantSpeed",
        "IB_HeaderedPumpsVariableSpeed",
        "IB_HeatPumpPlantLoopEIRCooling",
        "IB_HeatPumpPlantLoopEIRHeating",
        "IB_HeatPumpWaterToWaterEquationFitCooling",
        "IB_HeatPumpWaterToWaterEquationFitHeating",
        "IB_LoadProfilePlant",
        "IB_PipeAdiabatic",
        "IB_PipeIndoor",
        "IB_PipeOutdoor",
        "IB_PlantComponentTemperatureSource",
        "IB_PlantComponentUserDefined",
        "IB_SolarCollectorFlatPlatePhotovoltaicThermal",
        "IB_SolarCollectorFlatPlateWater",
        "IB_WaterHeaterHeatPump",
        "IB_WaterHeaterMixed",
        "IB_WaterUseConnections",
    }
)

GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES = frozenset(
    {
        "IB_ZoneHVACBaseboardConvectiveElectric",
        "IB_ZoneHVACBaseboardRadiantConvectiveElectric",
        "IB_ZoneHVACEnergyRecoveryVentilator",
        "IB_ZoneHVACHighTemperatureRadiant",
        "IB_ZoneHVACIdealLoadsAirSystem",
        "IB_ZoneHVACLowTempRadiantVarFlow",
        "IB_ZoneHVACUnitVentilator",
    }
)

NOOP_CONTAINER_SOURCE_CLASSES = frozenset(
    {
        "IB_AvailabilityManagerList",
        "IB_ElectricLoadCenter",
        "IB_EnergyManagementSystem",
        "IB_ExistingObj",
        "IB_ExistAirLoop",
        "IB_HVACSystem",
        "IB_NoAirLoop",
        "IB_NodeProbe",
        "IB_ZoneEquipmentGroup",
    }
)

SPECIAL_OPENSTUDIO_SOURCE_CLASSES = frozenset(
    {
        "IB_AirLoopHVACUnitaryHeatPumpAirToAir",
        "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed",
        "IB_CoilCoolingLowTempRadiantConstFlow",
        "IB_CoilCoolingLowTempRadiantVarFlow",
        "IB_CoilHeatingLowTempRadiantConstFlow",
        "IB_CoilHeatingLowTempRadiantVarFlow",
        "IB_ControllerWaterCoil",
        "IB_EnergyManagementSystemActuator",
        "IB_EnergyManagementSystemCurveVariable",
        "IB_EnergyManagementSystemInternalVariable",
        "IB_EnergyManagementSystemMeteredOutputVariable",
        "IB_EnergyManagementSystemSensor",
        "IB_EvaporativeCoolerDirectResearchSpecial",
        "IB_GeneratorPVWatts",
        "IB_GeneratorPhotovoltaic",
        "IB_ShadingSurface",
        "IB_SolarCollectorPerformanceFlatPlate",
        "IB_SolarCollectorPerformancePhotovoltaicThermal",
        "IB_SwimmingPoolIndoor",
        "IB_WaterHeaterSizing",
        "IB_WaterUseEquipment",
        "IB_ZoneHVACBaseboardConvectiveWater",
        "IB_ZoneHVACLowTempRadiantConstFlow",
        "IB_ZoneHVACLowTemperatureRadiantElectric",
        "IB_ZoneHVACWaterToAirHeatPump",
    }
)

SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES = frozenset(
    {
        "IB_AirLoopHVACUnitaryHeatPumpAirToAir",
        "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed",
        "IB_CoilCoolingLowTempRadiantConstFlow",
        "IB_CoilCoolingLowTempRadiantVarFlow",
        "IB_CoilHeatingLowTempRadiantConstFlow",
        "IB_CoilHeatingLowTempRadiantVarFlow",
        "IB_EvaporativeCoolerDirectResearchSpecial",
    }
)

SPECIAL_PLANT_COMPONENT_SOURCE_CLASSES = frozenset(
    {
        "IB_SolarCollectorPerformanceFlatPlate",
        "IB_SolarCollectorPerformancePhotovoltaicThermal",
        "IB_SwimmingPoolIndoor",
        "IB_WaterHeaterSizing",
        "IB_WaterUseEquipment",
    }
)

SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES = frozenset(
    {
        "IB_ZoneHVACBaseboardConvectiveWater",
        "IB_ZoneHVACLowTempRadiantConstFlow",
        "IB_ZoneHVACLowTemperatureRadiantElectric",
        "IB_ZoneHVACWaterToAirHeatPump",
    }
)
