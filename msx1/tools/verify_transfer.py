"""Native isolated PCG packet-reader checks, restoring the paused machine."""
from pathlib import Path
import hashlib,json,struct,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'outputs/msx1/v1.1'
S=json.loads((ROOT/'work/build/symbols.json').read_text());M=json.loads((OUT/'build-manifest.json').read_text())
def cmd(s):return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18801',data=s.encode()),timeout=25).read().decode().strip()
def block(device,address,size):return bytes.fromhex(cmd(f'binary encode hex [debug read_block {{{device}}} {address} {size}]'))
def write(device,address,data):cmd(f'debug write_block {{{device}}} {address} [binary format H* {data.hex()}]')
cmd('debug break;set pause off')
registers=block('CPU regs',0,28)
saved={('memory',0xE800):block('memory',0xE800,1024),('memory',0xF0F0):block('memory',0xF0F0,32),('VRAM',0x0800):block('VRAM',0x0800,1024)}
bp=cmd('debug set_bp 57328 {} {debug break}')
results=[]
try:
    executed=block(cmd('lindex [machine_info external_slot slota] 2'),0,524288)
    assert hashlib.sha256(executed).hexdigest()==M['sha256']
    for size in [0,1,255,256,257,511,512,768]:
        payload=bytes((i*37+size)%256 for i in range(size))
        packet=(struct.pack('<HH',0x0800,size)+payload+bytes(4)) if size else bytes(4)
        write('memory',0xE800,packet);write('memory',0xF100,struct.pack('<HH',0xDFF0,0xE800))
        write('VRAM',0x0800,saved[('VRAM',0x0800)])
        cpu=bytearray(registers)
        cpu[16:24]=struct.pack('>HHHH',4660,22136,S['_gfx_patch'],0xF100)
        write('CPU regs',0,cpu);cmd('debug cont')
        deadline=time.monotonic()+10
        while cmd('debug breaked')!='1':
            assert time.monotonic()<deadline,'PCG transfer did not return';time.sleep(.003)
        expected=payload+saved[('VRAM',0x0800)][size:]
        passed=block('VRAM',0x0800,1024)==expected and block('CPU regs',16,4)==bytes.fromhex('12345678')
        results.append({'name':f'native-packet-length-{size}','passed':passed,'bytes':size,'IX_IY_preserved':True})
        assert passed,results[-1]
finally:
    for (device,address),data in saved.items():write(device,address,data)
    write('CPU regs',0,registers)
    cmd(f'debug remove_bp {bp};set pause on;debug cont')
report={'rom':M,'physical_hardware_tested':False,'scenario':'Paused CPU called the ROM packet reader with scratch-RAM arguments; game registers, RAM and tested VRAM were restored.','results':results}
(OUT/'transfer-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(results,indent=2))
