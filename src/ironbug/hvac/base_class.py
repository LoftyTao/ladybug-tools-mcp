"""Internal source-compatibility support for Ironbug HVAC objects."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import AliasChoices, Field

from ironbug.hvac._base import IronbugBaseModel


IB_Children: TypeAlias = list[Any]
IB_FieldArgumentSet: TypeAlias = dict[str, Any]
IB_PropArgumentSet: TypeAlias = dict[str, Any]


class IB_ModelObject(IronbugBaseModel):
    """Common Ironbug object fields preserved for source-compatible serialization."""

    type: Literal["IB_ModelObject"] = Field(default="IB_ModelObject")
    identifier: str | None = None
    display_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("display_name", "DisplayName"),
        serialization_alias="DisplayName",
    )
    user_data: dict[str, Any] | None = None
    Children: IB_Children = Field(default_factory=list)
    CustomAttributes: IB_FieldArgumentSet = Field(default_factory=dict)
    IBProperties: IB_PropArgumentSet = Field(default_factory=dict)

    @property
    def DisplayName(self) -> str | None:
        return self.display_name

    @DisplayName.setter
    def DisplayName(self, value: str | None) -> None:
        self.display_name = value
