"""Generate and finalize build provenance metadata for bundled pyHygroThermFEM-Fairyfly."""

from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess


_NON_INPUT_NAMES = frozenset({
    '.git', '.github', '.pytest_cache', 'build', 'dist', 'doc', 'docs',
    'patches', 'tests', '__pycache__',
})


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('utf-8')


def _git_stdout(repo: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ['git', '-C', str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        return proc.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _iter_source_files(root: Path):
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _NON_INPUT_NAMES for part in rel.parts):
            continue
        if path.suffix in ('.pyc', '.pyo', '.pyd', '.so'):
            continue
        yield rel.as_posix(), path


def _tree_sha1(root: Path) -> str:
    digest = sha1()
    for rel_posix, path in _iter_source_files(root):
        digest.update(rel_posix.encode('utf-8'))
        digest.update(b'\0')
        digest.update(sha256(path.read_bytes()).digest())
    value = digest.hexdigest()
    return value if value != '0' * 40 else '1' + '0' * 39


def _resolve_commits(vendor_root: Path) -> tuple[str, str]:
    source_commit = _git_stdout(vendor_root, 'rev-parse', '--verify', 'HEAD')
    if not source_commit or len(source_commit) != 40:
        source_commit = _tree_sha1(vendor_root)

    kernel_commit = None
    ls_tree = _git_stdout(vendor_root, 'ls-tree', 'HEAD', 'vendor/HygroThermFEM')
    if ls_tree:
        parts = ls_tree.split()
        if len(parts) >= 3 and len(parts[2]) == 40:
            kernel_commit = parts[2]
    if not kernel_commit:
        kernel_commit = _tree_sha1(vendor_root / 'vendor' / 'HygroThermFEM')
    return source_commit, kernel_commit


def python_source_manifest(package_root: Path) -> dict[str, str]:
    """Return sorted relative POSIX paths -> SHA-256 digests for package .py files."""
    manifest: dict[str, str] = {}
    for path in sorted(package_root.rglob('*.py')):
        if path.is_file():
            rel = path.relative_to(package_root).as_posix()
            manifest[rel] = sha256(path.read_bytes()).hexdigest()
    if not {'run.py', '_build_source.py', '__init__.py'}.issubset(manifest):
        raise RuntimeError(
            f'Incomplete pyhygrothermfem_fairyfly Python sources in {package_root}'
        )
    return manifest


def prepare_identity(repo_root: Path) -> dict[str, object]:
    """Build canonical build identity matching pyhygrothermfem_fairyfly._build_source."""
    repo_root = Path(repo_root).resolve()
    vendor_root = repo_root / 'vendor' / 'pyHygroThermFEM-Fairyfly'
    native_cmake_root = repo_root / 'src' / 'pyhygrothermfem_native'
    package_root = repo_root / 'src' / 'pyhygrothermfem_fairyfly'

    if not vendor_root.is_dir():
        raise RuntimeError(
            f'Missing vendored pyHygroThermFEM-Fairyfly submodule at {vendor_root}. '
            'Run `git submodule update --init --recursive`.'
        )

    python_sha256 = python_source_manifest(package_root)
    source_commit, kernel_commit = _resolve_commits(vendor_root)

    closure_inputs: list[tuple[str, str]] = []
    for rel_posix, path in _iter_source_files(vendor_root / 'bindings'):
        closure_inputs.append((f'bindings/{rel_posix}', sha256(path.read_bytes()).hexdigest()))
    for sub in ('HygroThermFEM', 'KeffCavity', 'LBNLCPPCommon', 'Windows-CalcEngine', 'eigen'):
        subdir = vendor_root / 'vendor' / sub
        if not subdir.is_dir():
            raise RuntimeError(
                f'Missing vendored C++ dependency {subdir}. '
                'Run `git submodule update --init --recursive`.'
            )
        for rel_posix, path in _iter_source_files(subdir):
            closure_inputs.append((f'vendor/{sub}/{rel_posix}', sha256(path.read_bytes()).hexdigest()))
    for name in ('CMakeLists.txt', 'build_identity.py'):
        p = native_cmake_root / name
        closure_inputs.append((f'native/{name}', sha256(p.read_bytes()).hexdigest()))
    for rel_posix, digest in sorted(python_sha256.items()):
        closure_inputs.append((f'python/{rel_posix}', digest))

    source_closure_sha256 = sha256(_canonical(sorted(closure_inputs))).hexdigest()
    return {
        'schema_version': 1,
        'source_commit': source_commit,
        'kernel_commit': kernel_commit,
        'source_closure_sha256': source_closure_sha256,
        'python_sha256': python_sha256,
    }


def configure_header(repo_root: Path, header_path: Path, identity_path: Path) -> None:
    """Write build_source.hxx and build-source-identity.json for CMake compilation."""
    identity = prepare_identity(repo_root)
    encoded = _canonical(identity)
    literal = json.dumps(encoded.decode('utf-8'), ensure_ascii=True)
    header_text = (
        '// Generated by build_identity.py; do not edit.\n'
        '#pragma once\n\n'
        'namespace pyhygrotherm\n'
        '{\n'
        f'inline constexpr char kBuildSourceIdentity[] =\n    {literal};\n'
        '}\n'
    )
    header_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.write_text(header_text, encoding='utf-8')
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_bytes(encoded + b'\n')


def finalize_package(output_dir: Path, identity_path: Path, native_path: Path) -> dict[str, object]:
    """Write _build_source.json beside the compiled _native extension."""
    output_dir = Path(output_dir).resolve()
    native_path = Path(native_path).resolve()
    if (
        native_path.parent != output_dir
        or not native_path.is_file()
        or not native_path.name.startswith('_native')
        or native_path.suffix not in ('.pyd', '.so')
    ):
        raise RuntimeError(f'Missing or misplaced compiled native extension: {native_path}')
    identity = json.loads(Path(identity_path).read_text(encoding='utf-8'))
    metadata = {
        'schema_version': 1,
        'identity': identity,
        'native_sha256': sha256(native_path.read_bytes()).hexdigest(),
    }
    (output_dir / '_build_source.json').write_bytes(_canonical(metadata) + b'\n')
    return metadata


def main() -> None:
    """CLI entrypoint invoked by CMake during configure."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    cfg = sub.add_parser('configure')
    cfg.add_argument('--root', type=Path, required=True)
    cfg.add_argument('--header', type=Path, required=True)
    cfg.add_argument('--identity-file', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'configure':
        configure_header(args.root, args.header, args.identity_file)


if __name__ == '__main__':
    main()
