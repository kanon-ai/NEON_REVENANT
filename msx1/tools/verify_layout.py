"""Verify the released ROM's packed packets against the independent VRAM codec.

This inspects ROM bytes, not the generator's in-memory output. Pass --baseline
to additionally prove the previous edition's three scenes are unchanged.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from pcg_codec import verify_cycle, parse_packet

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs/msx1/v1.2'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    manifest=json.loads((OUT/'build-manifest.json').read_text())
    rom=(OUT/manifest['file']).read_bytes()
    assert len(rom)==524288 and rom[:2]==b'AB' and sha(rom)==manifest['sha256']
    reports=[];occupied=set();nonzero=0
    entries=manifest['packing']['packets']
    assert len(entries)==80 and {(e['stage'],e['phase']) for e in entries}=={(s,p) for s in range(5) for p in range(16)}
    for stage in range(5):
        initial=rom[(6+stage*2)*8192:(8+stage*2)*8192]
        assert initial==(ROOT/'assets'/f'world-{stage}.bin').read_bytes()
        packets=[]
        for phase in range(16):
            e=next(e for e in entries if (e['stage'],e['phase'])==(stage,phase))
            assert manifest['packing']['first_packet_bank']<=e['bank']<64
            assert 0<=e['offset'] and e['offset']+e['bytes']<=8192
            start=e['bank']*8192+e['offset'];end=start+e['bytes']
            positions=set(range(start,end));assert not positions&occupied
            occupied|=positions;nonzero+=bool(e['offset'])
            packet=rom[start:end]
            assert sha(packet)==e['sha256']
            assert packet==(ROOT/'assets'/f'phase-{stage}-{phase:02}.bin').read_bytes()
            parse_packet(packet);packets.append(packet)
        frames=np.load(ROOT/'assets'/f'frames-{stage}.npy')
        reports.append({'stage':stage,**verify_cycle(initial,packets,frames)})
    assert nonzero>0,'Packed-location readback was not exercised'
    assert rom[manifest['allocated_bytes']:]==bytes([255])*(len(rom)-manifest['allocated_bytes'])
    preserved=[]
    if args.baseline:
        for old in range(3):
            for name in [f'world-{old}.bin',f'frames-{old}.npy',*[f'phase-{old}-{p:02}.bin' for p in range(16)]]:
                new=name.replace(f'-{old}',f'-{old+1}',1)
                a=(args.baseline/name).read_bytes();b=(ROOT/'assets'/new).read_bytes()
                assert a==b,f'Original scene changed: {name} -> {new}'
                preserved.append({'before':name,'after':new,'sha256':sha(a)})
        for name in ['sprite-patterns.bin','sprite-records.bin']:
            assert (args.baseline/name).read_bytes()==(ROOT/'assets'/name).read_bytes()
    report={'passed':True,'rom_sha256':sha(rom),'rom_bytes':len(rom),
            'allocated_bytes':manifest['allocated_bytes'],'free_bytes':manifest['free_bytes'],
            'packets':80,'packets_at_nonzero_offset':nonzero,'overlaps':0,
            'worlds':reports,'preserved_original_assets':preserved,
            'validation':'ROM bytes decoded offline; native execution is checked separately.'}
    (OUT/'layout-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('worlds','preserved_original_assets')},indent=2))

if __name__=='__main__':main()
