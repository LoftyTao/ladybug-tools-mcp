"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilWaterHeatingAirToWaterHeatPump(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilWaterHeatingAirToWaterHeatPump'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilWaterHeatingAirToWaterHeatPump.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilWaterHeatingAirToWaterHeatPump_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'RatedHeatingCapacity',
        'RatedCOP',
        'RatedSensibleHeatRatio',
        'RatedEvaporatorInletAirDryBulbTemperature',
        'RatedEvaporatorInletAirWetBulbTemperature',
        'RatedCondenserInletWaterTemperature',
        'RatedEvaporatorAirFlowRate',
        'RatedCondenserWaterFlowRate',
        'EvaporatorFanPowerIncludedinRatedCOP',
        'CondenserPumpPowerIncludedinRatedCOP',
        'CondenserPumpHeatIncludedinRatedHeatingCapacityandRatedCOP',
        'CondenserWaterPumpPower',
        'FractionofCondenserPumpHeattoWater',
        'CrankcaseHeaterCapacity',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve',
        'MaximumAmbientTemperatureforCrankcaseHeaterOperation',
        'EvaporatorAirTemperatureTypeforCurveObjects',
        'HeatingCapacityFunctionofTemperatureCurve',
        'HeatingCapacityFunctionofAirFlowFractionCurve',
        'HeatingCapacityFunctionofWaterFlowFractionCurve',
        'HeatingCOPFunctionofTemperatureCurve',
        'HeatingCOPFunctionofAirFlowFractionCurve',
        'HeatingCOPFunctionofWaterFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CondenserPumpHeatIncludedinRatedHeatingCapacityandRatedCOP': 'bool | str',
        'CondenserPumpPowerIncludedinRatedCOP': 'bool | str',
        'CondenserWaterPumpPower': 'float',
        'CrankcaseHeaterCapacity': 'float',
        'EvaporatorFanPowerIncludedinRatedCOP': 'bool | str',
        'FractionofCondenserPumpHeattoWater': 'float',
        'MaximumAmbientTemperatureforCrankcaseHeaterOperation': 'float',
        'RatedCOP': 'float',
        'RatedCondenserInletWaterTemperature': 'float',
        'RatedCondenserWaterFlowRate': 'float',
        'RatedEvaporatorAirFlowRate': 'float',
        'RatedEvaporatorInletAirDryBulbTemperature': 'float',
        'RatedEvaporatorInletAirWetBulbTemperature': 'float',
        'RatedHeatingCapacity': 'float',
        'RatedSensibleHeatRatio': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'EvaporatorAirTemperatureTypeforCurveObjects': 'IB_Curve',
        'HeatingCOPFunctionofAirFlowFractionCurve': 'IB_Curve',
        'HeatingCOPFunctionofTemperatureCurve': 'IB_Curve',
        'HeatingCOPFunctionofWaterFlowFractionCurve': 'IB_Curve',
        'HeatingCapacityFunctionofAirFlowFractionCurve': 'IB_Curve',
        'HeatingCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'HeatingCapacityFunctionofWaterFlowFractionCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilWaterHeatingAirToWaterHeatPump'] = PydanticField(default='IB_CoilWaterHeatingAirToWaterHeatPump')

__all__ = [
    'IB_CoilWaterHeatingAirToWaterHeatPump',
]
