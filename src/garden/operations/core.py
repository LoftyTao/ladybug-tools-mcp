"""Atomic and recoverable Garden authoring operation primitives."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
from threading import Lock, RLock, local
import time
from typing import TYPE_CHECKING, Any, Iterator, Mapping
from uuid import uuid4

from garden.manifest import utc_now_iso
from garden.paths import validate_portable_file_name, windows_path_key

if TYPE_CHECKING:
    from garden.manifest import GardenManifest


OPERATION_SCHEMA_VERSION = "1"
OPERATION_ROOT = Path(".garden") / "operations"
PENDING_DIR = OPERATION_ROOT / "pending"
RECORDS_DIR = OPERATION_ROOT / "records"
PAYLOADS_DIR = OPERATION_ROOT / "payloads"
AUTHORING_LOCK_PATH = Path(".garden") / "authoring.lock.v2"
AUTHORING_LOCK_OWNERS_DIR = Path(".garden") / "authoring.lock.owners"
LOCK_ACQUIRE_TIMEOUT_SECONDS = 120.0
_WINDOWS_LEGACY_PATH_LIMIT = 260
_OPERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_NONTERMINAL_PHASES = {
    "prepared",
    "committing",
    "rolling_back",
    "interrupted",
    "recovery_blocked",
}
_PHASES = _NONTERMINAL_PHASES | {"committed", "failed"}
_PROCESS_LOCKS_GUARD = Lock()
_PROCESS_LOCKS: dict[tuple[int, str], RLock] = {}
_LOCK_STATE = local()
_PUBLIC_OPERATION_CONTROLS: ContextVar[tuple[str, int | None] | None] = ContextVar(
    "garden_public_operation_controls",
    default=None,
)
_OPERATION_SCOPE: ContextVar[tuple[str, int] | None] = ContextVar(
    "garden_operation_scope",
    default=None,
)


@contextmanager
def operation_controls(
    *, operation_id: str, expected_revision: int | None
) -> Iterator[None]:
    """Apply public MCP operation controls to nested synchronous services."""
    token = _PUBLIC_OPERATION_CONTROLS.set((operation_id, expected_revision))
    scope_token = _OPERATION_SCOPE.set((operation_id, 0))
    try:
        yield
    finally:
        _OPERATION_SCOPE.reset(scope_token)
        _PUBLIC_OPERATION_CONTROLS.reset(token)


def active_operation_controls() -> tuple[str, int | None] | None:
    """Return active public operation controls, when present."""
    return _PUBLIC_OPERATION_CONTROLS.get()


def _scoped_operation_controls(
    controls: tuple[str, int | None] | None,
) -> tuple[str, int | None] | None:
    """Give nested Garden writes distinct operation records within one call."""

    if controls is None:
        return None
    operation_id, expected_revision = controls
    scope = _OPERATION_SCOPE.get()
    if scope is None or scope[0] != operation_id:
        return controls
    index = scope[1]
    _OPERATION_SCOPE.set((operation_id, index + 1))
    if index == 0:
        return controls
    suffix = f"_sub{index}"
    return operation_id[: 128 - len(suffix)] + suffix, None


class GardenOperationError(RuntimeError):
    """Base error for Garden authoring operations."""


class GardenRevisionConflictError(GardenOperationError):
    """Raised when an authoring write was based on an old Garden revision."""

    def __init__(self, *, expected_revision: int, current_revision: int) -> None:
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            "Garden revision conflict: expected revision "
            f"{expected_revision}, current revision is {current_revision}. "
            "Reload the Garden before retrying the mutation."
        )


class GardenOperationStateError(GardenOperationError):
    """Raised when an operation id cannot be reused in its current state."""


class GardenRecoveryError(GardenOperationError):
    """Raised when an interrupted operation cannot be recovered safely."""


@dataclass(slots=True)
class GardenOperationRecord:
    """Persistent state for one Garden authoring operation."""

    operation_id: str
    operation_type: str
    garden_id: str
    phase: str
    expected_revision: int
    before_revision: int
    after_revision: int
    affected_paths: list[str]
    writes: list[dict[str, Any]]
    manifest_intent: dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    recoverable: bool = True
    replay_count: int = 0
    recovered_at: str | None = None
    recovery_action: str | None = None
    error: dict[str, str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GardenOperationRecord":
        """Validate and load one operation record."""
        if data.get("schema_version") != OPERATION_SCHEMA_VERSION:
            raise GardenRecoveryError(
                "Unsupported Garden operation record schema_version: "
                f"{data.get('schema_version')!r}."
            )
        phase = data.get("phase")
        if phase not in _PHASES:
            raise GardenRecoveryError(f"Invalid Garden operation phase: {phase!r}.")
        operation_id_value = data.get("operation_id")
        if not isinstance(operation_id_value, str):
            raise GardenRecoveryError(
                "Garden operation operation_id must be a non-empty string."
            )
        operation_id = _normalize_operation_id(operation_id_value)
        writes = _validate_record_writes(
            operation_id=operation_id,
            affected_paths=data.get("affected_paths"),
            writes=data.get("writes"),
        )
        recovery_action = data.get("recovery_action")
        if recovery_action not in {None, "commit", "rollback"}:
            raise GardenRecoveryError(
                f"Invalid Garden recovery_action: {recovery_action!r}."
            )
        manifest_intent = data.get("manifest_intent")
        if not isinstance(manifest_intent, dict):
            raise GardenRecoveryError("Garden operation manifest_intent must be an object.")
        expected_revision = _revision_value(
            data.get("expected_revision"), field_name="expected_revision"
        )
        before_revision = _revision_value(
            data.get("before_revision"), field_name="before_revision"
        )
        after_revision = _revision_value(
            data.get("after_revision"), field_name="after_revision"
        )
        if expected_revision != before_revision or after_revision != before_revision + 1:
            raise GardenRecoveryError(
                f"Operation {operation_id} has an invalid revision transition."
            )
        operation_type = data.get("operation_type")
        garden_id = data.get("garden_id")
        if not isinstance(operation_type, str) or not operation_type.strip():
            raise GardenRecoveryError("Garden operation_type must be a non-empty string.")
        if not isinstance(garden_id, str) or not garden_id.strip():
            raise GardenRecoveryError("Garden operation garden_id must be a non-empty string.")
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        if not isinstance(created_at, str) or not created_at:
            raise GardenRecoveryError("Garden operation created_at must be a string.")
        if not isinstance(updated_at, str) or not updated_at:
            raise GardenRecoveryError("Garden operation updated_at must be a string.")
        recoverable = data.get("recoverable", False)
        replay_count = data.get("replay_count", 0)
        if not isinstance(recoverable, bool):
            raise GardenRecoveryError("Garden operation recoverable must be a boolean.")
        if (
            isinstance(replay_count, bool)
            or not isinstance(replay_count, int)
            or replay_count < 0
        ):
            raise GardenRecoveryError(
                "Garden operation replay_count must be a non-negative integer."
            )
        expected_recoverable = phase in _NONTERMINAL_PHASES
        if recoverable != expected_recoverable:
            raise GardenRecoveryError(
                f"Operation {operation_id} has recoverable={recoverable!r} in "
                f"phase {phase!r}."
            )
        expected_action = {
            "committing": "commit",
            "rolling_back": "rollback",
        }.get(str(phase))
        if phase == "recovery_blocked":
            if recovery_action is None:
                raise GardenRecoveryError(
                    f"Operation {operation_id} recovery_blocked phase needs an action."
                )
        elif recovery_action != expected_action:
            raise GardenRecoveryError(
                f"Operation {operation_id} has invalid recovery_action "
                f"{recovery_action!r} in phase {phase!r}."
            )
        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            garden_id=garden_id,
            phase=str(phase),
            expected_revision=expected_revision,
            before_revision=before_revision,
            after_revision=after_revision,
            affected_paths=[item["path"] for item in writes],
            writes=writes,
            manifest_intent=dict(manifest_intent),
            created_at=created_at,
            updated_at=updated_at,
            recoverable=recoverable,
            replay_count=replay_count,
            recovered_at=(
                str(data["recovered_at"]) if data.get("recovered_at") else None
            ),
            recovery_action=recovery_action,
            error=dict(data["error"]) if isinstance(data.get("error"), dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this operation record."""
        return {
            "schema_version": OPERATION_SCHEMA_VERSION,
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "garden_id": self.garden_id,
            "phase": self.phase,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expected_revision": self.expected_revision,
            "before_revision": self.before_revision,
            "after_revision": self.after_revision,
            "affected_paths": self.affected_paths,
            "writes": self.writes,
            "manifest_intent": self.manifest_intent,
            "recoverable": self.recoverable,
            "replay_count": self.replay_count,
            "recovered_at": self.recovered_at,
            "recovery_action": self.recovery_action,
            "error": self.error,
        }


