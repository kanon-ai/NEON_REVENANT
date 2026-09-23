"""Reproducible native SDCC/Pasmo ROM build. No emulator/BIOS binaries packaged."""
from pathlib import Path
import subprocess, os, re, json, hashlib, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
build=ROOT/'work/build';build.mkdir(parents=True,exist_ok=True)
out=ROOT/'outputs';out.mkdir(exist_ok=True)
target_mode=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--target=')), 'external')
assert target_mode in ('external','internal'), 'Use --target=external or --target=internal'

local_tools=ROOT/'work/toolchain/sdcc/bin'
parent_tools=ROOT.parent/'work/toolchain/sdcc/bin'
bindir=Path(os.environ.get('SDCC_BIN',str(local_tools if local_tools.exists() else parent_tools)))
env=dict(os.environ);env['PATH']=str(bindir)+os.pathsep+env.get('PATH','')
sdcc=os.environ.get('SDCC',shutil.which('sdcc') or str(bindir/'sdcc.exe'))
pasmo=os.environ.get('PASMO',shutil.which('pasmo') or 'pasmo')
def run(args):
    r=subprocess.run([str(a) for a in args],env=env,text=True,capture_output=True)
    if r.stdout.strip():print(r.stdout.strip())
    if r.stderr.strip():print(r.stderr.strip())
    if r.returncode:raise SystemExit(r.returncode)
