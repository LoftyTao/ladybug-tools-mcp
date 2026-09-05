"""Strong public contract for Garden authoring operation results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GardenOperationTarget(BaseModel):
    """Stable reference for one Garden authoring operation."""

    target_type: Literal["garden_operation"] = "garden_operation"
    garden_id: str
    operation_id: str
    operation_type: str


class OperationPersistenceReceipt(BaseModel):
    """Existing persistence receipt carried by the unified result."""

    model_config = ConfigDict(extra="allow")

    status: str
    garden_id: str
    warnings: list[str] = Field(default_factory=list)
    persisted_path: str | None = None
    change_summary: dict[str, Any] = Field(default_factory=dict)


class OperationReport(BaseModel):
    """Existing compact report carried by the unified result."""

    model_config = ConfigDict(extra="allow")

    status: str
    message: str
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class GardenOperationResult(BaseModel):
    """Machine-verifiable result shared by Garden authoring mutations."""

    operation_target: GardenOperationTarget
    runtime_status: Literal[
        "prepared",
        "committing",
        "rolling_back",
        "interrupted",
        "recovery_blocked",
        "committed",
        "replayed",
        "failed",
        "conflict",
        "no_change",
    ]
    readiness_status: Literal[
        "ready",
        "retryable",
        "reload_required",
        "intervention_required",
    ]
    intervention_reason: str | None = None
    before_revision: int | None = Field(default=None, ge=0)
    after_revision: int | None = Field(default=None, ge=0)
    affected_targets: list[dict[str, Any]] = Field(default_factory=list)
    persistence_receipt: OperationPersistenceReceipt
    report: OperationReport
    checkpoint_target: dict[str, Any] | None = None
