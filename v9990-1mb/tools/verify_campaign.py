"""Native 1 MiB campaign checks. Stage/boss scenarios are explicitly RAM seeded."""
from pathlib import Path
import json,hashlib,time
from emulator_support import OpenMSX,tcl_word
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';S=json.loads((ROOT/'work/build/symbols.json').read_text())
ROM=OUT/'NEON_REVENANT-V9990-1MB-final.rom'
manifest=json.loads((OUT/'build-manifest.json').read_text());results=[]
def check(name,ok,**details):
    result=dict(name=name,passed=bool(ok),**details);results.append(result);print(result,flush=True);assert ok,name
with OpenMSX(work=ROOT/'work',executable='C:/Program Files/openMSX/openmsx_normal.exe') as e:
    e.command('machine Panasonic_FS-A1ST;ext gfx9000')
    e.command('set power off;cartb '+tcl_word(ROM.resolve().as_posix())+' -romtype ASCII8;set power on');e.run_for(20)
    def read(n,size=1,signed=False):return e.read_symbol(S,n,size,signed)
    def put(n,v,size=1):e.write_block('memory',S[n],int(v).to_bytes(size,'little',signed=v<0))
    def vram():
        p=e.read_block('Sunrise GFX9000 VRAM',0,524288);a=bytearray(524288);a[0::2]=p[:262144];a[1::2]=p[262144:];return bytes(a)
    def tap(row,mask):e.key(row,mask);e.run_for(.15);e.key(row,mask,False);e.run_for(.12)
    def resident(stage):
        for _ in range(80):
            if read('_world_loaded')==stage:return
            e.run_for(.25)
        raise AssertionError(('world load',stage,read('_world_loaded')))
    check('ROM-1MiB',len(ROM.read_bytes())==1048576,sha256=hashlib.sha256(ROM.read_bytes()).hexdigest())
    check('boot-title',read('_mode')==0 and read('_frame_counter',2)>0)
    check('R800-DRAM',bool(e.read_block('S1990 regs',6,1)[0]&32)==False,register6=e.read_block('S1990 regs',6,1)[0])
    feature=(ROOT/'assets/feature.bin').read_bytes()
    check('upper-ROM-feature-upload',vram()[0x7e000:0x7fe00]==feature[:7680],bank=manifest['feature']['bank'])
    # Explicitly select banks on both sides of 512 KiB and the final bank.
    saved=e.read_block('memory',0x6000,8192)
    for bank in [63,64,127]:
        e.write_block('memory',0x6800,bytes([bank]));check('mapper-bank-'+str(bank),e.read_block('memory',0x6000,8192)==ROM.read_bytes()[bank*8192:(bank+1)*8192])
    # The next draw forces a fresh stream and restores its own bank.
    put('_world_loaded',255);e.run_for(3);resident(0)
    tap(8,1);check('fire-starts-episode0',read('_mode')==1 and read('_stage')==0 and read('_bombs')==3)
    bp=e.command(f'debug set_bp {S["_sound_tick"]} {{}} {{lappend ::audio_stamp [machine_info time]}}')
    for stage in range(5):
        put('_stage',stage);put('_stage_clock',0,2);put('_mode',1);put('_world_loaded',255);put('_shield',6);put('_hurt_clock',255);put('_wave_number',0,2)
        e.write_block('memory',S['_foes'],bytes(14*9));e.write_block('memory',S['_shots'],bytes(9*14));e.run_for(.1);resident(stage)
        expected=(ROOT/'assets/world'/f'stage-{stage+1}.bin').read_bytes()
        check('world-'+str(stage)+'-VRAM',vram()[0x24000:0x7e000]==expected)
        seen=set();e.command('set ::audio_stamp {}');t0=float(e.command('machine_info time'));f0=read('_frame_counter',2)
        for _ in range(60):
            put('_shield',6);put('_hurt_clock',255);e.run_for(.2)
            foes=e.read_block('memory',S['_foes'],14*9)
            for i in range(9):
                if foes[i*14]:seen.add(foes[i*14+4])
        stamps=list(map(float,e.command('set ::audio_stamp').split()));dt=[b-a for a,b in zip(stamps,stamps[1:])]
        check('stage-'+str(stage)+'-patterns',seen==set(range(stage+2 if stage<2 else 6)),patterns=sorted(seen))
        check('stage-'+str(stage)+'-audio',len(dt)>300 and max(dt)<.036,mean=sum(dt)/len(dt),maximum=max(dt))
        fps=((read('_frame_counter',2)-f0)&65535)/(float(e.command('machine_info time'))-t0)
        check('stage-'+str(stage)+'-renders',fps>20,updates_per_second=fps)
        put('_mode',1);put('_shield',6);put('_hurt_clock',255);put('_stage_clock',[900,1200,1320,1440,1560][stage]-1,2)
        e.run_for(.12);check('stage-'+str(stage)+'-boss-entry',read('_mode')==2 and read('_boss_hp',2)==[70,100,140,180,240][stage])
        if stage==4:
            for hp,phase in [(230,0),(150,1),(70,2)]:
                put('_boss_hp',hp,2);e.run_for(.2);check('final-phase-'+str(phase),read('_final_phase')==phase)
        # Pause the boss and verify simulation clock and FM/PSG silence.
        tap(7,4);check('stage-'+str(stage)+'-pause',read('_mode')==6)
        bc=read('_boss_clock',2);e.run_for(.2);check('stage-'+str(stage)+'-pause-freezes',read('_boss_clock',2)==bc)
        check('stage-'+str(stage)+'-PSG-muted',e.read_block('PSG regs',8,3)==bytes(3))
        fm=e.read_block('MSX Music regs',0,64);check('stage-'+str(stage)+'-FM-muted',not any(x&16 for x in fm[32:41]) and not(fm[14]&31))
        tap(7,4);check('stage-'+str(stage)+'-resume',read('_mode')==2)
        # Actual fire input deals the last point; RAM only establishes the scenario.
        put('_boss_hp',1,2);put('_boss_clock',0,2);put('_player_x',128,2);put('_player_y',140,2);put('_shot_clock',0)
        e.key(8,1);e.run_for(.2);e.key(8,1,False)
        check('stage-'+str(stage)+'-boss-defeat',read('_mode')==3)
        e.run_for(6)
        check('stage-'+str(stage)+'-transition',read('_mode')==(5 if stage==4 else 1) and read('_stage')==(4 if stage==4 else stage+1),mode=read('_mode'),stage=read('_stage'),transition=read('_transition_clock'))
    e.command(f'debug remove_bp {bp}')
    e.run_for(2);tap(8,1);check('clear-restart',read('_mode')==1 and read('_stage')==0);resident(0);e.run_for(.3)
    x=read('_player_x',2);e.key(8,16);e.run_for(.2);e.key(8,16,False);check('left-input',read('_player_x',2)<x)
    b=read('_bombs');tap(5,32);check('NOVA-input',read('_bombs')==b-1)
    put('_shield',0);put('_mode',4);put('_transition_clock',40);tap(8,1);check('gameover-retry',read('_mode')==1 and read('_shield')==6)
    check('native-VDP-timing',e.timing_violations()==0,count=e.timing_violations())
(OUT/'campaign-verification.json').write_text(json.dumps(dict(passed=True,sha256=hashlib.sha256(ROM.read_bytes()).hexdigest(),physical_hardware_tested=False,method='openMSX FS-A1ST + GFX9000; RAM-seeded stage and boss scenarios; actual keyboard inputs',results=results),indent=2))
