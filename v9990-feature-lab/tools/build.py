"""Reproducible native SDCC/Pasmo ROM build. No emulator/BIOS binaries packaged."""
from pathlib import Path
import subprocess, os, re, json, hashlib, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
build=ROOT/'work/build';build.mkdir(parents=True,exist_ok=True)
out=ROOT/'outputs';out.mkdir(exist_ok=True)
local_tools=ROOT/'work/toolchain/sdcc/bin'
parent_tools=ROOT.parent/'work/toolchain/sdcc/bin'
bindir=Path(os.environ.get('SDCC_BIN',str(local_tools if local_tools.exists() else parent_tools)))
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
    run([sys.executable,'tools/generate_world.py'])
    run([sys.executable,'tools/generate_feature.py'])
from world_codec import compress, decompress, ATLAS_FRAME_BYTES, ATLAS_FRAME_COUNT, FEATURE_FRAME_BYTES
streams=[]
world_banks=[];world_offsets=[];world_stats=[]
# Boot still copies three banks to 8000h..DFFFh. Keep that tested boot/RAM
# contract; reclaim the 10 raw-atlas banks through lossless compression.
next_offset=4*8192
def add_stream(name,raw,frame_bytes,vram_address):
    global next_offset
    assert raw and len(raw)%frame_bytes==0
    packed=compress(raw,frame_bytes)
    assert decompress(packed,frame_bytes,len(raw)//frame_bytes)==raw
    info={'name':name,'raw_bytes':len(raw),'compressed_bytes':len(packed),
          'rom_offset':next_offset,'bank':next_offset//8192,'offset':next_offset%8192,
          'frame_bytes':frame_bytes,'frame_count':len(raw)//frame_bytes,
          'vram_address':vram_address,'vram_end_exclusive':vram_address+len(raw),
          'raw_sha256':hashlib.sha256(raw).hexdigest(),'compressed_sha256':hashlib.sha256(packed).hexdigest()}
    streams.append((info,packed));next_offset+=len(packed)
    return info
assets=(ROOT/'assets/vram.bin').read_bytes();assert len(assets)==ATLAS_FRAME_BYTES*ATLAS_FRAME_COUNT
atlas_stats=add_stream('atlas',assets,ATLAS_FRAME_BYTES,0x10000)
for stage in range(3):
    raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
    assert len(raw)==368640
    info=add_stream(f'world-{stage+1}',raw,23040,0x24000)
    info['stage']=stage+1
    world_banks.append(info['bank']);world_offsets.append(info['offset']);world_stats.append(info)
feature_path=ROOT/'assets/feature.bin'
feature_stats=None
if feature_path.exists():
    feature=feature_path.read_bytes();assert len(feature)==FEATURE_FRAME_BYTES,'feature.bin must be exactly 8192 bytes'
    feature_stats=add_stream('feature',feature,FEATURE_FRAME_BYTES,0x7E000)
assert next_offset<=524288, f'Compressed asset/world data exceeds ROM by {next_offset-524288} bytes'
header=['/* Generated bank-streamable lossless LZ locations. */',
        f'#define ASSET_BANK {atlas_stats["bank"]}',f'#define ASSET_OFFSET {atlas_stats["offset"]}',
        f'#define ASSET_FRAME_BYTES {ATLAS_FRAME_BYTES}',f'#define ASSET_FRAME_COUNT {ATLAS_FRAME_COUNT}',
        f'#define FEATURE_BANK {feature_stats["bank"] if feature_stats else 0}',
        f'#define FEATURE_OFFSET {feature_stats["offset"] if feature_stats else 0}',
        f'#define FEATURE_FRAME_BYTES {FEATURE_FRAME_BYTES}',f'#define FEATURE_FRAME_COUNT {1 if feature_stats else 0}',
        'static const unsigned char world_banks[3]={'+','.join(map(str,world_banks))+'};',
        'static const unsigned int world_offsets[3]={'+','.join(map(str,world_offsets))+'};']
(ROOT/'src/world_data.h').write_text('\n'.join(header)+'\n')
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
rom=bytearray(boot+runtime+b''.join(packed for _,packed in streams))
used=len(rom);rom+=bytes([0xFF])*(524288-len(rom));assert len(rom)==524288
assert used==next_offset
for info,packed in streams:
    start=info['rom_offset'];assert rom[start:start+len(packed)]==packed
target=out/'NEON_REVENANT-V9990-FeatureLab-v0.1.rom';target.write_bytes(rom)
(build/'symbols.json').write_text(json.dumps(symbols,indent=2))
manifest={'title':'NEON REVENANT - V9990 Feature Lab','version':'0.1','concept':'V9990 hardware feature experiments','file':target.name,'mapper':'ASCII8','rom_bytes':len(rom),'allocated_bytes':used,'free_bytes':len(rom)-used,'runtime_bytes':max(mem)-0x8000+1,'runtime_address':'8000-DFFF','data_address':'E000-E7FF, LZ history E800-EFFF','data_end':hex(int(area[1],16)+int(area[2],16)),'sprite_bytes':len(assets),'atlas':atlas_stats,'feature':feature_stats,'worlds':world_stats,'video':'V9990 B1 256x212 4bpp, 16 projected world frames per stage','sha256':hashlib.sha256(rom).hexdigest(),'entry':hex(symbols['_main']),
 'packing':{'format':'existing LZSS, 2048-byte history, 3..34-byte matches, complete output frames',
            'first_data_offset':4*8192,'runtime_reserved_bytes':len(runtime),
            'runtime_padding_bytes':len(runtime)-(max(mem)-0x8000+1),
            'stream_payload_bytes':sum(len(data) for _,data in streams),
            'atlas_bytes_saved':len(assets)-atlas_stats['compressed_bytes'],
            'extra_asset_bytes':feature_stats['compressed_bytes'] if feature_stats else 0,
            'source_window':'6000-7FFF, ASCII8 register 6800, streams cross banks without alignment padding'},
 'vram_layout':{'draw_pages':[0,0x10000],'atlas':[0x10000,0x24000],'world':[0x24000,0x7E000],'feature':[0x7E000,0x80000]}}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