def _revision_value(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GardenRecoveryError(f"{field_name} must be a non-negative integer.")
    return value


def _normalize_operation_id(value: Any | None) -> str:
    operation_id = str(value) if value is not None else f"op_{uuid4().hex}"
    if not _OPERATION_ID_PATTERN.fullmatch(operation_id):
        raise ValueError(
            "operation_id must contain 1-128 letters, numbers, periods, underscores, "
            "or hyphens, and must start with a letter or number."
        )
    validate_portable_file_name(operation_id, label="operation_id")
    return operation_id


def _normalize_relative_path(value: Any) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError("Garden operation path must be a relative path string.")
    text = str(value).strip().replace("\\", "/")
    path = PurePosixPath(text)
    windows_path = PureWindowsPath(text)
    if (
        not text
        or path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"Garden operation path must be relative and contained: {value!r}.")
    for part in path.parts:
        validate_portable_file_name(part, label="Garden operation path component")
    normalized = path.as_posix()
    normalized_key = windows_path_key(normalized)
    if normalized_key == ".garden" or normalized_key.startswith(".garden/"):
        raise ValueError("Garden operations cannot write their internal .garden state.")
    return normalized


def _validate_record_writes(
    *,
    operation_id: str,
    affected_paths: Any,
    writes: Any,
) -> list[dict[str, Any]]:
    if not isinstance(affected_paths, list) or not isinstance(writes, list):
        raise GardenRecoveryError(
            "Garden operation affected_paths and writes must be lists."
        )
    normalized_affected = [
        _normalize_relative_path(item) for item in affected_paths
    ]
    normalized_writes: list[dict[str, Any]] = []
    payload_root = PurePosixPath(PAYLOADS_DIR.as_posix()) / operation_id
    for raw_item in writes:
        if not isinstance(raw_item, dict):
            raise GardenRecoveryError("Garden operation writes entries must be objects.")
        path = _normalize_relative_path(raw_item.get("path"))
        staged_path = str(raw_item.get("staged_path", "")).replace("\\", "/")
        backup_path = str(raw_item.get("backup_path", "")).replace("\\", "/")
        expected_staged = (payload_root / "staged" / path).as_posix()
        expected_backup = (payload_root / "backups" / path).as_posix()
        if staged_path != expected_staged or backup_path != expected_backup:
            raise GardenRecoveryError(
                f"Operation {operation_id} has an invalid payload path for {path}."
            )
        existed_before = raw_item.get("existed_before")
        if not isinstance(existed_before, bool):
            raise GardenRecoveryError(
                f"Operation {operation_id} has invalid existed_before for {path}."
            )
        normalized_writes.append(
            {
                "path": path,
                "staged_path": staged_path,
                "backup_path": backup_path,
                "existed_before": existed_before,
            }
        )
    write_paths = [item["path"] for item in normalized_writes]
    write_path_keys = [windows_path_key(path) for path in write_paths]
    if (
        write_paths != normalized_affected
        or len(write_paths) != len(set(write_paths))
        or len(write_path_keys) != len(set(write_path_keys))
    ):
        raise GardenRecoveryError(
            f"Operation {operation_id} affected_paths do not match its write plan."
        )
    if not write_paths or write_paths[-1] != "garden.json":
        raise GardenRecoveryError(
            f"Operation {operation_id} must replace garden.json last."
        )
    return normalized_writes


def _process_lock(garden_root: Path) -> RLock:
    key = _lock_key(garden_root)
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = RLock()
            _PROCESS_LOCKS[key] = lock
        return lock


def _lock_key(garden_root: Path) -> tuple[int, str]:
    return os.getpid(), str(garden_root)


def _read_lock_owner(lock_path: Path) -> dict[str, Any] | None:
    if not _require_regular_file(
        lock_path,
        label="Garden authoring lock",
        missing_ok=True,
    ):
        return None
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _same_platform_owner_is_alive(owner: dict[str, Any] | None) -> bool | None:
    if not owner or owner.get("platform") != os.name:
        return None
    pid = owner.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "posix":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return None
        return True
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return None
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    return None


@contextmanager
def _platform_lock_gate(root: Path) -> Iterator[None]:
    gate_path = _payload_path(root, f".garden/authoring.{os.name}.gate")
    _require_regular_file(
        gate_path,
        label="Garden platform lock gate",
        missing_ok=True,
    )
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    with gate_path.open("a+b") as gate_file:
        gate_file.seek(0, os.SEEK_END)
        if gate_file.tell() == 0:
            gate_file.write(b"\0")
            gate_file.flush()
        started = time.monotonic()
        while True:
            gate_file.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(gate_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(
                        gate_file.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                break
            except OSError:
                if time.monotonic() - started > LOCK_ACQUIRE_TIMEOUT_SECONDS:
                    raise GardenOperationError(
                        f"Timed out waiting for Garden platform lock at {gate_path}."
                    )
                time.sleep(0.05)
        owner_pid = os.getpid()
        try:
            yield
        finally:
            if os.getpid() == owner_pid:
                gate_file.seek(0)
                if os.name == "nt":
                    msvcrt.locking(gate_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(gate_file.fileno(), fcntl.LOCK_UN)


def _owner_candidate_path(root: Path, token: str) -> Path:
    relative_path = (AUTHORING_LOCK_OWNERS_DIR / f"{token}.json").as_posix()
    return _payload_path(root, relative_path)


def _remove_owner_candidate(root: Path, owner: dict[str, Any] | None) -> None:
    token = owner.get("token") if owner else None
    if not isinstance(token, str) or not _OPERATION_ID_PATTERN.fullmatch(token):
        return
    candidate = _owner_candidate_path(root, token)
    try:
        candidate.unlink()
    except FileNotFoundError:
        return


def _acquire_lock_file(root: Path, token: str) -> tuple[Path, Path]:
    lock_path = _payload_path(root, AUTHORING_LOCK_PATH.as_posix())
    candidate_path = _owner_candidate_path(root, token)
    _require_regular_file(
        lock_path,
        label="Garden authoring lock",
        missing_ok=True,
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    owner = {
        "schema_version": "1",
        "token": token,
        "pid": os.getpid(),
        "platform": os.name,
        "created_at": utc_now_iso(),
    }
    _atomic_write_bytes(
        candidate_path,
        (json.dumps(owner, indent=2) + "\n").encode("utf-8"),
    )
    started = time.monotonic()
    linked = False
    try:
        while True:
            try:
                os.link(candidate_path, lock_path)
                linked = True
                return lock_path, candidate_path
            except FileExistsError:
                current_owner = _read_lock_owner(lock_path)
                if _same_platform_owner_is_alive(current_owner) is False:
                    confirmed_owner = _read_lock_owner(lock_path)
                    if (
                        confirmed_owner
                        and confirmed_owner.get("token") == current_owner.get("token")
                        and _same_platform_owner_is_alive(confirmed_owner) is False
                    ):
                        lock_path.unlink()
                        _remove_owner_candidate(root, confirmed_owner)
                        continue
                if time.monotonic() - started > LOCK_ACQUIRE_TIMEOUT_SECONDS:
                    raise GardenOperationError(
                        f"Timed out waiting for Garden authoring lock at {lock_path}."
                    )
                time.sleep(0.05)
    except Exception:
        if linked:
            _release_lock_file(lock_path, candidate_path, token)
        else:
            try:
                candidate_path.unlink()
            except OSError:
                pass
        raise


def _release_lock_file(lock_path: Path, candidate_path: Path, token: str) -> None:
    owner = _read_lock_owner(lock_path)
    owns_lock = owner is not None and owner.get("token") == token
    if not owns_lock:
        try:
            owns_lock = lock_path.samefile(candidate_path)
        except (FileNotFoundError, OSError):
            owns_lock = False
    if owns_lock:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        else:
            try:
                candidate_path.unlink()
            except OSError:
                pass
            return
    if not lock_path.exists():
        try:
            candidate_path.unlink()
        except OSError:
            pass
        return
    raise GardenOperationError("Could not safely release the Garden authoring lock.")


def _assert_authoring_lock_owned(root: Path) -> None:
    tokens = getattr(_LOCK_STATE, "tokens", {})
    token = tokens.get(_lock_key(root))
    owner = _read_lock_owner(_payload_path(root, AUTHORING_LOCK_PATH.as_posix()))
    if not token or not owner or owner.get("token") != token:
        raise GardenOperationError("The Garden authoring lock lease was lost.")


@contextmanager
def garden_authoring_lock(garden_root: Path) -> Iterator[None]:
    """Serialize Garden authoring across threads and operating-system processes."""
    root = garden_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Garden root directory not found: {root}")
    lock = _process_lock(root)
    with lock:
        depths = getattr(_LOCK_STATE, "depths", None)
        if depths is None:
            depths = {}
            _LOCK_STATE.depths = depths
        key = _lock_key(root)
        depth = depths.get(key, 0)
        if depth:
            depths[key] = depth + 1
            try:
                yield
            finally:
                depths[key] -= 1
            return

        token = uuid4().hex
        manifest_path = _payload_path(root, "garden.json")
        gate_path = _payload_path(root, f".garden/authoring.{os.name}.gate")
        lock_path = _payload_path(root, AUTHORING_LOCK_PATH.as_posix())
        _owner_candidate_path(root, token)
        _require_regular_file(
            manifest_path,
            label="Garden Manifest",
            missing_ok=True,
        )
        _require_regular_file(
            gate_path,
            label="Garden platform lock gate",
            missing_ok=True,
        )
        _require_regular_file(
            lock_path,
            label="Garden authoring lock",
            missing_ok=True,
        )
        with _platform_lock_gate(root):
            owner_pid = os.getpid()
            lock_path, candidate_path = _acquire_lock_file(root, token)
            tokens = getattr(_LOCK_STATE, "tokens", None)
            if tokens is None:
                tokens = {}
                _LOCK_STATE.tokens = tokens
            depths[key] = 1
            tokens[key] = token
            try:
                _require_regular_file(
                    _payload_path(root, "garden.json"),
                    label="Garden Manifest",
                    missing_ok=True,
                )
                yield
            finally:
                if os.getpid() == owner_pid:
                    depths.pop(key, None)
                    tokens.pop(key, None)
                    _release_lock_file(lock_path, candidate_path, token)


def _validate_materialized_path(path: Path) -> None:
    if os.name != "nt":
        return
    tmp_path = path.with_name(f".{('0' * 32)}.tmp")
    path_units = len(str(path).encode("utf-16-le")) // 2
    tmp_path_units = len(str(tmp_path).encode("utf-16-le")) // 2
    if path_units >= _WINDOWS_LEGACY_PATH_LIMIT or tmp_path_units >= (
        _WINDOWS_LEGACY_PATH_LIMIT
    ):
        raise GardenOperationError(
            f"Garden operation path is too long for this Windows runtime: {path}."
        )


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    _validate_materialized_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{uuid4().hex}.tmp")
    try:
        with tmp_path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        _fsync_directory(path.parent)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _replace_from_file(source: Path, target: Path) -> None:
    _validate_materialized_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".{uuid4().hex}.tmp")
    try:
        with source.open("rb") as source_file, tmp_path.open("xb") as target_file:
            shutil.copyfileobj(source_file, target_file)
            target_file.flush()
            os.fsync(target_file.fileno())
        os.replace(tmp_path, target)
        _fsync_directory(target.parent)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _pending_path(root: Path, operation_id: str) -> Path:
    return _payload_path(root, (PENDING_DIR / f"{operation_id}.json").as_posix())


def _record_path(root: Path, operation_id: str) -> Path:
    return _payload_path(root, (RECORDS_DIR / f"{operation_id}.json").as_posix())


def _write_record_unlocked(root: Path, record: GardenOperationRecord) -> None:
    _assert_authoring_lock_owned(root)
    record.updated_at = utc_now_iso()
    content = (
        json.dumps(
            record.to_dict(),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    pending_path = _pending_path(root, record.operation_id)
    record_path = _record_path(root, record.operation_id)
    if record.phase in _NONTERMINAL_PHASES:
        _atomic_write_bytes(pending_path, content)
        if record_path.exists():
            record_path.unlink()
    else:
        _atomic_write_bytes(record_path, content)
        if pending_path.exists():
            pending_path.unlink()


def _read_record_path(path: Path) -> GardenOperationRecord:
    _require_regular_file(path, label="Garden operation record")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GardenRecoveryError(f"Invalid Garden operation record at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GardenRecoveryError(f"Garden operation record must be an object: {path}")
    try:
        record = GardenOperationRecord.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise GardenRecoveryError(
            f"Invalid Garden operation record at {path}: {exc}"
        ) from exc
    expected_name = f"{record.operation_id}.json"
    if path.name != expected_name:
        raise GardenRecoveryError(
            f"Garden operation record file name must be {expected_name!r}: {path}."
        )
    return record


def _read_operation_record_unlocked(
    root: Path, operation_id: str
) -> GardenOperationRecord | None:
    operation_id = _normalize_operation_id(operation_id)
    operation_key = windows_path_key(operation_id)
    aliases: list[str] = []
    for directory in (RECORDS_DIR, PENDING_DIR):
        for path in _operation_record_paths(root, directory):
            candidate = path.stem
            if candidate != operation_id and windows_path_key(candidate) == operation_key:
                aliases.append(candidate)
    payloads_dir = _operation_directory(root, PAYLOADS_DIR)
    if payloads_dir.is_dir():
        for path in payloads_dir.iterdir():
            candidate = path.name
            if candidate != operation_id and windows_path_key(candidate) == operation_key:
                aliases.append(candidate)
    if aliases:
        raise GardenOperationStateError(
            f"operation_id {operation_id!r} conflicts with Windows-equivalent "
            f"operation_id {sorted(set(aliases))[0]!r}."
        )
    record_path = _record_path(root, operation_id)
    if _require_regular_file(
        record_path,
        label="Garden operation record",
        missing_ok=True,
    ):
        return _read_record_path(record_path)
    pending_path = _pending_path(root, operation_id)
    if _require_regular_file(
        pending_path,
        label="Garden pending operation record",
        missing_ok=True,
    ):
        return _read_record_path(pending_path)
    return None


def _current_manifest_unlocked(root: Path) -> GardenManifest | None:
    manifest_path = _payload_path(root, "garden.json")
    if not _require_regular_file(
        manifest_path,
        label="Garden Manifest",
        missing_ok=True,
    ):
        return None
    from garden.manifest import GardenManifest

    return GardenManifest._read_unlocked(root)


def _is_link_or_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _payload_path(root: Path, relative_path: str) -> Path:
    path = PurePosixPath(relative_path)
    windows_path = PureWindowsPath(relative_path)
    if (
        not path.parts
        or path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise GardenOperationError(
            f"Garden operation payload path must be relative and contained: "
            f"{relative_path!r}."
        )
    for part in path.parts:
        validate_portable_file_name(part, label="Garden operation path component")
    candidate = root
    for part in path.parts:
        if candidate.exists():
            if not candidate.is_dir():
                raise GardenOperationError(
                    "Garden operation path parent must be a directory: "
                    f"{candidate.relative_to(root).as_posix()}."
                )
            try:
                aliases = [
                    entry.name
                    for entry in candidate.iterdir()
                    if windows_path_key(entry.name) == windows_path_key(part)
                ]
            except OSError as exc:
                raise GardenOperationError(
                    f"Cannot inspect Garden operation path parent {candidate}: {exc}"
                ) from exc
            if aliases and (part not in aliases or len(aliases) != 1):
                raise GardenOperationError(
                    "Garden operation path conflicts with Windows-equivalent "
                    f"entry {sorted(aliases)[0]!r}: {relative_path}."
                )
        candidate = candidate / part
        if _is_link_or_reparse_point(candidate):
            raise GardenOperationError(
                "Garden operation paths cannot traverse symbolic links or reparse "
                f"points: {relative_path}."
            )
    candidate.relative_to(root)
    _validate_materialized_path(candidate)
    return candidate


def _require_regular_file(
    path: Path,
    *,
    label: str,
    missing_ok: bool = False,
) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return False
        raise GardenOperationError(f"{label} not found: {path}.") from None
    except OSError as exc:
        raise GardenOperationError(f"Cannot inspect {label} at {path}: {exc}") from exc
    is_reparse_point = bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )
    if stat.S_ISLNK(metadata.st_mode) or is_reparse_point or not stat.S_ISREG(
        metadata.st_mode
    ):
        raise GardenOperationError(f"{label} must be a regular file: {path}.")
    return True


def _operation_directory(root: Path, relative_path: Path) -> Path:
    directory = _payload_path(root, relative_path.as_posix())
    if directory.exists() and not directory.is_dir():
        raise GardenRecoveryError(
            f"Garden operation directory must be a directory: {directory}."
        )
    return directory


def _operation_record_paths(root: Path, relative_path: Path) -> list[Path]:
    directory = _operation_directory(root, relative_path)
    if not directory.is_dir():
        return []
    candidates = [
        path
        for path in directory.iterdir()
        if windows_path_key(path.suffix) == ".json"
    ]
    aliases: dict[str, list[str]] = {}
    for path in candidates:
        validate_portable_file_name(
            path.name,
            label="Garden operation record file name",
        )
        aliases.setdefault(windows_path_key(path.name), []).append(path.name)
    conflicting_names = next(
        (names for names in aliases.values() if len(names) > 1),
        None,
    )
    if conflicting_names:
        raise GardenRecoveryError(
            "Garden operation record names conflict on Windows: "
            f"{', '.join(sorted(conflicting_names))}."
        )
    for path in candidates:
        _validate_materialized_path(path)
        _require_regular_file(path, label="Garden operation record")
    return sorted(candidates)


def _ordered_writes(record: GardenOperationRecord) -> list[dict[str, Any]]:
    return sorted(record.writes, key=lambda item: item["path"] == "garden.json")


def _preflight_staged_writes(root: Path, record: GardenOperationRecord) -> None:
    missing = [
        item["staged_path"]
        for item in record.writes
        if not _payload_path(root, item["staged_path"]).is_file()
    ]
    if missing:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} is missing staged file(s): {', '.join(missing)}."
        )
    manifest_write = next(
        item for item in record.writes if item["path"] == "garden.json"
    )
    staged_manifest = _validate_operation_manifest_file(
        _payload_path(root, manifest_write["staged_path"]),
        record=record,
        expected_revision=record.after_revision,
    )
    if _manifest_intent(staged_manifest.to_dict()) != record.manifest_intent:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} staged Manifest does not match its intent."
        )


def _validate_operation_manifest_file(
    path: Path,
    *,
    record: GardenOperationRecord,
    expected_revision: int,
) -> GardenManifest:
    from garden.manifest import GardenManifest

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} has an invalid Manifest at {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise GardenRecoveryError(
            f"Operation {record.operation_id} Manifest must be a JSON object."
        )
    try:
        manifest = GardenManifest.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} has an invalid Manifest: {exc}"
        ) from exc
    if manifest.garden_id != record.garden_id:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} staged Manifest belongs to another Garden."
        )
    if manifest.revision != expected_revision:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} Manifest revision is {manifest.revision}, "
            f"expected {expected_revision}."
        )
    return manifest


