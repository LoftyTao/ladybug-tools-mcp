"""Cross-domain run ledger listing, polling, cancellation, and log inspection."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import time
from typing import Any

from garden.background import read_tail_lines, terminate_pid
from garden.manifest import GardenManifest
from garden.paths import (
    require_garden_root,
    resolve_contained_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_ledger import RunLedger, RunManager
from ladybug_tools_mcp.contracts import make_report


@dataclass(frozen=True)
class _DomainSpec:
    domain: str
    aliases: tuple[str, ...]
    target_type: str
    runs_dir: Path
    per_recipe_index: bool
    default_recipe: str
    recipes: tuple[str, ...]
    slug_lookup: bool
    module: str
    manager_attr: str
    reconcile_kind: str | None = None


_DOMAIN_SPECS: tuple[_DomainSpec, ...] = (
    _DomainSpec(
        domain="honeybee_energy",
        aliases=("energy", "honeybee_energy", "ep"),
        target_type="energy_run",
        runs_dir=Path("runs") / "energy",
        per_recipe_index=False,
        default_recipe="annual_energy_use",
        recipes=(),
        slug_lookup=False,
        module="garden.run_energy.annual",
        manager_attr="_ENERGY_RUNS",
        reconcile_kind="energy",
    ),
    _DomainSpec(
        domain="honeybee_radiance",
        aliases=("radiance", "honeybee_radiance", "rad"),
        target_type="radiance_run",
        runs_dir=Path("runs") / "radiance",
        per_recipe_index=False,
        default_recipe="point-in-time-grid",
        recipes=(),
        slug_lookup=False,
        module="garden.radiance.run",
        manager_attr="_RADIANCE_RUNS",
        reconcile_kind="radiance",
    ),
    _DomainSpec(
        domain="dragonfly_uwg",
        aliases=("uwg", "dragonfly_uwg"),
        target_type="uwg_run",
        runs_dir=Path("runs") / "uwg",
        per_recipe_index=False,
        default_recipe="urban_weather_generator",
        recipes=(),
        slug_lookup=True,
        module="garden.run_uwg",
        manager_attr="_UWG_RUNS",
    ),
    _DomainSpec(
        domain="urbanopt",
        aliases=("urbanopt", "dragonfly_urbanopt"),
        target_type="urbanopt_run",
        runs_dir=Path("runs") / "urbanopt",
        per_recipe_index=False,
        default_recipe="run_energy",
        recipes=(),
        slug_lookup=True,
        module="garden.run_urbanopt",
        manager_attr="_URBANOPT_RUNS",
    ),
    _DomainSpec(
        domain="dragonfly_des",
        aliases=("des", "dragonfly_des"),
        target_type="dragonfly_des_run",
        runs_dir=Path("runs") / "dragonfly_des",
        per_recipe_index=True,
        default_recipe="urbanopt",
        recipes=("urbanopt", "sys_param", "modelica"),
        slug_lookup=True,
        module="garden.dragonfly_des.runs",
        manager_attr="_DES_RUNS",
        reconcile_kind="des",
    ),
    _DomainSpec(
        domain="dragonfly_grid",
        aliases=("grid", "dragonfly_grid"),
        target_type="dragonfly_grid_run",
        runs_dir=Path("runs") / "dragonfly_grid",
        per_recipe_index=True,
        default_recipe="rnm",
        recipes=("rnm", "opendss", "reopt"),
        slug_lookup=False,
        module="garden.dragonfly_grid.runs",
        manager_attr="_GRID_RUNS",
    ),
    _DomainSpec(
        domain="fairyfly",
        aliases=("fairyfly", "fairyfly_therm", "therm", "ff"),
        target_type="fairyfly_therm_run",
        runs_dir=Path("runs") / "fairyfly_therm",
        per_recipe_index=False,
        default_recipe="therm",
        recipes=(),
        slug_lookup=False,
        module="garden.fairyfly.therm",
        manager_attr="_THERM_RUNS",
    ),
)

_SPECS_BY_DOMAIN = {spec.domain: spec for spec in _DOMAIN_SPECS}
_SPECS_BY_ALIAS = {
    alias: spec for spec in _DOMAIN_SPECS for alias in spec.aliases
}
_SPECS_BY_TARGET_TYPE = {spec.target_type: spec for spec in _DOMAIN_SPECS}

_ACTIVE_STATUSES = frozenset({"queued", "running"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "blocked", "superseded", "cancelled"})


@dataclass
class _ResolvedRun:
    spec: _DomainSpec
    module: Any | None
    manager: RunManager
    recipe: str | None
    run_id: str
    record: dict[str, Any]


def _normalize_domain(domain: str | None) -> _DomainSpec | None:
    if domain is None:
        return None
    key = str(domain).strip().lower().replace("-", "_").replace(" ", "_")
    if not key or key == "all":
        return None
    spec = _SPECS_BY_ALIAS.get(key)
    if spec is None:
        allowed = ", ".join(["all", *(item.domain for item in _DOMAIN_SPECS)])
        raise ValueError(f"Unsupported run domain {domain!r}. Allowed values: {allowed}.")
    return spec


def _fallback_manager(spec: _DomainSpec) -> RunManager:
    return RunManager(
        domain=spec.domain,
        target_type=spec.target_type,
        runs_dir=spec.runs_dir,
        default_recipe=spec.default_recipe,
        allowed_recipes=set(spec.recipes) if spec.recipes else None,
        per_recipe_index=spec.per_recipe_index,
        slug_lookup=spec.slug_lookup,
        not_found_label=spec.domain,
        ledger=RunLedger(
            lock="file",
            atomic=True,
            recover_trailing_json=True,
            empty_is_empty=True,
            sort_by_created_at=True,
        ),
    )


def _load_domain_manager(spec: _DomainSpec) -> tuple[Any | None, RunManager]:
    try:
        module = import_module(spec.module)
        manager = getattr(module, spec.manager_attr)
        if isinstance(manager, RunManager):
            return module, manager
    except ImportError:
        return None, _fallback_manager(spec)
    return None, _fallback_manager(spec)


def _existing_recipes_for_domain(garden_root: Path, spec: _DomainSpec) -> list[str | None]:
    base = garden_root / spec.runs_dir
    if not spec.per_recipe_index:
        return [None] if (base / "index.json").is_file() else []
    recipes: list[str] = []
    seen: set[str] = set()
    for recipe in spec.recipes:
        if (base / recipe / "index.json").is_file():
            recipes.append(recipe)
            seen.add(recipe)
    if base.is_dir():
        for child in sorted(base.iterdir()):
            if child.is_dir() and child.name not in seen and (child / "index.json").is_file():
                recipes.append(child.name)
                seen.add(child.name)
    return list(recipes)


def _candidate_recipes(garden_root: Path, spec: _DomainSpec, recipe: str | None) -> list[str | None]:
    if not spec.per_recipe_index:
        return [None]
    if recipe is not None:
        return [recipe]
    existing = _existing_recipes_for_domain(garden_root, spec)
    return existing or list(spec.recipes)


def _reconcile_record(
    *,
    garden_root: Path,
    spec: _DomainSpec,
    module: Any | None,
    recipe: str | None,
    record: dict[str, Any],
) -> dict[str, Any]:
    if module is None:
        return record
    if spec.reconcile_kind == "radiance" and hasattr(module, "_reconcile_running_record"):
        try:
            return module._reconcile_running_record(
                garden_root_path=garden_root,
                record=dict(record),
            )
        except Exception:
            return record
    if spec.reconcile_kind == "des" and recipe and hasattr(module, "_stabilize_running_record"):
        try:
            return module._stabilize_running_record(garden_root, recipe, dict(record))
        except Exception:
            return record
    return record


def _record_target(
    *,
    manifest: GardenManifest,
    spec: _DomainSpec,
    manager: RunManager,
    record: dict[str, Any],
    recipe: str | None,
) -> dict[str, Any]:
    target = record.get("target")
    if isinstance(target, dict) and target.get("run_id"):
        return dict(target)
    resolved_recipe = str(record.get("recipe") or recipe or spec.default_recipe)
    return manager.make_target(
        manifest.garden_id,
        str(record["run_id"]),
        recipe=resolved_recipe,
    )


def _runtime_status(record: dict[str, Any]) -> str:
    value = record.get("runtime_status") or record.get("status") or "unknown"
    return str(value)


def _read_worker_pid(garden_root: Path, record: dict[str, Any]) -> int | None:
    raw_pid = record.get("worker_pid")
    if isinstance(raw_pid, int) and not isinstance(raw_pid, bool) and raw_pid > 0:
        return raw_pid
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        return None
    try:
        run_dir = (garden_root / run_folder).resolve()
        run_dir.relative_to(garden_root)
    except ValueError:
        return None
    pid_path = run_dir / "worker.pid"
    if not pid_path.is_file():
        return None
    try:
        parsed = int(pid_path.read_text(encoding="utf-8", errors="replace").strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _run_summary_item(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    spec: _DomainSpec,
    manager: RunManager,
    record: dict[str, Any],
    recipe: str | None,
) -> dict[str, Any]:
    target = _record_target(
        manifest=manifest,
        spec=spec,
        manager=manager,
        record=record,
        recipe=recipe,
    )
    resolved_recipe = str(record.get("recipe") or recipe or spec.default_recipe)
    status = str(record.get("status") or _runtime_status(record))
    runtime_status = _runtime_status(record)
    item: dict[str, Any] = {
        "run_id": str(record.get("run_id") or target.get("run_id") or ""),
        "target": target,
        "run_target": target,
        "domain": spec.domain,
        "recipe": resolved_recipe,
        "status": status,
        "runtime_status": runtime_status,
        "created_at": record.get("created_at"),
        "run_folder": record.get("run_folder"),
    }
    if record.get("completed_at") is not None:
        item["completed_at"] = record.get("completed_at")
    worker_pid = _read_worker_pid(garden_root, record)
    if worker_pid is not None:
        item["worker_pid"] = worker_pid
    if record.get("error"):
        item["error"] = record.get("error")
    return item


def _lookup_in_domain(
    *,
    garden_root: Path,
    spec: _DomainSpec,
    run_id: str,
    recipe: str | None,
) -> list[_ResolvedRun]:
    candidates = _candidate_recipes(garden_root, spec, recipe)
    if not candidates:
        return []
    module, manager = _load_domain_manager(spec)
    matches: list[_ResolvedRun] = []
    for candidate_recipe in candidates:
        index_path = manager.index_path(garden_root, recipe=candidate_recipe)
        if not index_path.is_file():
            continue
        record = manager.get(garden_root, run_id, recipe=candidate_recipe)
        resolved_id = run_id
        if record is None and spec.slug_lookup:
            slugged = slugify_name(run_id)
            if slugged != run_id:
                record = manager.get(garden_root, slugged, recipe=candidate_recipe)
                if record is not None:
                    resolved_id = slugged
        if record is None:
            continue
        reconciled = _reconcile_record(
            garden_root=garden_root,
            spec=spec,
            module=module,
            recipe=candidate_recipe,
            record=record,
        )
        matches.append(
            _ResolvedRun(
                spec=spec,
                module=module,
                manager=manager,
                recipe=candidate_recipe,
                run_id=str(reconciled.get("run_id") or resolved_id),
                record=reconciled,
            )
        )
    return matches


def _resolve_run(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_target: dict[str, Any] | None = None,
    domain: str | None = None,
    run_id: str | None = None,
    recipe: str | None = None,
) -> _ResolvedRun:
    requested_spec = _normalize_domain(domain)

    if run_target is not None:
        if not isinstance(run_target, dict):
            raise ValueError("run_target must be a dictionary.")
        target_garden_id = run_target.get("garden_id")
        if target_garden_id and target_garden_id != manifest.garden_id:
            raise ValueError("run_target belongs to a different Garden.")
        target_type = run_target.get("target_type")
        target_domain = run_target.get("domain")
        spec: _DomainSpec | None = None
        if isinstance(target_type, str) and target_type in _SPECS_BY_TARGET_TYPE:
            spec = _SPECS_BY_TARGET_TYPE[target_type]
        elif isinstance(target_domain, str):
            spec = _normalize_domain(target_domain)
        if spec is None:
            raise ValueError("run_target has an unrecognized target_type or domain.")
        if target_domain is not None:
            normalized_target_domain = _normalize_domain(str(target_domain))
            if normalized_target_domain is not None and normalized_target_domain != spec:
                raise ValueError(
                    f"run_target domain {target_domain!r} does not match target_type {target_type!r}."
                )
        if requested_spec is not None and requested_spec != spec:
            raise ValueError(
                f"domain {domain!r} does not match run_target domain {spec.domain!r}."
            )
        target_recipe = run_target.get("recipe")
        if recipe is not None and target_recipe is not None and str(target_recipe) != recipe:
            raise ValueError(
                f"recipe {recipe!r} does not match run_target recipe {target_recipe!r}."
            )
        effective_recipe = recipe or (str(target_recipe) if target_recipe else None)
        target_run_id = run_target.get("run_id")
        if not isinstance(target_run_id, str) or not target_run_id:
            raise ValueError("run_target requires run_id.")
        if run_id is not None and run_id != target_run_id:
            if not (spec.slug_lookup and slugify_name(run_id) == target_run_id):
                raise ValueError("run_id does not match run_target.run_id.")
        matches = _lookup_in_domain(
            garden_root=garden_root,
            spec=spec,
            run_id=target_run_id,
            recipe=effective_recipe if spec.per_recipe_index else None,
        )
        if not matches:
            raise ValueError(f"{spec.domain} run was not found: {target_run_id}")
        if len(matches) > 1:
            raise ValueError(
                f"Multiple {spec.domain} runs matched {target_run_id}; specify recipe."
            )
        return matches[0]

    if not run_id:
        raise ValueError("Provide run_target or run_id.")

    if requested_spec is not None:
        matches = _lookup_in_domain(
            garden_root=garden_root,
            spec=requested_spec,
            run_id=run_id,
            recipe=recipe if requested_spec.per_recipe_index else None,
        )
        if not matches:
            raise ValueError(f"{requested_spec.domain} run was not found: {run_id}")
        if len(matches) > 1:
            recipes = ", ".join(m.recipe or requested_spec.default_recipe for m in matches)
            raise ValueError(
                f"Multiple {requested_spec.domain} runs matched {run_id} ({recipes}); "
                "specify recipe or run_target."
            )
        return matches[0]

    all_matches: list[_ResolvedRun] = []
    for candidate_spec in _DOMAIN_SPECS:
        all_matches.extend(
            _lookup_in_domain(
                garden_root=garden_root,
                spec=candidate_spec,
                run_id=run_id,
                recipe=recipe if candidate_spec.per_recipe_index else None,
            )
        )
    if not all_matches:
        raise ValueError(f"Run was not found in any domain ledger: {run_id}")
    if len(all_matches) > 1:
        found = ", ".join(
            f"{m.spec.domain}:{m.recipe or m.spec.default_recipe}" for m in all_matches
        )
        raise ValueError(
            f"Run id {run_id!r} matched multiple runs ({found}); "
            "pass run_target or domain (and recipe if needed)."
        )
    return all_matches[0]


def list_runs(
    *,
    garden_root: str,
    domain: str = "all",
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List simulation runs across one or all Garden run domains, newest first."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided.")
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    selected_spec = _normalize_domain(domain)
    specs = (selected_spec,) if selected_spec is not None else _DOMAIN_SPECS
    normalized_status = status.strip().lower() if isinstance(status, str) and status.strip() else None

    items: list[dict[str, Any]] = []
    domains_checked: list[str] = []
    for spec in specs:
        recipes = _existing_recipes_for_domain(garden_root_path, spec)
        if not recipes:
            continue
        domains_checked.append(spec.domain)
        module, manager = _load_domain_manager(spec)
        for recipe in recipes:
            for record in manager.list(garden_root_path, recipe=recipe):
                reconciled = _reconcile_record(
                    garden_root=garden_root_path,
                    spec=spec,
                    module=module,
                    recipe=recipe,
                    record=record,
                )
                item = _run_summary_item(
                    garden_root=garden_root_path,
                    manifest=manifest,
                    spec=spec,
                    manager=manager,
                    record=reconciled,
                    recipe=recipe,
                )
                if normalized_status is not None and (
                    str(item["status"]).lower() != normalized_status
                    and str(item["runtime_status"]).lower() != normalized_status
                ):
                    continue
                items.append(item)

    items.sort(
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("run_id") or "")),
        reverse=True,
    )
    total_count = len(items)
    if limit is not None:
        items = items[:limit]

    domain_label = selected_spec.domain if selected_spec is not None else "all"
    return {
        "matches": items,
        "runs": items,
        "summary_view": {
            "garden_target": manifest.target(),
            "domain": domain_label,
            "status": normalized_status or "all",
            "count": len(items),
            "total_count": total_count,
            "domains_with_runs": domains_checked,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(items)} run(s) for domain '{domain_label}'.",
        ),
    }


def poll_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    domain: str | None = None,
    run_id: str | None = None,
    recipe: str | None = None,
    wait_seconds: float | None = None,
    poll_interval: float | None = None,
    include_outputs: bool = True,
) -> dict[str, Any]:
    """Poll one Garden run across any domain, optionally waiting while queued or running."""
    if wait_seconds is not None and wait_seconds < 0:
        raise ValueError("wait_seconds must be non-negative.")
    interval = 1.0 if poll_interval is None else float(poll_interval)
    if interval <= 0:
        raise ValueError("poll_interval must be greater than zero.")

    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)

    deadline = (
        time.monotonic() + float(wait_seconds)
        if wait_seconds is not None and wait_seconds > 0
        else None
    )
    resolved = _resolve_run(
        garden_root=garden_root_path,
        manifest=manifest,
        run_target=run_target,
        domain=domain,
        run_id=run_id,
        recipe=recipe,
    )
    while deadline is not None and _runtime_status(resolved.record) in _ACTIVE_STATUSES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))
        resolved = _resolve_run(
            garden_root=garden_root_path,
            manifest=manifest,
            run_target=run_target,
            domain=resolved.spec.domain,
            run_id=resolved.run_id,
            recipe=resolved.recipe,
        )

    record = resolved.record
    target = _record_target(
        manifest=manifest,
        spec=resolved.spec,
        manager=resolved.manager,
        record=record,
        recipe=resolved.recipe,
    )
    resolved_recipe = str(
        record.get("recipe") or resolved.recipe or resolved.spec.default_recipe
    )
    status = str(record.get("status") or _runtime_status(record))
    runtime_status = _runtime_status(record)
    public = resolved.manager.public_run(record)
    worker_pid = _read_worker_pid(garden_root_path, record)
    if worker_pid is not None and "worker_pid" not in public:
        public["worker_pid"] = worker_pid

    outputs = record.get("outputs") if "outputs" in record else []
    if not include_outputs:
        public.pop("outputs", None)

    poll_next: dict[str, Any] | None = None
    if runtime_status in _ACTIVE_STATUSES:
        poll_next = {
            "tool": "GD_Poll_Run",
            "arguments": {"garden_root": str(garden_root_path), "run_target": target},
        }

    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "status": status,
        "runtime_status": runtime_status,
        "run_folder": record.get("run_folder"),
        "worker_pid": worker_pid,
        "run": public,
    }
    if include_outputs:
        summary_view["outputs"] = outputs
    if poll_next is not None:
        summary_view["poll_next"] = poll_next
    if record.get("error"):
        summary_view["error"] = record.get("error")

    warnings = list(record.get("warnings") or [])
    if not warnings:
        preflight = record.get("preflight")
        if isinstance(preflight, dict):
            warnings = [str(item) for item in preflight.get("issues", []) if item]

    report_status = (
        "warning"
        if runtime_status in {"blocked", "failed", "cancelled"}
        else "ok"
    )
    response: dict[str, Any] = {
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "status": status,
        "runtime_status": runtime_status,
        "summary_view": summary_view,
        "report": make_report(
            status=report_status,
            message=f"{resolved.spec.domain} run {resolved.run_id} is {runtime_status}.",
            warnings=warnings,
        ),
    }
    if include_outputs:
        response["outputs"] = outputs
    if poll_next is not None:
        response["poll_next"] = poll_next
    return response


def cancel_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    domain: str | None = None,
    run_id: str | None = None,
    recipe: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Cancel an active run, terminate its worker process if known, and update its ledger."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved = _resolve_run(
        garden_root=garden_root_path,
        manifest=manifest,
        run_target=run_target,
        domain=domain,
        run_id=run_id,
        recipe=recipe,
    )
    record = dict(resolved.record)
    target = _record_target(
        manifest=manifest,
        spec=resolved.spec,
        manager=resolved.manager,
        record=record,
        recipe=resolved.recipe,
    )
    resolved_recipe = str(
        record.get("recipe") or resolved.recipe or resolved.spec.default_recipe
    )
    current_status = _runtime_status(record)
    worker_pid = _read_worker_pid(garden_root_path, record)

    if current_status == "cancelled":
        summary_view = {
            "garden_target": manifest.target(),
            "target": target,
            "run_target": target,
            "domain": resolved.spec.domain,
            "recipe": resolved_recipe,
            "run_id": resolved.run_id,
            "status": "cancelled",
            "runtime_status": "cancelled",
            "cancelled": False,
            "already_cancelled": True,
            "worker_pid": worker_pid,
            "error": record.get("error"),
        }
        return {
            "target": target,
            "run_target": target,
            "domain": resolved.spec.domain,
            "recipe": resolved_recipe,
            "run_id": resolved.run_id,
            "cancelled": False,
            "status": "cancelled",
            "runtime_status": "cancelled",
            "worker_pid": worker_pid,
            "termination": None,
            "summary_view": summary_view,
            "report": make_report(
                status="ok",
                message=f"Run {resolved.run_id} was already cancelled.",
            ),
        }

    if current_status in _TERMINAL_STATUSES:
        summary_view = {
            "garden_target": manifest.target(),
            "target": target,
            "run_target": target,
            "domain": resolved.spec.domain,
            "recipe": resolved_recipe,
            "run_id": resolved.run_id,
            "status": str(record.get("status") or current_status),
            "runtime_status": current_status,
            "cancelled": False,
            "worker_pid": worker_pid,
        }
        return {
            "target": target,
            "run_target": target,
            "domain": resolved.spec.domain,
            "recipe": resolved_recipe,
            "run_id": resolved.run_id,
            "cancelled": False,
            "status": str(record.get("status") or current_status),
            "runtime_status": current_status,
            "worker_pid": worker_pid,
            "termination": None,
            "summary_view": summary_view,
            "report": make_report(
                status="warning",
                message=(
                    f"Run {resolved.run_id} is already in terminal state "
                    f"'{current_status}' and was not cancelled."
                ),
            ),
        }

    termination: dict[str, Any] | None = None
    warnings: list[str] = []
    if worker_pid is not None:
        termination = terminate_pid(worker_pid)
        if termination.get("error"):
            warnings.append(str(termination["error"]))
    else:
        warnings.append(
            "No worker_pid was recorded or found in worker.pid; marked ledger as cancelled."
        )

    record.update(resolved.manager.cancel_fields(reason))
    if worker_pid is not None:
        record["worker_pid"] = worker_pid
    resolved.manager.upsert(
        garden_root_path,
        record,
        recipe=resolved.recipe if resolved.spec.per_recipe_index else None,
    )

    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "status": "cancelled",
        "runtime_status": "cancelled",
        "cancelled": True,
        "worker_pid": worker_pid,
        "termination": termination,
        "error": record.get("error"),
    }
    return {
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "cancelled": True,
        "status": "cancelled",
        "runtime_status": "cancelled",
        "worker_pid": worker_pid,
        "termination": termination,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Cancelled {resolved.spec.domain} run {resolved.run_id}.",
            warnings=warnings,
        ),
    }


def _discover_run_logs(run_dir: Path, recipe: str | None) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def _add_if_log(path: Path) -> None:
        if len(candidates) >= 50:
            return
        try:
            resolved = path.resolve()
        except OSError:
            return
        if not resolved.is_file() or not resolved.is_relative_to(run_dir):
            return
        rel = to_posix_relative(resolved, run_dir)
        if rel not in seen:
            seen.add(rel)
            candidates.append(rel)

    priority = [
        "background_stdio.log",
        "recipe_stdio.log",
        "uwg_stdio.log",
        "eplusout.err",
        "openstudio/run/eplusout.err",
    ]
    if recipe:
        priority.append(f"{recipe.replace('-', '_')}/__logs__/logs.log")

    for rel in priority:
        _add_if_log(run_dir / rel)

    if run_dir.is_dir():
        for item in sorted(run_dir.rglob("*")):
            if len(candidates) >= 50:
                break
            if item.suffix.lower() in {".log", ".err"}:
                _add_if_log(item)

    return candidates


def read_run_logs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    domain: str | None = None,
    run_id: str | None = None,
    recipe: str | None = None,
    tail_lines: int = 100,
    log_file: str | None = None,
) -> dict[str, Any]:
    """Read tail lines from one run's contained stdio or engine log file."""
    if tail_lines < 1:
        raise ValueError("tail_lines must be at least 1.")
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved = _resolve_run(
        garden_root=garden_root_path,
        manifest=manifest,
        run_target=run_target,
        domain=domain,
        run_id=run_id,
        recipe=recipe,
    )
    record = resolved.record
    target = _record_target(
        manifest=manifest,
        spec=resolved.spec,
        manager=resolved.manager,
        record=record,
        recipe=resolved.recipe,
    )
    resolved_recipe = str(
        record.get("recipe") or resolved.recipe or resolved.spec.default_recipe
    )

    run_folder = record.get("run_folder")
    if isinstance(run_folder, str) and run_folder:
        run_dir = (garden_root_path / run_folder).resolve()
        run_dir.relative_to(garden_root_path)
    else:
        run_dir = resolved.manager.run_dir(
            garden_root_path,
            resolved.run_id,
            recipe=resolved.recipe,
            create=False,
        )

    available_logs = _discover_run_logs(run_dir, resolved_recipe) if run_dir.is_dir() else []

    selected_path: Path | None = None
    selected_rel: str | None = None
    selected_garden_rel: str | None = None
    if log_file is not None:
        if not run_dir.is_dir():
            raise ValueError(f"Run folder does not exist for run {resolved.run_id}.")
        candidate = resolve_contained_path(run_dir, log_file, label="Run log file")
        if not candidate.resolve().is_relative_to(run_dir):
            raise ValueError("Run log file must stay inside the run folder.")
        if not candidate.is_file():
            raise ValueError(f"Run log file was not found: {log_file}")
        selected_path = candidate
        selected_rel = to_posix_relative(candidate, run_dir)
        selected_garden_rel = to_posix_relative(candidate, garden_root_path)
    elif available_logs:
        selected_rel = available_logs[0]
        selected_path = (run_dir / selected_rel).resolve()
        selected_path.relative_to(run_dir)
        selected_garden_rel = to_posix_relative(selected_path, garden_root_path)

    log_text = read_tail_lines(selected_path, tail_lines=tail_lines) if selected_path else ""
    warnings = (
        []
        if selected_path is not None
        else [f"No log files were found in run folder for {resolved.run_id}."]
    )
    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "status": _runtime_status(record),
        "run_folder": record.get("run_folder"),
        "log_file": selected_rel,
        "log_path": selected_garden_rel,
        "tail_lines": tail_lines,
        "available_logs": available_logs,
        "line_count": len(log_text.splitlines()),
    }
    return {
        "target": target,
        "run_target": target,
        "domain": resolved.spec.domain,
        "recipe": resolved_recipe,
        "run_id": resolved.run_id,
        "log_file": selected_rel,
        "log_path": selected_garden_rel,
        "log_text": log_text,
        "available_logs": available_logs,
        "summary_view": summary_view,
        "report": make_report(
            status="ok" if selected_path is not None else "warning",
            message=(
                f"Read tail ({tail_lines} lines max) from {selected_rel}."
                if selected_rel
                else f"No log files available for run {resolved.run_id}."
            ),
            warnings=warnings,
        ),
    }


__all__ = [
    "cancel_run",
    "list_runs",
    "poll_run",
    "read_run_logs",
]
