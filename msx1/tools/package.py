"""Package the verified MSX1 v1.2 ROM, source, notices and native evidence."""
from pathlib import Path
import hashlib, json, zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
OUT=BASE/'outputs/msx1/v1.2'
LEGAL=BASE if (BASE/'DISCLAIMER.md').exists() else BASE/'work/github-publication/NEON_REVENANT'
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest=json.loads((OUT/'build-manifest.json').read_text())
rom=(OUT/manifest['file']).read_bytes()
assert len(rom)==524288 and rom[:2]==b'AB' and sha(rom)==manifest['sha256']
for standard in ('ntsc','pal'):
    for name in ('verification.json','world-verification.json','transfer-verification.json'):
        report=json.loads((OUT/standard/name).read_text())
        assert report['rom']['sha256']==manifest['sha256']
        assert all(item['passed'] for item in report['results'])
for name in ('layout-verification.json','sound-verification.json','campaign-verification.json','reproducibility.json','preservation-verification.json'):
    assert json.loads((OUT/name).read_text())['passed'],name
members={}
for directory in ('src','tools','assets'):
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.exe','.dll'):
            members['msx1/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
for name in ('README.md','README-en.md','requirements.txt','.gitignore'):
    members['msx1/'+name]=(ROOT/name).read_bytes()
    assert b'NATIVE_RESULTS_PENDING' not in members['msx1/'+name], 'Native validation is not finalized in the documentation'
for p in OUT.rglob('*'):
    if p.is_file() and p.suffix in ('.rom','.json','.png','.gif','.ps1'):
        members[p.relative_to(BASE).as_posix()]=p.read_bytes()
for name in ('DISCLAIMER.md','COPYRIGHT.md','THIRD_PARTY_NOTICES.md'):
    members[name]=(LEGAL/name).read_bytes()
members['docs/ASTRA_THANK_YOU_EDITION.md']=(LEGAL/'docs/ASTRA_THANK_YOU_EDITION.md').read_bytes()
for p in (LEGAL/'licenses').rglob('*'):
    if p.is_file():members[p.relative_to(LEGAL).as_posix()]=p.read_bytes()
members['README.md']=('''# NEON REVENANT — MSX1 PCG Drive v1.2

## ASTRAからの有難うエディション / ASTRA Thank-You Edition

遊んでくださった皆さん、動画を見てくださった皆さん、コメントや実機確認を届けてくださった皆さん、ありがとうございます。
Thank you for playing, watching, sharing your thoughts, and testing on real hardware.
[ASTRAから皆さんへ / A note from ASTRA](docs/ASTRA_THANK_YOU_EDITION.md)

Breakwater to Dawn: Episode 0 + the original three zones + a final zone.
512KiB ASCII8 ROM, 32KiB RAM at 8000h–FFFFh, 16KiB VRAM, standard PSG.

開発途中・無保証の試作版です。実機・実カートリッジ未検証です。
Prototype, provided without warranty. Physical hardware and flash cartridges have not been tested for this version.

- [日本語: 起動・操作・ビルド・検証](msx1/README.md)
- [English: requirements, controls and validation](msx1/README-en.md)
- [ROM](outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom)
- [Disclaimer](DISCLAIMER.md) / [Copyright](COPYRIGHT.md) / [Third-party notices](THIRD_PARTY_NOTICES.md)
''').encode('utf-8')
prefix='NEON_REVENANT-MSX1-v1.2/'
archive=OUT/'NEON_REVENANT-MSX1-v1.2-complete.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(members.items()):
        info=zipfile.ZipInfo(prefix+name,(2026,9,7,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert z.read(prefix+'outputs/msx1/v1.2/'+manifest['file'])==rom
(OUT/'SHA256SUMS.txt').write_text(manifest['sha256']+'  '+manifest['file']+'\n'+sha(archive.read_bytes())+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'files':len(members),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())},indent=2))
