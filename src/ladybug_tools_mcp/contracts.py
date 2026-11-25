"""Shared public contract helpers and Pydantic schemas for Ladybug Tools MCP tools."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, GetJsonSchemaHandler
from pydantic_core import CoreSchema

T = TypeVar("T", bound=BaseModel)


def make_report(
    status: str,
    message: str,
    *,
    warnings: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal report shape used by public tool returns."""
    return {
        "status": status,
        "message": message,
        "warnings": warnings or [],
        "details": details or {},
    }


def make_persistence_receipt(
    *,
    status: str,
    garden_id: str,
    base_honeybee_model_changed: bool = False,
    base_dragonfly_model_changed: bool = False,
    base_fairyfly_model_changed: bool = False,
    warnings: list[str] | None = None,
    model_target: dict[str, Any] | None = None,
    persisted_path: str | None = None,
    change_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal Garden persistence receipt shape."""
    return {
        "status": status,
        "garden_id": garden_id,
        "base_honeybee_model_changed": base_honeybee_model_changed,
        "base_dragonfly_model_changed": base_dragonfly_model_changed,
        "base_fairyfly_model_changed": base_fairyfly_model_changed,
        "warnings": warnings or [],
        "model_target": model_target or {},
        "persisted_path": persisted_path,
        "change_summary": change_summary or {},
    }


def make_artifact_receipt(
    *,
    status: str,
    garden_id: str,
    artifact_type: str,
    artifact_path: str,
    absolute_path: str,
    source: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build the minimal Garden artifact receipt shape."""
    return {
        "status": status,
        "garden_id": garden_id,
        "artifact_type": artifact_type,
        "artifact_path": artifact_path,
        "absolute_path": absolute_path,
        "source": source or {},
        "warnings": warnings or [],
    }


def make_garden_target(garden_id: str) -> dict[str, str]:
    """Build a Garden target."""
    return {
        "target_type": "garden",
        "garden_id": garden_id,
    }


def make_garden_version_target(
    garden_id: str,
    version_id: str,
    *,
    short_version_id: str | None = None,
) -> dict[str, str]:
    """Build a Garden version target."""
    target = {
        "target_type": "garden_version",
        "garden_id": garden_id,
        "version_id": version_id,
    }
    if short_version_id:
        target["short_version_id"] = short_version_id
    return target


def make_garden_properties_library_target(
    garden_id: str,
    *,
    domain: str,
    object_family: str,
    identifier: str,
    path: str,
) -> dict[str, str]:
    """Build a Garden Properties Library object target."""
    return {
        "target_type": "garden_properties_library_object",
        "garden_id": garden_id,
        "domain": domain,
        "object_family": object_family,
        "identifier": identifier,
        "path": path,
    }


def make_flowerpot(
    *,
    kind: str,
    label: str,
    target: dict[str, Any] | None = None,
    payload_context: dict[str, Any] | None = None,
    platform: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal opaque Flowerpot shape."""
    return {
        "type": "Flowerpot",
        "schema_version": "1",
        "kind": kind,
        "label": label,
        "target": target or {},
        "payload_context": payload_context or {},
        "platform": platform or {},
    }


def dump_input(value: Any) -> Any:
    """Recursively dump Pydantic models to plain dicts while dropping None fields."""
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    if isinstance(value, (list, tuple)):
        return [dump_input(item) for item in value]
    if isinstance(value, dict):
        return {key: dump_input(item) for key, item in value.items()}
    return value


def dump_target(target: BaseModel | dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert an optional target ref model or dict into a plain dict."""
    if target is None:
        return None
    if isinstance(target, BaseModel):
        return target.model_dump(exclude_none=True)
    return dump_input(target)


def dump_targets(targets: list[BaseModel | dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Convert an optional list of target ref models or dicts into plain dicts."""
    if targets is None:
        return None
    return [
        item.model_dump(exclude_none=True) if isinstance(item, BaseModel) else dump_input(item)
        for item in targets
    ]


def dump_models(items: list[Any] | None) -> list[dict[str, Any]] | None:
    """Convert a list of Pydantic models or dict-like payloads into plain dicts."""
    if items is None:
        return None
    return [
        item.model_dump(exclude_none=True) if isinstance(item, BaseModel) else dump_input(dict(item))
        for item in items
    ]


def validate_output(model_cls: type[T], payload: Any) -> T:
    """Validate and coerce a tool payload into a Pydantic output model instance."""
    if isinstance(payload, model_cls):
        return payload
    return model_cls.model_validate(payload)


class _MappingReadMixin:
    """Read-only dict-style lookup for direct Python tool.fn() callers."""

    def _present_keys(self) -> set[str]:
        fields_set = getattr(self, "model_fields_set", ())
        extra = getattr(self, "__pydantic_extra__", None)
        if extra:
            return set(fields_set) | set(extra)
        return set(fields_set)

    def __getitem__(self, key: str) -> Any:
        if key in self._present_keys():
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._present_keys():
            return getattr(self, key)
        return default

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._present_keys()


MappingReadMixin = _MappingReadMixin


class GardenTargetRef(_MappingReadMixin, BaseModel):
    """Base typed reference for Garden-managed targets and artifacts."""

    model_config = ConfigDict(extra="allow")

    target_type: str | None = Field(default=None, description="Target discriminator type.")
    garden_id: str | None = Field(default=None, description="Owning Garden identifier.")
    id: str | None = Field(default=None, description="Optional target ID.")
    identifier: str | None = Field(default=None, description="Asset or object identifier.")
    domain: str | None = Field(default=None, description="Target domain (e.g. 'honeybee', 'dragonfly', 'energy').")
    path: str | None = Field(default=None, description="Garden-relative path to the asset or artifact.")

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        """Emit a compact object schema so multi-target tools stay well under schema budgets."""
        return {
            "type": "object",
            "title": cls.__name__,
            "additionalProperties": True,
        }


class BuildingModelTargetRef(GardenTargetRef):
    """Target pointing to a Garden-managed Honeybee, Dragonfly, or Fairyfly model."""

    model_identifier: str | None = Field(default=None, description="Building model identifier in the Garden.")


class BuildingObjectTargetRef(GardenTargetRef):
    """Target pointing to an object inside a Honeybee or Dragonfly building model."""

    model_identifier: str | None = Field(default=None, description="Owning building model identifier.")
    object_type: str | None = Field(
        default=None,
        description="Object type such as 'room', 'face', 'aperture', 'room2d', 'story', or 'building'.",
    )
    object_identifier: str | None = Field(default=None, description="Identifier of the referenced object.")


class IronbugModelTargetRef(GardenTargetRef):
    """Target pointing to a Garden-managed Ironbug IB_HVACSystem asset."""

    root_type: str | None = Field(default=None, description="C# root class name, typically 'IB_HVACSystem'.")


class RunTargetRef(GardenTargetRef):
    """Target pointing to a Garden simulation or analysis run."""

    run_id: str | None = Field(default=None, description="Simulation or analysis run identifier.")
    recipe: str | None = Field(default=None, description="Recipe or workflow name for the run.")


class LibraryObjectTargetRef(GardenTargetRef):
    """Target pointing to a Garden Properties Library object."""

    object_family: str | None = Field(default=None, description="Properties library object family.")


class DataCollectionTargetRef(GardenTargetRef):
    """Target pointing to a persisted Ladybug DataCollection artifact."""

    artifact_type: str | None = Field(default=None, description="Data collection artifact type.")


class WeatherTargetRef(GardenTargetRef):
    """Target pointing to a Garden-managed weather file artifact."""

    artifact_type: str | None = Field(default=None, description="Weather artifact type such as 'epw' or 'wea'.")


class ArtifactTargetRef(GardenTargetRef):
    """Target pointing to a generic Garden-managed output artifact."""

    artifact_type: str | None = Field(default=None, description="Artifact type or file format.")


class SkyTargetRef(GardenTargetRef):
    """Target pointing to a Radiance sky artifact."""

    artifact_type: str | None = Field(default=None, description="Sky artifact type.")


class FlowerpotRef(_MappingReadMixin, BaseModel):
    """Typed reference for opaque Flowerpot handoff envelopes."""

    model_config = ConfigDict(extra="allow")

    type: str | None = Field(default=None, description="Envelope type marker, typically 'Flowerpot'.")
    schema_version: str | None = Field(default=None, description="Flowerpot schema version.")
    kind: str | None = Field(default=None, description="Flowerpot kind discriminator.")
    label: str | None = Field(default=None, description="Human-readable Flowerpot label.")
    target: dict[str, Any] | None = Field(default=None, description="Referenced Garden target metadata.")
    payload_context: dict[str, Any] | None = Field(default=None, description="Contextual payload metadata.")
    platform: dict[str, Any] | None = Field(default=None, description="Target platform metadata.")

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        """Emit a compact object schema while preserving runtime FlowerpotRef validation."""
        return {
            "type": "object",
            "title": cls.__name__,
            "additionalProperties": True,
        }


class ToolReportModel(_MappingReadMixin, BaseModel):
    """Compact tool report returned alongside structured payloads."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    message: str = ""
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class PersistenceReceiptModel(_MappingReadMixin, BaseModel):
    """Receipt describing Garden persistence and base-model mutations."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    garden_id: str | None = None
    base_honeybee_model_changed: bool = False
    base_dragonfly_model_changed: bool = False
    base_fairyfly_model_changed: bool = False
    warnings: list[str] = Field(default_factory=list)
    model_target: dict[str, Any] = Field(default_factory=dict)
    persisted_path: str | None = None
    change_summary: dict[str, Any] = Field(default_factory=dict)


class ArtifactReceiptModel(_MappingReadMixin, BaseModel):
    """Receipt describing a generated Garden artifact."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    garden_id: str | None = None
    artifact_type: str | None = None
    artifact_path: str | None = None
    absolute_path: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ToolResultModel(_MappingReadMixin, BaseModel):
    """Base structured MCP tool output envelope."""

    model_config = ConfigDict(extra="allow")

    summary_view: dict[str, Any] | None = None
    report: ToolReportModel | None = None


class MutationResultModel(ToolResultModel):
    """Output envelope for tools that create or mutate Garden-managed models/assets."""

    target: dict[str, Any] | None = None
    model_target: dict[str, Any] | None = None
    persistence_receipt: PersistenceReceiptModel | None = None


class ArtifactResultModel(ToolResultModel):
    """Output envelope for tools that export or generate Garden artifacts."""

    target: dict[str, Any] | None = None
    artifact_receipt: ArtifactReceiptModel | None = None
    persistence_receipt: PersistenceReceiptModel | None = None


class RunResultModel(ToolResultModel):
    """Output envelope for simulation and analysis run tools."""

    run_id: str | None = None
    status: str | None = None
    target: dict[str, Any] | None = None
    run_target: dict[str, Any] | None = None
    persistence_receipt: PersistenceReceiptModel | None = None


class QueryResultModel(ToolResultModel):
    """Output envelope for search, inspect, and listing tools."""

    target: dict[str, Any] | None = None
    model_target: dict[str, Any] | None = None
    matches: list[dict[str, Any]] | None = None
    count: int | None = None


class ValidationResultModel(ToolResultModel):
    """Output envelope for validation and check tools."""

    valid: bool | None = None
    target: dict[str, Any] | None = None
    model_target: dict[str, Any] | None = None
    errors: list[Any] | None = None
    warnings: list[Any] | None = None


class RuntimeConfigResultModel(ToolResultModel):
    """Output envelope for LB_Get_Runtime_Config."""

    missing_engine_guidance: list[dict[str, Any]] | None = None
    runtime_requirement_guidance: dict[str, Any] | None = None


__all__ = [
    "ArtifactReceiptModel",
    "ArtifactResultModel",
    "ArtifactTargetRef",
    "BuildingModelTargetRef",
    "BuildingObjectTargetRef",
    "DataCollectionTargetRef",
    "FlowerpotRef",
    "GardenTargetRef",
    "IronbugModelTargetRef",
    "LibraryObjectTargetRef",
    "MappingReadMixin",
    "MutationResultModel",
    "PersistenceReceiptModel",
    "QueryResultModel",
    "RunResultModel",
    "RunTargetRef",
    "RuntimeConfigResultModel",
    "SkyTargetRef",
    "ToolReportModel",
    "ToolResultModel",
    "ValidationResultModel",
    "WeatherTargetRef",
    "dump_input",
    "dump_models",
    "dump_target",
    "dump_targets",
    "make_artifact_receipt",
    "make_flowerpot",
    "make_garden_properties_library_target",
    "make_garden_target",
    "make_garden_version_target",
    "make_persistence_receipt",
    "make_report",
    "validate_output",
]
