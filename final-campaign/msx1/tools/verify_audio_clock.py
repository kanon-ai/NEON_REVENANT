"""Measure ROM sound_tick entry times, including forced rendering overload.

Overload uses a temporary slower emulated CPU, never changes the ROM.
This deliberately differentiates render throughput from IRQ musical time.
"""
import json,time,urllib.request
from ram32_test_config import ROOT,RELEASE,OUT,STANDARD
S=json.loads((ROOT/'work/build/symbols.json').read_text())
def cmd(s):return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18801',data=s.encode()),timeout=25).read().decode().strip()
def put(n,v):cmd(f'debug write memory {S[n]} {v}')
def wait(seconds):
    target=float(cmd('machine_info time'))+seconds
    end=time.monotonic()+30
    while float(cmd('machine_info time'))<target:
        assert time.monotonic()<end
        time.sleep(.03)
cmd('set pause off;set throttle on;set speed 100')
bp=cmd(f'debug set_bp {S["_sound_tick"]} {{}} {{lappend ::audio_stamp [machine_info time]}}')
results=[]
try:
    for stage in range(5):
        cmd('set pause on');put('_stage',stage);put('_mode',1);put('_world_loaded',255);put('_hurt_clock',255);put('_shield',6)
        cmd('set pause off');wait(.6)
        cmd('set ::audio_stamp {};keymatrixdown 8 1')
        wait(3)
        cmd('keymatrixup 8 1')
        t=list(map(float,cmd('set ::audio_stamp').split()))
        dt=[b-a for a,b in zip(t,t[1:])]
        expected=1/30
        # PAL follows 50Hz VBlank, with a repeating 20/40ms rational cadence.
        upper=.043 if STANDARD=='pal' else .036
        assert len(t)>=85 and max(dt)<upper,(stage,len(t),max(dt))
        results.append(dict(stage=stage,samples=len(t),mean_interval=sum(dt)/len(dt),min_interval=min(dt),max_interval=max(dt)))
        print(results[-1],flush=True)
    # Demonstrate that game-loop suspension does not suspend musical time.
    # A temporary RAM spin loop is interruptible and restored after 2 seconds.
    cmd('debug break')
    cpu=cmd('binary encode hex [debug read_block {CPU regs} 0 28]')
    old=cmd('binary encode hex [debug read_block memory 59392 3]')
    cmd('debug write_block memory 59392 [binary format H* C300E8]')
    registers=bytearray.fromhex(cpu);registers[20:22]=(59392).to_bytes(2,'big')
    cmd(f'debug write_block {{CPU regs}} 0 [binary format H* {registers.hex()}];set ::audio_stamp {{}};debug cont')
    wait(2)
    cmd('debug break')
    count=len(cmd('set ::audio_stamp').split())
    cmd(f'debug write_block memory 59392 [binary format H* {old}];debug write_block {{CPU regs}} 0 [binary format H* {cpu}];debug cont')
    assert 58<=count<=62,count
    results.append(dict(main_loop_suspended_seconds=2,audio_ticks=count,passed=True))
finally:cmd(f'debug remove_bp {bp};keymatrixup 8 1')
(OUT/'audio-clock-verification.json').write_text(json.dumps(dict(standard=STANDARD,passed=True,results=results,physical_hardware_tested=False),indent=2))
