from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'v9990-1mb/tools'))
from emulator_support import OpenMSX
kind=sys.argv[1];P=ROOT/kind;OUT=P/'outputs';S=json.loads((P/'work/build/symbols.json').read_text());M=json.loads((OUT/'build-manifest.json').read_text());checks=[]
def check(n,ok,**kw):
 d=dict(name=n,passed=bool(ok),**kw);checks.append(d);print(d,flush=True);assert ok,n
with OpenMSX(work=P/'work',executable='C:/Program Files/openMSX/openmsx_normal.exe') as e:
 if kind=='msx2':
  source=(e.profile.system_data/'machines/C-BIOS_MSX2_JP.xml').read_text();source=source.replace('<size>512</size>','<size>64</size>');(e.profile.user_data/'machines/NEON_MSX2_64.xml').write_text(source);e.command('machine NEON_MSX2_64')
 else:e.command('machine Panasonic_FS-A1ST')
 e.load_rom(OUT/M['file']);e.run_for(15)
 def r(n,size=1):return e.read_symbol(S,n,size)
 def put(n,v,size=1):e.write_block('memory',S[n],v.to_bytes(size,'little'))
 def tap(row,mask):e.key(row,mask);e.run_for(.2);e.key(row,mask,False);e.run_for(.15)
 def resident(st):
  for _ in range(200):
   if r('_world_loaded')==st:return
   e.run_for(.25)
  raise AssertionError(('load-timeout',st,r('_world_loaded')))
 check('512KiB',len((OUT/M['file']).read_bytes())==524288)
 check('title',r('_mode')==0 and r('_frame_counter',2)>0)
 if kind=='msx2':check('64KiB-RAM',int(e.command('debug size {Main RAM}'))==65536)
 else:check('R800-DRAM',not(e.read_block('S1990 regs',6,1)[0]&32))
 tap(8,1);resident(0);e.run_for(.4);check('fire-start',r('_mode')==1)
 bp=e.command(f'debug set_bp {S["_sound_tick"]} {{}} {{lappend ::audio_stamp [machine_info time]}}')
 for st in range(5):
  put('_stage',st);put('_mode',1);put('_stage_clock',0,2);put('_world_loaded',255);put('_wave_number',0,2);put('_shield',6);put('_hurt_clock',255)
  e.write_block('memory',S['_foes'],bytes(14*9));start=float(e.command('machine_info time'));e.run_for(.1);resident(st);load=float(e.command('machine_info time'))-start
  v=e.read_block('VRAM',0,131072);raw=(P/'assets/world'/f'stage-{st+1}.bin').read_bytes()
  check(f'stage-{st}-PCG-readback',all(v[f*16384+a:f*16384+a+6144]==raw[f*16384+a:f*16384+a+6144] for f in range(8) for a in [0,8192]),load_seconds=load)
  seen=set();e.command('set ::audio_stamp {}');t=float(e.command('machine_info time'));f0=r('_frame_counter',2)
  for _ in range(60):
   put('_hurt_clock',255);put('_shield',6);e.run_for(.2);foes=e.read_block('memory',S['_foes'],14*9)
   for i in range(9):
    if foes[i*14]:seen.add(foes[i*14+4])
  stamps=list(map(float,e.command('set ::audio_stamp').split()));dt=[b-a for a,b in zip(stamps,stamps[1:])]
  check(f'stage-{st}-audio',len(dt)>300 and max(dt)<.036,maximum=max(dt),mean=sum(dt)/len(dt))
  check(f'stage-{st}-patterns',seen==set(range(st+2 if st<2 else 6)),patterns=sorted(seen))
  check(f'stage-{st}-logic-rate',25<((r('_frame_counter',2)-f0)&65535)/(float(e.command('machine_info time'))-t)<32)
  put('_stage_clock',[900,1200,1320,1440,1560][st]-1,2);e.run_for(.2);check(f'stage-{st}-boss',r('_mode')==2 and r('_boss_hp',2)==[70,100,140,180,240][st])
  tap(7,4);check(f'stage-{st}-pause',r('_mode')==6);clock=r('_boss_clock',2);e.run_for(.2);check(f'stage-{st}-paused-clock',r('_boss_clock',2)==clock);check(f'stage-{st}-PSG-mute',e.read_block('PSG regs',8,3)==bytes(3));tap(7,4)
  put('_boss_hp',1,2);put('_boss_clock',0,2);put('_player_x',128,2);put('_player_y',140,2);put('_shot_clock',0);tap(8,1);check(f'stage-{st}-boss-defeat',r('_mode')==3)
  e.run_for(3)
  if st<4:resident(st+1)
  check(f'stage-{st}-transition',r('_mode')==(5 if st==4 else 1) and r('_stage')==(4 if st==4 else st+1))
 e.command(f'debug remove_bp {bp}');e.run_for(2);tap(8,1);resident(0);e.run_for(.5);check('restart',r('_mode')==1 and r('_stage')==0)
 x=r('_player_x',2);e.key(8,16);e.run_for(.3);e.key(8,16,False);check('movement',r('_player_x',2)<x)
 b=r('_bombs');tap(5,32);check('NOVA',r('_bombs')==b-1)
 check('VDP-timing',e.timing_violations()==0,count=e.timing_violations())
(OUT/'campaign-verification.json').write_text(json.dumps(dict(passed=True,sha256=M['sha256'],physical_hardware_tested=False,method='native openMSX; RAM-seeded stage and boss scenarios with real key input',results=checks),indent=2))
