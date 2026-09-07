"""Native openMSX integration checks. A running workspace emulator is required.
The gameplay checks inject controller input. Scenario checks explicitly seed
RAM to exercise distant states; they are not represented as a full playthrough.
"""
import urllib.request, time, json, hashlib, re
from pathlib import Path
from ram32_test_config import ROOT, RELEASE, OUT, STANDARD, MACHINE, STAGE_DURATIONS, TIMING_SETUP
SYM=json.loads((ROOT/'work/build/symbols.json').read_text())
MANIFEST=json.loads((RELEASE/'build-manifest.json').read_text())
ROM=(RELEASE/MANIFEST['file']).read_bytes()
assert hashlib.sha256(ROM).hexdigest()==MANIFEST['sha256']
results=[]
def cmd(s):
    r=urllib.request.Request('http://127.0.0.1:18801',data=s.encode(),method='POST')
    return urllib.request.urlopen(r,timeout=20).read().decode()
def read(n,size=1):
    a=SYM[n]
    return int(cmd(f'expr {{[debug read memory {a}]'+(f'+256*[debug read memory {a+1}]' if size==2 else '')+'}'))
def write(n,v,size=1):
    a=SYM[n];cmd(f'debug write memory {a} {v&255}'+(f';debug write memory {a+1} {v>>8}' if size==2 else ''))
def msxtime():return float(cmd('machine_info time'))
def advance(seconds):
    # set fastforward is deliberately off: timing uses actual emulated seconds.
    target=msxtime()+seconds
    while msxtime()<target:time.sleep(.025)
def key(row,mask,on):cmd(f'keymatrix{"down" if on else "up"} {row} {mask}')
def tap(row,mask):key(row,mask,True);advance(.15);key(row,mask,False);advance(.1)
def check(name,ok,**evidence):
    results.append(dict(name=name,passed=bool(ok),**evidence))
    print(name, 'PASS' if ok else 'FAIL',evidence,flush=True)
    if not ok:raise AssertionError(name)
def shot(name):cmd(f'openmsx::internal_screenshot -raw {{{(OUT/(name+".png")).as_posix()}}}')

def wait_world(stage):
    deadline=msxtime()+20
    while read('_world_loaded')!=stage and msxtime()<deadline:advance(.05)
    check(f'sector-{stage+1}-world-resident',read('_world_loaded')==stage)
    advance(.15)
cmd('set pause off; set speed 100; set limitsprites true; set accuracy pixel; set videosource MSX')
cmd(TIMING_SETUP)
# ROM is tested in native machine emulation, not a browser recreation.
deadline=time.monotonic()+20
while int(cmd('debug read {VDP regs} 0'))!=2 or int(cmd('debug read {VDP regs} 1'))!=0xC3:
    assert time.monotonic()<deadline,'boot timeout'
    time.sleep(.05)
