"""Reproducible native SDCC/Pasmo ROM build. No emulator/BIOS binaries packaged."""
from pathlib import Path
import subprocess, os, re, json, hashlib, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
build=ROOT/'work/build';build.mkdir(parents=True,exist_ok=True)
out=ROOT/'outputs';out.mkdir(exist_ok=True)
bindir=Path(os.environ.get('SDCC_BIN',str(ROOT/'work/toolchain/sdcc/bin')))
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
from world_codec import compress, decompress
world_streams=[]
world_banks=[];world_offsets=[];world_stats=[]
next_offset=14*8192
for stage in range(3):
    raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
    assert len(raw)==368640
    compressed=compress(raw)
    assert decompress(compressed)==raw
    world_banks.append(next_offset//8192);world_offsets.append(next_offset%8192)
    world_stats.append({'stage':stage+1,'raw_bytes':len(raw),'compressed_bytes':len(compressed),'rom_offset':next_offset,'raw_sha256':hashlib.sha256(raw).hexdigest()})
    world_streams.append(compressed);next_offset+=len(compressed)
assert next_offset<=524288, f'Animated world data exceeds ROM by {next_offset-524288} bytes'
(ROOT/'src/world_data.h').write_text('/* Generated compressed-world ROM locations. */\nstatic const unsigned char world_banks[3]={'+','.join(map(str,world_banks))+'};\nstatic const unsigned int world_offsets[3]={'+','.join(map(str,world_offsets))+'};\n')
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
assert area and int(area[1],16)+int(area[2],16)<=0xE800, 'Game data overlaps LZ history at E800'
runtime=bytearray([0xFF]*0x6000)
for a,b in mem.items():runtime[a-0x8000]=b
boot_src=(ROOT/'src/boot.asm').read_text().replace('ENTRY_POINT',str(symbols['_main']))
(build/'boot.asm').write_text(boot_src)
run([pasmo,'--bin',build/'boot.asm',build/'boot.bin'])
boot=(build/'boot.bin').read_bytes();assert len(boot)==8192
assets=(ROOT/'assets/vram.bin').read_bytes();assert len(assets)==81920
rom=bytearray(boot+runtime+assets+b''.join(world_streams))
used=len(rom);rom+=bytes([0xFF])*(524288-len(rom));assert len(rom)==524288
target=out/'NEON_REVENANT-v1.2.rom';target.write_bytes(rom)
(build/'symbols.json').write_text(json.dumps(symbols,indent=2))
manifest={'title':'NEON REVENANT','version':'1.2','concept':'MSX3 alternate history','file':target.name,'mapper':'ASCII8','rom_bytes':len(rom),'allocated_bytes':used,'runtime_bytes':max(mem)-0x8000+1,'runtime_address':'8000-DFFF','data_address':'E000-E7FF, LZ history E800-EFFF','sprite_bytes':len(assets),'worlds':world_stats,'video':'V9990 B1 256x212 4bpp, 16 projected world frames per stage','sha256':hashlib.sha256(rom).hexdigest(),'entry':hex(symbols['_main'])}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
