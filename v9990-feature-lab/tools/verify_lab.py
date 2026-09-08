"""Native Feature Lab checks and timestamped openMSX captures.

Scenario RAM writes select distant scenes; they are not a complete playthrough.
No PC-side scene renderer is used. The ROM performs all drawing and combat.
Run after verify_rom.py with the same ROM loaded on the local bridge port 18890.
"""
import hashlib, json, time, urllib.request
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SYM=json.loads((ROOT/'work/build/symbols.json').read_text())
MAN=json.loads((ROOT/'outputs/build-manifest.json').read_text())
OUT=ROOT/'outputs/feature-lab-v0.1';OUT.mkdir(exist_ok=True)
SCRATCH=ROOT/'work/lab-captures';SCRATCH.mkdir(exist_ok=True)
results=[]

def cmd(s):
    req=urllib.request.Request('http://127.0.0.1:18890',data=s.encode(),method='POST')
    try:return urllib.request.urlopen(req,timeout=30).read().decode().strip()
    except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from e
def read(n,size=1):
    a=SYM[n]
    return int(cmd(f'expr {{[debug read memory {a}]'+(f'+256*[debug read memory {a+1}]' if size==2 else '')+'}'))
def write(n,v,size=1):
    a=SYM[n];cmd(f'debug write memory {a} {v&255}'+(f';debug write memory {a+1} {(v>>8)&255}' if size==2 else ''))
def clock():return float(cmd('machine_info time'))
def until(pred,timeout=35):
    end=time.monotonic()+timeout
    while not pred():
        if time.monotonic()>end:raise TimeoutError('native machine progress')
        time.sleep(.01)
def advance(sec):
    target=clock()+sec;until(lambda:clock()>=target)
def check(name,ok,**evidence):
    results.append(dict(name=name,passed=bool(ok),**evidence))
    print(name,'PASS' if ok else 'FAIL',evidence,flush=True)
    assert ok,name
def reg(n):return int(cmd(f'debug read {{Sunrise GFX9000 regs}} {n}'))
def vram():
    raw=bytes.fromhex(cmd('binary encode hex [debug read_block {Sunrise GFX9000 VRAM} 0 524288]'))
    logical=bytearray(524288);logical[0::2]=raw[:262144];logical[1::2]=raw[262144:]
    return bytes(logical)
def shot(path):cmd(f'openmsx::internal_screenshot -raw {{{path.as_posix()}}}')
def tap(row,mask):
    cmd(f'keymatrixdown {row} {mask}');advance(.16)
    cmd(f'keymatrixup {row} {mask}');advance(.12)
def seed(stage,boss=False,reload=False):
    cmd('set pause on')
    for n,v,size in [('_mode',2 if boss else 1,1),('_stage',stage,1),
      ('_stage_clock',0,2),('_stage_banner',0,1),('_shield',6,1),('_bombs',3,1),
      ('_player_x',128,2),('_player_y',150 if boss else 166,2),
      ('_hurt_clock',0,1),('_bomb_flash',0,1),('_boss_flash',0,1),
      ('_old_keys',0,1),('_pickup_on',0,1),('_world_camera',0,2),
      ('_boss_clock',0,2),('_boss_hp',180 if boss else 0,2),
      ('_boss_x',128,2),('_boss_y',82,2),('_lab_enabled',1,1)]:write(n,v,size)
    for n,stride,count in [('_foes',12,9),('_shots',9,14),('_fx',7,7)]:
        cmd(';'.join(f'debug write memory {SYM[n]+i*stride} 0' for i in range(count)))
    if reload:write('_world_loaded',255)
    t=clock();cmd('set pause off');until(lambda:read('_world_loaded')==stage)
    load=clock()-t;advance(.15);return load
def capture(name,count,steer=False):
    bp=cmd(f'debug set_bp {SYM["_draw_frame"]} {{}} {{debug break}}')
    until(lambda:cmd('debug breaked')=='1')
    frames=[];times=[];boss_positions=[]
    try:
        for i in range(count):
            if steer:
                if i==0:cmd('keymatrixdown 8 17')
                if i==24:cmd('keymatrixup 8 16;keymatrixdown 8 128')
                if i==64:cmd('keymatrixup 8 128')
            p=SCRATCH/f'{name}-{i:03d}.png';shot(p)
            with Image.open(p) as src:frames.append(src.convert('RGB'))
            times.append(clock());boss_positions.append([read('_boss_x',2),read('_boss_y',2),read('_boss_clock',2)])
            cmd('debug cont');until(lambda:cmd('debug breaked')=='1')
    finally:cmd(f'keymatrixup 8 145;debug remove_bp {bp};debug cont')
    durations=[];accum=0
    for i in range(count):
        end=(times[i+1] if i+1<count else times[i]+times[-1]-times[-2])
        rounded=round((end-times[0])*100)
        durations.append(max(10,(rounded-accum)*10));accum=rounded
    enlarged=[p.resize((640,480),Image.Resampling.NEAREST) for p in frames]
    gif=OUT/f'{name}-native.gif'
    enlarged[0].save(gif,save_all=True,append_images=enlarged[1:],duration=durations,loop=0,optimize=False)
    exact=True
    with Image.open(gif) as saved:
        exact=saved.n_frames==count
        for i,source in enumerate(enlarged):
            saved.seek(i);exact &= saved.convert('RGB').tobytes()==source.tobytes()
    frames[count//3].save(OUT/f'{name}.png')
    unique=len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})
    fps=(count-1)/(times[-1]-times[0])
    check(name+'-native-motion',unique>count*.9 and fps>=19,frames=count,unique_frames=unique,
          consecutive_frame_fps=round(fps,3),duration_seconds=round(sum(durations)/1000,3),
          boss_x_range=[min(p[0] for p in boss_positions),max(p[0] for p in boss_positions)])
    check(name+'-gif-exact',exact,frames=count)