check('target-machine',cmd('machine_info config_name').strip()==MACHINE,version=cmd('openmsx_info version'))
check('SCREEN2-mode',int(cmd('debug read {VDP regs} 0'))==2 and int(cmd('debug read {VDP regs} 1'))==0xC3)
check('no-V9990-attached','GFX9000' not in cmd('debug list'))
check('16KiB-VRAM',int(cmd('debug size {physical VRAM}'))==16384)
check('32KiB-RAM',int(cmd('debug size {Main RAM}'))==32768)
executed=bytes.fromhex(cmd('binary encode hex [debug read_block [lsearch -inline [debug list] {*'+MANIFEST['file']+'}] 0 524288]'))
check('executed-ROM-sha256',hashlib.sha256(executed).hexdigest()==MANIFEST['sha256'],sha256=hashlib.sha256(executed).hexdigest())
check('title-on-boot',read('_mode')==0)
# This unused guard lies below the stack, far above the linked static data.
# Populate it only while execution is stopped; check it after all scenarios.
cmd('set pause on;debug write_block memory 61440 [string repeat [binary format c 165] 256];set pause off')
deadline=msxtime()+20
while read('_frame_counter',2)==0 and msxtime()<deadline:advance(.05)
check('startup-first-frame',read('_frame_counter',2)>0)
shot('title')
tap(8,1);wait_world(0);check('fire-starts-game',read('_mode')==1 and read('_shield')==6 and read('_bombs')==3)
advance(.2)
x=read('_player_x',2);key(8,0x10,True);advance(.35);key(8,0x10,False)
left=read('_player_x',2);check('left-control',left<x,before=x,after=left)
key(8,0x80,True);advance(.35);key(8,0x80,False);check('right-control',read('_player_x',2)>left)
y=read('_player_y',2);key(8,0x20,True);advance(.3);key(8,0x20,False);check('up-control',read('_player_y',2)<y)
key(8,0x40,True);advance(.3);key(8,0x40,False);check('down-control',read('_player_y',2)>=y-4)
tap(7,4);check('pause-input',read('_mode')==6)
t=read('_stage_clock',2);advance(.3);check('pause-freezes-simulation',read('_stage_clock',2)==t)
tap(7,4);check('resume-input',read('_mode')==1)
old=read('_bombs');tap(5,0x20);check('bomb-key-consumes-one',read('_bombs')==old-1)
key(5,0x20,True);advance(.8);key(5,0x20,False);check('held-bomb-is-edge-triggered',read('_bombs')==old-2)
t0=msxtime();f0=read('_frame_counter',2);advance(3.0);t1=msxtime();f1=read('_frame_counter',2)
fps=((f1-f0)&65535)/(t1-t0);check('measured-game-update-rate',fps>20,fps=round(fps,2),emulated_seconds=round(t1-t0,3))
# Controlled target placed inside reticle; all hit detection remains ROM code.
cmd('set pause on');write('_stage_banner',0);write('_hurt_clock',0);write('_old_keys',0)
for i in range(6):cmd(f'debug write memory {SYM["_foes"]+12*i} 0')
foe=[1,0,80,1,0,0,100,0,128,0,119,0]
for i,v in enumerate(foe):cmd(f'debug write memory {SYM["_foes"]+i} {v}')
write('_player_x',128,2);write('_player_y',166,2);write('_shot_clock',0)
before=read('_score',2);cmd('set pause off');key(8,1,True);advance(.22);key(8,1,False)
check('reticle-shot-kills-target',read('_score',2)>before,before=before,after=read('_score',2));shot('combat')
# Damage and game-over use a native enemy projectile overlapping the craft.
cmd('set pause on');write('_shield',1);write('_hurt_clock',0);write('_bomb_flash',0)
px=read('_player_x',2)*4;py=(read('_player_y',2)-3)*4
proj=[1,px&255,px>>8,py&255,py>>8,0,0,0,0]
for i,v in enumerate(proj):cmd(f'debug write memory {SYM["_shots"]+i} {v}')
cmd('set pause off');advance(.18);check('collision-game-over',read('_mode')==4 and read('_shield')==0);shot('game-over')
advance(2);tap(8,1);check('retry-resets-state',read('_mode')==1 and read('_shield')==6 and read('_score',2)==0)
for stage in range(5):
    check(f'campaign-position-{stage}',read('_stage')==stage and read('_mode')==1)
    cmd('set pause on');write('_stage_clock',STAGE_DURATIONS[stage]-1,2);write('_stage_banner',0);write('_old_keys',0)
    cmd('set pause off');advance(.12)
    wait_world(stage)
    check(f'sector-{stage+1}-boss-entry',read('_mode')==2 and read('_boss_hp',2)>0)
    shot(f'boss-{stage+1}')
    # Seed final-hit scenario with an aligned craft; input and damage are real.
    cmd('set pause on');write('_boss_hp',1,2);write('_boss_clock',63,2);write('_player_x',128,2);write('_player_y',130,2);write('_shot_clock',0);write('_old_keys',0)
    cmd('set pause off');key(8,1,True);advance(.2);key(8,1,False)
    check(f'sector-{stage+1}-boss-defeat',read('_mode')==3)
    deadline=msxtime()+10
    while read('_mode')==3 and msxtime()<deadline:advance(.2)
    check(f'sector-{stage+1}-transition',read('_mode')==(5 if stage==4 else 1))
    if stage<4:wait_world(stage+1)
shot('ending')
check('five-stage-clear',read('_mode')==5 and read('_stage')==4)
guard=bytes.fromhex(cmd('binary encode hex [debug read_block memory 61440 256]'))
check('stack-lower-guard-preserved',guard==bytes([165])*256,address='F000-F0FF',bytes=256)
advance(2);tap(8,1)
check('clear-retry-starts-episode-zero',read('_mode')==1 and read('_stage')==0 and read('_shield')==6 and read('_bombs')==3)
rom=(RELEASE/MANIFEST['file']).read_bytes()
check('ROM-size-and-header',len(rom)==524288 and rom[:2]==b'AB',size=len(rom),sha256=hashlib.sha256(rom).hexdigest())
check('no-too-fast-VRAM-access',int(cmd('set ::neon_fast_vram_count'))==0,violations=int(cmd('set ::neon_fast_vram_count')))
report={'emulator':cmd('openmsx_info version').strip(),'rom':MANIFEST,'machine':MACHINE,'video_standard':STANDARD,'physical_ram_bytes':32768,'extension':None,'physical_hardware_tested':False,'scenario_seeding':'RAM seeds target hits, collisions, stage clocks and final boss hits; all five boss transitions and clear execute in ROM. This is not a keyboard-only full playthrough. A guard is placed in unused RAM below the stack.','stage_durations_frames':STAGE_DURATIONS,'results':results}
report['rom_slot']={'connector':'slota','primary_slot':int(cmd('machine_info external_slot slota').split()[0]),'mapper':'ASCII8','file':MANIFEST['file']}
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('ALL CHECKS PASSED')
