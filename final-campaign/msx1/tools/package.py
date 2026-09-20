"""Package the verified MSX1 v1.3 ROM, source, notices and native evidence."""
from pathlib import Path
import hashlib, json, re, zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
OUT=BASE/'outputs/msx1/v1.3'
LEGAL=BASE if (BASE/'DISCLAIMER.md').exists() else BASE/'work/github-publication/NEON_REVENANT'
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest=json.loads((OUT/'build-manifest.json').read_text())
rom=(OUT/manifest['file']).read_bytes()
assert len(rom)==524288 and rom[:2]==b'AB' and sha(rom)==manifest['sha256']
for standard in ('ntsc','pal'):
    for name in ('verification.json','world-verification.json','transfer-verification.json','giant-verification.json'):
        report=json.loads((OUT/standard/name).read_text())
        assert report['rom']['sha256']==manifest['sha256']
        assert report['results'] and all(item['passed'] for item in report['results']), (standard,name)
checks={name:json.loads((OUT/name).read_text()) for name in
        ('layout-verification.json','sound-verification.json',
         'giant-preservation-verification.json','reproducibility.json')}
assert all(report['passed'] for report in checks.values())
assert checks['layout-verification.json']['rom_sha256']==manifest['sha256']
assert checks['reproducibility.json']['sha256']==manifest['sha256']
assert checks['sound-verification.json']['source_sha256']==sha((ROOT/'src/sound.c').read_bytes())
preserved=checks['giant-preservation-verification.json']
assert preserved['source_sha256']['current']==sha((ROOT/'src/game.c').read_bytes())
assert preserved['giant_mechanics']['passed']
assert set(preserved['positive_controls'])=={'damage','pause','spawn','final_play'}
for name,digest in preserved['current_dependency_sha256'].items():
    assert (ROOT/'src'/name).is_file() and sha((ROOT/'src'/name).read_bytes())==digest

def portable_json(data):
    """Keep recorded measurements and hashes; remove local-machine paths."""
    def convert(value):
        if isinstance(value,dict):return {k:convert(v) for k,v in value.items()}
        if isinstance(value,list):return [convert(v) for v in value]
        if not isinstance(value,str):return value
        for original,replacement in ((BASE/'work/giant-boss-regression/baseline-game-v1.2.c',
                                      'msx1/tests/baseline-v1.2/baseline-game-v1.2.c'),
                                     (ROOT,'msx1'),(BASE,'.')):
            value=value.replace(str(original),replacement).replace(original.as_posix(),replacement)
        if re.match(r'^[A-Za-z]:[\\/]',value):
            value='${EXTERNAL}/'+value.replace('\\','/').rsplit('/',1)[-1]
        return value
    return (json.dumps(convert(json.loads(data)),indent=2)+'\n').encode('utf-8')

