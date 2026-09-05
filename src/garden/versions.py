"""Garden Git-backed version management."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

from garden.manifest import GardenManifest, utc_now_iso
from garden.operations import (
    active_operation_controls,
    atomic_write_bytes,
    GardenOperationStateError,
    GardenRecoveryError,
    GardenRevisionConflictError,
    garden_authoring_lock,
    recover_interrupted_operations,
)
from garden.paths import validate_portable_file_name
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from ladybug_tools_mcp.contracts.targets import make_garden_version_target


AUTHORING_PATHS = ("garden.json", "models", "libraries")
GIT_USER_NAME = "Ladybug Tools MCP"
GIT_USER_EMAIL = "ladybug-tools-mcp@example.invalid"
RESTORE_STATE_DIR = Path(".garden") / "version-restores"
RESTORE_STATE_SCHEMA_VERSION = "1"
_PENDING_RESTORE_PHASES = {
    "prepared",
    "deleting",
    "checkout",
    "checkpointing",
    "recovery_blocked",
}


def _resolve_garden_root(garden_root: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    if not (root / "garden.json").is_file() and _pending_restore_state(root) is None:
        raise ValueError(f"Garden manifest not found at {root / 'garden.json'}")
    return root


def _run_git(
    root: Path,
    args: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=check,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Git-backed Garden version management requires Git on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"Git command failed: {stderr}") from exc


def is_git_available() -> bool:
    """Return whether Git can be invoked from the current environment."""
    return shutil.which("git") is not None


def ensure_garden_git_repository(root: Path) -> bool:
    """Ensure a Garden has its required local Git repository."""
    if (root / ".git").exists():
        _run_git(root, ["rev-parse", "--git-dir"])
        return False
    _run_git(root, ["init", "--quiet"])
    return True


def _head_version(root: Path) -> str | None:
    result = _run_git(root, ["rev-parse", "--verify", "HEAD"], check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _short_version(root: Path, version_id: str) -> str:
    result = _run_git(root, ["rev-parse", "--short", version_id])
    return result.stdout.strip()


def _authoring_status(root: Path) -> list[str]:
    result = _run_git(root, ["status", "--porcelain", "--", *AUTHORING_PATHS])
    return [line for line in result.stdout.splitlines() if line.strip()]


def _changed_file_count(root: Path) -> int:
    result = _run_git(root, ["status", "--porcelain", "--", *AUTHORING_PATHS])
    files = {
        line[3:].strip()
        for line in result.stdout.splitlines()
        if line.strip() and len(line) >= 4
    }
    return len(files)


def _stage_authoring_truth(root: Path) -> None:
    paths = [AUTHORING_PATHS[0]]
    for path in AUTHORING_PATHS[1:]:
        tracked = _run_git(root, ["ls-files", "--", path]).stdout.strip()
        if (root / path).exists() or tracked:
            paths.append(path)
    _run_git(root, ["add", "-A", "--", *paths])


def _staged_authoring_paths(root: Path) -> list[str]:
    result = _run_git(
        root,
        ["diff", "--cached", "--name-only", "--", *AUTHORING_PATHS],
    )
    return [line for line in result.stdout.splitlines() if line]


def _commit_summary_body(summary: dict[str, Any] | None, source: str | None) -> str:
    payload = {
        "schema_version": "1",
        "source": source or "agent",
        "summary": summary or {},
    }
    return "Garden-Version-Summary:\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _restore_state_path(root: Path, operation_id: str) -> Path:
    validate_portable_file_name(operation_id, label="Garden restore operation_id")
    return root / RESTORE_STATE_DIR / f"{operation_id}.json"


def _write_restore_state(root: Path, state: dict[str, Any]) -> None:
    operation_id = state.get("operation_id")
    if not isinstance(operation_id, str):
        raise ValueError("Garden restore operation_id must be a string.")
    validate_portable_file_name(operation_id, label="Garden restore operation_id")
    state["updated_at"] = utc_now_iso()
    path = _restore_state_path(root, operation_id)
    content = (
        json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    atomic_write_bytes(path, content)


def _restore_states(root: Path) -> list[dict[str, Any]]:
    directory = root / RESTORE_STATE_DIR
    if not directory.is_dir():
        return []
    states: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Invalid Garden restore state at {path}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"Garden restore state must be an object: {path}")
        if data.get("schema_version") != RESTORE_STATE_SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported Garden restore state schema: {path}")
        required = ("operation_id", "phase", "source_version", "starting_version")
        if any(
            not isinstance(data.get(field), str) or not data[field]
            for field in required
        ):
            raise RuntimeError(f"Garden restore state is incomplete: {path}")
        try:
            validate_portable_file_name(
                str(data["operation_id"]),
                label="Garden restore operation_id",
            )
        except ValueError as exc:
            raise RuntimeError(f"Invalid Garden restore state at {path}: {exc}") from exc
        if path.name != f"{data['operation_id']}.json":
            raise RuntimeError(f"Garden restore state name does not match its operation_id: {path}")
        if data["phase"] not in {*_PENDING_RESTORE_PHASES, "committed"}:
            raise RuntimeError(f"Garden restore state has an invalid phase: {path}")
        source_paths = data.get("source_paths")
        if (
            not isinstance(source_paths, list)
            or not source_paths
            or any(path_name not in AUTHORING_PATHS for path_name in source_paths)
        ):
            raise RuntimeError(f"Garden restore state has invalid source paths: {path}")
        if not isinstance(data.get("subject"), str) or not isinstance(
            data.get("summary"), dict
        ):
            raise RuntimeError(f"Garden restore state has invalid checkpoint data: {path}")
        states.append(data)
    return states


def _pending_restore_state(root: Path) -> dict[str, Any] | None:
    pending = [
        state
        for state in _restore_states(root)
        if state.get("phase") in _PENDING_RESTORE_PHASES
    ]
    if len(pending) > 1:
        raise RuntimeError(
            "Multiple Garden restores require recovery. Resolve the restore state files "
            "under .garden/version-restores before continuing."
        )
    return pending[0] if pending else None


def _manifest_for_version_status(
    root: Path,
    pending_restore: dict[str, Any] | None,
) -> GardenManifest:
    if (root / "garden.json").is_file():
        return GardenManifest._read_unlocked(root)
    if pending_restore is None:
        raise ValueError(f"Garden manifest not found at {root / 'garden.json'}")
    result = _run_git(
        root,
        ["show", f"{pending_restore['source_version']}:garden.json"],
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("Garden version manifest must be a JSON object.")
    return GardenManifest.from_dict(data)


def _restore_checkpoint_completed(root: Path, state: dict[str, Any]) -> bool:
    head = _head_version(root)
    if head is None or head == state["starting_version"]:
        return False
    parent = _run_git(root, ["rev-parse", "--verify", f"{head}^"], check=False)
    if parent.returncode != 0 or parent.stdout.strip() != state["starting_version"]:
        return False
    comparison = _run_git(
        root,
        ["diff", "--quiet", state["source_version"], head, "--", *AUTHORING_PATHS],
        check=False,
    )
    return comparison.returncode == 0


def _resume_restore(root: Path, state: dict[str, Any]) -> str | None:
    if _restore_checkpoint_completed(root, state):
        state["phase"] = "committed"
        state["recovery_action"] = None
        state["error"] = None
        _write_restore_state(root, state)
        return _head_version(root)

    head = _head_version(root)
    if head != state["starting_version"]:
        state["phase"] = "recovery_blocked"
        state["recovery_action"] = "inspect_git_history"
        state["error"] = {
            "message": "Garden version history advanced while a restore was incomplete."
        }
        _write_restore_state(root, state)
        raise GardenRecoveryError(
            "Garden restore recovery is blocked because version history advanced. "
            "Inspect .garden/version-restores and Git history before retrying."
        )

    try:
        state["phase"] = "deleting"
        state["recovery_action"] = "resume"
        _write_restore_state(root, state)
        _run_git(root, ["rm", "-r", "--ignore-unmatch", "--", *AUTHORING_PATHS])

        state["phase"] = "checkout"
        _write_restore_state(root, state)
        _run_git(
            root,
            [
                "restore",
                "--source",
                state["source_version"],
                "--",
                *state["source_paths"],
            ],
        )

        _stage_authoring_truth(root)
        changed_count = _changed_file_count(root)
        if changed_count == 0:
            state["phase"] = "committed"
            state["recovery_action"] = None
            state["error"] = None
            _write_restore_state(root, state)
            return None

        state["changed_file_count"] = changed_count
        state["phase"] = "checkpointing"
        _write_restore_state(root, state)
        commit_paths = _staged_authoring_paths(root)
        _run_git(
            root,
            [
                "-c",
                f"user.name={GIT_USER_NAME}",
                "-c",
                f"user.email={GIT_USER_EMAIL}",
                "commit",
                "-m",
                state["subject"],
                "-m",
                _commit_summary_body(
                    {
                        "operation": "restore_garden_version",
                        "restored_from_version": state["source_version"],
                        "summary": state.get("summary") or {},
                    },
                    state.get("source"),
                ),
                "--",
                *commit_paths,
            ],
        )
        version_id = _head_version(root)
        assert version_id is not None
        state["phase"] = "committed"
        state["recovery_action"] = None
        state["error"] = None
        state["version_id"] = version_id
        _write_restore_state(root, state)
        return version_id
    except Exception as exc:
        state["phase"] = "recovery_blocked"
        state["recovery_action"] = "resume"
        state["error"] = {"type": type(exc).__name__, "message": str(exc)}
        _write_restore_state(root, state)
        raise GardenRecoveryError(
            "Garden restore stopped with recoverable state. Retry the same restore "
            "to resume it."
        ) from exc


def _parse_summary(body: str) -> dict[str, Any]:
    marker = "Garden-Version-Summary:"
    if marker not in body:
        return {}
    raw = body.split(marker, 1)[1].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else {}


def _version_target(
    manifest: GardenManifest,
    root: Path,
    version_id: str,
) -> dict[str, str]:
    return make_garden_version_target(
        manifest.garden_id,
        version_id,
        short_version_id=_short_version(root, version_id),
    )


def _version_record(root: Path, version_id: str) -> dict[str, Any]:
    raw = _run_git(
        root,
        ["show", "-s", "--format=%H%x1f%aI%x1f%s%x1f%b", version_id],
    ).stdout
    full_id, created_at, subject, body = raw.split("\x1f", 3)
    manifest = GardenManifest.read(root)
    short_id = _short_version(root, full_id)
    return {
        "version_id": full_id,
        "short_version_id": short_id,
        "target": make_garden_version_target(
            manifest.garden_id,
            full_id,
            short_version_id=short_id,
        ),
        "created_at": created_at.strip(),
        "subject": subject.strip(),
        "summary": _parse_summary(body),
        "is_restore": subject.strip().startswith("restore:"),
    }


def get_garden_version_status(*, garden_root: str) -> dict[str, Any]:
    """Report compact Git status for Garden authoring truth."""
    root = _resolve_garden_root(garden_root)
    with garden_authoring_lock(root):
        recover_interrupted_operations(root)
        ensure_garden_git_repository(root)
        pending_restore = _pending_restore_state(root)
        manifest = _manifest_for_version_status(root, pending_restore)
        head = _head_version(root)
        status_lines = _authoring_status(root)
        changed_count = _changed_file_count(root)
    recovery = (
        {
            "operation_id": pending_restore["operation_id"],
            "phase": pending_restore["phase"],
            "recovery_action": pending_restore.get("recovery_action") or "resume",
        }
        if pending_restore
        else None
    )
    return {
        "garden_root": str(root),
        "version_id": head,
        "summary_view": {
            "garden_target": manifest.target(),
            "has_versions": head is not None,
            "is_dirty": bool(status_lines),
            "changed_file_count": changed_count,
            "restore_recovery": recovery,
        },
        "report": make_report(
            status="ok",
            message=(
                "Garden restore requires recovery."
                if recovery
                else "Garden authoring truth has uncommitted changes."
                if status_lines
                else "Garden authoring truth is clean."
            ),
        ),
    }


def create_garden_version(
    *,
    garden_root: str,
    subject: str,
    summary: dict[str, Any] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Create a compact Garden version commit for authoring truth."""
    root = _resolve_garden_root(garden_root)
    with garden_authoring_lock(root):
        recover_interrupted_operations(root)
        if _pending_restore_state(root) is not None:
            raise RuntimeError(
                "Garden restore recovery is required before creating a new version."
            )
        return _create_garden_version_unlocked(
            root,
            subject=subject,
            summary=summary,
            source=source,
        )


