# coding=utf-8
"""Run Fairyfly THMZ files through the isolated pyHygroTherm CLI."""
from __future__ import division, unicode_literals

import os
import io
import gc
import json
import hashlib
import math
import subprocess
import sys
import tempfile
import threading
import zipfile
import xml.etree.ElementTree as ET

from fairyfly.typing import clean_string
from fairyfly.config import folders as ff_folders
from fairyfly.model import Model
from .writer import model_to_thmz, _replace, _unlink
from .simulation.parameter import SimulationParameter


_PYHYGROTHERM_CHECK = '''
import sys
if sys.implementation.name != 'cpython' or not ((3, 11) <= sys.version_info[:2] < (3, 16)):
    raise SystemExit('Expected CPython 3.11-3.15.')
import importlib.metadata as metadata
from pathlib import Path
import pyhygrothermfem_fairyfly
module = Path(pyhygrothermfem_fairyfly.__file__).resolve()
installed = Path(metadata.distribution('pyHygroThermFEM-Fairyfly').locate_file(
    'pyhygrothermfem_fairyfly/__init__.py')).resolve()
prefix = Path(sys.prefix).resolve()
if sys.prefix == sys.base_prefix or not module.is_relative_to(prefix):
    raise SystemExit('Expected pyhygrothermfem_fairyfly installed in an isolated venv.')
if module != installed:
    raise SystemExit('Imported pyhygrothermfem_fairyfly does not match its installed distribution.')
print('Interpreter: CPython {}'.format(sys.version.split()[0]))
print('Executable: {}'.format(Path(sys.executable).resolve()))
print('pyHygroThermFEM-Fairyfly {}: {}'.format(
    metadata.version('pyHygroThermFEM-Fairyfly'), module))
'''


def _run_process(command, hide_console, timeout=3600):
    """Run a command and return its exit code and decoded output."""
    options = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}
    if hide_console and os.name == 'nt':
        options['creationflags'] = getattr(
            subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    process = subprocess.Popen(command, **options)
    if sys.version_info[0] < 3:
        output = []
        worker = threading.Thread(
            target=lambda: output.append(process.communicate()))
        worker.daemon = True
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            process.kill()
            worker.join()
            raise RuntimeError('timed out after {} seconds'.format(timeout))
        stdout, stderr = output[0]
    else:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('timed out after {} seconds'.format(timeout))
    return process.returncode, _decode(stdout), _decode(stderr)


def _decode(output):
    """Decode the UTF-8 output emitted by the isolated CPython process."""
    try:
        return output.decode('utf-8', 'replace')
    except AttributeError:
        return output


def _show_output(stream, output):
    """Write subprocess output on Python 2 hosts with a non-UTF-8 console."""
    if not output:
        return
    try:
        stream.write(output)
    except UnicodeEncodeError:
        stream.write(output.encode(getattr(stream, 'encoding', None) or 'utf-8',
                                   'replace'))


def _csv_rows(stream):
    """Yield (time, values) rows of a transient CSV member, skipping blanks."""
    text = stream.read()
    if not isinstance(text, str):
        text = text.decode('utf-8-sig')
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError('Result THMZ transient series is empty.')
    header = [cell.strip() for cell in lines[0].split(',')]
    if not header[0].lower().startswith('time'):
        raise ValueError('Result THMZ transient series lacks a time column.')
    yield None, len(header) - 1
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split(',')]
        yield cells, len(header)


