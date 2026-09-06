"""Native V9990 world readback, timing and frame captures.

Requires tools/emulator_host.mjs already running the current ROM. RAM seeds
only select the visual scenario; all rendering is executed by the MSX ROM.
"""
from pathlib import Path
import hashlib, json, time, urllib.request, re
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SYM=json.loads((ROOT/'work/build/symbols.json').read_text())
OUT=ROOT.parent/'outputs/turbor'
MANIFEST=json.loads((OUT/'build-manifest.json').read_text())
assert hashlib.sha256((OUT/MANIFEST['file']).read_bytes()).hexdigest()==MANIFEST['sha256']
SCRATCH=ROOT/'work/captures';SCRATCH.mkdir(exist_ok=True)
results=[]

def cmd(s):
    req=urllib.request.Request('http://127.0.0.1:18791',data=s.encode(),method='POST')
    return urllib.request.urlopen(req,timeout=30).read().decode().strip()

def read(name,size=1):
    a=SYM[name]
    return int(cmd(f'expr {{[debug read memory {a}]'+(f'+256*[debug read memory {a+1}]' if size==2 else '')+'}'))

def write(name,value,size=1):
    a=SYM[name]
    cmd(f'debug write memory {a} {value&255}'+(f'; debug write memory {a+1} {(value>>8)&255}' if size==2 else ''))

def clock():return float(cmd('machine_info time'))

def until(predicate,timeout=30):
    end=time.monotonic()+timeout
    while not predicate():
        if time.monotonic()>end:raise TimeoutError('native emulator wait')
        time.sleep(.01)

def advance(seconds):
    target=clock()+seconds
    until(lambda:clock()>=target)

def check(name,ok,**evidence):
    results.append(dict(name=name,passed=bool(ok),**evidence))
    print(name,'PASS' if ok else 'FAIL',evidence,flush=True)
    assert ok,name

def vram():
    return bytes.fromhex(cmd('binary encode hex [debug read_block VRAM 0 131072]'))

def screenshot(path):cmd(f'openmsx::internal_screenshot -raw {{{path.as_posix()}}}')

cmd('set pause off; set speed 100; set limitsprites true; set accuracy pixel; set videosource MSX')
for stage in range(3):
    cmd('set pause on')
    for n,v,size in [('_mode',1,1),('_stage',stage,1),('_stage_clock',0,2),
                     ('_stage_banner',0,1),('_player_x',128,2),('_player_y',166,2),
                     ('_shield',6,1),('_bombs',3,1),('_hurt_clock',0,1),
                     ('_bomb_flash',0,1),('_old_keys',0,1),('_world_camera',0,2),
                     ('_pickup_on',0,1)]:write(n,v,size)
    for name,stride,count in [('_foes',12,9),('_shots',9,14),('_fx',7,7)]:
        cmd(';'.join(f'debug write memory {SYM[name]+i*stride} 0' for i in range(count)))
    # Force reload even if the same stage was already resident.
    write('_world_loaded',255)
    started=clock()
    cmd('set pause off')
    until(lambda:read('_world_loaded')==stage)
    load_seconds=clock()-started
    advance(.15)
    cmd('set pause on')
    raw=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
    actual=vram();equal=True
    for f in range(8):
        base=f*16384
        for lo,hi in [(0,0x1800),(0x2000,0x3800),(0x3840,0x3AC0)]:
            equal=equal and actual[base+lo:base+hi]==raw[base+lo:base+hi]
    check(f'stage-{stage+1}-native-background-readback',equal,checked_bytes=103424,load_seconds=round(load_seconds,3))
    write('_stage_banner',0)
    cmd('set pause off')
    advance(.1)
    t0=clock();f0=read('_frame_counter',2)
    advance(2)
    fps=((read('_frame_counter',2)-f0)&65535)/(clock()-t0)
    check(f'stage-{stage+1}-update-rate',fps>25,fps=round(fps,2))
    fm=[]
    for i in range(4):
        fm.append(cmd('binary encode hex [debug read_block {MSX Music regs} 0 64]'))
        advance(.13)
    check(f'stage-{stage+1}-music-resumes-after-load',len(set(fm))>1,
          distinct_register_states=len(set(fm)))

    bp=cmd(f'debug set_bp {SYM["_draw_frame"]} {{}} {{debug break}}')
    until(lambda:cmd('debug breaked')=='1')
    pictures=[];times=[];cameras=[]
    for i in range(64):
        # Steer in both directions and fire; none of the scene pixels are
        # created on the PC. The debugger samples completed native frames.
        if i==0:cmd('keymatrixdown 8 17')
        if i==20:cmd('keymatrixup 8 16; keymatrixdown 8 128')
        if i==48:cmd('keymatrixup 8 128')
        p=SCRATCH/f'stage-{stage+1}-{i:02d}.png'
        screenshot(p)
        pictures.append(Image.open(p).convert('RGB'))
        times.append(clock())
        camera=read('_world_camera',2)
        cameras.append(camera if camera<32768 else camera-65536)
        cmd('debug cont')
        until(lambda:cmd('debug breaked')=='1')
    cmd('keymatrixup 8 145')
    cmd(f'debug remove_bp {bp}; debug cont')
    unique=len({hashlib.sha256(p.tobytes()).hexdigest() for p in pictures})
    check(f'stage-{stage+1}-native-moving-frames',unique>=24,unique_frames=unique,
          total_frames=len(pictures),camera_min=min(cameras),camera_max=max(cameras),
          consecutive_frame_fps=round((len(times)-1)/(times[-1]-times[0]),2))
    # GIF duration follows actual MSX frame timestamps, quantized to 10 ms.
    durations=[];accumulated=0
    for i in range(len(pictures)):
        elapsed=((times[i+1] if i+1<len(times) else times[i]+(times[-1]-times[-2]))-times[0])*1000
        rounded=round(elapsed/10)*10
        durations.append(max(10,rounded-accumulated));accumulated=rounded
    pictures[0].save(OUT/f'stage-{stage+1}.png')
    pictures[19].save(OUT/f'stage-{stage+1}-steer-left.png')
    pictures[47].save(OUT/f'stage-{stage+1}-steer-right.png')
    enlarged=[p.resize((640,480),Image.Resampling.NEAREST) for p in pictures]
    enlarged[0].save(OUT/f'stage-{stage+1}-native.gif',save_all=True,
                     append_images=enlarged[1:],duration=durations,loop=0,optimize=False)
    with Image.open(OUT/f'stage-{stage+1}-native.gif') as capture:
        exact=capture.n_frames==len(enlarged)
        for i,source in enumerate(enlarged):
            capture.seek(i)
            exact=exact and capture.convert('RGB').tobytes()==source.tobytes()
        check(f'stage-{stage+1}-native-gif-exact',exact,frames=capture.n_frames)

report={'emulator':cmd('openmsx_info version'),'rom':MANIFEST,
        'physical_hardware_tested':False,'visual_scenarios':'Stage and entity state seeded in RAM; ROM performs all rendering and input.',
        'native_capture':'64 consecutive MSX draw frames per stage; GIF timing from emulated timestamps.',
        'results':results}
(OUT/'world-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD CHECKS PASSED',flush=True)
