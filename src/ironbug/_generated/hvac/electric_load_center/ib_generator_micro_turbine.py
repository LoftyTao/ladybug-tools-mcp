"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_GeneratorMicroTurbine(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_GeneratorMicroTurbine'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_GeneratorMicroTurbine.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Generator',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_GeneratorMicroTurbine_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'ReferenceElectricalPowerOutput',
        'MinimumFullLoadElectricalPowerOutput',
        'MaximumFullLoadElectricalPowerOutput',
        'ReferenceElectricalEfficiencyUsingLowerHeatingValue',
        'ReferenceCombustionAirInletTemperature',
        'ReferenceCombustionAirInletHumidityRatio',
        'ReferenceElevation',
        'ElectricalPowerFunctionofTemperatureandElevationCurve',
        'ElectricalEfficiencyFunctionofTemperatureCurve',
        'ElectricalEfficiencyFunctionofPartLoadRatioCurve',
        'FuelType',
        'FuelHigherHeatingValue',
        'FuelLowerHeatingValue',
        'StandbyPower',
        'AncillaryPower',
        'AncillaryPowerFunctionofFuelInputCurve',
        'ReferenceExhaustAirMassFlowRate',
        'ExhaustAirFlowRateFunctionofTemperatureCurve',
        'ExhaustAirFlowRateFunctionofPartLoadRatioCurve',
        'NominalExhaustAirOutletTemperature',
        'ExhaustAirTemperatureFunctionofTemperatureCurve',
        'ExhaustAirTemperatureFunctionofPartLoadRatioCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AncillaryPower': 'float',
        'FuelHigherHeatingValue': 'float',
        'FuelLowerHeatingValue': 'float',
        'FuelType': 'str',
        'MaximumFullLoadElectricalPowerOutput': 'float',
        'MinimumFullLoadElectricalPowerOutput': 'float',
        'NominalExhaustAirOutletTemperature': 'float',
        'ReferenceCombustionAirInletHumidityRatio': 'float',
        'ReferenceCombustionAirInletTemperature': 'float',
        'ReferenceElectricalEfficiencyUsingLowerHeatingValue': 'float',
        'ReferenceElectricalPowerOutput': 'float',
        'ReferenceElevation': 'float',
        'ReferenceExhaustAirMassFlowRate': 'float',
        'StandbyPower': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AncillaryPowerFunctionofFuelInputCurve': 'IB_Curve',
        'AvailabilitySchedule': 'IB_Schedule',
        'ElectricalEfficiencyFunctionofPartLoadRatioCurve': 'IB_Curve',
        'ElectricalEfficiencyFunctionofTemperatureCurve': 'IB_Curve',
        'ElectricalPowerFunctionofTemperatureandElevationCurve': 'IB_Curve',
        'ExhaustAirFlowRateFunctionofPartLoadRatioCurve': 'IB_Curve',
        'ExhaustAirFlowRateFunctionofTemperatureCurve': 'IB_Curve',
        'ExhaustAirTemperatureFunctionofPartLoadRatioCurve': 'IB_Curve',
        'ExhaustAirTemperatureFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_GeneratorMicroTurbine'] = PydanticField(default='IB_GeneratorMicroTurbine')

__all__ = [
    'IB_GeneratorMicroTurbine',
]