def _apply_writes_unlocked(root: Path, record: GardenOperationRecord) -> None:
    _preflight_staged_writes(root, record)
    for item in _ordered_writes(record):
        _assert_authoring_lock_owned(root)
        source = _payload_path(root, item["staged_path"])
        target = _payload_path(root, item["path"])
        _replace_from_file(source, target)


def _preflight_backups(root: Path, record: GardenOperationRecord) -> None:
    missing = [
        item["backup_path"]
        for item in record.writes
        if item["existed_before"]
        and not _payload_path(root, item["backup_path"]).is_file()
    ]
    if missing:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} is missing backup file(s): {', '.join(missing)}."
        )
    manifest_write = next(
        item for item in record.writes if item["path"] == "garden.json"
    )
    if manifest_write["existed_before"]:
        _validate_operation_manifest_file(
            _payload_path(root, manifest_write["backup_path"]),
            record=record,
            expected_revision=record.before_revision,
        )


def _rollback_writes_unlocked(root: Path, record: GardenOperationRecord) -> None:
    _preflight_backups(root, record)
    for item in reversed(_ordered_writes(record)):
        _assert_authoring_lock_owned(root)
        target = _payload_path(root, item["path"])
        if item["existed_before"]:
            backup = _payload_path(root, item["backup_path"])
            _replace_from_file(backup, target)
        elif target.exists():
            target.unlink()


