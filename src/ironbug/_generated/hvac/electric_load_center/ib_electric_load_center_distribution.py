"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ElectricLoadCenterDistribution(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ElectricLoadCenterDistribution'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_ElectricLoadCenterDistribution.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ElectricLoadCenterDistribution_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Generators',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'Generators',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'GeneratorOperationSchemeType',
        'DemandLimitSchemePurchasedElectricDemandLimit',
        'TrackScheduleSchemeSchedule',
        'TrackMeterSchemeMeterName',
        'ElectricalBussType',
        'StorageOperationScheme',
        'StorageControlTrackMeterName',
        'MaximumStorageStateofChargeFraction',
        'MinimumStorageStateofChargeFraction',
        'DesignStorageControlChargePower',
        'StorageChargePowerFractionSchedule',
        'DesignStorageControlDischargePower',
        'StorageDischargePowerFractionSchedule',
        'StorageControlUtilityDemandTarget',
        'StorageControlUtilityDemandTargetFractionSchedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'DemandLimitSchemePurchasedElectricDemandLimit': 'float',
        'DesignStorageControlChargePower': 'float',
        'DesignStorageControlDischargePower': 'float',
        'ElectricalBussType': 'str',
        'GeneratorOperationSchemeType': 'str',
        'MaximumStorageStateofChargeFraction': 'float',
        'MinimumStorageStateofChargeFraction': 'float',
        'StorageControlTrackMeterName': 'str',
        'StorageControlUtilityDemandTarget': 'float',
        'StorageOperationScheme': 'str',
        'TrackMeterSchemeMeterName': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'StorageChargePowerFractionSchedule': 'IB_Schedule',
        'StorageControlUtilityDemandTargetFractionSchedule': 'IB_Schedule',
        'StorageDischargePowerFractionSchedule': 'IB_Schedule',
        'TrackScheduleSchemeSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Generators': 'List<IB_Generator>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'Generators': 'List<IB_Generator>',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ElectricLoadCenterDistribution'] = PydanticField(default='IB_ElectricLoadCenterDistribution')
    Generators: list[IB_Generator] | None = PydanticField(default=None)

__all__ = [
    'IB_ElectricLoadCenterDistribution',
]
