"""Verify the installed build identity without consulting Git or environment."""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from types import BuiltinFunctionType

from .errors import SolveError


_IDENTITY_FIELDS = frozenset((
    'schema_version', 'source_commit', 'kernel_commit',
    'source_closure_sha256', 'python_sha256'))
_PACKAGE_FIELDS = frozenset(('schema_version', 'identity', 'native_sha256'))


def _require(condition, message):
    """Reject missing or inconsistent provenance even under optimized Python."""
    if not condition:
        raise ValueError(message)


def _object(pairs, context='_build_source.json'):
    """Do not allow a duplicate JSON key to hide a conflicting identity."""
    result = {}
    for key, value in pairs:
        _require(key not in result,
                 'duplicate metadata key in {}: {}; received {!r}'.format(
                     context, key, value))
        result[key] = value
    return result


def _digest(value, width, field):
    _require(isinstance(value, str) and
             re.fullmatch('[0-9a-f]{' + str(width) + '}', value) is not None and
             value != '0' * width,
             '{} must be a known fixed digest: received {!r}; expected {} '
             'lowercase hex characters; all-zero digest is forbidden'.format(
                 field, value, width))


def _identity(value, context='compiled native identity'):
    _require(isinstance(value, dict) and set(value) == _IDENTITY_FIELDS,
             'unknown native identity structure in {}: received {!r}; '
             'required fields {!r}; missing fields {!r}'.format(
                 context, value, sorted(_IDENTITY_FIELDS),
                 sorted(_IDENTITY_FIELDS - value.keys())
                 if isinstance(value, dict) else sorted(_IDENTITY_FIELDS)))
    _require(type(value['schema_version']) is int and value['schema_version'] == 1,
             'unsupported native identity schema in {}: received {!r}; '
             'expected 1'.format(context, value['schema_version']))
    _digest(value['source_commit'], 40, context + ': source_commit')
    _digest(value['kernel_commit'], 40, context + ': kernel_commit')
    _digest(value['source_closure_sha256'], 64,
            context + ': source_closure_sha256')
    sources = value['python_sha256']
    _require(isinstance(sources, dict) and
             {'run.py', '_build_source.py', '__init__.py'}.issubset(sources),
             'the Python source manifest is incomplete in {}: received {!r}; '
             'required run.py, _build_source.py, __init__.py'.format(
                 context, sources))
    for name, expected in sources.items():
        _require(isinstance(name, str),
                 'invalid Python source path in {}: received {!r}'.format(
                     context, name))
        path = PurePosixPath(name)
        _require(not path.is_absolute() and path.as_posix() == name and
                  '\\' not in name and ':' not in name and
                  all(part not in ('.', '..') for part in path.parts) and
                  path.suffix == '.py',
                  'unsafe Python source path in {}: received {!r}'.format(
                      context, name))
        _digest(expected, 64, context + ': python_sha256/' + name)
    return value