def _cleanup_payload_unlocked(root: Path, operation_id: str) -> None:
    payload_root = _payload_path(
        root,
        (PAYLOADS_DIR / operation_id).as_posix(),
    )
    if payload_root.exists():
        shutil.rmtree(payload_root, ignore_errors=True)


def _failure_payload(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def _commit_record_unlocked(
    root: Path, record: GardenOperationRecord
) -> GardenOperationRecord:
    record.phase = "committing"
    record.recoverable = True
    record.recovery_action = "commit"
    record.error = None
    _write_record_unlocked(root, record)
    try:
        _apply_writes_unlocked(root, record)
    except Exception as exc:
        record.phase = "rolling_back"
        record.recovery_action = "rollback"
        record.error = _failure_payload(exc)
        _write_record_unlocked(root, record)
        try:
            _rollback_writes_unlocked(root, record)
        except Exception as rollback_exc:
            record.phase = "recovery_blocked"
            record.recoverable = True
            record.recovery_action = "rollback"
            record.error = _failure_payload(rollback_exc)
            _write_record_unlocked(root, record)
            raise GardenRecoveryError(
                f"Operation {record.operation_id} failed and rollback could not finish: "
                f"{rollback_exc}"
            ) from exc
        record.phase = "failed"
        record.recoverable = False
        record.recovery_action = None
        _write_record_unlocked(root, record)
        _cleanup_payload_unlocked(root, record.operation_id)
        raise

    record.phase = "committed"
    record.recoverable = False
    record.recovery_action = None
    record.error = None
    _write_record_unlocked(root, record)
    _cleanup_payload_unlocked(root, record.operation_id)
    return record


def _validate_recovery_revision_unlocked(
    root: Path, record: GardenOperationRecord
) -> int:
    current_manifest = _current_manifest_unlocked(root)
    current_revision = current_manifest.revision if current_manifest else 0
    if current_manifest and current_manifest.garden_id != record.garden_id:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} belongs to a different Garden."
        )
    if current_revision not in {record.before_revision, record.after_revision}:
        raise GardenRecoveryError(
            f"Operation {record.operation_id} expected Garden revision "
            f"{record.before_revision} or {record.after_revision}, but found "
            f"{current_revision}."
        )
    return current_revision


