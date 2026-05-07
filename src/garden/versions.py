"""Garden Git-backed version management."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from ladybug_tools_mcp.contracts.targets import make_garden_version_target


AUTHORING_PATHS = ("garden.json", "models", "libraries")
GIT_USER_NAME = "Ladybug Tools MCP"
GIT_USER_EMAIL = "ladybug-tools-mcp@example.invalid"


def _resolve_garden_root(garden_root: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    if not (root / "garden.json").is_file():
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


def _ensure_git_repo(root: Path) -> None:
    if not (root / ".git").exists():
        _run_git(root, ["init"])


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
    _run_git(root, ["add", "--", *AUTHORING_PATHS])


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
    manifest = GardenManifest.read(root)
    _ensure_git_repo(root)
    head = _head_version(root)
    status_lines = _authoring_status(root)
    changed_count = _changed_file_count(root)
    return {
        "garden_root": str(root),
        "version_id": head,
        "summary_view": {
            "garden_target": manifest.target(),
            "has_versions": head is not None,
            "is_dirty": bool(status_lines),
            "changed_file_count": changed_count,
        },
        "report": make_report(
            status="ok",
            message=(
                "Garden authoring truth has uncommitted changes."
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
    manifest = GardenManifest.read(root)
    if not subject or not subject.strip():
        raise ValueError("subject is required to create a Garden version.")

    _ensure_git_repo(root)
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
                change_summary={"operation": "create_garden_version"},
            ),
            "report": make_report(
                status="ok",
                message="No Garden authoring truth changes to version.",
            ),
        }

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
    _ensure_git_repo(root)
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
    manifest = GardenManifest.read(root)
    _ensure_git_repo(root)
    resolved_version = _assert_version_exists(root, version_id)
    if _authoring_status(root):
        raise ValueError(
            "Cannot restore Garden version with uncommitted authoring truth changes. "
            "Create a Garden version first or discard the changes outside MCP."
        )

    source_record = _version_record(root, resolved_version)
    restore_subject = subject or (
        f"restore: garden version {source_record['short_version_id']}"
    )
    source_paths = _authoring_paths_in_version(root, resolved_version)
    _run_git(root, ["rm", "-r", "--ignore-unmatch", "--", *AUTHORING_PATHS])
    _run_git(root, ["restore", "--source", resolved_version, "--", *source_paths])
    _stage_authoring_truth(root)
    changed_count = _changed_file_count(root)
    if changed_count == 0:
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
                    "restored_from_version": resolved_version,
                },
            ),
            "report": make_report(
                status="ok",
                message="Garden already matched the requested version.",
            ),
        }

    restore_summary = {
        "operation": "restore_garden_version",
        "restored_from_version": source_record,
        "summary": summary or {},
    }
    _run_git(
        root,
        [
            "-c",
            f"user.name={GIT_USER_NAME}",
            "-c",
            f"user.email={GIT_USER_EMAIL}",
            "commit",
            "-m",
            restore_subject,
            "-m",
            _commit_summary_body(restore_summary, source),
        ],
    )
    new_id = _head_version(root)
    assert new_id is not None
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
                "restored_from_version": resolved_version,
                "new_version": new_id,
                "summary": summary or {},
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
