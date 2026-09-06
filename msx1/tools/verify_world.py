"""Native TMS9918 VRAM/SAT verification and real ROM animation capture.

Requires the development bridge on localhost:18801. Scenarios are selected
in RAM; every pixel, input response and sound register write comes from ROM.
"""
from pathlib import Path
import hashlib,json,time,urllib.request
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'outputs/msx1'
SYM=json.loads((ROOT/'work/build/symbols.json').read_text())
MANIFEST=json.loads((OUT/'build-manifest.json').read_text());results=[]
SCRATCH=ROOT/'work/captures';SCRATCH.mkdir(exist_ok=True)

def cmd(s):
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18801',data=s.encode()),timeout=25).read().decode().strip()
def read(n,size=1):
    a=SYM[n];return int(cmd(f'expr {{[debug read memory {a}]'+(f'+256*[debug read memory {a+1}]' if size==2 else '')+'}'))
def put(n,v,size=1):cmd(';'.join(f'debug write memory {SYM[n]+i} {(v>>(8*i))&255}' for i in range(size)))
def block(dev,a,n):return bytes.fromhex(cmd(f'binary encode hex [debug read_block {{{dev}}} {a} {n}]'))
def clock():return float(cmd('machine_info time'))
def until(test):
    end=time.monotonic()+30
    while not test():
        assert time.monotonic()<end,'emulator timeout';time.sleep(.008)
def advance(seconds):
    target=clock()+seconds;until(lambda:clock()>=target)
def check(name,passed,**evidence):
    results.append(dict(name=name,passed=bool(passed),**evidence));print(name,'PASS' if passed else 'FAIL',evidence,flush=True);assert passed,name
def shot(path):cmd(f'openmsx::internal_screenshot -raw {{{path.as_posix()}}}')
def clear_entities():
    for n,stride,count in [('_foes',12,6),('_shots',9,8),('_fx',7,4)]:
        cmd(';'.join(f'debug write memory {SYM[n]+i*stride} 0' for i in range(count)))
    put('_pickup_on',0)
def setup(stage,mode=1):
    cmd('set pause on')
    for n,v,size in [('_mode',mode,1),('_stage',stage,1),('_stage_clock',0,2),('_world_loaded',255,1),
      ('_stage_banner',0,1),('_player_x',128,2),('_player_y',166,2),('_shield',6,1),('_bombs',3,1),
      ('_hurt_clock',0,1),('_bomb_flash',0,1),('_old_keys',0,1),('_keys',0,1),('_frame_counter',0,2)]:put(n,v,size)
    clear_entities();started=clock();cmd('set pause off');until(lambda:read('_world_loaded')==stage);return clock()-started
def breakpoint():
    bp=cmd(f'debug set_bp {SYM["_draw_frame"]} {{}} {{debug break}}');until(lambda:cmd('debug breaked')=='1');return bp
def frame():cmd('debug cont');until(lambda:cmd('debug breaked')=='1')
def unbreak(bp):cmd(f'debug remove_bp {bp};debug cont')

cmd('set speed 100;set limitsprites true;set accuracy pixel;set videosource MSX;set pause off')
check('target-is-original-MSX',cmd('machine_info config_name')=='C-BIOS_MSX1_JP' and 'TMS99X8A' in cmd('machine_info device VDP'))
check('physical-VRAM-16KiB',int(cmd('debug size {physical VRAM}'))==16384)
check('normal-Z80-speed',int(cmd('machine_info z80_freq'))==3579545,hz=int(cmd('machine_info z80_freq')))
actual_rom=bytes.fromhex(cmd('binary encode hex [debug read_block [lindex [machine_info external_slot slota] 2] 0 524288]'))
check('executed-ROM-sha256',hashlib.sha256(actual_rom).hexdigest()==MANIFEST['sha256'],sha256=hashlib.sha256(actual_rom).hexdigest())
check('sprite-limit-enabled',cmd('set limitsprites')=='true')
for stage in range(3):
    load_time=setup(stage);advance(.2);bp=breakpoint()
    v=block('VRAM',0,16384);source=(ROOT/'assets'/f'world-{stage}.bin').read_bytes()
    check(f'stage-{stage+1}-resident-pattern-color-readback',v[:0x1800]==source[:0x1800] and v[0x2000:0x3800]==source[0x2000:0x3800],checked_bytes=12288,load_seconds=round(load_time,3))
    check(f'stage-{stage+1}-resident-sprite-readback',v[0x1800:0x2000]==(ROOT/'assets/sprite-patterns.bin').read_bytes())
    pictures=[];times=[];phases=set();names=(ROOT/'assets'/f'names-{stage}.bin').read_bytes();psg=[]
    for i in range(64):
        if i==0:cmd('keymatrixdown 8 17')
        if i==20:cmd('keymatrixup 8 16;keymatrixdown 8 128')
        if i==48:cmd('keymatrixup 8 128')
        phase=read('_world_phase');phases.add(phase)
        assert block('VRAM',0x3840,640)==names[phase*640:(phase+1)*640],f'names phase {phase}'
        path=SCRATCH/f'stage-{stage+1}-{i:02d}.png';shot(path);pictures.append(Image.open(path).convert('RGB'));times.append(clock())
        psg.append(block('PSG regs',0,14));frame()
    cmd('keymatrixup 8 145');unbreak(bp)
    fps=(len(times)-1)/(times[-1]-times[0]);unique=len({p.tobytes() for p in pictures})
    check(f'stage-{stage+1}-8-native-name-phases',len(phases)==8,phases=sorted(phases))
    check(f'stage-{stage+1}-native-moving-frames',unique>=24,unique_frames=unique,frames=len(pictures),fps=round(fps,2))
    check(f'stage-{stage+1}-PSG-music-and-effects',len(set(psg))>3 and all((p[7]&0xC0)==0x80 for p in psg),distinct_states=len(set(psg)))
    durations=[];accumulated=0
    for i in range(len(pictures)):
        end=times[i+1] if i+1<len(times) else times[i]+times[-1]-times[-2]
        rounded=round((end-times[0])*100);durations.append(max(10,(rounded-accumulated)*10));accumulated=rounded
    pictures[0].save(OUT/f'stage-{stage+1}.png')
    pictures[0].save(OUT/f'stage-{stage+1}-native.gif',save_all=True,append_images=pictures[1:],duration=durations,loop=0)

