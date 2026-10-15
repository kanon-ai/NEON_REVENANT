"""Compile the isolated v2 adapter; retain all accepted baseline artwork/audio."""
from pathlib import Path
import subprocess, re, struct, hashlib, json, os
P=Path(__file__).resolve().parent
O=P/'out';O.mkdir(exist_ok=True)
import shutil
T=Path(os.environ['SDCC_BIN']) if os.environ.get('SDCC_BIN') else Path(shutil.which('sdcc') or 'sdcc').resolve().parent
os.environ['PATH']=str(T)+os.pathsep+os.environ['PATH']
def run(*args):subprocess.run([str(x) for x in args],cwd=P,check=True)
run(T/'sdcc.exe','-mz80','--opt-code-speed','-c',P/'src/sound.c','-o',O/'sound.rel')
run(T/'sdcc.exe','-mz80','-DNEON_FAST','--std-c99','--opt-code-speed','--no-std-crt0','--code-loc','0x8000','--data-loc','0xD000','-Wl-b_HOME=0xB500','-I'+str(P/'src'),P/'src/hc_logic.c',O/'sound.rel','-o',O/'hc.ihx')
m=(O/'hc.map').read_text()
a=re.search(r'_CODE\s+([0-9A-F]{8})\s+([0-9A-F]{8})',m)
assert int(a[1],16)+int(a[2],16)<=0xB500,a[0]
sy={}
for line in m.splitlines():
 a=re.search(r'([0-9A-F]{8})\s+(_hc_init|_hc_tick|_hc_draw|_audio_setup|_assets_init|_mode)\s',line)
 if a:sy[a[2]]=int(a[1],16)
assert len(sy)==6
(P/'src/hc_symbols.inc').write_text(''.join(k[1:]+' = '+hex(v)+'\n' for k,v in sy.items()))
run(T/'sdasz80.exe','-los',O/'player.rel',P/'src/player.asm')
run(T/'sdldz80.exe','-n','-i',O/'player',O/'player.rel')
r=bytearray((P/'baseline/game.rom').read_bytes())
for kind in ('player','hc'):
 for line in (O/(kind+'.ihx')).read_text().splitlines():
  b=bytes.fromhex(line[1:]);assert sum(b)%256==0
  if b[3]:continue
  n=b[0];a=int.from_bytes(b[1:3],'big')
  if kind=='player':
   if a>=0xE800:assert a+n<=0xF000;a=a-0xE800+0x4100
   a-=0x4000
  else:
   assert 0x8000<=a and a+n<=0xB700
   a=a-0x8000+0x900
  r[a:a+n]=b[4:4+n]
models=[]
for bank in [1,2,3,250,64,65,229,230,231,232,233,234,235,236]:
 start=bank*16384;p=bytes(r[start:start+16384]);nv,nf=p[:2];vb,fb=struct.unpack_from('<HH',p,2)
 slot={1:0,2:1,3:2,250:3}.get(bank,4+(bank&1))
 base=256+slot*64 if slot<4 else 512+(slot-4)*128
 capacity=64 if slot<4 else 128
 assert nv<=capacity and nf<=capacity
 faces=bytearray()
 for i in range(nf):
  f=p[6+vb+i*11:6+vb+(i+1)*11];ids=[x+base for x in f[:4]]
  faces+=bytes(x&255 for x in ids)+bytes([sum((x>>8)<<(2*j) for j,x in enumerate(ids))])+f[4:]
 texsize=struct.unpack_from('<H',p,16382)[0]
 data=p[:2]+struct.pack('<HH',vb,len(faces))+p[6:6+vb]+faces+p[6+vb+fb:6+vb+fb+texsize]
 assert len(data)<16382
 r[start:start+len(data)]=data
 models.append(dict(bank=bank,slot=slot,base=base,vertices=nv,faces=nf))
assert len(r)==4*1024*1024
dest=O/'NEON_REVENANT-HC-Geo3D-v2-resident-test.rom';dest.write_bytes(r)
(O/'manifest.json').write_text(json.dumps(dict(rom_bytes=len(r),sha256=hashlib.sha256(r).hexdigest(),models=models),indent=2))
print(dest)
