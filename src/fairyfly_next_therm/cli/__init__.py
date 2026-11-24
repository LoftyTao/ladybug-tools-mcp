"""Standalone Fairyfly-Next THERM commands."""
import click
import sys
import logging
import json

from ..config import folders
from .setconfig import set_config
from .translate import translate
from .simulate import simulate

_logger = logging.getLogger(__name__)


# command group for all therm extension commands.
@click.group(help='Fairyfly-Next THERM commands.')
@click.version_option()
def therm():
    pass


@therm.command('config')
@click.option('--output-file', help='Optional file to output the JSON string of '
              'the config object. By default, it will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def config(output_file):
    """Get a JSON object with all configuration information"""
    try:
        config_dict = {
            'therm_path': folders.therm_path,
            'therm_version': folders.therm_version_str,
            'lbnl_data_path': folders.lbnl_data_path,
            'therm_settings_path': folders.therm_settings_path,
            'therm_lib_path': folders.therm_lib_path
        }
        output_file.write(json.dumps(config_dict, indent=4))
    except Exception as e:
        _logger.exception('Failed to retrieve configurations.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


# add sub-commands to therm
therm.add_command(set_config, name='set-config')
therm.add_command(translate)
therm.add_command(simulate)
