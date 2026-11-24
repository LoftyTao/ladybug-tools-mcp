"""Garden manifest, atomic file persistence, and process/thread locking."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from threading import Lock, RLock, local
import time
from typing import Any, Iterator, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from garden.paths import resolve_contained_path, windows_path_key
from ladybug_tools_mcp.contracts import make_garden_target


CURRENT_SCHEMA_VERSION = "1"
LOCK_ACQUIRE_TIMEOUT_SECONDS = 60.0

_PROCESS_LOCKS_GUARD = Lock()
_PROCESS_LOCKS: dict[tuple[int, str], RLock] = {}
_LOCK_STATE = local()


def utc_now_iso() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Atomically write bytes via a sibling temp file and ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{uuid4().hex}.tmp")
    try:
        with tmp_path.open("xb") as handle:
            handle.write(content)
            handle.flush()
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(0.02 * (attempt + 1))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_json_file(
    path: Path,
    data: dict[str, Any],
    *,
    ensure_ascii: bool = True,
) -> None:
    """Atomically write a UTF-8 JSON object with a stable trailing newline."""
    payload = (json.dumps(data, indent=2, ensure_ascii=ensure_ascii) + "\n").encode("utf-8")
    atomic_write_bytes(path, payload)


def _process_lock(root: Path) -> RLock:
    key = (os.getpid(), str(root))
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = RLock()
            _PROCESS_LOCKS[key] = lock
        return lock


@contextmanager
def garden_lock(garden_root: Path) -> Iterator[None]:
    """Serialize Garden mutations across threads and OS processes."""
    root = garden_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Garden root directory not found: {root}")
    key = (os.getpid(), str(root))
    with _process_lock(root):
        depths = getattr(_LOCK_STATE, "depths", None)
        if depths is None:
            depths = {}
            _LOCK_STATE.depths = depths
        depth = depths.get(key, 0)
        if depth:
            depths[key] = depth + 1
            try:
                yield
            finally:
                depths[key] -= 1
            return

        lock_path = root / ".garden" / "garden.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            started = time.monotonic()
            while True:
                lock_file.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if time.monotonic() - started > LOCK_ACQUIRE_TIMEOUT_SECONDS:
                        raise TimeoutError(
                            f"Timed out waiting for Garden lock at {lock_path}."
                        ) from exc
                    time.sleep(0.05)

            owner_pid = os.getpid()
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
                if os.getpid() == owner_pid:
                    lock_file.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class GardenManifest(BaseModel):
    """Garden project manifest persisted in ``garden.json``."""

    model_config = ConfigDict(extra="ignore", validate_assignment=False)

    schema_version: str = CURRENT_SCHEMA_VERSION
    revision: int = 0
    garden_id: str
    name: str
    description: str = ""
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    base_honeybee_model: dict[str, Any] | None = None
    base_dragonfly_model: dict[str, Any] | None = None
    base_fairyfly_model: dict[str, Any] | None = None
    models: list[dict[str, Any]] = Field(default_factory=list)
    weather_files: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _validate_schema_version(cls, value: Any) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("Garden manifest schema_version must be a non-empty string.")
        if value != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported Garden manifest schema_version: "
                f"{value!r}; supported version is {CURRENT_SCHEMA_VERSION!r}."
            )
        return value

    @field_validator("revision", mode="before")
    @classmethod
    def _validate_revision(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Garden manifest revision must be a non-negative integer.")
        return value

    @field_validator("garden_id", "name", mode="before")
    @classmethod
    def _validate_non_blank_string(cls, value: Any, info: ValidationInfo) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Garden manifest {info.field_name} must be a non-empty string.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _validate_description(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Garden manifest description must be a string.")
        return value

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamp(cls, value: Any, info: ValidationInfo) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"Garden manifest {info.field_name} must be a non-empty string.")
        return value

    @field_validator(
        "base_honeybee_model",
        "base_dragonfly_model",
        "base_fairyfly_model",
        mode="before",
    )
    @classmethod
    def _validate_base_model(
        cls, value: Any, info: ValidationInfo
    ) -> dict[str, Any] | None:
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"Garden manifest {info.field_name} must be an object or null.")
        return value

    @field_validator("models", "weather_files", "artifacts", mode="before")
    @classmethod
    def _validate_object_list(
        cls, value: Any, info: ValidationInfo
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValueError(f"Garden manifest {info.field_name} must be a list of objects.")
        return list(value)

    @classmethod
    def new(cls, name: str, description: str = "") -> "GardenManifest":
        """Create a new manifest with a generated Garden id."""
        return cls(
            garden_id=f"garden_{uuid4().hex[:12]}",
            name=name,
            description=description,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GardenManifest":
        """Load and validate a manifest from a JSON-compatible dict."""
        if not isinstance(data, dict):
            raise ValueError("Garden manifest must be a JSON object.")
        if "schema_version" not in data:
            raise ValueError("Garden manifest schema_version must be a non-empty string.")
        return cls.model_validate(data)

    @classmethod
    def read(cls, garden_root: Path) -> "GardenManifest":
        """Read ``garden.json`` from a Garden root without creating lock files."""
        root = garden_root.expanduser().resolve()
        with (root / "garden.json").open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Garden manifest must be a JSON object.")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest."""
        return self.model_dump()

    def validate(self) -> None:
        """Validate the complete in-memory manifest before persistence."""
        # Validate current attributes directly so invalid mutations raise before model_dump().
        type(self).model_validate(
            {field_name: getattr(self, field_name) for field_name in type(self).model_fields}
        )

    def upsert_artifact(
        self,
        artifact: dict[str, Any],
        *,
        key_fields: tuple[str, ...] = ("artifact_type", "path"),
    ) -> dict[str, Any]:
        """Replace an artifact matching its identity fields and append the new record."""
        if not key_fields:
            raise ValueError("Artifact key_fields must not be empty.")
        self.artifacts = [
            item
            for item in self.artifacts
            if any(item.get(field) != artifact.get(field) for field in key_fields)
        ]
        self.artifacts.append(artifact)
        return artifact

    def write(
        self,
        garden_root: Path,
        *,
        staged_writes: Mapping[str, bytes] | None = None,
    ) -> Path:
        """Atomically persist optional staged files and ``garden.json`` under lock."""
        self.validate()
        root = garden_root.expanduser().resolve()
        resolved_writes: list[tuple[str, Path, bytes]] = []
        seen_keys: set[str] = set()
        for raw_path, content in (staged_writes or {}).items():
            if not isinstance(content, bytes):
                raise TypeError("Garden staged_writes values must be bytes.")
            target = resolve_contained_path(root, raw_path, label="Garden staged path")
            rel_posix = target.relative_to(root).as_posix()
            key = windows_path_key(rel_posix)
            if key == "garden.json" or key.startswith("garden.json/"):
                raise ValueError("staged_writes cannot replace garden.json directly.")
            if key == ".garden" or key.startswith(".garden/"):
                raise ValueError("staged_writes cannot write internal .garden state.")
            if key in seen_keys:
                raise ValueError(f"staged_writes contains duplicate path alias: {raw_path}.")
            seen_keys.add(key)
            resolved_writes.append((rel_posix, target, content))
        resolved_writes.sort(key=lambda item: item[0])

        with garden_lock(root):
            previous_revision = self.revision
            previous_updated_at = self.updated_at
            try:
                for _, target, content in resolved_writes:
                    atomic_write_bytes(target, content)
                self.revision += 1
                self.updated_at = utc_now_iso()
                manifest_bytes = (
                    json.dumps(
                        self.to_dict(),
                        indent=2,
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("utf-8")
                atomic_write_bytes(root / "garden.json", manifest_bytes)
            except Exception:
                self.revision = previous_revision
                self.updated_at = previous_updated_at
                raise
        return root / "garden.json"

    def target(self) -> dict[str, str]:
        """Return this Garden's public target."""
        return make_garden_target(self.garden_id)
