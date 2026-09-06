"""Native sprite-table readback and deliberately crowded renderer scenarios."""
import hashlib,json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs/turbor'
S=json.loads((ROOT/'work/build/symbols.json').read_text())
manifest=json.loads((OUT/'build-manifest.json').read_text())
results=[]
def cmd(s):
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18791',data=s.encode(),method='POST'),timeout=25).read().decode().strip()
def block(dev,a,n):return bytes.fromhex(cmd(f'binary encode hex [debug read_block {{{dev}}} {a} {n}]'))
def read(s):return int(cmd(f'debug read memory {S[s]}'))
def put(s,v,n=1):
    cmd(';'.join(f'debug write memory {S[s]+i} {(v>>(i*8))&255}' for i in range(n)))
def check(name,passed,**evidence):
    print(name,'PASS' if passed else 'FAIL',evidence,flush=True)
    results.append(dict(name=name,passed=bool(passed),**evidence));assert passed,name
def until(f):
    end=time.monotonic()+25
    while not f():
        assert time.monotonic()<end,'timeout';time.sleep(.005)
def timestamp():return float(cmd('machine_info time'))
cmd('set limitsprites true;set accuracy pixel;set pause on')
check('hardware-sprite-limit-enabled',cmd('set limitsprites')=='true')
check('sprite-zero-transparent',int(cmd('debug read {VDP regs} 8'))==8)
put('_mode',6);put('_pause_previous',2);put('_stage',2);put('_world_loaded',255)
put('_player_x',128,2);put('_player_y',119,2);put('_boss_x',128,2);put('_boss_y',108,2)
put('_boss_hp',180,2);put('_hurt_clock',0);put('_bomb_flash',0);put('_boss_flash',0)
put('_keys',0);put('_old_keys',0);put('_frame_counter',0,2)
for name,stride,count in [('_foes',12,9),('_shots',9,14),('_fx',7,7)]:
    cmd(';'.join(f'debug write memory {S[name]+i*stride} 0' for i in range(count)))
put('_pickup_on',0)
cmd('set pause off');until(lambda:read('_world_loaded')==2)
bp=cmd(f'debug set_bp {S["_draw_frame"]} {{}} {{debug break}}');until(lambda:cmd('debug breaked')=='1')
for crowded in [False,True]:
    if crowded:
        for i in range(14):
            x=(34+i*14)*4;y=(40+(i%4)*30)*4
            values=[1,x&255,x>>8,y&255,y>>8,0,0,0,0]
            cmd(';'.join(f'debug write memory {S["_shots"]+i*9+j} {v}' for j,v in enumerate(values)))
        for i in range(9):
            values=[1,i%3,210,3,0,0,0,0,40+i*20,0,100,0]
            cmd(';'.join(f'debug write memory {S["_foes"]+i*12+j} {v}' for j,v in enumerate(values)))
    stamps=[]
    for frame in range(18):
        cmd('debug cont');until(lambda:cmd('debug breaked')=='1');stamps.append(timestamp())
    n=read('_sprite_count');page=1-read('_sprite_page')
    patterns=block('memory',S['_pattern_buffer'],n*32)
    colors=block('memory',S['_color_buffer'],n*16)
    attrs=block('memory',S['_attr_buffer'],n*4+(n<32))
    check(('crowded' if crowded else 'boss')+'-sprite-table-readback',
          block('VRAM',0x9800 if page else 0x1800,len(patterns))==patterns and
          block('VRAM',0xD800 if page else 0x5800,len(colors))==colors and
          block('VRAM',0xDA00 if page else 0x5A00,len(attrs))==attrs,
          records=n,dropped=read('_sprite_dropped'))
    counts=[0]*192
    for i in range(n):
        y=(attrs[i*4]+1)&255
        for row in range(max(0,y),min(192,y+32)):counts[row]+=1
    fps=(len(stamps)-1)/(stamps[-1]-stamps[0])
    check(('crowded' if crowded else 'boss')+'-renderer-progress',fps>=19,
          fps=round(fps,2),max_records_per_scanline=max(counts),
          scanlines_above_hardware_limit=sum(v>8 for v in counts))
    name='crowded-sprites' if crowded else 'boss-upper-position'
    cmd(f'openmsx::internal_screenshot -raw {{{(OUT/(name+".png")).as_posix()}}}')
cmd(f'debug remove_bp {bp};debug cont')
report={'rom':manifest,'physical_hardware_tested':False,
        'scenario':'Paused scene selected in RAM, followed by 14 projectiles and 9 opponents to exercise the 32-record and 8-per-line hardware limits; all drawing is ROM execution.',
        'results':results}
(OUT/'sprite-verification.json').write_text(json.dumps(report,indent=2)+'\n')
