"""Reproducible native SDCC/Pasmo ROM build. No emulator/BIOS binaries packaged."""
from pathlib import Path
import subprocess, os, re, json, hashlib, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
build=ROOT/'work/build';build.mkdir(parents=True,exist_ok=True)
out=ROOT.parent/'outputs/msx1/v1.1';out.mkdir(parents=True,exist_ok=True)
bindir=Path(os.environ.get('SDCC_BIN',str(ROOT.parent/'work/toolchain/sdcc/bin')))
env=dict(os.environ);env['PATH']=str(bindir)+os.pathsep+env.get('PATH','')
sdcc=os.environ.get('SDCC',str(bindir/'sdcc.exe'))
pasmo=os.environ.get('PASMO',shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe')
def run(args):
    r=subprocess.run([str(a) for a in args],env=env,text=True,capture_output=True)
    if r.stdout.strip():print(r.stdout.strip())
    if r.stderr.strip():print(r.stderr.strip())
    if r.returncode:raise SystemExit(r.returncode)
if '--pack-only' not in sys.argv:
    run([sys.executable,'tools/generate_assets.py'])
world_stats=[]
for stage in range(3):
    raw=(ROOT/'assets'/f'world-{stage}.bin').read_bytes();assert len(raw)==16384
    packets=[(ROOT/'assets'/f'phase-{stage}-{phase:02}.bin').read_bytes() for phase in range(16)]
    assert all(len(p)<=8192 for p in packets)
    world_stats.append({'stage':stage+1,'bytes':len(raw),'vram_bytes':16384,'phases':16,'pcg_packet_bytes':sum(map(len,packets)),'raw_sha256':hashlib.sha256(raw).hexdigest()})
flags=['-mz80','--std-sdcc11','--opt-code-speed','--no-std-crt0','--code-loc','0x8000','--data-loc','0xE000']
rels=[]
for name in ['game','hardware','sound','world_load']:
    rel=build/(name+'.rel');rels.append(rel)
    # Always compile the current descriptors, including when --pack-only
    # reuses already generated artwork.
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
records=(ROOT/'assets/sprite-records.bin').read_bytes();assert len(records)<8192
patterns=(ROOT/'assets/sprite-patterns.bin').read_bytes();assert len(patterns)==2048
rom=bytearray([0xFF]*524288)
def bank_write(bank,data):
    assert bank*8192+len(data)<=len(rom)
    rom[bank*8192:bank*8192+len(data)]=data
bank_write(0,boot);bank_write(1,runtime);bank_write(4,records);bank_write(5,patterns)
for stage in range(3):
    bank_write(6+stage*2,(ROOT/'assets'/f'world-{stage}.bin').read_bytes())
    for phase in range(16):
        packet=(ROOT/'assets'/f'phase-{stage}-{phase:02}.bin').read_bytes();assert len(packet)<=8192
        bank_write(14+stage*16+phase,packet)
bank_write(12,(ROOT/'assets/title.bin').read_bytes())
used=62*8192
target=out/'NEON_REVENANT-MSX1-v1.1.rom';target.write_bytes(rom)
(build/'symbols.json').write_text(json.dumps(symbols,indent=2))
manifest={'title':'NEON REVENANT - MSX1 PCG Drive','version':'1.1','file':target.name,'mapper':'ASCII8','rom_bytes':len(rom),'allocated_bytes':used,'runtime_bytes':max(mem)-0x8000+1,'runtime_address':'8000-DFFF','data_end':hex(int(area[1],16)+int(area[2],16)),'sprite_bytes':len(patterns),'worlds':world_stats,'video':'TMS9918A SCREEN2 256x192, 16 streamed PCG phases, two name pages, fixed palette, resident mode1 MAG2 sprites','v9990_required':False,'sha256':hashlib.sha256(rom).hexdigest(),'entry':hex(symbols['_main'])}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