# Freeze at the frame boundary and use real ESC input at every update phase.
setup(0);advance(.2);bp=breakpoint()
for phase in range(4):
    put('_frame_counter',phase,2);put('_mode',1);put('_old_keys',0);put('_keys',0)
    put('_hud_last_mode',1);cmd('keymatrixdown 7 4');frame();cmd('keymatrixup 7 4');frame()
    check(f'pause-phase-{phase}-mode',read('_mode')==6)
    nt=block('VRAM',0x3800+32,32);decoded=''.join(chr(c-160) if 192<=c<=255 else '?' for c in nt)
    check(f'pause-phase-{phase}-visible-label','PAUSED / ESC TO RESUME' in decoded,label=decoded.strip())
    c=read('_stage_clock',2);frame();frame();check(f'pause-phase-{phase}-stopped',read('_stage_clock',2)==c)
    cmd('keymatrixdown 7 4');frame();cmd('keymatrixup 7 4');frame();check(f'pause-phase-{phase}-resumed',read('_mode')==1)
cmd('keymatrixdown 5 32');frame();cmd('keymatrixup 5 32');frame()
check('NOVA-before-pause-active',read('_bomb_flash')>0)
cmd('keymatrixdown 7 4');frame();cmd('keymatrixup 7 4');frame()
label=''.join(chr(c-160) if 192<=c<=255 else '?' for c in block('VRAM',0x3820,32))
check('NOVA-then-pause-visible-label',read('_mode')==6 and 'PAUSED / ESC TO RESUME' in label,label=label.strip())
flash=read('_bomb_flash');frame();frame();check('NOVA-paused-flash-stops',read('_bomb_flash')==flash)
cmd('keymatrixdown 7 4');frame();cmd('keymatrixup 7 4');frame()
unbreak(bp)

# Deliberately dense renderer stress: no claim of a normal-play workload.
setup(2,6);put('_pause_previous',2);put('_boss_x',128,2);put('_boss_y',100,2);put('_boss_hp',180,2);put('_boss_flash',0)
bp=breakpoint();stress=[]
for crowded in [False,True]:
    if crowded:
        for i in range(8):
            x=(25+i*28)*4;y=(60+(i%3)*35)*4;data=[1,x&255,x>>8,y&255,y>>8,0,0,0,0]
            cmd(';'.join(f'debug write memory {SYM["_shots"]+i*9+j} {v}' for j,v in enumerate(data)))
        for i in range(6):
            data=[1,i%3,210,3,0,0,0,0,40+i*32,0,100,0]
            cmd(';'.join(f'debug write memory {SYM["_foes"]+i*12+j} {v}' for j,v in enumerate(data)))
    stamps=[]
    for i in range(20):frame();stamps.append(clock())
    n=read('_sprite_count');attrs=block('memory',SYM['_attr_buffer'],n*4+(n<32));base=int(cmd('debug read {VDP regs} 5'))*128
    check(('crowded' if crowded else 'boss')+'-SAT-readback',block('VRAM',base,len(attrs))==attrs,records=n,dropped=read('_sprite_dropped'))
    counts=[0]*192
    for i in range(n):
        y=(attrs[4*i]+1)&255
        for row in range(max(0,y),min(192,y+32)):counts[row]+=1
    fps=(len(stamps)-1)/(stamps[-1]-stamps[0]);item={'scene':'crowded' if crowded else 'boss','fps':round(fps,2),'max_sprites_per_scanline':max(counts),'scanlines_above_four':sum(v>4 for v in counts)}
    check(item['scene']+'-renderer-progress',fps>12,**item);stress.append(item);shot(OUT/(item['scene']+'-native.png'))
unbreak(bp)

report={'rom':MANIFEST,'machine':'C-BIOS_MSX1_JP','video':'TMS99X8A, physical 16KiB VRAM','physical_hardware_tested':False,
 'scenario_seeding':'Stage selection, all pause phases and stationary crowded scenarios use RAM injection; drawing/input/sound execute in the ROM.',
 'sprite_limit':'32 total, 4 per scanline, 1 color per sprite; lines above four can disappear or flicker on real hardware.',
 'results':results,'stress':stress}
(OUT/'world-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('ALL NATIVE WORLD CHECKS PASSED')
