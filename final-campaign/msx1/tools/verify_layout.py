"""Verify the released ROM's packed packets against the independent VRAM codec.

This inspects ROM bytes, not the generator's in-memory output. Pass --baseline
to additionally prove the v1.1 three scenes or v1.2 five scenes are unchanged.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from pcg_codec import verify_cycle, parse_packet
from compile_boss import _verify as verify_boss_states
from pcg_boss_art import generate_frames as boss_frames

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs/msx1/v1.3'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    manifest=json.loads((OUT/'build-manifest.json').read_text())
    rom=(OUT/manifest['file']).read_bytes()
    assert len(rom)==524288 and rom[:2]==b'AB' and sha(rom)==manifest['sha256']
    reports=[];occupied=set();nonzero=0;extents={};aliases=0
    scenes=6
    assert len(manifest['worlds'])==scenes
    def read_artifact(e, filename):
        nonlocal nonzero,aliases
        assert manifest['packing']['first_packet_bank']<=e['bank']<64
        assert 0<=e['offset'] and e['offset']+e['bytes']<=8192
        start=e['bank']*8192+e['offset'];end=start+e['bytes']
        data=rom[start:end]
        assert len(data)==e['bytes'] and sha(data)==e['sha256']
        assert data==(ROOT/'assets'/filename).read_bytes(),filename
        if (start,end) in extents:
            # Deduplicated damage-name files intentionally share one complete
            # interval. Partial overlap is never accepted, even for equal bytes.
            assert extents[start,end]==data,'Aliased artifacts differ'
            aliases+=1
        else:
            positions=set(range(start,end));assert not positions&occupied
            occupied.update(positions);extents[start,end]=data
        nonzero+=bool(e['offset'])
        return data
    entries=manifest['packing']['packets']
    assert len(entries)==96 and {(e['stage'],e['phase']) for e in entries}=={(s,p) for s in range(scenes) for p in range(16)}
    boss_expected=[boss_frames(state) for state in range(4)]
    boss_initial=None;boss_packets=None
    for stage in range(scenes):
        initial=rom[(6+stage*2)*8192:(8+stage*2)*8192]
        assert initial==(ROOT/'assets'/f'world-{stage}.bin').read_bytes()
        assert sha(initial)==manifest['worlds'][stage]['raw_sha256']
        packets=[]
        for phase in range(16):
            e=next(e for e in entries if (e['stage'],e['phase'])==(stage,phase))
            packet=read_artifact(e,f'phase-{stage}-{phase:02}.bin')
            parse_packet(packet);packets.append(packet)
        frames=np.load(ROOT/'assets'/f'frames-{stage}.npy') if stage<5 else boss_expected[0]
        reports.append({'stage':stage,**verify_cycle(initial,packets,frames)})
        if stage==5:boss_initial,boss_packets=initial,packets
    packet_nonzero=nonzero
    codec_data=(ROOT/'assets/codec-manifest-5.json').read_bytes()
    assert sha(codec_data)==manifest['giant_boss']['codec_sha256']
    boss_codec=json.loads(codec_data)
    assert sha(boss_initial)==boss_codec['initial']['sha256']
    assert boss_codec['state_input_sha256']==[sha(f.tobytes()) for f in boss_expected]
    names_entries=manifest['packing']['boss_names']
    assert len(names_entries)==48
    assert {(e['state'],e['phase']) for e in names_entries}=={(s,p) for s in range(1,4) for p in range(16)}
    names=[[parse_packet(p)[2] for p in boss_packets]]
    for state in range(1,4):
        names.append([])
        for phase in range(16):
            e=next(e for e in names_entries if (e['state'],e['phase'])==(state,phase))
            source=next(n for n in boss_codec['names'] if (n['state'],n['phase'])==(state,phase))
            assert all(e[k]==source[k] for k in ('file','bytes','sha256'))
            assert e['bytes']==640
            names[state].append(read_artifact(e,e['file']))
    boss_proof=verify_boss_states(boss_initial,boss_packets,boss_expected,names,boss_codec['static_regions'])
    assert nonzero>0,'Packed-location readback was not exercised'
    assert len(occupied)==manifest['packing']['payload_bytes'],'Packed payload accounting differs'
    assert rom[manifest['allocated_bytes']:]==bytes([255])*(len(rom)-manifest['allocated_bytes'])
    preserved=[]
    if args.baseline:
        previous_count=5 if (args.baseline/'world-4.bin').exists() else 3
        for old in range(previous_count):
            for name in [f'world-{old}.bin',f'frames-{old}.npy',*[f'phase-{old}-{p:02}.bin' for p in range(16)]]:
                new=name if previous_count==5 else name.replace(f'-{old}',f'-{old+1}',1)
                a=(args.baseline/name).read_bytes();b=(ROOT/'assets'/new).read_bytes()
                assert a==b,f'Original scene changed: {name} -> {new}'
                preserved.append({'before':name,'after':new,'sha256':sha(a)})
        for name in ['sprite-patterns.bin','sprite-records.bin']:
            assert (args.baseline/name).read_bytes()==(ROOT/'assets'/name).read_bytes()
    report={'passed':True,'rom_sha256':sha(rom),'rom_bytes':len(rom),
            'allocated_bytes':manifest['allocated_bytes'],'free_bytes':manifest['free_bytes'],
            'packets':96,'packets_at_nonzero_offset':packet_nonzero,'overlaps':0,
            'boss_name_entries':48,'boss_name_unique_files':len({e['file'] for e in names_entries}),
            'exact_shared_artifact_references':aliases,'boss_states':boss_proof,
            'worlds':reports,'preserved_original_assets':preserved,
            'validation':'ROM bytes decoded offline; native execution is checked separately.'}
    (OUT/'layout-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('worlds','preserved_original_assets')},indent=2))

if __name__=='__main__':main()