if target_mode=='internal':
    from pack_internal import generate
    generate(ROOT)
    DELTA_GAP=int(next((v.split('=',1)[1] for v in sys.argv if v.startswith('--delta-gap=')),'3'))
    # Lossless frame differences: retain every original pixel and all 16 phases.
    payload=bytearray((ROOT/'assets/vram-internal.bin').read_bytes()+(ROOT/'assets/feature.bin').read_bytes())
    rawbanks=[];dbanks=[];doffsets=[];codec_stats=[];cachebanks=[];bandtops=[]
    for stage in range(5):
     raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes();frames=[raw[i*23040:(i+1)*23040] for i in range(16)]
     costs=[sum(sum(p!=q for p,q in zip(frames[f-1][y*128:(y+1)*128],frames[f][y*128:(y+1)*128])) for f in range(16)) for y in range(180)]
     top=max(range(124),key=lambda y:sum(costs[y:y+57]));bandtops.append(top)
     while (32768+len(payload))%8192:payload.append(255)
     cachebanks.append((32768+len(payload))//8192)
     for frame in frames:payload.extend(frame[top*128:(top+57)*128])
     while (32768+len(payload))%8192:payload.append(255)
     rawbanks.append((32768+len(payload))//8192);payload.extend(frames[0]);banks=[];offsets=[]
     for frame in range(16):
      a,b=frames[frame-1],frames[frame];changes=[i for i in range(23040) if a[i]!=b[i] and not top*128<=i<(top+57)*128];runs=[]
      for i in changes:
       if not runs or i-runs[-1][1]>DELTA_GAP or i-runs[-1][0]>=255 or (i+8192)//16384!=(runs[-1][0]+8192)//16384:runs.append([i,i])
       else:runs[-1][1]=i
      stream=bytearray();oracle=bytearray(a)
      for start,last in runs:
       length=last-start+1;stream.extend(bytes([length,(start+8192)&255,(((start+8192)>>8)&63)|64|(((start+8192)>>7)&128)])+b[start:last+1]);oracle[start:last+1]=b[start:last+1]
      stream.append(0);oracle[top*128:(top+57)*128]=b[top*128:(top+57)*128];assert bytes(oracle)==b
      loc=32768+len(payload);banks.append(loc//8192);offsets.append(loc%8192);payload.extend(stream)
      codec_stats.append({'stage':stage,'frame':frame,'runs':len(runs),'encoded_bytes':len(stream)})
     dbanks.append(banks);doffsets.append(offsets)
    (ROOT/'src/world_offsets.h').write_text('static const u8 raw_banks[5]={'+','.join(map(str,rawbanks))+'};\nstatic const u8 delta_banks[5][16]={'+','.join('{'+','.join(map(str,a))+'}' for a in dbanks)+'};\nstatic const u16 delta_offsets[5][16]={'+','.join('{'+','.join(map(str,a))+'}' for a in doffsets)+'};\n')
    with (ROOT/'src/world_offsets.h').open('a') as f:f.write('static const u8 cache_banks[5]={'+','.join(map(str,cachebanks))+'};\nstatic const u8 band_tops[5]={'+','.join(map(str,bandtops))+'};\n')
    (out/'lossless-codec.json').write_text(json.dumps({'all_80_frame_reconstructions_exact':True,'payload_bytes':len(payload),'gap_threshold':DELTA_GAP,'cached_band_rows':57,'band_tops':bandtops,'frames':codec_stats},indent=2))
else:
    DELTA_GAP=int(next((v.split('=',1)[1] for v in sys.argv if v.startswith('--delta-gap=')),'8'))
    # Lossless frame differences: retain every original pixel and all 16 phases.
    payload=bytearray((ROOT/'assets/vram.bin').read_bytes()+(ROOT/'assets/feature.bin').read_bytes())
    rawbanks=[];dbanks=[];doffsets=[];codec_stats=[];cachebanks=[];bandtops=[]
    for stage in range(5):
     raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes();frames=[raw[i*23040:(i+1)*23040] for i in range(16)]
     costs=[sum(sum(p!=q for p,q in zip(frames[f-1][y*128:(y+1)*128],frames[f][y*128:(y+1)*128])) for f in range(16)) for y in range(180)]
     top=max(range(141),key=lambda y:sum(costs[y:y+40]));bandtops.append(top)
     while (32768+len(payload))%8192:payload.append(255)
     cachebanks.append((32768+len(payload))//8192)
     for frame in frames:payload.extend(frame[top*128:(top+40)*128])
     while (32768+len(payload))%8192:payload.append(255)
     rawbanks.append((32768+len(payload))//8192);payload.extend(frames[0]);banks=[];offsets=[]
     for frame in range(16):
      a,b=frames[frame-1],frames[frame];changes=[i for i in range(23040) if a[i]!=b[i] and not top*128<=i<(top+40)*128];runs=[]
      for i in changes:
       if not runs or i-runs[-1][1]>DELTA_GAP or i-runs[-1][0]>=255 or i//16384!=runs[-1][0]//16384:runs.append([i,i])
       else:runs[-1][1]=i
      stream=bytearray();oracle=bytearray(a)
      for start,last in runs:
       length=last-start+1;stream.extend(bytes([length,start&255,start>>8])+b[start:last+1]);oracle[start:last+1]=b[start:last+1]
      stream.append(0);oracle[top*128:(top+40)*128]=b[top*128:(top+40)*128];assert bytes(oracle)==b
      loc=32768+len(payload);banks.append(loc//8192);offsets.append(loc%8192);payload.extend(stream)
      codec_stats.append({'stage':stage,'frame':frame,'runs':len(runs),'encoded_bytes':len(stream)})
     dbanks.append(banks);doffsets.append(offsets)
    (ROOT/'src/world_offsets.h').write_text('static const u8 raw_banks[5]={'+','.join(map(str,rawbanks))+'};\nstatic const u8 delta_banks[5][16]={'+','.join('{'+','.join(map(str,a))+'}' for a in dbanks)+'};\nstatic const u16 delta_offsets[5][16]={'+','.join('{'+','.join(map(str,a))+'}' for a in doffsets)+'};\n')
    with (ROOT/'src/world_offsets.h').open('a') as f:f.write('static const u8 cache_banks[5]={'+','.join(map(str,cachebanks))+'};\nstatic const u8 band_tops[5]={'+','.join(map(str,bandtops))+'};\n')
    (out/'lossless-codec.json').write_text(json.dumps({'all_80_frame_reconstructions_exact':True,'payload_bytes':len(payload),'gap_threshold':DELTA_GAP,'cached_band_rows':40,'band_tops':bandtops,'frames':codec_stats},indent=2))
flags=['-mz80','--std-sdcc11','--opt-code-speed','--no-std-crt0','--code-loc','0x8000','--data-loc','0xE000','-Wl-b_HOME=0xD000']
rels=[]
for name in ['game','hardware','sound','world_load']:
    rel=build/(name+'.rel');rels.append(rel)
    # World offsets depend on compression; always compile/link the current
    # tables, including when --pack-only reuses already generated artwork.
    source_name=name+'-internal' if target_mode=='internal' and name in ('game','hardware','world_load') else name
    run([sdcc,*flags,'-I','src','-c','src/'+source_name+'.c','-o',rel])
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
rom=boot+runtime+payload
assert len(rom)<=2097152
rom+=bytes([255])*(2097152-len(rom))
target=out/('NEON_REVENANT-HC-V9968-INTERNAL.rom' if target_mode=='internal' else 'NEON_REVENANT-HC-V9968.rom');target.write_bytes(rom)
(build/'symbols.json').write_text(json.dumps(symbols,indent=2))
manifest={'title':'NEON REVENANT HC','edition':'Hard Core / V9968','file':target.name,'bytes':len(rom),'sha256':hashlib.sha256(rom).hexdigest(),'runtime_bytes':max(mem)-0x8000+1,'version':'1.2' if target_mode=='internal' else '1.1','profile':('current V9968 internal 98h' if target_mode=='internal' else 'current V9968 external 88h'),'source':'V9990 final five-stage campaign','art':'lossless repacked sprites and original five 16-frame worlds' if target_mode=='internal' else 'byte-identical original atlas, five 16-frame worlds, feature','hardware_verified':False}
(out/('build-manifest-'+target_mode+'.json')).write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
