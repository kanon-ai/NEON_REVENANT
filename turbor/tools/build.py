"""Reproducible native SDCC/Pasmo ROM build. No emulator/BIOS binaries packaged."""
from pathlib import Path
import subprocess, os, re, json, hashlib, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
build=ROOT/'work/build';build.mkdir(parents=True,exist_ok=True)
out=ROOT.parent/'outputs/turbor';out.mkdir(parents=True,exist_ok=True)
bindir=Path(os.environ.get('SDCC_BIN',str(ROOT.parent/'work/toolchain/sdcc/bin')))
env=dict(os.environ);env['PATH']=str(bindir)+os.pathsep+env.get('PATH','')
sdcc=os.environ.get('SDCC',str(bindir/'sdcc.exe'))
pasmo=os.environ.get('PASMO',shutil.which('pasmo') or 'pasmo')
def run(args):
    r=subprocess.run([str(a) for a in args],env=env,text=True,capture_output=True)
    if r.stdout.strip():print(r.stdout.strip())
    if r.stderr.strip():print(r.stderr.strip())
    if r.returncode:raise SystemExit(r.returncode)
if '--pack-only' not in sys.argv:
    run([sys.executable,'tools/generate_assets.py'])
    run([sys.executable,'tools/generate_world.py'])
world_streams=[];world_stats=[]
for stage in range(3):
    raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
    assert len(raw)==131072
    world_streams.append(raw)
    world_stats.append({'stage':stage+1,'raw_bytes':len(raw),'rom_offset':0x10000+stage*0x20000,'raw_sha256':hashlib.sha256(raw).hexdigest()})
flags=['-mz80','--std-sdcc11','--opt-code-speed','--no-std-crt0','--code-loc','0x8000','--data-loc','0xE000']
rels=[]
for name in ['game','hardware','sound','world_load']:
    rel=build/(name+'.rel');rels.append(rel)
    # World offsets depend on compression; always compile/link the current
    # tables, including when --pack-only reuses already generated artwork.
    run([sdcc,*flags,'-I','src','-c','src/'+name+'.c','-o',rel])
run([sdcc,*flags,'-o',build/'game.ihx',*rels])
mem={}
for line in (build/'game.ihx').read_text().splitlines():
    if not line.startswith(':'):continue
    rec=bytes.fromhex(line[1:]);assert sum(rec)%256==0,'Intel HEX checksum'
    size=rec[0];addr=int.from_bytes(rec[1:3],'big');typ=rec[3]
    if typ==0:
        for n,b in enumerate(rec[4:4+size]):
            assert 0x8000<=addr+n<0xE000,f'ROM runtime overflow: {addr+n:04X}'
            mem[addr+n]=b
text=(build/'game.map').read_text()
symbols={m.group(2):int(m.group(1),16) for m in re.finditer(r'^\s*([0-9A-F]{8})\s+(_[\w]+)\s',text,re.M)}
assert '_main' in symbols
area=re.search(r'^_DATA\s+([0-9A-F]+)\s+([0-9A-F]+)',text,re.M)
assert area and int(area[1],16)+int(area[2],16)<=0xF100, 'Game data overlaps stack guard at F100'
runtime=bytearray([0xFF]*0x6000)
for a,b in mem.items():runtime[a-0x8000]=b
boot_src=(ROOT/'src/boot.asm').read_text().replace('ENTRY_POINT',str(symbols['_main']))
(build/'boot.asm').write_text(boot_src)
run([pasmo,'--bin',build/'boot.asm',build/'boot.bin'])
boot=(build/'boot.bin').read_bytes();assert len(boot)==8192
assets=(ROOT/'assets/sprites.bin').read_bytes();assert len(assets)<=32768
rom=bytearray(boot+runtime+assets+bytes([0xFF])*(32768-len(assets))+b''.join(world_streams)+(ROOT/'assets/title.bin').read_bytes())
used=len(rom);rom+=bytes([0xFF])*(524288-len(rom));assert len(rom)==524288
target=out/'NEON_REVENANT-TurboR-v1.0.rom';target.write_bytes(rom)
(build/'symbols.json').write_text(json.dumps(symbols,indent=2))
manifest={'title':'NEON REVENANT - Turbo R Edition','version':'1.0','file':target.name,'mapper':'ASCII8','rom_bytes':len(rom),'allocated_bytes':used,'runtime_bytes':max(mem)-0x8000+1,'runtime_address':'8000-DFFF','data_end':hex(int(area[1],16)+int(area[2],16)),'sprite_bytes':len(assets),'worlds':world_stats,'video':'V9958 SCREEN4 256x192, 8 resident world frames per stage, mode2 MAG2 sprites','v9990_required':False,'sha256':hashlib.sha256(rom).hexdigest(),'entry':hex(symbols['_main'])}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
