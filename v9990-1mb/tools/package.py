"""Package verified V9990 Feature Lab sources, ROM and evidence; never tools/BIOS binaries."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
STEM = 'NEON_REVENANT-V9990-FeatureLab-v0.1'
ROM_NAME, ZIP_NAME = STEM + '.rom', STEM + '-complete.zip'
ROM_BYTES = 524288
REPORT_NAMES = (
    'verification-feature-lab-v0.1.json', 'feature-verification.json',
    'repro-verification.json', 'compression-verification.json',
    'baseline-protection-verification.json',
)
OPTIONAL_REPORT_NAMES = ('bridge-verification.json',)
TOOLS = {
    'art_palette.py', 'build.py', 'emu.py',
    'emulator_host.mjs', 'generate_assets.py', 'generate_feature.py', 'generate_world.py',
    'package.py', 'verify_compression.py', 'verify_lab.py', 'verify_repro.py',
    'verify_rom.py', 'world_codec.py',
}
ASSET_BINARIES = {
    'assets/vram.bin', 'assets/feature.bin', 'assets/world/stage-1.bin',
    'assets/world/stage-2.bin', 'assets/world/stage-3.bin',
}
LEGAL = (
    'COPYRIGHT.md', 'DISCLAIMER.md', 'THIRD_PARTY_NOTICES.md',
    'licenses/sdcc-runtime/GPL-2.0.txt', 'licenses/sdcc-runtime/OBJECT_VERIFICATION.json',
    'licenses/sdcc-runtime/PROVENANCE.json', 'licenses/sdcc-runtime/README.md',
    'licenses/sdcc-runtime/src/divsigned.s', 'licenses/sdcc-runtime/src/divunsigned.s',
    'licenses/sdcc-runtime/src/modunsigned.s', 'licenses/sdcc-runtime/src/mul.s',
)
NOTES = '''# V9990 Feature Lab v0.1 — package notes / 配布物について

本配布物は独立した機能試験版です。無保証で、実機での動作は未検証です。
将来の修正・サポートを保証しません。著作権・利用条件は COPYRIGHT.md、
免責事項は DISCLAIMER.md、第三者コードは THIRD_PARTY_NOTICES.md と
licenses/ を参照してください。公開ソースであることは、プロジェクト全体に
オープンソースライセンスを付与する意味ではありません。

README.md の手順に従い、外部の Python、Pillow、NumPy、SDCC、Pasmo を用意すれば、
このソース一式から素材を再生成し ROM をビルドできます。コンパイラ、
エミュレーター、MSX BIOS は同梱していません。

tools/verify_repro.py は再生成ビルドに加え、開発元の従来版 71 ファイルと
work/baseline-sha256.json を使用する保全検査も行います。この baseline 検査は
開発ワークスペース限定です。元のワークスペースと registry は本 ZIP に含まれず、
このスクリプト全体を ZIP 単体でそのまま実行できるという保証はありません。
素材再生成と ROM ビルドそのものは、同梱 tools/build.py で独立して行えます。

outputs/feature-lab-v0.1/ の画像・GIF は openMSX 上で実際の ROM を動かした
検証時の記録です。特定場面を選ぶための RAM 設定は検証 JSON に明記しています。
assets/ 配下の画像・GIF は素材や生成プレビューであり、native と名の付く
既存プレビューも含めて実行速度や実機動作を証明するものではありません。

This is an independent experimental feature build, supplied without warranty.
Physical hardware has not been tested. Future fixes or support are not promised.
See COPYRIGHT.md, DISCLAIMER.md, THIRD_PARTY_NOTICES.md and licenses/ for the
unchanged project-specific rights and third-party terms. Publishing source does
not grant an open-source license to the project as a whole.

With the external Python/Pillow/NumPy and SDCC/Pasmo tools described in README.md,
the included sources can regenerate the assets and build the ROM. Compilers,
emulators and machine BIOS files are not bundled.

tools/verify_repro.py also checks 71 original-edition files using the development
workspace's work/baseline-sha256.json. That baseline protection check requires the
original workspace and registry, neither of which is bundled. Its full combined
verification workflow is therefore not standalone; asset regeneration and ROM
building through tools/build.py are standalone with the required external tools.

outputs/feature-lab-v0.1/ contains captures of the ROM running in openMSX. The
verification reports disclose RAM-seeded targeted scenarios. Images and GIFs
under assets/ are generated artwork/previews, including historical files named
native, and do not establish execution speed or physical-hardware compatibility.
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    require(isinstance(value, dict), 'Expected JSON object: ' + str(path))
    return value


def passed_items(report, key, label):
    items = report.get(key)
    require(isinstance(items, list) and bool(items), label + ': missing ' + key)
    require(all(isinstance(item, dict) and item.get('passed') is True for item in items),
            label + ': failing ' + key)
    return items


def validate_evidence(manifest, rom, reports):
    sha = digest(rom)
    require(manifest.get('version') == '0.1', 'Wrong Feature Lab version')
    require(manifest.get('file') == ROM_NAME, 'Wrong ROM filename')
    require(manifest.get('mapper') == 'ASCII8', 'Wrong ROM mapper')
    require(len(rom) == manifest.get('rom_bytes') == ROM_BYTES, 'Expected 512 KiB ROM')
    require(rom[:2] == b'AB', 'Missing cartridge AB header')
    require(manifest.get('sha256') == sha, 'ROM differs from build manifest')
    native, feature, repro, compression, baseline = (reports[name] for name in REPORT_NAMES)
    for name in OPTIONAL_REPORT_NAMES:
        if name in reports:
            require(reports[name].get('passed') is True, 'Optional verification failed: ' + name)
            passed_items(reports[name], 'results', name)
    passed_items(native, 'results', 'Native verification')
    passed_items(feature, 'results', 'Feature verification')
    require(native.get('rom', {}).get('sha256') == sha, 'Native evidence has a different ROM')
    require(feature.get('rom_sha256') == sha, 'Feature evidence has a different ROM')
    for label, report in (('Native', native), ('Feature', feature)):
        require(report.get('physical_hardware_tested') is False,
                label + ': review package hardware-validation wording')
    require(repro.get('passed') is True, 'Reproduction failed')
    require(repro.get('expected_rom_sha256') == sha, 'Reproduction expected a different ROM')
    rebuilt = repro.get('rebuilt_ROM', {})
    require(rebuilt.get('sha256') == sha and rebuilt.get('identical') is True
            and rebuilt.get('bytes') == ROM_BYTES, 'Regenerated ROM is not byte-identical')
    for key in ('live_ROM_unchanged', 'live_inputs_unchanged', 'baseline_71_files_unchanged'):
        require(repro.get(key) is True, 'Reproduction integrity failed: ' + key)
    require(repro.get('errors') == [], 'Reproduction errors remain')
    require(baseline.get('passed') is True and baseline.get('expected_files') == 71,
            'Original-edition baseline protection failed')
    for stage in ('before', 'after'):
        result = baseline.get(stage, {})
        require(result.get('passed') is True, 'Baseline failed: ' + stage)
        entries = passed_items(result, 'entries', 'Baseline ' + stage)
        require(len(entries) == 71, 'Incomplete baseline inventory: ' + stage)
        require(all(item.get('expected_sha256') == item.get('actual_sha256') for item in entries),
                'Baseline hash differs: ' + stage)
    require(compression.get('passed') is True, 'Compression verification failed')
    passed_items(compression, 'tests', 'Compression verification')
    streams = passed_items(compression, 'streams', 'Compression verification')
    expected = [manifest['atlas'], *manifest['worlds'], manifest['feature']]
    require(len(streams) == len(expected) == 5, 'Incomplete compressed stream proof')
    by_name = {stream['name']: stream for stream in streams}
    require(len(by_name) == 5, 'Duplicate compressed stream proof')
    for stream in expected:
        verified = by_name.get(stream['name'], {})
        require(all(verified.get(key) == value for key, value in stream.items() if key != 'stage'),
                'Compression manifest differs: ' + stream['name'])
        offset, size = stream['rom_offset'], stream['compressed_bytes']
        require(32768 <= offset < offset + size <= len(rom), 'Invalid stream extent')
        require(digest(rom[offset:offset + size]) == stream['compressed_sha256'],
                'Compressed bytes differ: ' + stream['name'])
        raw_path = ('assets/vram.bin' if stream['name'] == 'atlas' else
                    'assets/feature.bin' if stream['name'] == 'feature' else
                    'assets/world/stage-' + str(stream['stage']) + '.bin')
        raw = (ROOT / raw_path).read_bytes()
        require(len(raw) == stream['raw_bytes'] and digest(raw) == stream['raw_sha256'],
                'Uncompressed artwork differs: ' + raw_path)
    for key in ('rom_bytes', 'allocated_bytes', 'free_bytes'):
        require(compression.get(key) == manifest.get(key), 'Compression capacity differs: ' + key)
    return sha


def allowed(relative):
    path = PurePosixPath(relative)
    if not path.parts or '\\' in relative or ':' in relative or path.is_absolute() or any(
            part in ('', '.', '..') for part in path.parts):
        return False
    if any(part.lower() in ('work', '.git', '__pycache__', 'systemroms', 'bios',
                            'toolchain', 'node_modules') for part in path.parts):
        return False
    if relative in ('README.md', 'VALIDATION.md', 'requirements.txt', 'LICENSE', *LEGAL):
        return True
    if path.parts[0] == 'src':
        return len(path.parts) == 2 and path.suffix in ('.c', '.h', '.asm')
    if path.parts[0] == 'tools':
        return len(path.parts) == 2 and path.name in TOOLS
    if path.parts[0] == 'assets':
        return path.suffix in ('.png', '.gif', '.json') or relative in ASSET_BINARIES
    if path.parts[0] == 'outputs':
        if len(path.parts) == 2:
            return path.name in (ROM_NAME, 'build-manifest.json', *REPORT_NAMES, *OPTIONAL_REPORT_NAMES)
        return (len(path.parts) == 3 and path.parts[1] == 'feature-lab-v0.1'
                and path.suffix in ('.png', '.gif'))
    return False


def collect_files():
    required = ['README.md', 'requirements.txt', *LEGAL,
                'outputs/' + ROM_NAME, 'outputs/build-manifest.json',
                *('outputs/' + name for name in REPORT_NAMES),
                *('tools/' + name for name in sorted(TOOLS)), *sorted(ASSET_BINARIES)]
    paths = [ROOT / relative for relative in required]
    for optional in ('LICENSE', 'VALIDATION.md'):
        if (ROOT / optional).is_file():
            paths.append(ROOT / optional)
    paths.extend(OUT / name for name in OPTIONAL_REPORT_NAMES if (OUT / name).is_file())
    for directory in ('src', 'assets'):
        paths.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and allowed(path.relative_to(ROOT).as_posix()))
    for extension in ('png', 'gif'):
        captures = sorted((OUT / 'feature-lab-v0.1').glob('*.' + extension))
        require(bool(captures), 'Missing native ' + extension + ' captures')
        paths.extend(captures)
    files = {}
    for path in sorted(set(paths)):
        relative = path.relative_to(ROOT).as_posix()
        require(path.is_file() and not path.is_symlink(), 'Missing/linked file: ' + relative)
        require(path.resolve().is_relative_to(ROOT.resolve()), 'File escapes package root')
        require(allowed(relative), 'File is not allowlisted: ' + relative)
        data = path.read_bytes()
        require(not data.startswith((b'MZ', b'\x7fELF')), 'Executable binary forbidden: ' + relative)
        files[relative] = data
    require(any(name.startswith('src/') for name in files), 'Missing game sources')
    return files


def check_reproduced_sources(files, repro):
    inventory = repro.get('input_inventory')
    require(isinstance(inventory, list) and bool(inventory), 'Missing reproduction inventory')
    entries = {entry['path']: entry for entry in inventory}
    require(len(entries) == len(inventory), 'Duplicate reproduction input')
    selected = {name: data for name, data in files.items()
                if name.split('/')[0] in ('src', 'assets', 'tools')}
    require(set(entries) == set(selected), 'Package inputs differ from reproduction inventory')
    for name, data in selected.items():
        require(entries[name]['sha256'] == digest(data) and entries[name]['bytes'] == len(data),
                'Changed after reproduction; rerun verification: ' + name)


def main():
    manifest = read_json(OUT / 'build-manifest.json')
    report_names = [*REPORT_NAMES, *(name for name in OPTIONAL_REPORT_NAMES if (OUT / name).is_file())]
    reports = {name: read_json(OUT / name) for name in report_names}
    rom = (OUT / ROM_NAME).read_bytes()
    rom_sha = validate_evidence(manifest, rom, reports)
    files = collect_files()
    check_reproduced_sources(files, reports['repro-verification.json'])
    require(json.loads(files['outputs/build-manifest.json']) == manifest,
            'Build manifest changed during packaging')
    require(files['outputs/' + ROM_NAME] == rom, 'ROM changed during packaging')
    for name, report in reports.items():
        require(json.loads(files['outputs/' + name]) == report,
                'Verification report changed during packaging: ' + name)
    generated = {'PACKAGE_NOTES.md': NOTES.encode('utf-8'),
                 'ROM-SHA256SUMS.txt': (rom_sha + '  outputs/' + ROM_NAME + '\n').encode('ascii')}
    payload = {**files, **generated}
    archive, temporary = OUT / ZIP_NAME, OUT / (ZIP_NAME + '.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(STEM + '/' + name, (2026, 9, 8, 0, 0, 0))
            info.compress_type, info.create_system = zipfile.ZIP_DEFLATED, 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data, compresslevel=9)
    members = []
    with zipfile.ZipFile(temporary) as bundle:
        require(bundle.testzip() is None, 'ZIP CRC failed')
        names = bundle.namelist()
        require(len(names) == len(set(names)) == len(payload), 'Duplicate/missing ZIP entries')
        require(set(names) == {STEM + '/' + name for name in payload}, 'ZIP entry set differs')
        for name, expected in sorted(payload.items()):
            require(allowed(name) or name in generated, 'Unsafe ZIP member: ' + name)
            actual = bundle.read(STEM + '/' + name)
            require(actual == expected, 'ZIP content differs: ' + name)
            if name in files:
                require((ROOT / name).read_bytes() == expected, 'Source changed while packaging: ' + name)
            require(not actual.startswith((b'MZ', b'\x7fELF')), 'Executable content in ZIP')
            members.append({'path': name, 'bytes': len(actual), 'sha256': digest(actual),
                            'origin': 'source' if name in files else 'generated package note'})
    temporary.replace(archive)
    zip_data = archive.read_bytes()
    sums = rom_sha + '  ' + ROM_NAME + '\n' + digest(zip_data) + '  ' + ZIP_NAME + '\n'
    (OUT / 'SHA256SUMS.txt').write_text(sums, encoding='ascii', newline='\n')
    report = {
        'passed': True,
        'archive': {'file': ZIP_NAME, 'bytes': len(zip_data), 'sha256': digest(zip_data)},
        'rom': {'file': ROM_NAME, 'bytes': len(rom), 'sha256': rom_sha},
        'entries': len(members), 'source_entries': len(files),
        'checks': {'all_required_evidence_passed': True, 'same_ROM_hash': True,
                   'reproduced_source_inventory_identical': True, 'ZIP_CRC': True,
                   'ZIP_bytes_equal_source_snapshot': True, 'live_sources_unchanged': True,
                   'unique_safe_allowlisted_paths': True,
                   'no_compiler_emulator_BIOS_or_executable_binaries': True},
        'verification_reports': [{'file': name, 'sha256': digest(files['outputs/' + name])}
                                 for name in reports],
        'package_rebuild_executed': False,
        'rebuild_evidence': 'Included repro-verification.json; its input inventory and ROM hash are checked.',
        'baseline_check_scope': 'Development workspace only; original 71 files and registry are not bundled.',
        'physical_hardware_tested': False, 'members': members,
    }
    (OUT / 'package-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('passed', 'archive', 'rom', 'entries')}, indent=2))


if __name__ == '__main__':
    main()