def verified_kernel_commit():
    """Return the compiled kernel pin only after checking installed bytes.

    The package record is generated after compiling this extension. The
    private native getter is compiled from the same verified source closure.
    Neither a package version nor a caller-supplied commit substitutes for
    these two records and their corresponding installed file hashes.
    """
    try:
        from . import _native

        package = Path(__file__).resolve().parent
        metadata_path = package / '_build_source.json'
        metadata_text = metadata_path.read_text(encoding='utf-8')
        try:
            metadata = json.loads(metadata_text,
                                  object_pairs_hook=lambda pairs: _object(
                                      pairs, str(metadata_path)))
        except json.JSONDecodeError as error:
            raise json.JSONDecodeError(
                'Invalid package metadata JSON in {}: received {!r}; '
                'reason: {}'.format(metadata_path, metadata_text, error),
                metadata_text, error.pos) from error
        _require(isinstance(metadata, dict) and set(metadata) == _PACKAGE_FIELDS,
                 'unknown package build metadata structure in {}: received {!r}; '
                 'required fields {!r}; missing fields {!r}'.format(
                     metadata_path, metadata, sorted(_PACKAGE_FIELDS),
                     sorted(_PACKAGE_FIELDS - metadata.keys())
                     if isinstance(metadata, dict) else sorted(_PACKAGE_FIELDS)))
        _require(type(metadata['schema_version']) is int and
                 metadata['schema_version'] == 1,
                 'unsupported package metadata schema in {}: received {!r}; '
                 'expected 1'.format(metadata_path, metadata['schema_version']))
        recorded = _identity(metadata['identity'], str(metadata_path) + ': identity')
        _digest(metadata['native_sha256'], 64,
                str(metadata_path) + ': native_sha256')
        getter = getattr(_native, '_build_source_identity', None)
        _require(isinstance(getter, BuiltinFunctionType) and
                  getter.__module__ == _native.__name__ and
                  getter.__name__ == '_build_source_identity',
                  'the compiled native build identity is missing or replaced '
                  'for {}: received {!r}'.format(_native.__file__, getter))
        encoded = getter()
        _require(isinstance(encoded, str),
                 'the native build identity is not text in {}: received {!r}'.format(
                     _native.__file__, encoded))
        native_context = 'compiled native identity: ' + str(_native.__file__)
        try:
            native_identity = json.loads(
                encoded, object_pairs_hook=lambda pairs: _object(
                    pairs, native_context))
        except json.JSONDecodeError as error:
            raise json.JSONDecodeError(
                'Invalid native identity JSON in {}: received {!r}; '
                'reason: {}'.format(native_context, encoded, error),
                encoded, error.pos) from error
        compiled = _identity(native_identity, native_context)
        mismatch = next((field for field in recorded
                         if compiled[field] != recorded[field]), None)
        missing_side = ''
        if mismatch == 'python_sha256':
            mismatch = next((name for name in sorted(
                             recorded['python_sha256'].keys() |
                             compiled['python_sha256'].keys())
                             if compiled['python_sha256'].get(name) !=
                             recorded['python_sha256'].get(name)),
                            'python_sha256')
            recorded_sources = recorded['python_sha256']
            compiled_sources = compiled['python_sha256']
            if mismatch not in recorded_sources:
                missing_side = 'recorded missing key {!r}; '.format(mismatch)
                received = recorded_sources
                actual_value = compiled_sources[mismatch]
            elif mismatch not in compiled_sources:
                missing_side = 'compiled missing key {!r}; '.format(mismatch)
                received = recorded_sources[mismatch]
                actual_value = compiled_sources
            else:
                received = recorded_sources[mismatch]
                actual_value = compiled_sources[mismatch]
        else:
            received = recorded[mismatch] if mismatch is not None else recorded
            actual_value = compiled[mismatch] if mismatch is not None else compiled
        _require(compiled == recorded,
                 'native and package build identities differ in {}: {}: {}'
                 'received {!r}; compiled {!r}'.format(
                     metadata_path, mismatch, missing_side, received, actual_value))
        native = Path(_native.__file__).resolve()
        _require(native.parent == package,
                 'native extension is outside the package: received {!r}; '
                 'expected parent {!r}'.format(str(native), str(package)))
        native_actual = sha256(native.read_bytes()).hexdigest()
        _require(native_actual == metadata['native_sha256'],
                 'installed native bytes differ from the build record in {}: '
                 'native_sha256: received {!r}; actual {!r}'.format(
                     native, metadata['native_sha256'], native_actual))
        sources = recorded['python_sha256']
        actual = {path.relative_to(package).as_posix() for path in package.rglob('*.py')
                  if path.is_file()}
        _require(actual == set(sources),
                 'installed Python source manifest differs in {}: received {!r}; '
                 'expected {!r}'.format(package, actual, set(sources)))
        for name, expected in sources.items():
            source = package.joinpath(*PurePosixPath(name).parts).resolve()
            _require(source.is_relative_to(package),
                     'Python source is outside the package: {}: received {!r}'.format(
                         name, str(source)))
            source_actual = sha256(source.read_bytes()).hexdigest()
            _require(source_actual == expected,
                     'installed Python source bytes differ: {}: {}: received {!r}; '
                     'actual {!r}'.format(source, name, expected, source_actual))
        return compiled['kernel_commit']
    except (OSError, ImportError, AttributeError, TypeError, ValueError,
             RuntimeError) as error:
        raise SolveError('Build provenance validation failed: {}'.format(error)) from error
