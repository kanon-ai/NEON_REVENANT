"""Native V9990 world readback, timing and frame captures.

Requires tools/emulator_host.mjs already running the current ROM. RAM seeds
only select the visual scenario; all rendering is executed by the MSX ROM.
"""
from pathlib import Path
import hashlib, json, time, urllib.request, re
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SYM=json.loads((ROOT/'work/build/symbols.json').read_text())
MANIFEST=json.loads((ROOT/'outputs/build-manifest.json').read_text())
VERSION=str(MANIFEST['version'])
assert re.fullmatch(r'\d+\.\d+(?:\.\d+)?',VERSION), 'Invalid release version'
assert tuple(map(int,VERSION.split('.'))) >= (1,2), 'Build v1.2 or newer before verifying; v1.1 evidence is preserved'
RELEASE='v'+VERSION
assert MANIFEST['file']==f'NEON_REVENANT-{RELEASE}.rom'
assert hashlib.sha256((ROOT/'outputs'/MANIFEST['file']).read_bytes()).hexdigest()==MANIFEST['sha256'], 'ROM differs from build manifest'
OUT=ROOT/'outputs'/RELEASE
OUT.mkdir(exist_ok=True)
SCRATCH=ROOT/'work'/f'world-captures-{RELEASE}'
SCRATCH.mkdir(exist_ok=True)
results=[]

def cmd(s):
    req=urllib.request.Request('http://127.0.0.1:18790',data=s.encode(),method='POST')
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
    raw=bytes.fromhex(cmd('binary encode hex [debug read_block {Sunrise GFX9000 VRAM} 0 524288]'))
    logical=bytearray(524288)
    logical[0::2]=raw[:262144]
    logical[1::2]=raw[262144:]
    return bytes(logical)

def screenshot(path):cmd(f'openmsx::internal_screenshot -raw {{{path.as_posix()}}}')

cmd('set pause off; set speed 100; set videosource GFX9000')
advance(.1)
cmd('set pause on')
atlas=(ROOT/'assets/vram.bin').read_bytes()
check('sprite-atlas-native-readback',vram()[0x10000:0x24000]==atlas,bytes=len(atlas),sha256=hashlib.sha256(atlas).hexdigest())
cmd('set pause off')

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
    check(f'stage-{stage+1}-native-decompression',vram()[0x24000:0x7e000]==raw,
          bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),load_seconds=round(load_seconds,3))
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
    check(f'stage-{stage+1}-native-moving-frames',unique>=48,unique_frames=unique,
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

cmd('set pause on')
write('_stage',0);write('_mode',0);write('_old_keys',0)
cmd('set pause off')
until(lambda:read('_world_loaded')==0)
advance(.2)
screenshot(OUT/'title.png')
report={'emulator':cmd('openmsx_info version'),'rom':MANIFEST,
        'physical_hardware_tested':False,'visual_scenarios':'Stage and entity state seeded in RAM; ROM performs all rendering and input.',
        'native_capture':'64 consecutive MSX draw frames per stage; GIF timing from emulated timestamps.',
        'results':results}
(ROOT/'outputs'/f'world-verification-{RELEASE}.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD CHECKS PASSED',flush=True)
