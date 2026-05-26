"""Shared Pydantic settings and source metadata for Ironbug HVAC objects."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IronbugBaseModel(BaseModel):
    """Base model with source-compatible field population."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _deduplicate_display_name_alias(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            if "display_name" in value and "DisplayName" in value:
                value.pop("DisplayName")
            for field_name in getattr(cls, "SOURCE_METADATA_ONLY_FIELDS", ()):
                value.pop(field_name, None)
        return value


class IronbugSourceMetadata(IronbugBaseModel):
    """Reference from a Python class back to Ironbug and simulation vocabulary."""

    source_class: str
    source_path: str
    source_namespace: str
    source_bases: tuple[str, ...] = ()
    source_interfaces: tuple[str, ...] = ()
    source_field_set: str | None = None
    source_properties: tuple[str, ...] = ()
    source_data_members: tuple[str, ...] = ()
    source_should_serialize: tuple[str, ...] = ()
    source_field_names: tuple[str, ...] = ()
    source_field_types: dict[str, str] = Field(default_factory=dict)
    source_field_target_types: dict[str, str] = Field(default_factory=dict)
    source_field_target_list_names: tuple[str, ...] = ()
    source_property_types: dict[str, str] = Field(default_factory=dict)
    source_data_member_types: dict[str, str] = Field(default_factory=dict)
    energyplus_object: str | None = None
    openstudio_class: str | None = None


class IronbugSourceMixin:
    """Class-level source metadata shared by Ironbug HVAC objects."""

    SOURCE_CLASS: ClassVar[str]
    SOURCE_PATH: ClassVar[str]
    SOURCE_NAMESPACE: ClassVar[str] = ""
    SOURCE_BASES: ClassVar[tuple[str, ...]] = ()
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None

    @classmethod
    def source_metadata(cls) -> IronbugSourceMetadata:
        return IronbugSourceMetadata(
            source_class=cls.SOURCE_CLASS,
            source_path=cls.SOURCE_PATH,
            source_namespace=cls.SOURCE_NAMESPACE,
            source_bases=cls.SOURCE_BASES,
            source_interfaces=cls.SOURCE_INTERFACES,
            source_field_set=cls.SOURCE_FIELD_SET,
            source_properties=cls.SOURCE_PROPERTIES,
            source_data_members=cls.SOURCE_DATA_MEMBERS,
            source_should_serialize=cls.SOURCE_SHOULD_SERIALIZE,
            source_field_names=cls.SOURCE_FIELD_NAMES,
            source_field_types=cls.SOURCE_FIELD_TYPES,
            source_field_target_types=cls.SOURCE_FIELD_TARGET_TYPES,
            source_field_target_list_names=cls.SOURCE_FIELD_TARGET_LIST_NAMES,
            source_property_types=cls.SOURCE_PROPERTY_TYPES,
            source_data_member_types=cls.SOURCE_DATA_MEMBER_TYPES,
            energyplus_object=cls.ENERGYPLUS_OBJECT,
            openstudio_class=cls.OPENSTUDIO_CLASS,
        )


class IronbugInterfaceMarker(IronbugSourceMixin):
    """Source metadata marker for Ironbug C# interfaces."""
