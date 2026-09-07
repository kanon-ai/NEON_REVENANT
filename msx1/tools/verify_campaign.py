"""Run the real C combat simulation against the archived three-sector release.

No emulator, renderer, ROM builder or generated game assets are touched. The
host harness replaces hardware headers with fixed-width storage types and a
sound-event recorder, then compiles the unmodified simulation function bodies.
This checks gameplay equivalence, not Z80 instruction timing or VDP behavior.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
WORK = PROJECT / 'work/campaign-test'
REPORT = PROJECT / 'outputs/msx1/v1.2/campaign-verification.json'
SCALARS = ('mode shield bombs score highscore stage_clock frame_counter boss_hp '
           'player_x player_y old_keys keys edge draw_page shot_clock bomb_flash '
           'hurt_clock stage_banner transition_clock boss_phase boss_flash combo '
           'combo_clock rng boss_clock frames_played frame_ticks aim_x aim_y '
           'boss_x boss_y pickup_on pickup_z pickup_x pickup_y pause_previous').split()

PREAMBLE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
static uint32_t sound_hash, sound_events[7];
void sound_effect(u8 id) {
    if (id > 6) { fprintf(stderr, "invalid sound effect %u\n", id); exit(2); }
    ++sound_events[id];sound_hash=sound_hash*33u+id;
}
'''

HARNESS = r'''
static FILE *trace;
static unsigned snapshots, assertions, normal_ticks, boss_ticks, bullet_samples;
static unsigned damage_samples, deaths, boss_kills, pickups;
static const unsigned seeds[]={1,0x7A31,0xCAFE,0xFFFF};

static void check(int condition,const char *label) {
    ++assertions;
    if (!condition) { fprintf(stderr,"CHECK FAILED: %s\n",label);exit(2); }
}
static void fresh(unsigned which,unsigned seed) {
    memset(foes,0,sizeof(foes));memset(shots,0,sizeof(shots));memset(fx,0,sizeof(fx));
    mode=stage=shield=bombs=0;score=highscore=stage_clock=frame_counter=boss_hp=0;
    player_x=player_y=0;old_keys=keys=edge=draw_page=shot_clock=bomb_flash=hurt_clock=0;
    stage_banner=transition_clock=boss_phase=boss_flash=combo=combo_clock=0;
    boss_clock=frames_played=frame_ticks=0;aim_x=aim_y=boss_x=boss_y=0;
    pickup_on=pickup_z=0;pickup_x=pickup_y=0;pause_previous=0;world_camera=0;
    sound_hash=0;memset(sound_events,0,sizeof(sound_events));rng=seed;
    new_game();stage=(u8)which;
}
static void emit(unsigned scenario,unsigned level,unsigned seed,unsigned step) {
    int32_t values[256];unsigned count=0,i;
#define APPEND(v) values[count++]=(int32_t)(v)
    APPEND(scenario);APPEND(level);APPEND(seed);APPEND(step);
    APPEND(stage-IS_CURRENT);
    /* SCALAR_SNAPSHOT */
    APPEND(sound_hash);
    for(i=0;i<7;++i)APPEND(sound_events[i]);
    for(i=0;i<ENEMIES;++i){
        APPEND(foes[i].active);APPEND(foes[i].kind);APPEND(foes[i].z);APPEND(foes[i].hp);
        APPEND(foes[i].wx);APPEND(foes[i].wy);APPEND(foes[i].x);APPEND(foes[i].y);
    }
    for(i=0;i<BULLETS;++i){
        APPEND(shots[i].active);APPEND(shots[i].x);APPEND(shots[i].y);
        APPEND(shots[i].dx);APPEND(shots[i].dy);
        if(shots[i].active)++bullet_samples;
    }
    for(i=0;i<FXMAX;++i){
        APPEND(fx[i].active);APPEND(fx[i].age);APPEND(fx[i].size);
        APPEND(fx[i].x);APPEND(fx[i].y);
    }
    if(hurt_clock)++damage_samples;
    if(mode==OVER)++deaths;
    if(mode==TRANSIT)++boss_kills;
    check(fwrite(values,sizeof(values[0]),count,trace)==count,"write trace");
    ++snapshots;
#undef APPEND
}
static void input_step(unsigned t,unsigned shoot,unsigned bomb_at) {
    unsigned horizontal=(t/29)%4,vertical=(t/47)%4;
    keys=(horizontal==0?1:horizontal==2?2:0)|(vertical==0?4:vertical==2?8:0);
    if(shoot&&(t%11)<8)keys|=16;
    if(t==bomb_at||t==bomb_at+281||t==bomb_at+617)keys|=32;
    edge=keys&~old_keys;old_keys=keys;
}
static void regression(void) {
    unsigned level,k,t,which,i,variant;
    for(level=0;level<3;++level)for(k=0;k<4;++k){
        which=level+IS_CURRENT;
        /* Ordinary motion, spawns, fire, bombs and collision damage. */
        fresh(which,seeds[k]);
        for(t=0;t<1800;++t){
            input_step(t,1,173);update_play();++frame_counter;
            if(mode==PLAY)++normal_ticks;else if(mode==BOSS)++boss_ticks;
            emit(0,level,seeds[k],t);
            if(mode==OVER||mode==TRANSIT)break;
        }
        /* Long boss pattern exposure: full original shield and live damage. */
        fresh(which,seeds[k]);mode=BOSS;boss_hp=100+40*level;boss_x=128;boss_y=108;
        for(t=0;t<900;++t){
            input_step(t,0,143);update_play();++frame_counter;++boss_ticks;
            emit(1,level,seeds[k],t);
            if(mode==OVER)break;
        }
        /* Defeat every original boss with actual hit detection and scoring. */
        fresh(which,seeds[k]);mode=BOSS;boss_hp=100+40*level;boss_x=128;boss_y=108;
        for(t=0;t<220;++t){
            keys=0;edge=t==17?32:0;update_play();++frame_counter;++boss_ticks;
            aim_x=boss_x;aim_y=boss_y;player_fire();
            emit(2,level,seeds[k],t);
            if(mode==OVER||mode==TRANSIT)break;
        }
        check(mode==TRANSIT,"scripted aim defeats original boss");
        /* All three aimed-shot variants, including edge-origin trajectories. */
        for(variant=0;variant<3;++variant){
            fresh(which,seeds[k]);
            fire_enemy(10,80,variant);fire_enemy(245,90,variant);fire_enemy(128,166,variant);
            for(t=0;t<100;++t){
                update_objects();++frame_counter;
                emit(3+variant,level,seeds[k],t);
            }
        }
        /* Saturated pools, enemy HP and combo rewards, then real bomb clear. */
        fresh(which,seeds[k]);shield=4;
        for(i=0;i<ENEMIES+2;++i)spawn_foe();
        for(i=0;i<BULLETS+2;++i)fire_enemy(100,80,i%3);
        for(t=0;t<12;++t){
            aim_x=foes[t%ENEMIES].x;aim_y=foes[t%ENEMIES].y;
            player_fire();update_objects();++frame_counter;
            emit(6,level,seeds[k],t);
        }
        use_bomb();emit(6,level,seeds[k],12);
        /* Invulnerability, bomb immunity, transit immunity and loss state. */
        fresh(which,seeds[k]);damage();emit(7,level,seeds[k],0);
        damage();emit(7,level,seeds[k],1);
        hurt_clock=0;bomb_flash=3;damage();emit(7,level,seeds[k],2);
        bomb_flash=0;mode=TRANSIT;damage();emit(7,level,seeds[k],3);
        mode=PLAY;shield=1;damage();emit(7,level,seeds[k],4);
        /* Seeded drop chances and successful collection through real logic. */
        fresh(which,seeds[k]);
        for(t=0;t<128;++t){
            reset_entities();shield=4;spawn_foe();kill_foe(&foes[0]);
            if(pickup_on){pickup_x=player_x;pickup_y=player_y-2;++pickups;}
            update_objects();++frame_counter;emit(8,level,seeds[k],t);
        }
        /* Existing sector-to-sector recovery remains identical. */
        if(level<2){
            fresh(which,seeds[k]);mode=TRANSIT;shield=2;bombs=0;
            for(t=0;t<90;++t){keys=edge=0;update_play();++frame_counter;emit(9,level,seeds[k],t);}
        }
    }
    check(normal_ticks>1000&&boss_ticks>1000,"ordinary and boss simulation covered");
    check(bullet_samples>1000&&damage_samples>0&&deaths>0,"bullet collisions and damage covered");
    check(boss_kills>=12&&pickups>0,"boss rewards and seeded pickups covered");
}
static void campaign(void) {
#if IS_CURRENT
    static const unsigned lengths[]={750,1500,1500,1500,1200};
    static const unsigned initial_hp[]={100,100,140,180,180};
    unsigned current,t,before_score;
    for(current=0;current<5;++current){
        fresh(current,0x7A31);
        for(t=0;t<lengths[current];++t){
            keys=edge=0;update_play();++frame_counter;
            check(stage==current,"no premature stage increment");
            check(mode==(t+1==lengths[current]?BOSS:PLAY),"actual stage boss-entry timing");
            reset_entities(); /* Observe timing without collision-induced loss. */
        }
        check(boss_hp==initial_hp[current],"boss starts with intended HP");
        shield=2;bombs=0;boss_hp=1;aim_x=boss_x;aim_y=boss_y;
        player_fire();check(mode==TRANSIT,"boss defeat initiates transition");
        before_score=score;
        for(t=0;t<90;++t){
            keys=edge=0;update_play();++frame_counter;
            if(t<89)check(mode==TRANSIT&&stage==current,"transition holds for 90 ticks");
        }
        if(current<4){
            check(mode==PLAY&&stage==current+1&&stage_clock==0,"advance to next campaign zone");
            check(shield==(current==0?6:4),"intro replenishes; later zones retain original recovery");
            check(bombs==(current==0?3:1),"intro replenishes bombs; later zones recover one");
        }else{
            check(mode==CLEAR&&stage==4,"clear occurs only after final zone");
            check(score==before_score+200,"final shield reward is awarded once");
        }
        world_loaded=0;new_game();
        check(stage==0&&mode==PLAY&&shield==6&&bombs==3&&score==0,"retry returns to Episode 0");
        check(world_loaded==255,"retry forces background reload even inside Episode 0");
    }
#endif
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    trace=fopen(argv[1],"wb");if(!trace)return 2;
    regression();campaign();fclose(trace);
    printf("{\"passed\":true,\"snapshots\":%u,\"assertions\":%u,"
           "\"normal_ticks\":%u,\"boss_ticks\":%u,\"active_bullet_samples\":%u,"
           "\"hurt_samples\":%u,\"loss_samples\":%u,\"transit_samples\":%u,\"pickups_collected\":%u}\n",
           snapshots,assertions,normal_ticks,boss_ticks,bullet_samples,damage_samples,deaths,boss_kills,pickups);
    return 0;
}
'''


def simulation(source: str) -> str:
    marker = '/* 64 resident 16x16 patterns'
    if source.count(marker) != 1:
        raise RuntimeError('Cannot locate the reviewed simulation/renderer boundary')
    prefix = source.split(marker)[0]
    prefix = re.sub(r'^#include "[^"\n]+"\s*$', '', prefix, flags=re.M)
    # Same fixed-width object storage on both sides; host integer promotion
    # still follows the host ABI, so this is not a Z80 arithmetic emulator.
    prefix = prefix.replace('typedef signed int s16;', 'typedef int16_t s16;')
    return prefix


def run(command, env):
    result = subprocess.run([str(x) for x in command], env=env, text=True,
                            capture_output=True, cwd=WORK)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {command}\n'
                           f'{result.stdout}\n{result.stderr}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True,
                        help='External archived v1.1 game.c; not included in the new source package')
    parser.add_argument('--gcc', type=Path,
                        default=Path('C:/msys64/ucrt64/bin/gcc.exe'))
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    current = ROOT / 'src/game.c'
    WORK.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['PATH'] = str(args.gcc.parent) + os.pathsep + env.get('PATH', '')
    schemas = ['scenario', 'original_sector', 'seed', 'step', 'normalized_stage'] + SCALARS + ['sound_hash']
    schemas += [f'sound_events[{i}]' for i in range(7)]
    schemas += [f'foes[{i}].{name}' for i in range(6) for name in ('active', 'kind', 'z', 'hp', 'wx', 'wy', 'x', 'y')]
    schemas += [f'shots[{i}].{name}' for i in range(8) for name in ('active', 'x', 'y', 'dx', 'dy')]
    schemas += [f'fx[{i}].{name}' for i in range(4) for name in ('active', 'age', 'size', 'x', 'y')]
    harness = HARNESS.replace('/* SCALAR_SNAPSHOT */', '\n'.join(f'APPEND({name});' for name in SCALARS))
    results = {}
    source_hashes = {}
    report = {
        'passed': False,
        'method': 'Execute archived and current C simulation bodies under the same GCC host ABI; compare every serialized state field after identical inputs.',
        'baseline': str(baseline),
        'current': str(current),
        'original_to_campaign_stages': [[0, 1], [1, 2], [2, 3]],
        'seeds': [1, 0x7A31, 0xCAFE, 0xFFFF],
        'limits': [
            'No renderer, VDP, music synthesis, controller polling, ROM bank layout or emulator timing is exercised.',
            '16-bit object storage is used, but C expression promotion follows GCC rather than the SDCC Z80 ABI.',
            'Equivalence starts from identical seeded original-sector state; Episode 0 carryover is intentionally not expected to reproduce the old campaign RNG state.',
            'Visual world_loaded is excluded from combat equivalence; its retry invalidation is tested separately.',
        ],
    }
    try:
        for name, path, is_current in [('baseline', baseline, 0), ('current', current, 1)]:
            source = path.read_text(encoding='utf-8')
            source_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            generated = WORK / f'{name}-simulation.c'
            generated.write_text(PREAMBLE + f'\n#define IS_CURRENT {is_current}\n' + simulation(source) + harness,
                                 encoding='utf-8')
            executable = WORK / f'{name}-simulation.exe'
            run([args.gcc, '-std=c99', '-O2', '-fno-strict-aliasing', generated, '-o', executable], env)
            results[name] = json.loads(run([executable, WORK / f'{name}-trace.bin'], env))
        old_trace = (WORK / 'baseline-trace.bin').read_bytes()
        new_trace = (WORK / 'current-trace.bin').read_bytes()
        if old_trace != new_trace:
            import struct
            word = next((i for i in range(min(len(old_trace), len(new_trace)) // 4)
                         if old_trace[4*i:4*i+4] != new_trace[4*i:4*i+4]), None)
            if word is None:
                raise AssertionError(f'Trace lengths differ: {len(old_trace)} != {len(new_trace)}')
            frame, field = divmod(word, len(schemas))
            values = struct.unpack_from('<5i', old_trace, frame * len(schemas) * 4)
            before = struct.unpack_from('<i', old_trace, word * 4)[0]
            after = struct.unpack_from('<i', new_trace, word * 4)[0]
            raise AssertionError(f'First mismatch snapshot {frame}, context={values}, '
                                 f'{schemas[field]}: {before} != {after}')
        report.update(passed=True, source_sha256=source_hashes, execution=results,
                      compared_snapshots=results['current']['snapshots'],
                      fields_per_snapshot=len(schemas), trace_bytes=len(new_trace),
                      identical_trace_sha256=hashlib.sha256(new_trace).hexdigest(),
                      campaign_checks='Five actual PLAY durations, boss entry HP, player_fire defeat, 90-tick transitions, intro full resupply, original recovery, final clear reward and retry reload all passed.')
    except Exception as exc:
        report.update(source_sha256=source_hashes, execution=results, error=str(exc))
        REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        raise
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