cmd('set pause off;set speed 100;set videosource GFX9000;keymatrixup 8 255;keymatrixup 7 255;keymatrixup 5 255')
rom=(ROOT/'outputs'/MAN['file']).read_bytes()
check('artifact-hash',hashlib.sha256(rom).hexdigest()==MAN['sha256'])
cmd('set pause on')
runtime=bytes.fromhex(cmd(f'binary encode hex [debug read_block memory 32768 {MAN["runtime_bytes"]}]'))
check('loaded-runtime-matches-ROM',runtime==rom[8192:8192+len(runtime)],bytes=len(runtime))
write('_mode',0);write('_old_keys',0);write('_lab_enabled',1)
cmd('set pause off');until(lambda:read('_world_loaded')==0);advance(.2)
shot(OUT/'title.png')
tap(8,0x21);until(lambda:read('_world_loaded')==2)
check('up-fire-enters-giant-boss',read('_mode')==2 and read('_stage')==2 and read('_boss_hp',2)>0)
advance(.2)
cmd('set pause on');data=vram()
atlas=(ROOT/'assets/vram.bin').read_bytes();feature=(ROOT/'assets/feature.bin').read_bytes()
check('atlas-native-lossless-decode',data[0x10000:0x24000]==atlas,bytes=len(atlas))
check('giant-art-native-lossless-decode',data[0x7E000:0x7FE00]==feature[:7680],bytes=7680)
check('cursor-planes-enabled',reg(8)==0x82 and reg(28)==15)
check('two-native-cursor-patterns',any(data[0x7FF00:0x7FF80]) and any(data[0x7FF80:]))
cmd('set pause off')

for stage in range(3):
    load=seed(stage,reload=True);cmd('set pause on')
    raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
    check(f'stage-{stage+1}-native-decode',vram()[0x24000:0x7E000]==raw,
          bytes=len(raw),phases=16,load_seconds=round(load,3))
    cmd('set pause off');t=clock();f=read('_frame_counter',2);advance(2)
    fps=((read('_frame_counter',2)-f)&65535)/(clock()-t)
    check(f'stage-{stage+1}-effects-performance',fps>=19,fps=round(fps,3))
    fm=[]
    for i in range(4):
        fm.append(cmd('binary encode hex [debug read_block {MSX Music regs} 0 64]'));advance(.15)
    check(f'stage-{stage+1}-music-after-load',len(set(fm))>1)
    if stage==1:capture('skyway-energy-gates',96,True)

seed(2,True);capture('giant-siege-carrier',128)
cmd('set pause on');data=vram()
attrs=data[0x7FE00:0x7FE10]
x=attrs[4]+((attrs[6]&3)<<8)+15;y=attrs[0]+((attrs[2]&1)<<8)+16
check('hardware-cursor-tracks-aim',x==read('_aim_x',2) and y==read('_aim_y',2)
      and not(attrs[6]&0x10) and not(attrs[14]&0x10),cursor_center=[x,y])
check('warm-bitmap-fixed-cursor-palette',reg(13)==8 and reg(28)==15,
      bitmap_palette_start=32,cursor_palette_start=60)
cmd('set pause off')
# Pause input freezes simulation and hides the always-foreground cursors.
tap(7,4);check('giant-pause',read('_mode')==6)
before=[read('_boss_clock',2),read('_boss_x',2),read('_boss_y',2),read('_boss_hp',2)]
advance(.3);shot(OUT/'effects-on.png')
cmd('set pause on');data=vram()
check('pause-dialog-hides-native-cursors',data[0x7FE06]&0x10 and data[0x7FE0E]&0x10)
cmd('set pause off');tap(7,8);advance(.2);shot(OUT/'effects-off.png')
after=[read('_boss_clock',2),read('_boss_x',2),read('_boss_y',2),read('_boss_hp',2)]
check('effects-toggle-preserves-paused-boss',read('_lab_enabled')==0 and before==after,boss_state=after)
cmd('set pause on');data=vram()
check('effects-off-hides-hardware-cursors',reg(13)==0 and data[0x7FE06]&0x10 and data[0x7FE0E]&0x10)
cmd('set pause off');tap(7,8);tap(7,4)
check('effects-and-game-resume',read('_lab_enabled')==1 and read('_mode')==2)
tap(5,0x20);cmd('set pause on')
check('nova-bright-palette',reg(13)==12 and read('_bomb_flash')>0)
shot(OUT/'nova-flash.png')
data=vram()
check('art-remains-intact-after-gameplay',data[0x10000:0x24000]==atlas and data[0x7E000:0x7FE00]==feature[:7680])
cmd('set pause off')
report={'rom_sha256':MAN['sha256'],'emulator':cmd('openmsx_info version'),
        'machine':cmd('machine_info config_name'),'extension':'gfx9000','physical_hardware_tested':False,
        'scenario_seeding':'RAM selects distant scenes and isolates objects; native ROM executes all rendering.',
        'capture':'Consecutive ROM draw frames; GIF delays derived from emulated time, no speed-up.',
        'audio':'FM register activity checked; no physical audio-output test.',
        'results':results}
(ROOT/'outputs/feature-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('FEATURE LAB CHECKS PASSED',flush=True)