def _verify_transient_result(archive, mesh, model):
    """Check the ``transient results/`` member set of a solved THMZ."""
    engine = model.find('Properties/CalculationOptions/EngineParameters')
    try:
        num_steps = int(float(engine.findtext('NumberOfTimesteps')))
    except (AttributeError, TypeError, ValueError):
        raise ValueError('Result THMZ is missing timestep count metadata.')
    nodes = mesh.findall('Case/Nodes/Node')
    if not nodes:
        raise ValueError('Result THMZ is missing mesh nodes.')
    node_count = len(nodes)
    # Exterior edges are the edges used by exactly one Q4 element.
    edge_count = {}
    for element in mesh.findall('Case/Elements/Element'):
        corners = [int(element.findtext(tag))
                   for tag in ('node1', 'node2', 'node3', 'node4')]
        for index in range(4):
            edge = tuple(sorted((corners[index],
                                 corners[(index + 1) % 4])))
            edge_count[edge] = edge_count.get(edge, 0) + 1
    exterior_count = sum(1 for count in edge_count.values() if count == 1)
    members = {
        'transient results/Geometry.xml': None,
        'transient results/Temperatures.csv': node_count,
        'transient results/Humidities.csv': node_count,
        'transient results/HeatFlux.csv': node_count,
        'transient results/HeatFluxEdges.csv': exterior_count,
        'transient results/WaterContent.csv': node_count,
        'transient results/WaterFlux.csv': node_count,
        'transient results/WaterFluxEdges.csv': exterior_count,
    }
    for member, width in members.items():
        if width is None:
            try:
                geometry = ET.fromstring(archive.read(member))
            except KeyError:
                raise ValueError('Result THMZ is missing {}.'.format(member))
            if len(geometry.findall('Nodes/Node')) != node_count:
                raise ValueError('Result THMZ transient geometry is '
                                 'incomplete.')
            continue
        try:
            stream = archive.open(member)
        except KeyError:
            raise ValueError('Result THMZ is missing {}.'.format(member))
        with stream:
            rows = 0
            previous = -float('inf')
            for record, columns in _csv_rows(stream):
                if record is None:
                    if columns != width:
                        raise ValueError('Result THMZ {} has wrong column '
                                         'count.'.format(member))
                    continue
                if len(record) != columns:
                    raise ValueError('Result THMZ {} has a ragged row.'
                                     .format(member))
                try:
                    time = float(record[0])
                    [float(cell) for cell in record[1:]]
                except ValueError:
                    raise ValueError('Result THMZ {} has non-numeric data.'
                                     .format(member))
                if math.isnan(time) or math.isinf(time) or time < previous:
                    raise ValueError('Result THMZ {} times are not '
                                     'non-decreasing.'.format(member))
                previous = time
                rows += 1
        if rows != num_steps + 1:
            raise ValueError('Result THMZ {} has {} data rows, expected {}.'
                             .format(member, rows, num_steps + 1))