def _create_garden_version_unlocked(
    root: Path,
    *,
    subject: str,
    summary: dict[str, Any] | None,
    source: str | None,
) -> dict[str, Any]:
    manifest = GardenManifest._read_unlocked(root)
    controls = active_operation_controls()
    if controls and controls[1] is not None and controls[1] != manifest.revision:
        raise GardenRevisionConflictError(
            expected_revision=controls[1],
            current_revision=manifest.revision,
        )
    operation_id = controls[0] if controls else f"version_{uuid4().hex}"
    if not subject or not subject.strip():
        raise ValueError("subject is required to create a Garden version.")

    ensure_garden_git_repository(root)
    _stage_authoring_truth(root)
    changed_count = _changed_file_count(root)
    if changed_count == 0:
        head = _head_version(root)
        version_target = _version_target(manifest, root, head) if head else {}
        return {
            "garden_root": str(root),
            "version_id": head,
            "version_target": version_target,
            "summary_view": {
                "garden_target": manifest.target(),
                "is_dirty": False,
                "changed_file_count": 0,
                "subject": subject,
            },
            "persistence_receipt": make_persistence_receipt(
                status="no_change",
                garden_id=manifest.garden_id,
                persisted_path=None,
                change_summary={
                    "operation": "create_garden_version",
                    "operation_id": operation_id,
                    "before_revision": manifest.revision,
                    "after_revision": manifest.revision,
                },
            ),
            "report": make_report(
                status="ok",
                message="No Garden authoring truth changes to version.",
            ),
        }

    commit_paths = _staged_authoring_paths(root)
    _run_git(
        root,
        [
            "-c",
            f"user.name={GIT_USER_NAME}",
            "-c",
            f"user.email={GIT_USER_EMAIL}",
            "commit",
            "-m",
            subject.strip(),
            "-m",
            _commit_summary_body(summary, source),
            "--",
            *commit_paths,
        ],
    )
    version_id = _head_version(root)
    assert version_id is not None
    short_id = _short_version(root, version_id)
    version_target = make_garden_version_target(
        manifest.garden_id,
        version_id,
        short_version_id=short_id,
    )
    return {
        "garden_root": str(root),
        "version_id": version_id,
        "version_target": version_target,
        "target": version_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "version_id": version_id,
            "short_version_id": short_id,
            "subject": subject.strip(),
            "summary": summary or {},
            "changed_file_count": changed_count,
            "is_dirty": False,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            persisted_path=".git",
            change_summary={
                "operation": "create_garden_version",
                "operation_id": operation_id,
                "before_revision": manifest.revision,
                "after_revision": manifest.revision,
                "version_id": version_id,
                "subject": subject.strip(),
                "summary": summary or {},
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Garden version created: {short_id}.",
        ),
    }


