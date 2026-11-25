"""Methods to write Honeybee models to native GBAS DWG files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .dwg import build, validation
from .model import room_codes


def atomic_write(path, data, overwrite):
    """Write bytes atomically to a target path."""
    if path.exists() and not overwrite:
        raise FileExistsError(f"Native DWG export requires an available destination: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".offline-dwg-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
            os.unlink(temporary)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare_model(model):
    """Validate room calculation codes and return a model copy for normalization."""
    room_codes(room.identifier for room in model.rooms)
    if not model.rooms:
        raise ValueError("Native building export requires source rooms")
    return model.duplicate()


def model_to_dwg(model, output_file, report_path=None, overwrite=False):
    """Export a Honeybee Model as a native GBAS DWG.

    Args:
        model: Honeybee Model to translate.
        output_file: Destination DWG path.
        report_path: Optional destination JSON report path.
        overwrite: Replace existing destination files when True.

    Returns:
        A tuple of (Path, dict) with the written DWG path and export report.
    """
    output = Path(output_file).resolve()
    report_target = Path(report_path).resolve() if report_path is not None else None
    if output.suffix.lower() != ".dwg":
        raise ValueError("Native DWG export requires a DWG output")
    if report_target is not None and report_target.suffix.lower() != ".json":
        raise ValueError("Native DWG export requires a JSON report")
    if report_target is not None and report_target == output:
        raise ValueError("Native DWG export requires distinct drawing and report paths")
    if not overwrite and output.exists():
        raise FileExistsError(f"Native DWG export requires an available output path: {output}")
    if report_target is not None and not overwrite and report_target.exists():
        raise FileExistsError(f"Native DWG export requires an available report path: {report_target}")
    prepared = prepare_model(model)
    drawing, report = build(prepared, inclined_carriers=True)
    data = drawing.bytes()
    validation.validate(model, data, report)
    validation.require_export(report)
    report.update(
        status="translated",
        output=str(output),
        output_bytes=len(data),
        runtime={"writer": "Python", "format": "AC1015", "intermediate_format": "direct_binary"},
        host_validation={"status": "pending"},
    )
    payload = None
    if report_target is not None:
        payload = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    atomic_write(output, data, overwrite)
    if report_target is not None:
        atomic_write(report_target, payload, overwrite)
    return output, report