def _recover_interrupted_operations_unlocked(
    root: Path,
) -> list[GardenOperationRecord]:
    recovered: list[GardenOperationRecord] = []
    for path in _operation_record_paths(root, PENDING_DIR):
        record = _read_record_path(path)
        recovery_action: str | None = None
        try:
            if record.phase == "prepared":
                record.phase = "interrupted"
                record.recoverable = True
                record.recovered_at = utc_now_iso()
                record.error = {
                    "type": "OperationInterrupted",
                    "message": (
                        "The process stopped before commit started; retry with the "
                        "same operation_id."
                    ),
                }
                _write_record_unlocked(root, record)
            elif record.phase == "interrupted":
                current_manifest = _current_manifest_unlocked(root)
                current_revision = current_manifest.revision if current_manifest else 0
                if current_manifest and current_manifest.garden_id != record.garden_id:
                    raise GardenRecoveryError(
                        f"Interrupted operation {record.operation_id} belongs to a "
                        "different Garden."
                    )
                if current_revision != record.before_revision:
                    record.phase = "failed"
                    record.recoverable = False
                    record.recovery_action = None
                    record.recovered_at = utc_now_iso()
                    record.error = {
                        "type": "GardenRevisionConflictError",
                        "message": (
                            f"Interrupted operation expected revision "
                            f"{record.before_revision}, but current revision is "
                            f"{current_revision}."
                        ),
                    }
                    _write_record_unlocked(root, record)
                    _cleanup_payload_unlocked(root, record.operation_id)
            elif record.phase == "committing" or (
                record.phase == "recovery_blocked"
                and record.recovery_action == "commit"
            ):
                recovery_action = "commit"
                _validate_recovery_revision_unlocked(root, record)
                _apply_writes_unlocked(root, record)
                record.phase = "committed"
                record.recoverable = False
                record.recovery_action = None
                record.recovered_at = utc_now_iso()
                record.error = None
                _write_record_unlocked(root, record)
                _cleanup_payload_unlocked(root, record.operation_id)
            elif record.phase == "rolling_back" or (
                record.phase == "recovery_blocked"
                and record.recovery_action == "rollback"
            ):
                recovery_action = "rollback"
                _validate_recovery_revision_unlocked(root, record)
                _rollback_writes_unlocked(root, record)
                record.phase = "failed"
                record.recoverable = False
                record.recovery_action = None
                record.recovered_at = utc_now_iso()
                _write_record_unlocked(root, record)
                _cleanup_payload_unlocked(root, record.operation_id)
            elif record.phase == "recovery_blocked":
                raise GardenRecoveryError(
                    f"Operation {record.operation_id} has no valid recovery action."
                )
            recovered.append(record)
        except Exception as exc:
            if recovery_action is not None:
                record.phase = "recovery_blocked"
                record.recovery_action = recovery_action
            if record.phase in _NONTERMINAL_PHASES:
                record.recoverable = True
                record.recovered_at = utc_now_iso()
                record.error = _failure_payload(exc)
                try:
                    _write_record_unlocked(root, record)
                except Exception:
                    pass
            raise GardenRecoveryError(
                f"Garden operation recovery failed for {record.operation_id}: {exc}"
            ) from exc
    return recovered


