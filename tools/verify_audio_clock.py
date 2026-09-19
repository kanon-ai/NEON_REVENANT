"""Native openMSX audio-clock regression test for the four non-MSX1 editions.
Requires the local CLI-only bridge on 18801. Uses seeded stage scenarios.
"""
import json,time,html,urllib.request,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/audio-clock';OUT.mkdir(exist_ok=True)
def cmd(s):
    try:return html.unescape(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18801',data=s.encode()),timeout=20).read().decode().strip())
    except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode())
def wait(seconds):
    target=float(cmd('machine_info time'))+seconds;deadline=time.monotonic()+45
    while float(cmd('machine_info time'))<target:
        assert time.monotonic()<deadline,'emulator stalled'
        time.sleep(.025)
def read(n,size=1):return int.from_bytes(bytes.fromhex(cmd(f'binary encode hex [debug read_block memory {S[n]} {size}]')),'little')
def put(n,v):cmd(f'debug write memory {S[n]} {v}')
cmd('set ::audio_original_machine [activate_machine]')
for row in cmd('debug list_bp').splitlines():
    if '::audio_stamp' in row:cmd('debug remove_bp '+row.split()[0])
results=[]
for folder,rom,machine,ext in [('', 'outputs/NEON_REVENANT-v1.2.rom','Panasonic_FS-A1ST',True),('turbor','outputs/turbor/NEON_REVENANT-TurboR-v1.0.rom','Panasonic_FS-A1ST',False),('msx2','outputs/msx2/NEON_REVENANT-MSX2-v1.0.rom','C-BIOS_MSX2_JP',False),('v9990-feature-lab','v9990-feature-lab/outputs/NEON_REVENANT-V9990-feature-lab-v0.1.rom','Panasonic_FS-A1ST',True)]:
    path=ROOT/rom
    if not path.exists():
        candidates=list((ROOT/folder/'outputs').glob('*.rom')) if folder=='v9990-feature-lab' else []
        assert len(candidates)==1,(rom,candidates)
        path=candidates[0]
    S=json.loads((ROOT/folder/'work/build/symbols.json').read_text())
    cmd('set ::test_machine [create_machine];${::test_machine}::load_machine '+machine+';activate_machine $::test_machine;set power off')
    if ext:cmd('ext gfx9000')
    cmd(f'cart {{{path.as_posix()}}} -romtype ASCII8;set power on;set pause off;set throttle off;debug cont')
    wait(10)
    assert read('_mode')==0
    bp=cmd(f'debug set_bp {S["_sound_tick"]} {{}} {{lappend ::audio_stamp [machine_info time]}}')
    checks=[]
    for stage in range(3):
        cmd('set pause on');put('_stage',stage);put('_mode',1);put('_world_loaded',255);put('_shield',6);put('_hurt_clock',255)
        cmd('set pause off');wait(1)
        deadline=float(cmd('machine_info time'))+15
        while read('_world_loaded')!=stage and float(cmd('machine_info time'))<deadline:wait(.1)
        assert read('_world_loaded')==stage,(folder,stage,read('_world_loaded'))
        # Resident background patterns must survive IRQs during ROM/VRAM transfer.
        expected=(ROOT/folder/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
        if ext:
            physical=bytes.fromhex(cmd('binary encode hex [debug read_block {Sunrise GFX9000 VRAM} 0 524288]'))
            logical=bytearray(524288);logical[0::2]=physical[:262144];logical[1::2]=physical[262144:]
            actual=bytes(logical[147456:516096])
            assert actual==expected,(folder,stage,'background VRAM')
        else:
            actual=bytes.fromhex(cmd('binary encode hex [debug read_block VRAM 0 131072]'))
            for frame in range(8):
                for offset in [0,8192]:
                    a=frame*16384+offset
                    assert actual[a:a+6144]==expected[a:a+6144],(folder,stage,frame,offset)
        cmd('set ::audio_stamp {}');wait(2)
        ts=list(map(float,cmd('set ::audio_stamp').split()));dt=[b-a for a,b in zip(ts,ts[1:])]
        assert len(ts)>=58 and max(dt)<.036,(folder,stage,len(ts),max(dt))
        checks.append(dict(stage=stage,count=len(ts),minimum=min(dt),maximum=max(dt),mean=sum(dt)/len(dt)))
    # Enter at an interruptible foreground point before substituting a RAM loop.
    cmd('set throttle on;set speed 100')
    bp2=cmd(f'debug set_bp {S["_input_read"]} {{}} {{debug break}}')
    time.sleep(.15)
    cmd('debug break')
    oldregs=cmd('binary encode hex [debug read_block {CPU regs} 0 28]');regs=bytearray.fromhex(oldregs)
    assert regs[27]&1,(folder,'interrupts disabled at foreground')
    cmd(f'debug remove_bp {bp2}')
    old=cmd('binary encode hex [debug read_block memory 62336 3]')
    regs[20:22]=(62336).to_bytes(2,'big')
    cmd(f'debug write_block memory 62336 [binary format H* c380f3];debug write_block {{CPU regs}} 0 [binary format H* {regs.hex()}];set ::audio_stamp {{}};debug cont')
    wait(2)
    cmd('debug break');count=len(cmd('set ::audio_stamp').split())
    assert 58<=count<=66,(folder,count)
    cmd(f'debug write_block memory 62336 [binary format H* {old}];debug write_block {{CPU regs}} 0 [binary format H* {oldregs}];debug cont')
    # Controller, pause and resume still work with concurrent audio.
    put('_mode',1);put('_shield',6);put('_hurt_clock',255)
    x=read('_player_x',2);cmd('keymatrixdown 8 16');wait(.25);cmd('keymatrixup 8 16');assert read('_player_x',2)<x
    cmd('keymatrixdown 7 4');wait(.15);cmd('keymatrixup 7 4');wait(.1);assert read('_mode')==6
    clock=read('_stage_clock',2);wait(.2);assert read('_stage_clock',2)==clock
    psg=bytes.fromhex(cmd('binary encode hex [debug read_block {PSG regs} 8 3]'));assert psg==bytes(3)
    if folder!='msx2':
        fm=bytes.fromhex(cmd('binary encode hex [debug read_block {MSX Music regs} 0 64]'))
        assert not any(v&16 for v in fm[32:41]) and not(fm[14]&31),'FM not silent during pause'
    cmd('keymatrixdown 7 4');wait(.15);cmd('keymatrixup 7 4');wait(.1);assert read('_mode')==1
    put('_bombs',3);bombs=read('_bombs');cmd('keymatrixdown 5 32');wait(.15);cmd('keymatrixup 5 32');assert read('_bombs')==bombs-1
    cmd(f'debug remove_bp {bp}')
    results.append(dict(edition=folder or 'v9990',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),stages=checks,main_loop_suspended_audio_ticks=count,controls_pause_resume=True,background_vram_matches=True,bomb_input=True,passed=True))
    print(results[-1],flush=True)
    cmd('set power off;activate_machine $::audio_original_machine;delete_machine $::test_machine')
(OUT/'verification.json').write_text(json.dumps(dict(passed=True,physical_hardware_tested=False,results=results),indent=2))