def list_garden_versions(*, garden_root: str, limit: int = 10) -> dict[str, Any]:
    """List compact Garden version records without patch content."""
    root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    ensure_garden_git_repository(root)
    safe_limit = max(1, int(limit))
    result = _run_git(root, ["log", f"-{safe_limit}", "--format=%H"], check=False)
    version_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    matches = [_version_record(root, version_id) for version_id in version_ids]
    return {
        "matches": matches,
        "versions": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(matches),
            "limit": safe_limit,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Garden version(s).",
        ),
    }


def _assert_version_exists(root: Path, version_id: str) -> str:
    result = _run_git(
        root,
        ["rev-parse", "--verify", f"{version_id}^{{commit}}"],
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Garden version not found: {version_id}")
    return result.stdout.strip()


def _authoring_paths_in_version(root: Path, version_id: str) -> list[str]:
    result = _run_git(
        root,
        ["ls-tree", "-r", "--name-only", version_id, "--", *AUTHORING_PATHS],
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    paths: list[str] = []
    if "garden.json" in files:
        paths.append("garden.json")
    if any(path.startswith("models/") for path in files):
        paths.append("models")
    if any(path.startswith("libraries/") for path in files):
        paths.append("libraries")
    if not paths:
        raise ValueError(f"Garden version has no authoring truth: {version_id}")
    return paths


def restore_garden_version(
    *,
    garden_root: str,
    version_id: str,
    subject: str | None = None,
    summary: dict[str, Any] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Safely restore authoring truth from a version and commit the restore."""
    root = _resolve_garden_root(garden_root)
    with garden_authoring_lock(root):
        recover_interrupted_operations(root)
        ensure_garden_git_repository(root)
        pending = _pending_restore_state(root)
        controls = active_operation_controls()
        if pending is not None:
            requested_operation_id = controls[0] if controls else None
            if (
                requested_operation_id is not None
                and requested_operation_id != pending["operation_id"]
            ):
                raise GardenOperationStateError(
                    "A different Garden restore operation requires recovery. Retry "
                    f"operation_id {pending['operation_id']!r}."
                )
            if pending["source_version"] != _assert_version_exists(root, version_id):
                raise RuntimeError(
                    "A different Garden restore requires recovery. Retry that restore "
                    "before starting another one."
                )
            new_id = _resume_restore(root, pending)
            manifest = GardenManifest._read_unlocked(root)
            resolved_version = pending["source_version"]
            source_record = _version_record(root, resolved_version)
            restore_summary = pending.get("summary") or {}
            changed_count = int(pending.get("changed_file_count", 0))
            restore_state = pending
        else:
            manifest = GardenManifest._read_unlocked(root)
            if controls and controls[1] is not None and controls[1] != manifest.revision:
                raise GardenRevisionConflictError(
                    expected_revision=controls[1],
                    current_revision=manifest.revision,
                )
            resolved_version = _assert_version_exists(root, version_id)
            if _authoring_status(root):
                raise ValueError(
                    "Cannot restore Garden version with uncommitted authoring truth changes. "
                    "Create a Garden version first or discard the changes outside MCP."
                )
            source_record = _version_record(root, resolved_version)
            state = {
                "schema_version": RESTORE_STATE_SCHEMA_VERSION,
                "operation_id": controls[0] if controls else f"restore_{uuid4().hex}",
                "phase": "prepared",
                "source_version": resolved_version,
                "source_paths": _authoring_paths_in_version(root, resolved_version),
                "starting_version": _head_version(root),
                "subject": subject
                or f"restore: garden version {source_record['short_version_id']}",
                "summary": summary or {},
                "source": source,
                "created_at": utc_now_iso(),
                "before_revision": manifest.revision,
                "recovery_action": "resume",
                "error": None,
            }
            if state["starting_version"] is None:
                raise ValueError(
                    "Cannot restore a Garden without an existing version checkpoint."
                )
            _write_restore_state(root, state)
            new_id = _resume_restore(root, state)
            restore_summary = state["summary"]
            changed_count = int(state.get("changed_file_count", 0))
            restore_state = state

        manifest = GardenManifest._read_unlocked(root)
        operation_id = str(restore_state["operation_id"])
        before_revision = int(
            restore_state.get("before_revision", manifest.revision)
        )
        after_revision = manifest.revision

        if new_id is None:
            return {
                "garden_root": str(root),
                "restored_from_version": source_record,
                "new_version": source_record,
                "summary_view": {
                    "garden_target": manifest.target(),
                    "restored_from_version": source_record,
                    "changed_file_count": 0,
                },
                "persistence_receipt": make_persistence_receipt(
                    status="no_change",
                    garden_id=manifest.garden_id,
                    persisted_path=None,
                    change_summary={
                        "operation": "restore_garden_version",
                        "operation_id": operation_id,
                        "before_revision": before_revision,
                        "after_revision": after_revision,
                        "restored_from_version": resolved_version,
                    },
                ),
                "report": make_report(
                    status="ok",
                    message="Garden already matched the requested version.",
                ),
            }

        new_record = _version_record(root, new_id)
    return {
        "garden_root": str(root),
        "restored_from_version": source_record,
        "new_version": new_record,
        "version_id": new_id,
        "version_target": new_record["target"],
        "target": new_record["target"],
        "summary_view": {
            "garden_target": manifest.target(),
            "restored_from_version": source_record,
            "new_version": new_record,
            "changed_file_count": changed_count,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            persisted_path=".git",
            change_summary={
                "operation": "restore_garden_version",
                "operation_id": operation_id,
                "before_revision": before_revision,
                "after_revision": after_revision,
                "restored_from_version": resolved_version,
                "new_version": new_id,
                "summary": restore_summary,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                "Garden authoring truth restored from "
                f"{source_record['short_version_id']} as "
                f"{new_record['short_version_id']}."
            ),
        ),
    }
