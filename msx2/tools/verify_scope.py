"""Local development audit against the preserved turbo R source and a rebuild."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'outputs/msx2'
original=ROOT.parent/'turbor'
M=json.loads((OUT/'build-manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def body(text,name):
    start=re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',text).start()
    opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
names=['random16','abs16','clamp','add_score','explode','reset_entities','new_game','damage','fire_enemy','kill_foe','player_fire','use_bomb','spawn_foe','update_objects','update_boss','update_play']
a=(original/'src/game.c').read_text();b=(ROOT/'src/game.c').read_text()
logic={name:body(a,name)==body(b,name) for name in names}
art={name:sha(original/'assets'/name)==sha(ROOT/'assets'/name) for name in ['sprites.bin','world/stage-1.bin','world/stage-2.bin','world/stage-3.bin']}
rebuilt=ROOT/'work/rebuild-check/outputs/msx2'/M['file']
results=[{'name':'sixteen-gameplay-functions-unchanged','passed':all(logic.values()),'functions':logic},
         {'name':'background-and-sprite-pixels-preserved','passed':all(art.values()),'assets':art},
         {'name':'standalone-full-regeneration-identical','passed':sha(rebuilt)==M['sha256'],'sha256':sha(rebuilt)},
         {'name':'original-turboR-ROM-preserved','passed':sha(ROOT.parent/'outputs/turbor/NEON_REVENANT-TurboR-v1.0.rom')=='23f129c1ebbdd491b8fb1a2fd133c2dfd7c3a61386f150c92e87cf5d0bcfe195'}]
report={'rom':M,'physical_hardware_tested':False,'results':results}
(OUT/'scope-verification.json').write_text(json.dumps(report,indent=2)+'\n')
for result in results:print(result)
assert all(r['passed'] for r in results)
