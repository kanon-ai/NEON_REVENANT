"""Package the selected v1.4 ROM and public source, without external runtimes."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent;OUT=BASE/'outputs/msx1/v1.4'
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((OUT/'build-manifest.json').read_text())
rom=(OUT/manifest['file']).read_bytes()
assert len(rom)==524288 and sha(rom)==manifest['sha256']=='77aa5eabcd4f1bd6510e344570b440fc57f6d0816b747476c676fb41499dd691'
checks=json.loads((OUT/'ntsc/world-verification.json').read_text())
assert all(x['passed'] for x in checks['results'])
proof=json.loads((OUT/'title-only-change.json').read_text())
assert proof['before_sha256']==checks['rom']['sha256'] and proof['after_sha256']==sha(rom)
boot=json.loads((OUT/'final-boot-verification.json').read_text())
assert boot['passed'] and boot['sha256']==sha(rom)
members={}
for folder in ('src','assets','tools'):
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.exe','.dll'):
            members[p.relative_to(BASE).as_posix()]=p.read_bytes()
for name in ('README.md','README-en.md','REFINED-v1.4.md','GIANT_BOSS-v1.3.md','requirements.txt','.gitignore'):
    members['msx1/'+name]=(ROOT/name).read_bytes()
for name in ('DISCLAIMER.md','COPYRIGHT.md','THIRD_PARTY_NOTICES.md','requirements.txt'):
    members[name]=(BASE/name).read_bytes()
for p in (BASE/'licenses').rglob('*'):
    if p.is_file():members[p.relative_to(BASE).as_posix()]=p.read_bytes()
for p in OUT.rglob('*'):
    if p.is_file() and p.suffix in ('.rom','.json','.png','.gif','.md'):
        members[p.relative_to(BASE).as_posix()]=p.read_bytes()
members['README.md']=('''# NEON REVENANT MSX1 v1.4

Start with [the Japanese/English guide](msx1/REFINED-v1.4.md).
The ROM and validation evidence are in `outputs/msx1/v1.4`.
512 KiB ASCII8, 32 KiB RAM, 16 KiB VRAM, standard MSX1 PSG.
Experimental prototype, AS IS, WITHOUT WARRANTY. No BIOS or external runtime
is included. Historical guides may link to old files in the GitHub repository.
''').encode()
target=OUT/'NEON_REVENANT-MSX1-v1.4-complete.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(members.items()):z.writestr(name,data)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert all(z.read(name)==data for name,data in members.items())
    assert z.read('outputs/msx1/v1.4/'+manifest['file'])==rom
(OUT/'SHA256SUMS-v1.4.txt').write_text(sha(rom)+'  '+manifest['file']+'\n'+sha(target.read_bytes())+'  '+target.name+'\n')
print(target);print('Checked ZIP members:',len(members))
