"""Command-line access to the public THMZ runner."""
import click

from ..errors import THMZError
from ..run import run_thmz


@click.group()
def main():
    """Run premeshed thermal models with HygroThermFEM."""


@main.command('run-thmz')
@click.argument('path', type=click.Path(exists=True, dir_okay=False))
@click.option('--output', type=click.Path(dir_okay=False), default=None,
              help='Result THMZ path. Defaults to <input>_solved.thmz.')
def run_thmz_cli(path, output):
    """Solve PATH and print its result path only after successful publication."""
    try:
        result = run_thmz(path, output=output)
    except (THMZError, ValueError, RuntimeError, OSError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(result)