members={}
for directory in ('src','tools','assets'):
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.exe','.dll'):
            members['msx1/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
for name in ('README.md','README-en.md','GIANT_BOSS-v1.3.md','requirements.txt','.gitignore'):
    members['msx1/'+name]=(ROOT/name).read_bytes()
    assert b'NATIVE_RESULTS_PENDING' not in members['msx1/'+name], 'Native validation is not finalized in the documentation'
for p in OUT.rglob('*'):
    if p.is_file() and p.suffix in ('.rom','.json','.png','.gif','.ps1'):
        data=p.read_bytes()
        members[p.relative_to(BASE).as_posix()]=portable_json(data) if p.suffix=='.json' else data
# The retained v1.2 guides link their historical measurements and captures.
# Keep that evidence under its original version directory; no old archive,
# emulator or toolchain executable is included.
for p in (BASE/'outputs/msx1/v1.2').rglob('*'):
    if p.is_file() and p.suffix in ('.json','.png','.gif','.ps1'):
        data=p.read_bytes()
        members[p.relative_to(BASE).as_posix()]=portable_json(data) if p.suffix=='.json' else data
# A small authenticated v1.2 baseline makes the new preservation harness
# reproducible after extraction. No compiler binaries or host trace dumps.
baseline=ROOT/'tests/baseline-v1.2'
for name in ('baseline-game-v1.2.c','baseline-hashes.json'):
    members['msx1/tests/baseline-v1.2/'+name]=(baseline/name).read_bytes()
assert sha(members['msx1/tests/baseline-v1.2/baseline-game-v1.2.c'])==preserved['source_sha256']['baseline']
registry=json.loads(members['msx1/tests/baseline-v1.2/baseline-hashes.json'])
allowed={Path(entry['path']).name for entry in preserved['explicit_versioned_asset_exceptions']}
for entry in registry:
    name=entry['path']
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    if name not in members:
        members[name]=(BASE/name).read_bytes()
    data=members[name]
    if name.startswith('msx1/assets/') and Path(name).name in allowed:
        continue
    assert len(data)==entry['bytes'] and sha(data)==entry['sha256'],name
for name in ('DISCLAIMER.md','COPYRIGHT.md','THIRD_PARTY_NOTICES.md'):
    members[name]=(LEGAL/name).read_bytes()
members['docs/ASTRA_THANK_YOU_EDITION.md']=(LEGAL/'docs/ASTRA_THANK_YOU_EDITION.md').read_bytes()
for p in (LEGAL/'licenses').rglob('*'):
    if p.is_file():members[p.relative_to(LEGAL).as_posix()]=p.read_bytes()
members['README.md']=('''# NEON REVENANT — MSX1 PCG Drive v1.3: Dawn Leviathan

## 夜明けを塞ぐ巨大戦艦 / The giant battleship blocking the dawn

初代MSXの最終区域 DAWN EXODUS に巨大PCGボスを追加しました。左右の砲台を壊し、中央装甲が開いてからコアを攻撃します。船体は左右・上下へ8ドット単位で動き、砲身は2ドット反動、露出コアは明滅します。最初の4区域と最終区域の通常道中はv1.2を維持しています。

The final zone, DAWN EXODUS, now ends with a giant PCG battleship. Destroy both cannon pods, wait for the central armour to open, then attack the core. Its hull moves in 8-pixel steps, barrels recoil by 2 pixels, and the exposed reactor pulses. The first four zones and ordinary play before the final boss retain v1.2 behavior.

**512 KiB ASCII8 ROM; 32 KiB RAM covering 8000h–FFFFh in one RAM slot; 16 KiB VRAM; standard PSG.**

開発途中・無保証の試作版です。実機・実カートリッジ未検証です。
Prototype, provided without warranty. Physical hardware and flash cartridges have not been tested for this version.

- [日本語 / English: v1.3起動・操作・ビルド・検証](msx1/GIANT_BOSS-v1.3.md)
- [Current v1.3 ROM](outputs/msx1/v1.3/NEON_REVENANT-MSX1-v1.3.rom)
- [ASTRAから皆さんへ / A note from ASTRA](docs/ASTRA_THANK_YOU_EDITION.md)
- [Disclaimer](DISCLAIMER.md) / [Copyright](COPYRIGHT.md) / [Third-party notices](THIRD_PARTY_NOTICES.md)

`outputs/msx1/v1.2/`のROMは比較検証用の旧版です。通常プレイには上のv1.3 ROMを使用してください。
The older ROM under `outputs/msx1/v1.2/` is included only as the preservation baseline. Use the v1.3 ROM above to play this edition.
''').encode('utf-8')
prefix='NEON_REVENANT-MSX1-v1.3/'
archive=OUT/'NEON_REVENANT-MSX1-v1.3-complete.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(members.items()):
        info=zipfile.ZipInfo(prefix+name,(2026,9,7,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert z.read(prefix+'outputs/msx1/v1.3/'+manifest['file'])==rom
(OUT/'SHA256SUMS.txt').write_text(manifest['sha256']+'  '+manifest['file']+'\n'+sha(archive.read_bytes())+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'files':len(members),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())},indent=2))
