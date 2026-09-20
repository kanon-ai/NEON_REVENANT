from pathlib import Path
import sys,json
sys.path.insert(0,'v9990-1mb/tools')
from emulator_support import OpenMSX,tcl_word
P=Path('v9990-1mb').resolve();S=json.loads((P/'work/build/symbols.json').read_text());M=json.loads((P/'outputs/build-manifest.json').read_text());results=[]
with OpenMSX(work=P/'work',executable='C:/Program Files/openMSX/openmsx_normal.exe') as e:
 e.command('machine Panasonic_FS-A1ST;ext gfx9000');e.command('set power off;cartb '+tcl_word((P/'outputs'/M['file']).as_posix())+' -romtype ASCII8;set power on');e.run_for(20)
 for st in (1,2,3):
  e.write_block('memory',S['_stage'],bytes([st]));e.write_block('memory',S['_mode'],bytes([1]));e.write_block('memory',S['_world_loaded'],bytes([255]));e.run_for(10)
  values=[]
  for i in range(20):
   e.write_block('memory',S['_shield'],bytes([6]));e.write_block('memory',S['_hurt_clock'],bytes([255]));e.run_for(.5);values.append(e.read_block('Sunrise GFX9000 regs',13,1)[0])
  assert set(values)=={0},(st,values);results.append({'stage':st,'palette_register_13_values':values,'passed':True})
(P/'outputs/palette-verification.json').write_text(json.dumps({'passed':True,'sha256':M['sha256'],'results':results},indent=2));print('Original three scenes retain base palette over full animation cycle')