def recover_interrupted_operations(
    garden_root: Path,
) -> list[GardenOperationRecord]:
    """Recover pending commits or classify pre-commit interruptions."""
    root = garden_root.expanduser().resolve()
    with garden_authoring_lock(root):
        return _recover_interrupted_operations_unlocked(root)


def _prepare_record_unlocked(
    root: Path,
    *,
    operation_id: str,
    operation_type: str,
    garden_id: str,
    expected_revision: int,
    before_revision: int,
    writes: Mapping[str, bytes],
) -> GardenOperationRecord:
    for relative_path in writes:
        target = _payload_path(root, relative_path)
        staged_relative = (
            PAYLOADS_DIR / operation_id / "staged" / Path(relative_path)
        ).as_posix()
        backup_relative = (
            PAYLOADS_DIR / operation_id / "backups" / Path(relative_path)
        ).as_posix()
        _payload_path(root, staged_relative)
        _payload_path(root, backup_relative)
        if target.exists() and not target.is_file():
            raise GardenOperationError(
                "Garden operation target must be a regular file when it exists: "
                f"{relative_path}."
            )

    payload_root = _payload_path(root, (PAYLOADS_DIR / operation_id).as_posix())
    if payload_root.exists():
        shutil.rmtree(payload_root)
    write_records: list[dict[str, Any]] = []
    for relative_path, content in writes.items():
        _assert_authoring_lock_owned(root)
        staged_relative = (
            PAYLOADS_DIR / operation_id / "staged" / Path(relative_path)
        ).as_posix()
        backup_relative = (
            PAYLOADS_DIR / operation_id / "backups" / Path(relative_path)
        ).as_posix()
        target = _payload_path(root, relative_path)
        staged = _payload_path(root, staged_relative)
        backup = _payload_path(root, backup_relative)
        _atomic_write_bytes(staged, content)
        existed_before = target.is_file()
        if existed_before:
            _replace_from_file(target, backup)
        write_records.append(
            {
                "path": relative_path,
                "staged_path": staged_relative,
                "backup_path": backup_relative,
                "existed_before": existed_before,
            }
        )

    record = GardenOperationRecord(
        operation_id=operation_id,
        operation_type=operation_type,
        garden_id=garden_id,
        phase="prepared",
        expected_revision=expected_revision,
        before_revision=before_revision,
        after_revision=before_revision + 1,
        affected_paths=list(writes),
        writes=write_records,
        manifest_intent=_manifest_intent(
            json.loads(writes["garden.json"].decode("utf-8"))
        ),
    )
    _write_record_unlocked(root, record)
    return record


