"""OpenStudio file helpers for the Python Ironbug Console."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def backup_osm_file(osm_path: str | Path) -> Path:
    """Copy the input OSM beside itself using the C# Console backup suffix."""

    source = Path(osm_path)
    backup_path = source.with_suffix(source.suffix + ".backup")
    shutil.copy2(source, backup_path)
    return backup_path


def load_openstudio_model(openstudio: Any, osm_path: str | Path) -> Any:
    """Load an existing OpenStudio model with VersionTranslator."""

    candidate = Path(osm_path)
    if not candidate.exists() or candidate.suffix.lower() != ".osm":
        raise ValueError(f"Invalid osm file: {candidate}")
    translator = openstudio.osversion.VersionTranslator()
    optional_model = translator.loadModel(openstudio.path(str(candidate)))
    if not optional_model.is_initialized():
        errors = [
            error.logMessage()
            for error in getattr(translator, "errors", lambda: [])()
        ]
        suffix = f": {'; '.join(errors)}" if errors else ""
        raise ValueError(f"Failed to load OpenStudio Model from {candidate}{suffix}")
    model = optional_model.get()
    if hasattr(model, "isValid") and not model.isValid():
        raise ValueError(f"Found an invalid OpenStudio Model from {candidate}")
    return model


def save_openstudio_model(openstudio: Any, model: Any, osm_path: str | Path) -> Path:
    """Save an OpenStudio model to an OSM file."""

    target = Path(osm_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not model.save(openstudio.path(str(target)), True):
        raise ValueError(f"Failed to save OpenStudio Model to {target}")
    return target


def save_workflow_seed_file(openstudio: Any, model: Any, osm_path: str | Path) -> Path:
    """Write the workflow.osw sibling used by the C# Console runtime role."""

    osm = Path(osm_path)
    workflow_path = osm.parent / osm.stem / "workflow.osw"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow = model.workflowJSON()
    workflow.setSeedFile(openstudio.path(str(Path("..") / osm.name)))
    if not workflow.saveAs(openstudio.path(str(workflow_path))):
        raise ValueError(f"Failed to create workflowJSON file: {workflow_path}")
    return workflow_path
