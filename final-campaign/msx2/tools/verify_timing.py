"""Native three-minute Z80/IM2 soak and VBlank page-switch audit.

Scenario RAM selects a third-stage boss and replenishes shields for the soak.
The emulator is unthrottled for this longevity check; it is not an FPS test.
"""
from pathlib import Path
import json,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'outputs/msx2'
S=json.loads((ROOT/'work/build/symbols.json').read_text());M=json.loads((OUT/'build-manifest.json').read_text())
def cmd(s):
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18802',data=s.encode(),method='POST'),timeout=30).read().decode().strip()
def put(n,v,size=1):cmd(';'.join(f'debug write memory {S[n]+i} {(v>>(8*i))&255}' for i in range(size)))
def read(n,size=1):return int(cmd('expr {'+'+'.join(f'{1<<(i*8)}*[debug read memory {S[n]+i}]' for i in range(size))+'}'))
def stamp():return float(cmd('machine_info time'))
def block(a,n):return bytes.fromhex(cmd(f'binary encode hex [debug read_block memory {a} {n}]'))
cmd('set pause on;keymatrixup 8 255')
for n,v,size in [('_mode',2,1),('_stage',2,1),('_world_loaded',255,1),('_shield',6,1),('_boss_hp',65000,2),('_player_x',128,2),('_player_y',135,2),('_boss_clock',0,2),('_hurt_clock',60,1),('_bomb_flash',0,1),('_boss_flash',0,1),('_old_keys',0,1)]:put(n,v,size)
for name,stride,count in [('_foes',12,9),('_shots',9,14),('_fx',7,7)]:cmd(';'.join(f'debug write memory {S[name]+i*stride} 0' for i in range(count)))
cmd('set pause off;set throttle false')
deadline=time.monotonic()+30
while read('_world_loaded')!=2:
    assert time.monotonic()<deadline,'stage load timeout';time.sleep(.01)
cmd('set page_switches 0;set bad_switches 0;set irq_samples 0;set min_sp 65535')
page_bp=cmd(f'debug set_bp {S["_gfx_sprite_page"]} {{}} {{incr ::page_switches;if {{!([debug read {{VDP status regs}} 2]&64)}} {{incr ::bad_switches}}}}')
irq_bp=cmd(f'debug set_bp {S["_gfx_irq"]} {{}} {{incr ::irq_samples;if {{[reg SP]<$::min_sp}} {{set ::min_sp [reg SP]}}}}')
try:
    cmd('keymatrixdown 8 1')
    start=stamp();f0=read('_frame_counter',2);latest=start;wall=time.monotonic()
    while latest<start+180:
        put('_shield',6);put('_hurt_clock',60)
        t=stamp()
        if t>latest:latest=t;wall=time.monotonic()
        assert time.monotonic()-wall<15,'emulated clock stalled'
        time.sleep(.01)
    elapsed=stamp()-start;f1=read('_frame_counter',2)
    switches=int(cmd('set page_switches'));bad=int(cmd('set bad_switches'))
    interrupts=int(cmd('set irq_samples'));min_sp=int(cmd('set min_sp'))
    vector=block(0xEE00,257);trampoline=block(0xEFEF,3)
    target=bytes([0xC3,S['_gfx_irq']&255,S['_gfx_irq']>>8])
    results=[
      {'name':'three-minute-clock-progress','passed':elapsed>=180 and ((f1-f0)&65535)>4500,'emulated_seconds':round(elapsed,3),'logic_updates':(f1-f0)&65535},
      {'name':'all-display-page-switches-in-VBlank','passed':switches>1000 and bad==0,'switches':switches,'outside_vblank':bad},
      {'name':'IM2-vector-and-trampoline-intact','passed':vector==bytes([0xEF])*257 and trampoline==target,'irq_samples':interrupts},
      {'name':'stack-stays-above-reserved-IRQ-area','passed':min_sp>=0xF000,'lowest_sampled_irq_sp':hex(min_sp)},
      {'name':'boss-simulation-still-running','passed':read('_mode')==2,'mode':read('_mode')},
    ]
    report={'rom':M,'physical_hardware_tested':False,'scenario':'Stage 3 boss seeded in RAM, auto fire held and shield/invulnerability replenished for 180 emulated seconds; unthrottled longevity check, not performance benchmark. IRQ entry samples stack depth.','results':results}
    (OUT/'timing-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    for result in results:print(result,flush=True)
    assert all(r['passed'] for r in results)
finally:
    cmd(f'debug remove_bp {page_bp};debug remove_bp {irq_bp};keymatrixup 8 1;set throttle true;set speed 100')
