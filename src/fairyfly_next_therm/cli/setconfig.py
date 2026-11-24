"""Commands to set Fairyfly-Next THERM configurations."""
import click
import sys
import logging
import json

from fairyfly_next_therm.config import folders

_logger = logging.getLogger(__name__)


@click.group(help='Commands to set Fairyfly-Next THERM configurations.')
def set_config():
    pass


@set_config.command('therm-path')
@click.argument('folder-path', required=False, type=click.Path(
    exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def therm_path(folder_path):
    """Set the therm-path configuration variable.

    \b
    Args:
        folder_path: Path to a folder to be set as the therm-path.
            If unspecified, the therm-path will be set back to the default.
    """
    _set_config_variable(folder_path, 'therm_path')


@set_config.command('lbnl-data-path')
@click.argument('folder-path', required=False, type=click.Path(
    exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def lbnl_data_path(folder_path):
    """Set the lbnl-data-path configuration variable.

    \b
    Args:
        folder_path: Path to a folder to be set as the lbnl-data-path.
            If unspecified, the lbnl-data-path will be set back to the default.
    """
    _set_config_variable(folder_path, 'lbnl_data_path')


@set_config.command('therm-lib-path')
@click.argument('folder-path', required=False, type=click.Path(
    exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def therm_lib_path(folder_path):
    """Set the therm-lib-path configuration variable.

    \b
    Args:
        folder_path: Path to a folder to be set as the therm-lib-path.
            If unspecified, the therm-lib-path will be set back to the default.
    """
    _set_config_variable(folder_path, 'therm_lib_path')


def _set_config_variable(folder_path, variable_name):
    var_cli_name = variable_name.replace('_', '-')
    try:
        config_file = folders.config_file
        with open(config_file) as inf:
            data = json.load(inf)
        data[variable_name] = folder_path if folder_path is not None else ''
        with open(config_file, 'w') as fp:
            json.dump(data, fp, indent=4)
        msg_end = 'reset to default' if folder_path is None \
            else 'set to: {}'.format(folder_path)
        print('{} successfully {}.'.format(var_cli_name, msg_end))
    except Exception as e:
        _logger.exception('Failed to set {}.\n{}'.format(var_cli_name, e))
        sys.exit(1)
    else:
        sys.exit(0)
