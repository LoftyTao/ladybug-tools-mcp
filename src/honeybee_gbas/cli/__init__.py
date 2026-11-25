"""honeybee-gbas commands which will be added to honeybee command line interface."""

import click
from honeybee.cli import main

from .. import __version__
from .translate import translate


@click.group(help="honeybee gbas commands.")
@click.version_option(version=__version__)
def gbas():
    pass


gbas.add_command(translate)

main.add_command(gbas)
