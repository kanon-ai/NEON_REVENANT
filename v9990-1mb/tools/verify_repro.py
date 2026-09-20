"""Rebuild Feature Lab in an isolated directory and protect the old project.

Requires a completed current build. No emulator is used. The original 71-file
registry is checked before and after the isolated full artwork regeneration.
SDCC/Pasmo remain external; their executables are never copied into the run.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
ROM_NAME = 'NEON_REVENANT-V9990-FeatureLab-v0.1.rom'
GENERATED_INPUTS = ('assets/vram.bin', 'assets/feature.bin',
                    'assets/world/stage-1.bin', 'assets/world/stage-2.bin',
                    'assets/world/stage-3.bin', 'src/assets.h', 'src/palette.h',
                    'src/feature_assets.h', 'src/world_data.h')


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def checked_child(root, relative):
    key = PurePosixPath(relative.replace('\\', '/'))
    if key.is_absolute() or '..' in key.parts:
        raise ValueError('Unsafe relative path: '+relative)
    result = root.joinpath(*key.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes the specified root: '+relative)
    return result


def baseline_check(root, registry):
    results = []
    for relative, expected in sorted(registry.items()):
        path = checked_child(root, relative)
        actual = sha_file(path) if path.is_file() else None
        results.append(dict(path=relative.replace('\\', '/'), expected_sha256=expected,
                            actual_sha256=actual, passed=actual == expected))
    return dict(passed=len(results) == 71 and all(item['passed'] for item in results),
                files=len(results), entries=results)


def input_inventory(root):
    entries = []
    for directory in ('src', 'assets', 'tools'):
        for path in sorted((root/directory).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix.lower() in ('.pyc', '.pyo'):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Input symlinks are not copied: '+str(path))
            if path.suffix.lower() in ('.exe', '.dll'):
                raise ValueError('Tool binaries must remain external: '+str(path))
            entries.append(dict(path=path.relative_to(root).as_posix(), bytes=path.stat().st_size,
                                sha256=sha_file(path)))
    return entries


def inventory_hash(entries):
    text = ''.join(entry['path']+' '+entry['sha256']+'\n' for entry in entries)
    return hashlib.sha256(text.encode()).hexdigest()


def executable(value, fallback):
    candidate = value or fallback
    path = Path(candidate)
    resolved = path.resolve() if path.is_file() else Path(shutil.which(str(candidate)) or '')
    if not resolved.is_file():
        raise FileNotFoundError('Configure external compiler: '+str(candidate))
    return resolved.resolve()


def build_environment():
    env = dict(os.environ)
    local = ROOT/'work/toolchain/sdcc/bin'
    parent = ROOT.parent/'work/toolchain/sdcc/bin'
    bindir = Path(env.get('SDCC_BIN', str(local if local.exists() else parent)))
    default_sdcc = str(bindir/'sdcc.exe') if (bindir/'sdcc.exe').is_file() else 'sdcc'
    sdcc = executable(env.get('SDCC'), default_sdcc)
    pasmo = executable(env.get('PASMO'), shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe')
    env.update(SDCC=str(sdcc), SDCC_BIN=str(sdcc.parent), PASMO=str(pasmo), PYTHONDONTWRITEBYTECODE='1')
    env['PATH'] = str(sdcc.parent)+os.pathsep+env.get('PATH', '')
    return env, dict(sdcc=dict(file=sdcc.name, sha256=sha_file(sdcc)),
                     pasmo=dict(file=pasmo.name, sha256=sha_file(pasmo)),
                     python=sys.version.split()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path, default=ROOT.parent)
    parser.add_argument('--baseline-registry', type=Path, default=ROOT/'work/baseline-sha256.json')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--work', type=Path, default=ROOT/'work/repro')
    parser.add_argument('--report', type=Path, default=ROOT/'outputs/repro-verification.json')
    parser.add_argument('--baseline-report', type=Path, default=ROOT/'outputs/baseline-protection-verification.json')
    args = parser.parse_args()
    registry_data = args.baseline_registry.read_bytes()
    registry = json.loads(registry_data)
    assert isinstance(registry, dict) and len(registry) == 71, 'Expected the original 71-file registry'
    expected_manifest = json.loads((ROOT/'outputs/build-manifest.json').read_text())
    expected_rom = ROOT/'outputs'/ROM_NAME
    expected_hash = sha_file(expected_rom)
    assert expected_manifest['file'] == ROM_NAME and expected_manifest['sha256'] == expected_hash
    assert expected_rom.stat().st_size == 524288
    original_inputs = input_inventory(ROOT)
    baseline_before = baseline_check(args.baseline_root, registry)
    baseline_report = dict(passed=False, baseline_registry_sha256=hashlib.sha256(registry_data).hexdigest(),
                           expected_files=71, before=baseline_before, after=None)
    json_write(args.baseline_report, baseline_report)
    assert baseline_before['passed'], 'Original project already differs from its baseline; see baseline report'
    env, toolchain = build_environment()
    args.work.mkdir(parents=True, exist_ok=True)
    work_root = args.work.resolve()
    isolated = Path(tempfile.mkdtemp(prefix='full-', dir=work_root)).resolve()
    assert isolated.is_relative_to(work_root) and isolated != work_root
    # The retained run directory is useful if a generator or compiler fails.
    # It contains source/assets/logs only, and is never a distributable bundle.
    report = dict(passed=False, expected_rom_sha256=expected_hash, expected_rom_bytes=524288,
                  method='Full generate_assets.py + generate_world.py + generate_feature.py + native SDCC/Pasmo build in an isolated source copy; generated ROM-input files are removed first.',
                  native_execution_tested=False, input_files=len(original_inputs),
                  input_inventory_sha256=inventory_hash(original_inputs), input_inventory=original_inputs,
                  isolated_directory=isolated.relative_to(ROOT).as_posix() if isolated.is_relative_to(ROOT) else isolated.name,
                  generated_inputs_removed=list(GENERATED_INPUTS), external_toolchain=toolchain,
                  artifacts_before=dict(rom_sha256=expected_hash), errors=[])
    started = time.monotonic()
    failure = None
    try:
        for entry in original_inputs:
            source = checked_child(ROOT, entry['path'])
            destination = checked_child(isolated, entry['path'])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            assert sha_file(destination) == entry['sha256']
        for relative in GENERATED_INPUTS:
            path = checked_child(isolated, relative)
            if path.exists():
                path.unlink()
        print('Isolated full artwork regeneration and ROM build started.', flush=True)
        log_path = isolated/'full-build.log'
        with log_path.open('w', encoding='utf-8') as log:
            process = subprocess.run([sys.executable, str(isolated/'tools/build.py')], cwd=isolated,
                                     env=env, stdout=log, stderr=subprocess.STDOUT, text=True,
                                     timeout=args.timeout)
        report['build_exit_code'] = process.returncode
        report['build_log'] = log_path.name
        assert process.returncode == 0, 'Isolated build failed; inspect '+str(log_path)
        rebuilt = isolated/'outputs'/ROM_NAME
        rebuilt_manifest = json.loads((isolated/'outputs/build-manifest.json').read_text())
        actual_hash = sha_file(rebuilt)
        assert rebuilt.stat().st_size == 524288
        assert actual_hash == rebuilt_manifest['sha256'] == expected_hash, 'Regenerated ROM differs'
        regenerated_inputs = []
        for relative in GENERATED_INPUTS:
            path = checked_child(isolated, relative)
            assert path.is_file(), 'Full generation did not recreate '+relative
            live = checked_child(ROOT, relative)
            actual, expected = sha_file(path), sha_file(live)
            assert actual == expected, 'Regenerated ROM input differs: '+relative
            regenerated_inputs.append(dict(path=relative, bytes=path.stat().st_size, sha256=actual, passed=True))
        report['regenerated_inputs'] = regenerated_inputs
        report['rebuilt_ROM'] = dict(file=ROM_NAME, bytes=rebuilt.stat().st_size, sha256=actual_hash, identical=True)
        report['allocated_bytes'] = rebuilt_manifest['allocated_bytes']
        report['free_bytes'] = rebuilt_manifest['free_bytes']
    except Exception as exception:
        failure = exception
        report['errors'].append(repr(exception))
    finally:
        baseline_after = baseline_check(args.baseline_root, registry)
        baseline_report['after'] = baseline_after
        baseline_report['passed'] = baseline_before['passed'] and baseline_after['passed']
        json_write(args.baseline_report, baseline_report)
        live_inputs = input_inventory(ROOT)
        live_hash = sha_file(expected_rom)
        report['artifacts_after'] = dict(rom_sha256=live_hash,
                                         input_inventory_sha256=inventory_hash(live_inputs))
        report['live_ROM_unchanged'] = live_hash == expected_hash
        report['live_inputs_unchanged'] = live_inputs == original_inputs
        report['baseline_71_files_unchanged'] = baseline_report['passed']
        if not baseline_report['passed']:
            report['errors'].append('Original baseline changed during isolated build')
        if not report['live_ROM_unchanged'] or not report['live_inputs_unchanged']:
            report['errors'].append('Live Feature Lab input or ROM changed during verification')
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['passed'] = not report['errors'] and failure is None
        json_write(args.report, report)
    if failure:
        raise failure
    assert report['passed'], 'Reproduction/preservation failed; inspect verification reports'
    print(json.dumps({key: report[key] for key in ('passed', 'rebuilt_ROM', 'allocated_bytes', 'free_bytes',
                     'input_files', 'live_ROM_unchanged', 'live_inputs_unchanged',
                     'baseline_71_files_unchanged', 'elapsed_seconds')}, indent=2))


if __name__ == '__main__':
    main()
