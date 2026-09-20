from pathlib import Path
import sys,json,time
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'v9990-1mb/tools'))
from emulator_support import OpenMSX,tcl_word
kind=sys.argv[1];P=ROOT.parent/'v9990-1mb' if kind=='v9990' else ROOT/kind;OUT=P/'outputs';M=json.loads((OUT/'build-manifest.json').read_text());S=json.loads((P/'work/build/symbols.json').read_text())
with OpenMSX(work=P/'work',executable='C:/Program Files/openMSX/openmsx_normal.exe') as e:
 if kind in ('turbor','v9990'):e.command('machine Panasonic_FS-A1ST')
 elif kind=='msx2':e.command('machine C-BIOS_MSX2_JP')
 if kind=='v9990':
  e.command('ext gfx9000');e.command('set power off;cartb '+tcl_word((OUT/M['file']).resolve().as_posix())+' -romtype ASCII8;set power on')
 else:e.load_rom(OUT/M['file'])
 e.run_for(15);print(e.command('openmsx_info setting videosource'),flush=True);e.command('set renderer SDLGL-PP;set throttle on;set speed 100;set minframeskip 0;set maxframeskip 0;set blur 0;set glow 0');print(e.command('openmsx_info setting videosource'),flush=True);e.run_for(.2);e.command('set videosource '+('GFX9000' if kind=='v9990' else 'MSX'));e.run_for(.2);e.screenshot(OUT/'title-native.png',640)
 def boundary():
  bp=e.command(f'debug set_bp {S["_input_read"]} {{}} {{debug break}}');e.command('set pause off;debug cont')
  deadline=time.monotonic()+20
  while e.command('debug breaked')!='1':
   assert time.monotonic()<deadline;time.sleep(.01)
  e.command(f'set pause on;debug remove_bp {bp}')
 original_run=e.run_for
 def advance(seconds,*args,**kwargs):
  e.command('debug cont;set pause on');original_run(seconds,*args,**kwargs)
 e.run_for=advance
 def put(n,v,size=1):e.write_block('memory',S[n],v.to_bytes(size,'little'))
 for st in [0,1,4]:
  boundary();put('_stage',st);put('_mode',1);put('_stage_clock',0,2);put('_world_loaded',255);put('_player_x',128,2);put('_player_y',166,2);put('_shield',6);put('_stage_banner',0);put('_hurt_clock',0)
  e.run_for(.5)
  for wait in range(240):
   if e.read_symbol(S,'_world_loaded')==st:break
   e.run_for(.25)
  assert e.read_symbol(S,'_world_loaded')==st
  boundary();put('_shield',6);put('_bombs',3);put('_hurt_clock',0);put('_pickup_on',0)
  for name,stride,count in [('_foes',13 if kind=='msx1' else 14,6 if kind=='msx1' else 9),('_shots',9,8 if kind=='msx1' else 14),('_fx',7,4 if kind=='msx1' else 7)]:e.write_block('memory',S[name],bytes(stride*count))
  e.run_for(.3);put('_stage_banner',0);assert e.read_symbol(S,'_stage')==st,(st,e.read_symbol(S,'_stage'));e.screenshot(OUT/f'stage-{st}-native.png',640)
  if st in (0,4):
   pictures=[]
   for i in range(24):
    put('_hurt_clock',0);path=OUT/f'capture-{i}.png';e.screenshot(path,320);pictures.append(Image.open(path).convert('RGB'));path.unlink()
   pictures[0].save(OUT/f'stage-{st}-native.gif',save_all=True,append_images=pictures[1:],duration=100,loop=0)
 if kind in ('msx1','v9990'):
  boundary();put('_mode',2);put('_boss_hp',240,2);put('_boss_clock',0,2);put('_shield',6);put('_hurt_clock',0)
  if kind=='msx1':
   put('_giant_phase',1);put('_giant_left_hp',32);put('_giant_right_hp',32);put('_giant_core_hp',116);put('_world_loaded',255)
  e.run_for(2);e.screenshot(OUT/'giant-native.png',640)
 print(kind,'captured',flush=True)