def _validate_existing_operation(
    record: GardenOperationRecord,
    *,
    operation_type: str,
    garden_id: str,
    expected_revision: int | None,
    affected_paths: list[str],
    manifest_intent: dict[str, Any],
) -> None:
    if record.operation_type != operation_type or record.garden_id != garden_id:
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} belongs to a different operation."
        )
    expected_matches = expected_revision == record.expected_revision or (
        record.phase == "committed" and expected_revision == record.after_revision
    )
    if expected_revision is not None and not expected_matches:
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} was created for expected revision "
            f"{record.expected_revision}, not {expected_revision}."
        )
    if record.affected_paths != affected_paths:
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} was created for different affected paths."
        )
    if record.manifest_intent != manifest_intent:
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} was created for different "
            "Manifest content."
        )


def _manifest_intent(data: dict[str, Any]) -> dict[str, Any]:
    intent = dict(data)
    intent.pop("revision", None)
    intent.pop("updated_at", None)
    return intent


def _validate_operation_intent_unlocked(
    root: Path,
    record: GardenOperationRecord,
    *,
    manifest: GardenManifest,
    staged_writes: Mapping[str, bytes],
    source: str,
) -> dict[str, Any]:
    if source == "staged":
        manifest_path = next(
            _payload_path(root, item["staged_path"])
            for item in record.writes
            if item["path"] == "garden.json"
        )
    elif source == "current":
        manifest_path = _payload_path(root, "garden.json")
    else:
        raise ValueError(f"Unsupported operation intent source: {source}")
    try:
        saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GardenOperationStateError(
            f"Cannot verify operation_id {record.operation_id!r} intent: {exc}"
        ) from exc
    if not isinstance(saved_manifest, dict) or _manifest_intent(
        saved_manifest
    ) != _manifest_intent(manifest.to_dict()):
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} was created for different "
            "Manifest content."
        )
    if not isinstance(saved_manifest.get("updated_at"), str):
        raise GardenOperationStateError(
            f"operation_id {record.operation_id!r} has no staged updated_at."
        )
    for item in record.writes:
        path = item["path"]
        if path == "garden.json":
            continue
        source_path = (
            _payload_path(root, item["staged_path"])
            if source == "staged"
            else _payload_path(root, path)
        )
        try:
            saved_content = source_path.read_bytes()
        except OSError as exc:
            raise GardenOperationStateError(
                f"Cannot verify operation_id {record.operation_id!r} intent for "
                f"{path}: {exc}"
            ) from exc
        if saved_content != staged_writes[path]:
            raise GardenOperationStateError(
                f"operation_id {record.operation_id!r} was created for different "
                f"content at {path}."
            )
    return saved_manifest


