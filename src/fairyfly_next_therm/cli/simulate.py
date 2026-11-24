"""Fairyfly-Next THERM simulation running commands."""
import click
import sys
import logging

from ladybug.commandutil import process_content_to_output
from fairyfly.model import Model
from fairyfly_next_therm.run import run_model

_logger = logging.getLogger(__name__)


@click.group(help='Simulate with pyHygroThermFEM-Fairyfly inside the Rhino Python runtime.')
def simulate():
    pass


@simulate.command('model')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--folder', '-f', help='Folder on this computer, into which the THMZ '
    'and simulation files will be written. If None, the files will be output '
    'to the Fairyfly-Next default simulation folder and placed in a project '
    'folder with the same name as the model-file.',
    default=None, show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option(
    '--log-file', '-log', help='Optional log file to output the paths of the '
    'generated THMZ file if successfully created. By default the list will '
    'be printed out to stdout', type=click.File('w'), default='-', show_default=True)
def simulate_model_cli(model_file, folder, log_file):
    """Mesh a Fairyfly-Next Model in Rhino and solve it with pyHygroTherm.

    \b
    Args:
        model_file: Full path to a Model file as either a FFJSON or FFpkl.
    """
    try:
        simulate_model(model_file, folder, log_file)
    except Exception as e:
        _logger.exception('Model simulation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def simulate_model(model_file, folder=None, log_file=None):
    """Mesh a Fairyfly-Next Model in Rhino and solve it with pyHygroTherm.

    Args:
        model_file: Full path to a Fairyfly-Next Model file (FFJSON or FFpkl).
        Folder on this computer, into which the THMZ and simulation files will
            be written. If None, the files will be output to the fairyfly
            default simulation folder and placed in a project folder with the
            same name as the model-file.
        output_file: Optional THMZ file path to output the THMZ string of the
            translation. If None, the string will be returned from this function.
    """
    model = Model.from_file(model_file)
    thmz_file = run_model(model, folder, silent=True)
    process_content_to_output(thmz_file, log_file)
