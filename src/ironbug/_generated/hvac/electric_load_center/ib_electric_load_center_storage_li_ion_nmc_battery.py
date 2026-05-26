"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ElectricLoadCenterStorageLiIonNMCBattery(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ElectricLoadCenterStorageLiIonNMCBattery'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_ElectricLoadCenterStorageLiIonNMCBattery.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ElecStorage',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ElectricLoadCenterStorageLiIonNMCBattery_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'RadiativeFraction',
        'LifetimeModel',
        'NumberofCellsinSeries',
        'NumberofStringsinParallel',
        'InitialFractionalStateofCharge',
        'DCtoDCChargingEfficiency',
        'BatteryMass',
        'BatterySurfaceArea',
        'BatterySpecificHeatCapacity',
        'HeatTransferCoefficientBetweenBatteryandAmbient',
        'FullyChargedCellVoltage',
        'CellVoltageatEndofExponentialZone',
        'CellVoltageatEndofNominalZone',
        'DefaultNominalCellVoltage',
        'FullyChargedCellCapacity',
        'FractionofCellCapacityRemovedattheEndofExponentialZone',
        'FractionofCellCapacityRemovedattheEndofNominalZone',
        'ChargeRateatWhichVoltagevsCapacityCurveWasGenerated',
        'BatteryCellInternalElectricalResistance',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BatteryCellInternalElectricalResistance': 'float',
        'BatteryMass': 'float',
        'BatterySpecificHeatCapacity': 'float',
        'BatterySurfaceArea': 'float',
        'CellVoltageatEndofExponentialZone': 'float',
        'CellVoltageatEndofNominalZone': 'float',
        'DCtoDCChargingEfficiency': 'float',
        'DefaultNominalCellVoltage': 'float',
        'FractionofCellCapacityRemovedattheEndofExponentialZone': 'float',
        'FractionofCellCapacityRemovedattheEndofNominalZone': 'float',
        'FullyChargedCellCapacity': 'float',
        'FullyChargedCellVoltage': 'float',
        'HeatTransferCoefficientBetweenBatteryandAmbient': 'float',
        'InitialFractionalStateofCharge': 'float',
        'LifetimeModel': 'str',
        'NumberofCellsinSeries': 'int',
        'NumberofStringsinParallel': 'int',
        'RadiativeFraction': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'ChargeRateatWhichVoltagevsCapacityCurveWasGenerated': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ElectricLoadCenterStorageLiIonNMCBattery'] = PydanticField(default='IB_ElectricLoadCenterStorageLiIonNMCBattery')

__all__ = [
    'IB_ElectricLoadCenterStorageLiIonNMCBattery',
]