def _verify_result(path, input_digest, expected_tags):
    """Check that a child process published complete results for this input."""
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Result THMZ has a CRC error.')
            provenance = json.loads(archive.read('pyHygroTherm.json'))
            if provenance.get('input_sha256') != input_digest:
                raise ValueError('Result THMZ does not match this input.')
            mesh = ET.fromstring(archive.read('Mesh.xml'))
            model = ET.fromstring(archive.read('Model.xml'))
            mode = model.findtext(
                'Properties/CalculationOptions/CalculationMode')
            if mode == 'Transient':
                _verify_transient_result(archive, mesh, model)
                return
            results = ET.fromstring(archive.read('SteadyStateMeshResults.xml'))
            steady = ET.fromstring(archive.read('SteadyStateResults.xml'))
            steady_cases = steady.findall('Case')
            if len(steady_cases) != 1:
                raise ValueError(
                    'Result THMZ has incomplete U-factor results.')
            steady_case = steady_cases[0]
            if steady_case.findtext('ModelType') != 'U-factor':
                raise ValueError(
                    'Result THMZ has incomplete U-factor results.')
            actual_tags = [item.findtext('Tag')
                           for item in steady_case.findall('U-factors')]
            if (len(actual_tags) != len(expected_tags) or
                    set(actual_tags) != expected_tags):
                raise ValueError(
                    'Result THMZ has incomplete U-factor results.')
            from .result import UFactor
            supported_projections = (
                'Total Length', 'Projected X', 'Projected Y',
                'Projected in glass plane', 'Custom Rotation')
            for factor in steady_case.findall('U-factors'):
                try:
                    parsed = UFactor(factor)
                except (AttributeError, TypeError, ValueError):
                    raise ValueError(
                        'Result THMZ has incomplete U-factor results.')
                if (math.isnan(parsed.delta_temperature) or
                        math.isinf(parsed.delta_temperature) or
                        math.isnan(parsed.heat_flux) or
                        math.isinf(parsed.heat_flux)):
                    raise ValueError(
                        'Result THMZ has incomplete U-factor results.')
                projection_types = set()
                for projection in factor.findall('Projection'):
                    projection_type = projection.findtext('Length-type')
                    if (projection_type not in supported_projections or
                            projection_type in projection_types):
                        raise ValueError(
                            'Result THMZ has incomplete U-factor results.')
                    projection_types.add(projection_type)
                    try:
                        length = float(projection.findtext('Length'))
                    except (TypeError, ValueError):
                        raise ValueError(
                            'Result THMZ has incomplete U-factor results.')
                    if (math.isnan(length) or math.isinf(length) or
                            length < 0):
                        raise ValueError(
                            'Result THMZ has incomplete U-factor results.')
                    u_factor = projection.findtext('U-factor')
                    if u_factor is None:
                        if parsed.delta_temperature != 0 and length > 0:
                            raise ValueError(
                                'Result THMZ has incomplete U-factor results.')
                    else:
                        try:
                            u_factor = float(u_factor)
                        except (TypeError, ValueError):
                            raise ValueError(
                                'Result THMZ has incomplete U-factor results.')
                        if math.isnan(u_factor) or math.isinf(u_factor):
                            raise ValueError(
                                'Result THMZ has incomplete U-factor results.')
                if 'Total Length' not in projection_types:
                    raise ValueError(
                        'Result THMZ has incomplete U-factor results.')
            nodes = mesh.findall('Case/Nodes/Node')
            solved = results.findall('Case/Nodes/Node')
            if not nodes or len(nodes) != len(solved):
                raise ValueError('Result THMZ has incomplete node results.')
            for node, result in zip(nodes, solved):
                if node.findtext('index') != result.findtext('Index'):
                    raise ValueError('Result THMZ node labels changed.')
                for field in ('Temperature', 'X-flux', 'Y-flux'):
                    value = float(result.findtext(field))
                    if math.isnan(value) or math.isinf(value):
                        raise ValueError('Result THMZ has nonfinite {}.'.format(
                            field))
    except (OSError, zipfile.BadZipfile, KeyError, ET.ParseError,
            TypeError) as error:
        raise ValueError('Result THMZ is incomplete: {}.'.format(error))


def run_model(model, directory=None, silent=False, simulation_par=None):
    """Mesh and run a Fairyfly-Next Model through pyHygroTherm.

    Args:
        model: Fairyfly-Next Model to write and run.
        directory: Output directory. Defaults to the Fairyfly-Next simulation folder.
        silent: Suppress solver output and its console window.
        simulation_par: Fairyfly-Next THERM simulation parameters. Default: None.

    Returns:
        The path to the model THMZ with results.

    Raises:
        ValueError: The model, mesh, solver, or error target fails.
        IOError: The THMZ cannot be written or atomically published.

    Notes:
        Model meshing uses Rhino's native mesh API. Direct THMZ solving via
        ``run_thmz`` does not require Rhino.
    """
    assert isinstance(model, Model), \
        'Expected Fairyfly-Next Model. Got {}.'.format(type(model))
    model_name = clean_string(model.display_name)
    if directory is None:
        directory = os.path.join(ff_folders.default_simulation_folder, model_name)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    thmz_file = os.path.join(directory, '{}.thmz'.format(model_name))
    sim_par = simulation_par if simulation_par is not None else SimulationParameter()
    control = sim_par.mesh
    target = control.parameter
    attempts = control.max_iterations if control.run_error_estimator else 1
    fd, staged = tempfile.mkstemp(prefix='.' + model_name + '-',
                                  suffix='.thmz', dir=directory)
    os.close(fd)
    _unlink(staged)
    try:
        for attempt in range(1, attempts + 1):
            settings = sim_par.duplicate()
            settings.mesh.parameter = target
            model_to_thmz(model, staged, settings, rhino_mesh=True,
                          model_path=thmz_file)
            run_thmz(staged, silent)
            if not control.run_error_estimator:
                _replace(staged, thmz_file)
                return thmz_file
            with zipfile.ZipFile(staged) as archive:
                result = json.loads(archive.read('pyHygroTherm.json'))
            if sys.version_info[0] < 3:
                # IronPython can retain a ZIP file handle until collection.
                gc.collect()
            error = result.get('energy_error_percent')
            if error is None or not 0 <= error <= 100:
                raise ValueError('Energy error estimation did not produce a '
                                 'valid result.')
            print('Rhino mesh pass {}/{}: TargetQuadCount={}, energy error='
                  '{:.4g}% (limit {}%).'.format(
                      attempt, attempts, target, error,
                      control.max_error_percent))
            if error <= control.max_error_percent:
                _replace(staged, thmz_file)
                return thmz_file
            # ponytail: global x4 refinement; use native local guides if cost matters.
            target *= 4
        raise ValueError('Energy error {:.4g}% exceeds {}% after {} Rhino mesh '
                         'passes; no accuracy claim is available.'.format(
                             error, control.max_error_percent, attempts))
    finally:
        if os.path.exists(staged):
            _unlink(staged)


