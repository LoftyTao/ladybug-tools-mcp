"""Fairyfly-Next THERM translation commands."""
import click
import sys
import os
import logging
import base64
import tempfile
import uuid

from fairyfly.model import Model
from fairyfly_next_therm.writer import model_to_thmz as model_to_thmz_file

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Fairyfly-Next JSON files to THMZ files.')
def translate():
    pass


@translate.command('model-to-thmz')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-o', help='Optional THMZ file path to output the THMZ bytes '
    'of the translation. By default this will be printed out to stdout.',
    type=click.File('w'), default='-', show_default=True)
def model_to_thmz_cli(model_file, output_file):
    """Translate a Fairyfly-Next Model file to an THERM THMZ file.
    \b

    Args:
        model_file: Full path to a Fairyfly-Next Model file (FFJSON or FFpkl).
    """
    try:
        model_to_thmz(model_file, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_thmz(model_file, output_file=None):
    """Translate a Fairyfly-Next Model file to an THERM THMZ file.

    Args:
        model_file: Full path to a Fairyfly-Next Model file (FFJSON or FFpkl).
        output_file: Optional THMZ file path to output the THMZ string of the
            translation. If None, the string will be returned from this function.
    """
    # translate the Model to THMZ
    model = Model.from_file(model_file)
    if isinstance(output_file, str):
        folder = os.path.dirname(output_file)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        model_to_thmz_file(model, output_file=output_file)
    else:
        if output_file is None or output_file.name == '<stdout>':  # get a temporary file
            out_folder = tempfile.gettempdir()
            out_file = str(uuid.uuid4())[:6]
            out_file = os.path.join(out_folder, out_file)
        else:
            out_file = output_file.name
        thmz_file = model_to_thmz_file(model, output_file=out_file)
        if output_file is None or output_file.name == '<stdout>':  # load file contents
            with open(thmz_file, 'rb') as of:  # THMZ can only be read as binary
                f_contents = of.read()
            b = base64.b64encode(f_contents)
            base64_string = b.decode('utf-8')
            if output_file is None:
                return base64_string
            else:
                output_file.write(base64_string)
