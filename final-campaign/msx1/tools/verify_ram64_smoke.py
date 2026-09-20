"""Compatibility smoke on the same MSX1 with its original 64 KiB RAM size."""
import hashlib,json,time,urllib.request
from ram32_test_config import ROOT, RELEASE, STANDARD, TIMING_SETUP

symbols=json.loads((ROOT/'work/build/symbols.json').read_text())
manifest=json.loads((RELEASE/'build-manifest.json').read_text())
results=[]
def cmd(s):
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18801',data=s.encode()),timeout=25).read().decode().strip()
def read(name,size=1):
    address=symbols[name]
    return sum(int(cmd(f'debug read memory {address+i}'))<<(8*i) for i in range(size))
def wait(test,seconds=20):
    deadline=time.monotonic()+seconds
    while not test():
        assert time.monotonic()<deadline,'Smoke test timed out'
        time.sleep(.02)
def advance(seconds):
    target=float(cmd('machine_info time'))+seconds
    wait(lambda:float(cmd('machine_info time'))>=target)
def tap(row,mask):
    cmd(f'keymatrixdown {row} {mask}');advance(.15)
    cmd(f'keymatrixup {row} {mask}');advance(.15)
def check(name,value,**evidence):
    results.append({'name':name,'passed':bool(value),**evidence})
    print(name,'PASS' if value else 'FAIL',flush=True)
    assert value,name

cmd('set pause off;set speed 100;set limitsprites true;set accuracy pixel')
cmd(TIMING_SETUP)
wait(lambda:int(cmd('debug read {VDP regs} 1'))==195)
check('64KiB-machine',cmd('machine_info config_name')=='NEON_MSX1_RAM64_'+STANDARD.upper() and int(cmd('debug size {Main RAM}'))==65536)
check('16KiB-VRAM',int(cmd('debug size {physical VRAM}'))==16384)
rom=bytes.fromhex(cmd('binary encode hex [debug read_block [lsearch -inline [debug list] {*'+manifest['file']+'}] 0 524288]'))
check('same-ROM-sha256',hashlib.sha256(rom).hexdigest()==manifest['sha256'])
check('title-on-boot',read('_mode')==0)
tap(8,1);wait(lambda:read('_world_loaded')==0)
check('Episode0-start',read('_mode')==1 and read('_stage')==0)
x=read('_player_x',2);cmd('keymatrixdown 8 16');advance(.3);cmd('keymatrixup 8 16')
check('keyboard-movement',read('_player_x',2)<x)
tap(7,4);check('pause',read('_mode')==6)
clock=read('_stage_clock',2);advance(.3);check('pause-freezes-stage',read('_stage_clock',2)==clock)
tap(7,4);check('resume',read('_mode')==1)
bombs=read('_bombs');tap(5,32);check('bomb',read('_bombs')==bombs-1)
check('no-too-fast-VRAM-access',int(cmd('set ::neon_fast_vram_count'))==0)
cmd(f'openmsx::internal_screenshot -raw {{{(RELEASE/"ram64-smoke.png").as_posix()}}}')
report={'machine':cmd('machine_info config_name'),'emulator':cmd('openmsx_info version'),'physical_ram_bytes':65536,'rom_sha256':manifest['sha256'],'scope':'Fresh boot and keyboard-only Episode0 movement, pause, resume and bomb smoke; full campaign scenarios are covered by the 32 KiB suites.','physical_hardware_tested':False,'results':results}
(RELEASE/'ram64-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
