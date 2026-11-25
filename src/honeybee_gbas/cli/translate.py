"""honeybee-gbas translation commands."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from honeybee.model import Model

_logger = logging.getLogger(__name__)


@click.group(help="Commands for translating Honeybee Model files to GBAS DWG files.")
def translate():
    pass


@translate.command("model-to-dwg")
@click.argument(
    "model-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--output-file",
    "-o",
    help="Optional DWG file path to write the translated model.",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
    default=None,
    show_default=True,
)
@click.option(
    "--report",
    help="Optional JSON report path.",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
    default=None,
    show_default=True,
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    show_default=True,
    help="Flag to allow overwriting existing destination files.",
)
def model_to_dwg_cli(model_file, output_file, report, overwrite):
    """Translate a Honeybee Model JSON file to a native GBAS DWG file."""
    try:
        written, summary = model_to_dwg(model_file, output_file, report, overwrite)
        click.echo(
            json.dumps(
                {
                    "status": summary["status"],
                    "output": str(written),
                    "counts": summary["counts"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception as e:
        _logger.exception("Model translation failed.\n{}".format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_dwg(model_file, output_file=None, report_path=None, overwrite=False):
    """Translate a Honeybee Model file to a native GBAS DWG file.

    Args:
        model_file: Full path to a Honeybee Model file (HBJSON or HBpkl).
        output_file: Optional destination DWG file path. Defaults to the
            input stem with a .dwg suffix.
        report_path: Optional destination JSON report path.
        overwrite: Replace existing destination files when True.

    Returns:
        A tuple of (Path, dict) with the written DWG path and export report.
    """
    model = Model.from_file(str(model_file))
    target = Path(output_file) if output_file else Path(model_file).with_suffix(".dwg")
    report = Path(report_path) if report_path else None
    return model.to.dwg(model, target, report, overwrite)
