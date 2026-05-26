"""Source-compatible helpers for Ironbug plant operation schemes."""

from __future__ import annotations

from typing import Any

from ironbug.hvac.base_class import IB_PropArgumentSet


PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W = 1000000000
PLANT_OPERATION_EQUIPMENTS_PROPERTY = "_equipments"


class PlantEquipmentOperationSchemeItem:
    """Nested source item used by IB_PlantEquipmentOperationSchemeBase."""

    __slots__ = ("Limit", "Obj")

    SOURCE_PARENT_CLASS = "IB_PlantEquipmentOperationSchemeBase"
    SOURCE_CLASS = "PlantEquipmentOperationSchemeItem"
    SOURCE_METHOD = "IB_PlantEquipmentOperationSchemeBase.AddEquipment"
    SOURCE_CONSOLE_TYPE = (
        "Ironbug.HVAC.IB_PlantEquipmentOperationSchemeBase+"
        "PlantEquipmentOperationSchemeItem, Ironbug.HVAC"
    )

    def __init__(self, *, Limit: int, Obj: Any) -> None:
        self.Limit = Limit
        self.Obj = Obj

    def to_source_dict(self) -> dict[str, Any]:
        return {
            "$type": self.SOURCE_CONSOLE_TYPE,
            "Limit": self.Limit,
            "Obj": self.Obj,
        }


def plant_equipment_operation_ib_properties(
    equipment: Any,
    *,
    upper_limit_w: int = PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
) -> IB_PropArgumentSet:
    """Return the source backing payload for AddEquipment(limit, obj)."""

    item = PlantEquipmentOperationSchemeItem(
        Limit=upper_limit_w,
        Obj=equipment,
    )
    return {
        PLANT_OPERATION_EQUIPMENTS_PROPERTY: [
            item.to_source_dict(),
        ],
    }
