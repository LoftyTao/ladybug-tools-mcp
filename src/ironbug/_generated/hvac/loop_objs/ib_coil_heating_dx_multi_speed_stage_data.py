"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilHeatingDXMultiSpeedStageData(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilHeatingDXMultiSpeedStageData'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingDXMultiSpeedStageData.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilHeatingDXMultiSpeedStageData_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'GrossRatedHeatingCapacity',
        'GrossRatedHeatingCOP',
        'RatedAirFlowRate',
        'RatedSupplyAirFanPowerPerVolumeFlowRate',
        'RatedSupplyAirFanPowerPerVolumeFlowRate2017',
        'RatedSupplyAirFanPowerPerVolumeFlowRate2023',
        'HeatingCapacityFunctionofTemperatureCurve',
        'HeatingCapacityFunctionofFlowFractionCurve',
        'EnergyInputRatioFunctionofTemperatureCurve',
        'EnergyInputRatioFunctionofFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'RatedWasteHeatFractionofPowerInput',
        'WasteHeatFunctionofTemperatureCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'GrossRatedHeatingCOP': 'float',
        'GrossRatedHeatingCapacity': 'float',
        'RatedAirFlowRate': 'float',
        'RatedSupplyAirFanPowerPerVolumeFlowRate': 'str | float | int | bool',
        'RatedSupplyAirFanPowerPerVolumeFlowRate2017': 'float',
        'RatedSupplyAirFanPowerPerVolumeFlowRate2023': 'float',
        'RatedWasteHeatFractionofPowerInput': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'EnergyInputRatioFunctionofFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'HeatingCapacityFunctionofFlowFractionCurve': 'IB_Curve',
        'HeatingCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'WasteHeatFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilHeatingDXMultiSpeedStageData'] = PydanticField(default='IB_CoilHeatingDXMultiSpeedStageData')

__all__ = [
    'IB_CoilHeatingDXMultiSpeedStageData',
]