def run_thmz(thmz_file, silent=False):
    """Solve a THMZ in place with pyHygroThermFEM-Fairyfly (in-process or external venv).

    Args:
        thmz_file: Path to a premeshed THMZ file.
        silent: Suppress solver output and its console window.

    Returns:
        The absolute path to the input THMZ with solver results.

    Raises:
        ValueError: The input THMZ is invalid, the interpreter is invalid,
            the solver fails, or it does not publish complete results at the
            requested path.
        OSError: The THMZ or solver log cannot be accessed.

    Environment:
        ``PYHYGROTHERMFEM_FAIRYFLY_PYTHON`` (or ``PYHYGROTHERM_PYTHON``) may
        optionally point to an external isolated CPython venv; when unset,
        the bundled ``pyhygrothermfem_fairyfly`` package runs in-process.
        ``PYHYGROTHERMFEM_FAIRYFLY_TIMEOUT_SECONDS`` (or
        ``PYHYGROTHERM_TIMEOUT_SECONDS``) sets the external subprocess deadline
        (default 3600).
    """
    thmz_file = os.path.abspath(thmz_file)
    if not os.path.isfile(thmz_file):
        raise ValueError('No THMZ file found at {}.'.format(thmz_file))
    if os.path.splitext(thmz_file)[1].lower() != '.thmz':
        raise ValueError('Expected a .thmz file. Got {}.'.format(thmz_file))

    python = (os.environ.get('PYHYGROTHERMFEM_FAIRYFLY_PYTHON')
              or os.environ.get('PYHYGROTHERM_PYTHON'))
    timeout = None
    if python:
        python = os.path.abspath(os.path.expanduser(python))
        if not os.path.isfile(python):
            raise ValueError(
                'PYHYGROTHERMFEM_FAIRYFLY_PYTHON does not point to a file: {}'.format(python))
        try:
            timeout_raw = (os.environ.get('PYHYGROTHERMFEM_FAIRYFLY_TIMEOUT_SECONDS')
                           or os.environ.get('PYHYGROTHERM_TIMEOUT_SECONDS', '3600'))
            timeout = float(timeout_raw)
        except ValueError:
            raise ValueError('PYHYGROTHERMFEM_FAIRYFLY_TIMEOUT_SECONDS must be positive.')
        if math.isnan(timeout) or math.isinf(timeout) or timeout <= 0:
            raise ValueError('PYHYGROTHERMFEM_FAIRYFLY_TIMEOUT_SECONDS must be positive.')

    with open(thmz_file, 'rb') as source:
        input_digest = hashlib.sha256(source.read()).hexdigest()
    try:
        with zipfile.ZipFile(thmz_file) as source:
            model = ET.fromstring(source.read('Model.xml'))
    except (OSError, zipfile.BadZipfile, KeyError, ET.ParseError) as error:
        raise ValueError('Invalid input THMZ {}: {}'.format(thmz_file, error))
    expected_tags = set()
    for boundary in model.findall('Boundaries/Boundary'):
        tag = boundary.findtext('FluxTag')
        if tag:
            expected_tags.add(tag)

    stderr = ''
    log_file = os.path.join(os.path.dirname(thmz_file), 'pyhygrotherm.log')
    with io.open(log_file, 'w', encoding='utf-8') as log:
        if python:
            check_cmd = [python, '-I', '-X', 'utf8', '-c', _PYHYGROTHERM_CHECK]
            try:
                check_code, check_out, check_err = _run_process(
                    check_cmd, True, timeout=30)
            except (OSError, RuntimeError) as error:
                log.write('Interpreter check could not start: {}\n'.format(error))
                raise ValueError(
                    'Could not start the configured pyHygroTherm interpreter. '
                    'See {}. {}'.format(log_file, error))
            log.write('Interpreter check exit code: {}\n'.format(check_code))
            log.write(check_out)
            log.write(check_err)
            if check_code != 0:
                raise ValueError(
                    'PYHYGROTHERMFEM_FAIRYFLY_PYTHON must be an isolated CPython venv '
                    'with the expected pyhygrothermfem_fairyfly package. See {}.\n{}{}'.format(
                        log_file, check_out, check_err))

        fd, result_file = tempfile.mkstemp(
            prefix='.pyhygrotherm-', suffix='.thmz',
            dir=os.path.dirname(thmz_file))
        os.close(fd)
        _unlink(result_file)
        try:
            if python:
                command = [python, '-I', '-X', 'utf8', '-m', 'pyhygrothermfem_fairyfly',
                           'run-thmz', thmz_file, '--output', result_file]
                try:
                    code, stdout, stderr = _run_process(command, silent,
                                                        timeout=timeout)
                except (OSError, RuntimeError) as error:
                    log.write('Solver process failed: {}\n'.format(error))
                    raise ValueError('pyHygroTherm process failed. See {}. '
                                     '{}'.format(log_file, error))
                log.write('Solver exit code: {}\n'.format(code))
                log.write('stdout:\n{}\nstderr:\n{}'.format(stdout, stderr))
                if code != 0:
                    details = stderr.strip() or stdout.strip()
                    raise ValueError('pyHygroTherm failed with exit code {}. '
                                     'See {}.\n{}'.format(code, log_file, details))
                reported = stdout.strip().splitlines()[-1] if stdout.strip() else ''
            else:
                try:
                    from pyhygrothermfem_fairyfly.run import run_thmz as _inprocess_run_thmz
                except ImportError as error:
                    log.write('Bundled pyhygrothermfem_fairyfly import failed: {}\n'.format(error))
                    raise ValueError(
                        'Bundled pyhygrothermfem_fairyfly solver is not available. '
                        'See {}. {}'.format(log_file, error))
                try:
                    reported = _inprocess_run_thmz(thmz_file, output=result_file)
                except Exception as error:
                    log.write('In-process solver failed: {}\n'.format(error))
                    raise ValueError('pyHygroTherm in-process solve failed. '
                                     'See {}. {}'.format(log_file, error))
                log.write('In-process solver exit code: 0\noutput: {}\n'.format(reported))

            if (os.path.normcase(os.path.abspath(reported)) !=
                    os.path.normcase(result_file)):
                raise ValueError('pyHygroTherm did not report its result at '
                                 '{}. See {}.'.format(result_file, log_file))
            _verify_result(result_file, input_digest, expected_tags)
            if sys.version_info[0] < 3:
                # Release ZIP readers before replacing their archive on Windows.
                gc.collect()
            with open(thmz_file, 'rb') as source:
                if hashlib.sha256(source.read()).hexdigest() != input_digest:
                    raise ValueError('Input THMZ changed during solving.')
            _replace(result_file, thmz_file)
        finally:
            if os.path.exists(result_file):
                _unlink(result_file)

    if not silent:
        _show_output(sys.stdout, thmz_file + '\n')
        if stderr:
            _show_output(sys.stderr, stderr)
    return thmz_file
