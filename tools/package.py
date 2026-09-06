"""Package four verified prototype variants with disclosures and source."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
documents=['README.md','DISCLAIMER.md','COPYRIGHT.md','THIRD_PARTY_NOTICES.md',
           'requirements.txt','.gitignore','.gitattributes','docs/ASTRA_MSX_GAMEDEV_JA.md']
variants=[(OUT,'NEON_REVENANT-v1.2.rom',
           ['verification-v1.2.json','world-verification-v1.2.json']),
          (OUT/'turbor','NEON_REVENANT-TurboR-v1.0.rom',
           ['verification.json','world-verification.json','sprite-verification.json']),
          (OUT/'msx2','NEON_REVENANT-MSX2-v1.0.rom',
           ['verification.json','world-verification.json','sprite-verification.json','timing-verification.json']),
          (OUT/'msx1','NEON_REVENANT-MSX1-v1.0.rom',
           ['verification.json','world-verification.json'])]
checksums=[]
for directory,filename,reports in variants:
    manifest=json.loads((directory/'build-manifest.json').read_text())
    rom=(directory/filename).read_bytes()
    assert len(rom)==524288 and rom[:2]==b'AB'
    digest=hashlib.sha256(rom).hexdigest()
    assert manifest['file']==filename and manifest['sha256']==digest
    checksums.append((digest,filename))
    for report in reports:
        result=json.loads((directory/report).read_text())
        assert result['rom']['sha256']==digest,report
        assert result['results'] and all(item['passed'] for item in result['results']),report
for port in ['msx2','msx1']:
    sound=json.loads((OUT/port/'sound-verification.json').read_text())
    assert sound['passed'] and not sound['failures']
    assert sound['source_sha256']==hashlib.sha256((ROOT/port/'src/sound.c').read_bytes()).hexdigest()
for filename in documents:
    assert (ROOT/filename).is_file(),filename
assert 'WITHOUT WARRANTY' in (ROOT/'DISCLAIMER.md').read_text(encoding='utf-8')
files={ROOT/filename for filename in documents}
for directory in ['src','tools','assets','turbor/src','turbor/tools','turbor/assets',
                  'msx2/src','msx2/tools','msx2/assets','msx1/src','msx1/tools','msx1/assets',
                  'licenses','docs']:
    files.update(p for p in (ROOT/directory).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.exe','.dll'])
files.update([ROOT/'turbor/README.md',ROOT/'turbor/requirements.txt',ROOT/'turbor/.gitignore'])
for port in ['msx2','msx1']:
    files.update([ROOT/port/'README.md',ROOT/port/'requirements.txt',ROOT/port/'.gitignore'])
files.update(p for p in OUT.rglob('*') if p.is_file() and p.suffix in ['.rom','.json','.md','.ps1','.png','.gif','.txt']
             and not p.name.startswith('SHA256SUMS'))
archive=OUT/'NEON_REVENANT-public-prototype.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(files):
        z.write(p,'NEON_REVENANT/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert 'NEON_REVENANT/DISCLAIMER.md' in z.namelist()
    assert 'NEON_REVENANT/docs/ASTRA_MSX_GAMEDEV_JA.md' in z.namelist()
    assert any(n.startswith('NEON_REVENANT/licenses/sdcc-runtime/') for n in z.namelist())
    assert not any('/work/' in n or '/.git/' in n or n.endswith(('.exe','.dll')) for n in z.namelist())
checksums.append((hashlib.sha256(archive.read_bytes()).hexdigest(),archive.name))
(OUT/'SHA256SUMS-publication.txt').write_text(''.join(digest+'  '+name+'\n' for digest,name in checksums))
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'checksums':dict((name,digest) for digest,name in checksums)},indent=2))
