"""Shared persistence primitives for Garden run ledgers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Iterator
from uuid import uuid4

from garden.manifest import atomic_write_bytes, garden_lock, utc_now_iso
from garden.paths import slugify_name, windows_path_key


def serialized_run_start(function):
    """Serialize directory preparation and registration, not background execution."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        with garden_lock(Path(kwargs["garden_root"])):
            return function(*args, **kwargs)

    return wrapped


class RunLedger:
    """Persist ``{"runs": [...]}`` indexes with the ledger's required semantics."""

    def __init__(
        self,
        *,
        lock: str = "none",
        atomic: bool = False,
        recover_trailing_json: bool = False,
        empty_is_empty: bool = False,
        sort_by_created_at: bool = False,
        ensure_ascii: bool = False,
    ) -> None:
        if lock not in {"none", "thread", "file"}:
            raise ValueError("RunLedger lock must be 'none', 'thread', or 'file'.")
        self._lock_mode = lock
        self._thread_lock = Lock() if lock == "thread" else None
        self._atomic = atomic
        self._recover_trailing_json = recover_trailing_json
        self._empty_is_empty = empty_is_empty
        self._sort_by_created_at = sort_by_created_at
        self._ensure_ascii = ensure_ascii

    def list(self, path: Path) -> list[dict[str, Any]]:
        """Read the records in one ledger index."""
        if not path.is_file():
            return []
        with self._locked(path):
            return self._read_unlocked(path)

    def get(self, path: Path, run_id: str) -> dict[str, Any] | None:
        """Return one record by its stable run identifier."""
        return next(
            (record for record in self.list(path) if record.get("run_id") == run_id),
            None,
        )

    def write(self, path: Path, records: list[dict[str, Any]]) -> None:
        """Replace one ledger index with the supplied records."""
        with self._locked(path):
            self._write_unlocked(path, records)

    def upsert(self, path: Path, record: dict[str, Any]) -> None:
        """Replace a record with the same ``run_id`` and append the new value."""
        with self._locked(path):
            existing = self._read_unlocked(path)
            if any(
                item.get("run_id") == record.get("run_id")
                and item.get("status") == "superseded"
                for item in existing
            ):
                return
            records = [
                item for item in existing if item.get("run_id") != record.get("run_id")
            ]
            records.append(record)
            if self._sort_by_created_at:
                records.sort(key=lambda item: str(item.get("created_at", "")))
            self._write_unlocked(path, records)

    def prepare_folder(
        self,
        path: Path,
        run_folder: str,
        *,
        recipe: str | None = None,
        model_target: dict[str, Any] | None = None,
        preserve_other_recipes: bool = False,
    ) -> None:
        """Retire replaced outputs; call inside the serialized start operation."""
        with self._locked(path):
            records = self._read_unlocked(path)
            folder_key = windows_path_key(run_folder).rstrip("/")
            matching = [
                record
                for record in records
                if (previous := windows_path_key(record.get("run_folder", "")).rstrip("/"))
                and (
                    previous == folder_key
                    or previous.startswith(folder_key + "/")
                    or folder_key.startswith(previous + "/")
                )
            ]
            for record in matching:
                if record.get("status") == "running":
                    raise ValueError(
                        f"Simulation folder is in use by run {record['run_id']}: "
                        f"{run_folder}. Poll that run before starting another."
                    )
                previous_model = record.get("model_target") or {}
                if model_target and previous_model and (
                    previous_model.get("model_identifier")
                    != model_target.get("model_identifier")
                ):
                    raise ValueError(
                        f"Simulation folder belongs to another model: {run_folder}. "
                        "Use distinct model display names."
                    )
            changed = False
            for record in matching:
                if (
                    preserve_other_recipes
                    and recipe is not None
                    and record.get("recipe") != recipe
                    and windows_path_key(record["run_folder"]).rstrip("/") == folder_key
                ):
                    continue
                record.update(status="superseded", outputs=[])
                if "runtime_status" in record:
                    record["runtime_status"] = "superseded"
                changed = True
            if changed:
                self._write_unlocked(path, records)

    @contextmanager
    def _locked(self, path: Path) -> Iterator[None]:
        path = Path(path)
        if self._lock_mode == "thread":
            assert self._thread_lock is not None
            with self._thread_lock:
                yield
            return
        if self._lock_mode == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = path.with_suffix(".lock")
            with lock_path.open("a+b") as lock_file:
                if os.name == "nt":
                    import msvcrt

                    lock_file.seek(0, os.SEEK_END)
                    if lock_file.tell() == 0:
                        lock_file.write(b"\0")
                        lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    try:
                        yield
                    finally:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            return
        yield

    def _read_unlocked(self, path: Path) -> list[dict[str, Any]]:
        path = Path(path)
        if not path.is_file():
            return []
        raw = path.read_text(encoding="utf-8")
        if self._empty_is_empty and not raw.strip():
            return []
        return list(self._decode(raw).get("runs", []))

    def _write_unlocked(self, path: Path, records: list[dict[str, Any]]) -> None:
        path = Path(path)
        payload = (
            json.dumps({"runs": records}, indent=2, ensure_ascii=self._ensure_ascii) + "\n"
        )
        if self._atomic:
            atomic_write_bytes(path, payload.encode("utf-8"))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")

    def _decode(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            if not self._recover_trailing_json or exc.msg != "Extra data":
                raise
            payload, _ = json.JSONDecoder().raw_decode(raw)
            if not isinstance(payload, dict):
                raise
            return payload


def normalize_run_id(value: str | None, fallback: str) -> str:
    """Slugify an optional identifier, using the supplied generated fallback."""
    return slugify_name(value or fallback)


def make_run_target(
    *,
    target_type: str,
    domain: str,
    garden_id: str,
    recipe: str,
    run_id: str,
) -> dict[str, str]:
    """Build the common target shape used by Garden run ledgers."""
    return {
        "target_type": target_type,
        "garden_id": garden_id,
        "domain": domain,
        "recipe": recipe,
        "run_id": run_id,
    }


def run_id_from_target_or_value(
    target: dict[str, Any] | None,
    run_id: str | None,
    *,
    target_type: str,
    domain: str | None = None,
    domain_message: str | None = None,
    recipe: str | None = None,
    allowed_recipes: set[str] | None = None,
    missing_message: str = "Provide run_target or run_id.",
    target_run_id_required: bool = True,
    slug_value: bool = False,
) -> str:
    """Resolve a run identifier while preserving each target family's checks."""
    if target is not None:
        if target.get("target_type") != target_type:
            raise ValueError(f"run_target must be a {target_type} target.")
        if domain is not None and target.get("domain") != domain:
            raise ValueError(domain_message or f"run_target must reference {domain}.")
        target_recipe = target.get("recipe")
        if allowed_recipes is not None and target_recipe not in allowed_recipes:
            allowed = ", ".join(sorted(allowed_recipes))
            raise ValueError(f"run_target must reference one of: {allowed}.")
        if recipe is not None and target_recipe != recipe:
            raise ValueError(f"run_target must reference recipe '{recipe}'.")
        if target_run_id_required:
            value = target.get("run_id")
            if not value:
                raise ValueError("run_target requires run_id.")
            return str(value)
        return str(target["run_id"])
    if run_id:
        return slugify_name(run_id) if slug_value else run_id
    raise ValueError(missing_message)


def project_run(
    record: dict[str, Any],
    fields: tuple[str, ...],
    *,
    include_missing: bool = False,
) -> dict[str, Any]:
    """Project an internal record onto a domain's public run summary."""
    if include_missing:
        return {field: record.get(field) for field in fields}
    return {field: record.get(field) for field in fields if field in record}


def _default_run_ledger() -> RunLedger:
    return RunLedger(
        lock="file",
        atomic=True,
        recover_trailing_json=True,
        empty_is_empty=True,
        sort_by_created_at=True,
    )


@dataclass
class RunManager:
    """Cohesive run-index, target-validation, and status manager for simulation runners."""

    domain: str
    target_type: str
    runs_dir: Path
    default_recipe: str
    allowed_recipes: set[str] | None = None
    per_recipe_index: bool = False
    run_id_prefix: str | None = None
    use_uuid_fallback: bool = False
    slug_lookup: bool = False
    target_run_id_required: bool = True
    validate_target_domain: bool = True
    domain_message: str | None = None
    missing_message: str = "Provide run_target or run_id."
    not_found_label: str = "Simulation"
    public_fields: tuple[str, ...] = ("run_id", "target", "recipe", "status", "created_at")
    include_missing_public: bool = False
    ledger: RunLedger = field(default_factory=_default_run_ledger)

    def index_path(self, garden_root: Path, recipe: str | None = None) -> Path:
        """Return the ``index.json`` path for this runner (optionally per recipe)."""
        base = garden_root / self.runs_dir
        if self.per_recipe_index:
            resolved = recipe or self.default_recipe
            return base / resolved / "index.json"
        return base / "index.json"

    def run_dir(
        self,
        garden_root: Path,
        run_id: str,
        *,
        recipe: str | None = None,
        create: bool = True,
    ) -> Path:
        """Resolve and validate the Garden-contained directory for one run."""
        root = garden_root.expanduser().resolve()
        base = root / self.runs_dir
        if self.per_recipe_index:
            base = base / (recipe or self.default_recipe)
        target_dir = (base / run_id).resolve()
        target_dir.relative_to(root)
        if create:
            target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def list(self, garden_root: Path, *, recipe: str | None = None) -> list[dict[str, Any]]:
        """List stored run records for this runner (or recipe)."""
        return self.ledger.list(self.index_path(garden_root, recipe=recipe))

    def get(
        self,
        garden_root: Path,
        run_id: str,
        *,
        recipe: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch one run record by identifier, returning None if missing."""
        return self.ledger.get(self.index_path(garden_root, recipe=recipe), run_id)

    def require(
        self,
        garden_root: Path,
        run_id: str,
        *,
        recipe: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one run record or raise a clear ValueError."""
        record = self.get(garden_root, run_id, recipe=recipe)
        if record is None:
            raise ValueError(f"{self.not_found_label} run was not found: {run_id}")
        return record

    def upsert(
        self,
        garden_root: Path,
        record: dict[str, Any],
        *,
        recipe: str | None = None,
    ) -> None:
        """Persist or update one run record in the ledger."""
        self.ledger.upsert(self.index_path(garden_root, recipe=recipe), record)

    def prepare_folder(
        self,
        garden_root: Path,
        run_folder: str,
        *,
        recipe: str | None = None,
        model_target: dict[str, Any] | None = None,
        preserve_other_recipes: bool = False,
    ) -> None:
        """Retire prior superseded records sharing ``run_folder``."""
        self.ledger.prepare_folder(
            self.index_path(garden_root, recipe=recipe),
            run_folder,
            recipe=recipe,
            model_target=model_target,
            preserve_other_recipes=preserve_other_recipes,
        )

    def normalize_run_id(
        self,
        value: str | None,
        *,
        prefix: str | None = None,
        recipe: str | None = None,
        fallback: str | None = None,
    ) -> str:
        """Slugify ``value`` or synthesize a deterministic unique run identifier."""
        if fallback is None:
            tag = prefix or (
                f"{self.run_id_prefix}_{recipe}"
                if (self.run_id_prefix and recipe)
                else (self.run_id_prefix or recipe or self.default_recipe)
            )
            if self.use_uuid_fallback:
                fallback = f"{tag}_{utc_now_iso()}_{uuid4().hex[:8]}"
            else:
                stamp = utc_now_iso().replace(":", "").replace("-", "").replace("Z", "").lower()
                fallback = f"{tag}_{stamp}"
        return normalize_run_id(value, fallback)

    def make_target(
        self,
        garden_id: str,
        run_id: str,
        *,
        recipe: str | None = None,
    ) -> dict[str, str]:
        """Build a typed run target dict for this runner."""
        resolved_recipe = recipe or self.default_recipe
        if self.allowed_recipes is not None and resolved_recipe not in self.allowed_recipes:
            raise ValueError(f"Unsupported {self.not_found_label} run recipe: {resolved_recipe}.")
        return make_run_target(
            target_type=self.target_type,
            domain=self.domain,
            garden_id=garden_id,
            recipe=resolved_recipe,
            run_id=run_id,
        )

    def resolve_run_id(
        self,
        run_target: dict[str, Any] | None,
        run_id: str | None,
        *,
        recipe: str | None = None,
    ) -> str:
        """Validate ``run_target`` or fall back to ``run_id``."""
        return run_id_from_target_or_value(
            run_target,
            run_id,
            target_type=self.target_type,
            domain=self.domain if self.validate_target_domain else None,
            domain_message=self.domain_message,
            recipe=recipe,
            allowed_recipes=None if recipe is not None else self.allowed_recipes,
            missing_message=self.missing_message,
            target_run_id_required=self.target_run_id_required,
            slug_value=self.slug_lookup,
        )

    def public_run(self, record: dict[str, Any]) -> dict[str, Any]:
        """Project one internal record onto its public summary fields."""
        return project_run(
            record,
            self.public_fields,
            include_missing=self.include_missing_public,
        )

    @staticmethod
    def failure_fields(error: str, traceback_text: str | None = None) -> dict[str, Any]:
        """Return standard failure status fields for run ledger updates."""
        fields: dict[str, Any] = {
            "status": "failed",
            "runtime_status": "failed",
            "completed_at": utc_now_iso(),
            "error": error,
        }
        if traceback_text is not None:
            fields["traceback"] = traceback_text
        return fields