def commit_manifest(
    garden_root: Path,
    manifest: GardenManifest,
    *,
    operation_type: str = "manifest_write",
    operation_id: str | None = None,
    expected_revision: int | None = None,
    staged_writes: Mapping[str, bytes] | None = None,
) -> GardenOperationRecord:
    """Commit a manifest and optional staged files as one recoverable operation."""
    root = garden_root.expanduser().resolve()
    manifest.validate()
    if not operation_type or not operation_type.strip():
        raise ValueError("operation_type must be a non-empty string.")
    operation_type = operation_type.strip()
    public_controls = _PUBLIC_OPERATION_CONTROLS.get()
    scoped_controls = _scoped_operation_controls(public_controls)
    normalized_operation_id = _normalize_operation_id(
        scoped_controls[0] if scoped_controls else operation_id
    )
    expected = (
        scoped_controls[1]
        if scoped_controls and scoped_controls[1] is not None
        else manifest.revision
        if expected_revision is None
        else expected_revision
    )
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        raise ValueError("expected_revision must be a non-negative integer.")
    normalized_writes: dict[str, bytes] = {}
    normalized_write_keys: set[str] = set()
    for raw_path, content in (staged_writes or {}).items():
        relative_path = _normalize_relative_path(raw_path)
        relative_path_key = windows_path_key(relative_path)
        if relative_path_key == "garden.json" or relative_path_key.startswith(
            "garden.json/"
        ):
            raise ValueError("staged_writes cannot replace garden.json directly.")
        if relative_path_key in normalized_write_keys:
            raise ValueError(
                "staged_writes cannot contain Windows-equivalent path aliases: "
                f"{relative_path}."
            )
        if not isinstance(content, bytes):
            raise TypeError("Garden operation staged_writes values must be bytes.")
        normalized_write_keys.add(relative_path_key)
        normalized_writes[relative_path] = content
    affected_paths = [*sorted(normalized_writes), "garden.json"]

    with garden_authoring_lock(root):
        _recover_interrupted_operations_unlocked(root)
        existing = _read_operation_record_unlocked(root, normalized_operation_id)
        if existing is not None:
            _validate_existing_operation(
                existing,
                operation_type=operation_type,
                garden_id=manifest.garden_id,
                expected_revision=expected,
                affected_paths=affected_paths,
                manifest_intent=_manifest_intent(manifest.to_dict()),
            )
            if existing.phase == "committed":
                current_manifest = _current_manifest_unlocked(root)
                if current_manifest is None:
                    raise GardenOperationStateError(
                        f"Cannot replay operation_id {existing.operation_id!r}: "
                        "Garden Manifest is missing."
                    )
                if current_manifest.garden_id != existing.garden_id:
                    raise GardenOperationStateError(
                        f"Cannot replay operation_id {existing.operation_id!r}: "
                        "the Garden identity changed."
                    )
                if current_manifest.revision < existing.after_revision:
                    raise GardenOperationStateError(
                        f"Cannot replay operation_id {existing.operation_id!r}: "
                        "the Garden revision regressed."
                    )
                if current_manifest.revision == existing.after_revision:
                    _validate_operation_intent_unlocked(
                        root,
                        existing,
                        manifest=manifest,
                        staged_writes=normalized_writes,
                        source="current",
                    )
                elif normalized_writes:
                    raise GardenOperationStateError(
                        f"Cannot verify non-Manifest content for old operation_id "
                        f"{existing.operation_id!r} after the Garden advanced."
                    )
                existing.replay_count += 1
                _write_record_unlocked(root, existing)
                return existing
            if existing.phase == "failed":
                raise GardenOperationStateError(
                    f"operation_id {existing.operation_id!r} is failed and cannot be reused."
                )
            if existing.phase != "interrupted":
                raise GardenOperationStateError(
                    f"operation_id {existing.operation_id!r} is in phase {existing.phase!r}."
                )
            staged_manifest = _validate_operation_intent_unlocked(
                root,
                existing,
                manifest=manifest,
                staged_writes=normalized_writes,
                source="staged",
            )
            current_manifest = _current_manifest_unlocked(root)
            current_revision = current_manifest.revision if current_manifest else 0
            if current_manifest and current_manifest.garden_id != manifest.garden_id:
                raise GardenOperationStateError(
                    "The in-memory manifest belongs to a different Garden."
                )
            if current_revision != existing.before_revision:
                existing.phase = "failed"
                existing.recoverable = False
                existing.recovery_action = None
                existing.error = {
                    "type": "GardenRevisionConflictError",
                    "message": (
                        f"Interrupted operation expected revision {existing.before_revision}, "
                        f"but current revision is {current_revision}."
                    ),
                }
                _write_record_unlocked(root, existing)
                _cleanup_payload_unlocked(root, existing.operation_id)
                raise GardenRevisionConflictError(
                    expected_revision=existing.before_revision,
                    current_revision=current_revision,
                )
            record = _commit_record_unlocked(root, existing)
            manifest.revision = record.after_revision
            manifest.updated_at = str(staged_manifest["updated_at"])
            return record

        current_manifest = _current_manifest_unlocked(root)
        current_revision = current_manifest.revision if current_manifest else 0
        if current_manifest and current_manifest.garden_id != manifest.garden_id:
            raise GardenOperationStateError(
                "The in-memory manifest belongs to a different Garden."
            )
        if current_revision != expected:
            raise GardenRevisionConflictError(
                expected_revision=expected,
                current_revision=current_revision,
            )

        previous_revision = manifest.revision
        previous_updated_at = manifest.updated_at
        try:
            manifest.revision = current_revision + 1
            manifest.updated_at = utc_now_iso()
            manifest_content = (
                json.dumps(
                    manifest.to_dict(),
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
            commit_writes = {
                path: normalized_writes[path] for path in sorted(normalized_writes)
            }
            commit_writes["garden.json"] = manifest_content
            record = _prepare_record_unlocked(
                root,
                operation_id=normalized_operation_id,
                operation_type=operation_type,
                garden_id=manifest.garden_id,
                expected_revision=expected,
                before_revision=current_revision,
                writes=commit_writes,
            )
            return _commit_record_unlocked(root, record)
        except Exception:
            manifest.revision = previous_revision
            manifest.updated_at = previous_updated_at
            raise


def read_operation_record(
    garden_root: Path, operation_id: str
) -> GardenOperationRecord | None:
    """Read one operation record after recovering active commits."""
    root = garden_root.expanduser().resolve()
    with garden_authoring_lock(root):
        _recover_interrupted_operations_unlocked(root)
        return _read_operation_record_unlocked(root, operation_id)


def list_operation_records(garden_root: Path) -> list[GardenOperationRecord]:
    """List operation records from newest to oldest."""
    root = garden_root.expanduser().resolve()
    with garden_authoring_lock(root):
        _recover_interrupted_operations_unlocked(root)
        paths = [
            *_operation_record_paths(root, RECORDS_DIR),
            *_operation_record_paths(root, PENDING_DIR),
        ]
        records = [_read_record_path(path) for path in paths]
        return sorted(records, key=lambda item: item.created_at, reverse=True)
