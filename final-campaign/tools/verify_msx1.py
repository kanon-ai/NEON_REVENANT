from pathlib import Path
import sys,json,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'msx1';OUT=P/'outputs';sys.path.insert(0,str(ROOT.parent/'v9990-1mb/tools'));sys.path.insert(0,str(P/'tools'))
from emulator_support import OpenMSX
from pcg_codec import decode_screen
standard=sys.argv[1] if len(sys.argv)>1 else 'ntsc';S=json.loads((P/'work/build/symbols.json').read_text());M=json.loads((OUT/'build-manifest.json').read_text());checks=[]
def check(n,ok,**kw):
 d=dict(name=n,passed=bool(ok),**kw);checks.append(d);print(d,flush=True);assert ok,n
with OpenMSX(standard,work=P/'work',executable='C:/Program Files/openMSX/openmsx_normal.exe') as e:
 e.load_rom(OUT/M['file']);e.run_for(12)
 original_run=e.run_for
 def advance(seconds):
  e.command('debug cont;set pause on');original_run(seconds)
 e.run_for=advance
 def r(n,size=1):return e.read_symbol(S,n,size)
 def put(n,v,size=1):e.write_block('memory',S[n],v.to_bytes(size,'little'))
 def tap(row,mask):e.key(row,mask);e.run_for(.3);e.key(row,mask,False);e.run_for(.2)
 def boundary():
  bp=e.command(f'debug set_bp {S["_input_read"]} {{}} {{debug break}}');e.command('set pause off;debug cont')
  deadline=time.monotonic()+20
  while e.command('debug breaked')!='1':
   assert time.monotonic()<deadline;time.sleep(.01)
  e.command(f'set pause on;debug remove_bp {bp}')
 check('32KiB-RAM',int(e.command('debug size {Main RAM}'))==32768)
 check('16KiB-VRAM',int(e.command('debug size {physical VRAM}'))==16384)
 check('512KiB-ROM',len((OUT/M['file']).read_bytes())==524288)
 check('title',r('_mode')==0);tap(8,1);e.run_for(1);check('start',r('_mode')==1)
 bp=e.command(f'debug set_bp {S["_sound_tick"]} {{}} {{lappend ::audio_stamp [machine_info time]}}')
 for st in range(5):
  boundary();put('_stage',st);put('_stage_clock',0,2);put('_mode',1);put('_world_loaded',255);put('_shield',6);put('_hurt_clock',255);e.run_for(1)
  check(f'stage-{st}-loaded',r('_world_loaded')==st)
  expected=np.load(P/'assets'/f'frames-{st}.npy');phases=set();e.command('set ::audio_stamp {}')
  for sample in range(96):
   boundary();v=e.read_block('VRAM',0,16384);phase=r('_world_phase');phases.add(phase);name=e.read_block('VDP regs',2,1)[0]*1024
   actual=decode_screen(v,name)[16:176]; wanted=expected[phase,16:176]
   if not np.array_equal(actual,wanted):
    ys,xs=np.where(actual!=wanted);print('DIFF',st,phase,'pending',r('_world_pending'),'name',name,'pixels',len(ys),'bounds',(int(xs.min()),int(ys.min()+16),int(xs.max()),int(ys.max()+16)),flush=True);(OUT/'failed-vram.bin').write_bytes(v);assert False
   put('_hurt_clock',255);put('_shield',6);e.run_for(.025)
   if len(phases)==16 and sample>=31:break
  check(f'stage-{st}-16-phases-PCG',len(phases)==16,phases=sorted(phases))
  stamps=list(map(float,e.command('set ::audio_stamp').split()));dt=[b-a for a,b in zip(stamps,stamps[1:])];check(f'stage-{st}-audio',max(dt)<.045,maximum=max(dt),mean=sum(dt)/len(dt))
  tap(7,4);check(f'stage-{st}-pause',r('_mode')==6);check(f'stage-{st}-mute',e.read_block('PSG regs',8,3)==bytes(3));tap(7,4)
 e.command(f'debug remove_bp {bp}');boundary();put('_stage',4);put('_mode',2);put('_giant_phase',1);put('_giant_left_hp',32);put('_giant_right_hp',32);put('_giant_core_hp',116);put('_world_loaded',255);e.run_for(2)
 check('giant-resident',r('_world_loaded')==5);phases=set()
 for _ in range(64):
  e.run_for(.07);phases.add(r('_world_phase'));put('_hurt_clock',255);put('_shield',6)
 check('giant-moving',len(phases)>8,phases=sorted(phases))
 check('VDP-timing',e.timing_violations()==0,count=e.timing_violations())
(OUT/f'campaign-verification-{standard}.json').write_text(json.dumps(dict(passed=True,sha256=M['sha256'],physical_hardware_tested=False,method=f'openMSX synthetic 32KiB MSX1 {standard}; 16 native PCG phases per stage; seeded giant boss',results=checks),indent=2))
