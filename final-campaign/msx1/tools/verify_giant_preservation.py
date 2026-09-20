"""Compare the unchanged MSX1 campaign with the archived v1.2 C simulation.

The final-zone giant boss is deliberately outside this equivalence claim.
Zones 0--3 include normal play, boss fights, transitions, and actual main-loop
pause/retry dispatch. Zone 4 includes ordinary play through tick 1199 only.
This executes the production C function bodies, not a Python game model.
Host integer promotion, renderer behavior and Z80/VDP timing require separate
native emulator checks. An external v1.2 baseline is required for distribution.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
DEFAULT_WORK = PROJECT / "work/giant-boss-regression"
SCALARS = ("mode shield bombs score highscore stage_clock frame_counter boss_hp "
           "player_x player_y old_keys keys edge draw_page shot_clock bomb_flash "
           "hurt_clock stage_banner transition_clock boss_phase boss_flash combo "
           "combo_clock rng boss_clock frames_played frame_ticks aim_x aim_y "
           "boss_x boss_y pickup_on pickup_z pickup_x pickup_y pause_previous "
           "world_loaded world_camera").split()
SEEDS = [1, 0x7A31, 0xCAFE, 0xFFFF]

PREAMBLE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
static uint32_t sound_hash, sound_events[7], mute_hash, mute_events;
static uint32_t music_hash, music_events;
static u8 host_keys;
u8 input_read(void) { return host_keys; }
void sound_effect(u8 id) {
    if (id > 6) { fprintf(stderr,"invalid sound effect %u\n",id);exit(2); }
    ++sound_events[id];sound_hash=sound_hash*33u+id;
}
void sound_mute(u8 value) { ++mute_events;mute_hash=mute_hash*33u+value; }
void sound_tick(u8 tune,u8 active) {
    ++music_events;music_hash=(music_hash*33u+tune)*33u+active;
}
'''

HARNESS = r'''
static FILE *trace;
static unsigned snapshots, assertions, normal_ticks, boss_ticks, bullet_samples;
static unsigned damage_samples, deaths, boss_kills, pickups, pause_samples;
static unsigned stage4_play_ticks, stage4_boss_ticks, retries, transition_ticks;
static const unsigned seeds[]={1,0x7A31,0xCAFE,0xFFFF};
static const unsigned lengths[]={750,1500,1500,1500,1200};
static const unsigned initial_hp[]={100,100,140,180,180};

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
    world_loaded=0;host_keys=0;mute_hash=mute_events=music_hash=music_events=0;
    sound_hash=0;memset(sound_events,0,sizeof(sound_events));rng=seed;
    new_game();stage=(u8)which;
}
static void emit(unsigned scenario,unsigned level,unsigned seed,unsigned step) {
    int32_t values[256];unsigned count=0,i;
#define APPEND(v) values[count++]=(int32_t)(v)
    APPEND(scenario);APPEND(level);APPEND(seed);APPEND(step);APPEND(stage);
    /* SCALAR_SNAPSHOT */
    APPEND(sound_hash);
    for(i=0;i<7;++i)APPEND(sound_events[i]);
    APPEND(mute_hash);APPEND(mute_events);APPEND(music_hash);APPEND(music_events);
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
    if(mode==TRANSIT)++transition_ticks;
    if(mode==PAUSED)++pause_samples;
    if(mode==PLAY){++normal_ticks;if(stage==4)++stage4_play_ticks;}
    if(mode==BOSS){++boss_ticks;if(stage==4)++stage4_boss_ticks;}
    check(stage4_boss_ticks==0,"the changed final boss is never in equivalence trace");
    check(count==SCHEMA_COUNT,"serialized schema has expected field count");
    check(fwrite(values,sizeof(values[0]),count,trace)==count,"write trace");
    ++snapshots;
#undef APPEND
}
static void input_step(unsigned t,unsigned shoot,unsigned bomb_at) {
    unsigned horizontal=(t/29)%4,vertical=(t/47)%4;
    host_keys=(horizontal==0?1:horizontal==2?2:0)|(vertical==0?4:vertical==2?8:0);
    if(shoot&&(t%11)<8)host_keys|=16;
    if(t==bomb_at||t==bomb_at+281||t==bomb_at+617)host_keys|=32;
    /* Real main dispatch pauses/resumes, with held key and release samples. */
    if(t==33||t==34||t==42||t==202||t==213)host_keys|=64;
}
static void regression(void) {
    unsigned level,k,t,i,variant;
    for(level=0;level<5;++level)for(k=0;k<4;++k){
        /* Normal inputs reach natural spawns, shots, bombs and damage. */
        fresh(level,seeds[k]);
        for(t=0;t<1800;++t){
            if(level==4&&stage_clock>=1199)break;
            input_step(t,1,173);host_dispatch();emit(0,level,seeds[k],t);
            if(mode==OVER||mode==TRANSIT)break;
        }
        /* Survive ordinary play to every unchanged entry, using actual code. */
        fresh(level,seeds[k]);
        for(t=0;t<lengths[level]-(level==4);++t){
            host_keys=0;host_dispatch();emit(1,level,seeds[k],t);
            check(stage==level,"no premature stage increment");
            check(mode==(t+1==lengths[level]?BOSS:PLAY),"unchanged boss-entry timing");
            reset_entities();
        }
        if(level<4)check(boss_hp==initial_hp[level],"unchanged boss-entry HP");
        else check(mode==PLAY&&stage_clock==1199,"final ordinary play stops before changed entry");
        /* Boss gameplay is compared only for the four unchanged bosses. */
        if(level<4){
            fresh(level,seeds[k]);mode=BOSS;boss_hp=initial_hp[level];boss_x=128;boss_y=108;
            for(t=0;t<900;++t){
                input_step(t,0,143);host_dispatch();emit(2,level,seeds[k],t);
                if(mode==OVER)break;
            }
            /* Defeat with actual hit detection, score and bomb interaction. */
            fresh(level,seeds[k]);mode=BOSS;boss_hp=initial_hp[level];boss_x=128;boss_y=108;
            for(t=0;t<240;++t){
                host_keys=t==17?32:0;host_dispatch();
                aim_x=boss_x;aim_y=boss_y;player_fire();emit(3,level,seeds[k],t);
                if(mode==OVER||mode==TRANSIT)break;
            }
            check(mode==TRANSIT,"aimed input defeats unchanged boss");++boss_kills;
            /* Transition, shield/bomb resupply and the next PLAY tick. */
            for(t=0;t<91;++t){
                host_keys=0;host_dispatch();emit(4,level,seeds[k],t);
            }
            check(mode==PLAY&&stage==level+1,"unchanged boss advances to next zone");
        }
        /* Each aimed trajectory starts near left/right/bottom screen edges. */
        for(variant=0;variant<3;++variant){
            fresh(level,seeds[k]);
            fire_enemy(10,80,variant);fire_enemy(245,90,variant);fire_enemy(128,166,variant);
            for(t=0;t<100;++t){
                update_objects();++frame_counter;emit(5+variant,level,seeds[k],t);
            }
        }
        /* Saturated pools, enemy HP and combo rewards, then actual bomb. */
        fresh(level,seeds[k]);shield=4;
        for(i=0;i<ENEMIES+2;++i)spawn_foe();
        for(i=0;i<BULLETS+2;++i)fire_enemy(100,80,i%3);
        for(t=0;t<12;++t){
            aim_x=foes[t%ENEMIES].x;aim_y=foes[t%ENEMIES].y;
            player_fire();update_objects();++frame_counter;emit(8,level,seeds[k],t);
        }
        use_bomb();emit(8,level,seeds[k],12);
        /* Invulnerability, nova immunity, transition immunity and loss. */
        fresh(level,seeds[k]);damage();emit(9,level,seeds[k],0);
        damage();emit(9,level,seeds[k],1);
        hurt_clock=0;bomb_flash=3;damage();emit(9,level,seeds[k],2);
        bomb_flash=0;mode=TRANSIT;damage();emit(9,level,seeds[k],3);
        mode=PLAY;shield=1;damage();emit(9,level,seeds[k],4);
        /* Actual loss/retry gate, including a held fire button. */
        for(t=0;t<46;++t){
            host_keys=(t<43||t==44)?16:0;host_dispatch();emit(10,level,seeds[k],t);
        }
        check(mode==PLAY&&stage==0&&shield==6&&bombs==3,"loss retry returns to Episode 0");++retries;
        check(world_loaded==255,"retry invalidates world even inside Episode 0");
        /* Seeded pickup chances and real collection behavior. */
        fresh(level,seeds[k]);
        for(t=0;t<128;++t){
            reset_entities();shield=4;spawn_foe();kill_foe(&foes[0]);
            if(pickup_on){pickup_x=player_x;pickup_y=player_y-2;++pickups;}
            update_objects();++frame_counter;emit(11,level,seeds[k],t);
        }
        /* Pause PLAY and unchanged BOSS with held fire/nova and movement. */
        for(variant=0;variant<(level<4?2:1);++variant){
            fresh(level,seeds[k]);
            if(variant){mode=BOSS;boss_hp=initial_hp[level];boss_x=128;boss_y=108;}
            for(t=0;t<80;++t){
                host_keys=(t<20?0:16|32|2)|(t==10||t==11||t==50?64:0);
                host_dispatch();emit(12+variant,level,seeds[k],t);
                if(t>=10&&t<50)check(mode==PAUSED,"pause survives held input until new Escape edge");
            }
        }
    }
    check(normal_ticks>10000&&boss_ticks>1000,"ordinary and boss gameplay exercised");
    check(bullet_samples>1000&&damage_samples>0&&deaths>0,"bullets, damage and loss exercised");
    check(boss_kills==16&&pickups>0&&retries==20,"all unchanged bosses, pickups and retries exercised");
    check(pause_samples>1000&&stage4_play_ticks>=1199*4,"pause and complete final ordinary path exercised");
    check(stage4_boss_ticks==0,"changed final boss is excluded without excluding ordinary fields");
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    trace=fopen(argv[1],"wb");if(!trace)return 2;
    regression();fclose(trace);
    printf("{\"passed\":true,\"snapshots\":%u,\"assertions\":%u,"
           "\"normal_ticks\":%u,\"boss_ticks\":%u,\"active_bullet_samples\":%u,"
           "\"hurt_samples\":%u,\"loss_samples\":%u,\"transition_ticks\":%u,"
           "\"bosses_defeated\":%u,\"pickups_collected\":%u,\"pause_samples\":%u,"
           "\"retries\":%u,\"stage4_play_ticks\":%u,\"stage4_boss_ticks\":%u}\n",
           snapshots,assertions,normal_ticks,boss_ticks,bullet_samples,damage_samples,
           deaths,transition_ticks,boss_kills,pickups,pause_samples,retries,
           stage4_play_ticks,stage4_boss_ticks);
    return 0;
}
'''

GIANT_HARNESS = r'''
static unsigned complete_fights, hit_boundaries, gated_shots, reachable_targets;
static unsigned nova_cases, giant_pauses, clear_rewards, giant_retries;
static s16 physical_to_logical(unsigned physical) {
    unsigned y;
    for(y=0;y<256;++y)if(video_y(y)==physical)return y;
    fprintf(stderr,"unrepresentable physical target %u\n",physical);exit(2);
}
static void giant_fresh(unsigned motion) {
    fresh(4,0x7A31);stage_clock=1199;host_keys=0;
    world_phase=motion;world_pending=0;world_target=motion;
    world_boss_state=world_boss_display_state=0;
    host_dispatch();
    check(mode==BOSS&&giant_phase==0,"final boss starts with warning");
    check(giant_left_hp==32&&giant_right_hp==32&&giant_core_hp==116&&boss_hp==180,
          "intended multipart health at actual final entry");
    reset_entities();
}
static void enter_guns(unsigned motion) {
    unsigned t;
    giant_fresh(motion);
    for(t=0;t<36;++t){
        host_keys=0;host_dispatch();
        check(giant_phase==(t==35?1:0),"warning lasts precisely 36 boss ticks");
    }
    check(mode==BOSS&&giant_phase==1,"guns become active after warning");
}
static void point_at(unsigned part,int dx,int dy) {
    const GiantTargets *target=giant_targets(world_phase);
    unsigned x=part==1?target->lx:part==2?target->rx:target->cx;
    unsigned y=part==1?target->ly:part==2?target->ry:target->cy;
    aim_x=x+dx;aim_y=physical_to_logical(y+dy);
}
static void confirm_closed(unsigned expected) {
    point_at(3,0,0);player_fire();
    check(giant_core_hp==116&&boss_hp==expected,"closed core ignores actual player shot");
    ++gated_shots;
}
static void wait_gate(void) {
    unsigned t;
    check(giant_phase==2&&giant_left_hp==0&&giant_right_hp==0,"both guns required before opening");
    for(t=0;t<24;++t){
        confirm_closed(116);host_keys=0;host_dispatch();reset_entities();
        check(giant_phase==(t==23?3:2),"core opening waits exactly 24 ticks");
    }
    point_at(3,0,0);player_fire();
    check(giant_core_hp==116,"core cannot be hit before its PCG state is displayed");
    ++gated_shots;world_boss_display_state=3;
}
static void target_reachable(unsigned motion,unsigned part) {
    const GiantTargets *target;
    unsigned x,y;int found=0;
    enter_guns(motion);target=giant_targets(motion);
    /* Move the production player/aim update across positions reachable from
     * the default craft in 4/3-pixel input steps. The collision test stays
     * production player_fire(), not an approximate test-owned rectangle. */
    for(x=20;x<=236&&!found;x+=4)for(y=121;y<=181&&!found;y+=3){
        player_x=x;player_y=y;host_keys=0;host_dispatch();reset_entities();
        if(part==3){giant_phase=3;giant_left_hp=giant_right_hp=0;world_boss_display_state=3;}
        player_fire();
        if((part==1&&giant_left_hp<32)||(part==2&&giant_right_hp<32)||
           (part==3&&giant_core_hp<116))found=1;
    }
    check(found,"target can be reached through production player-to-reticle mapping");
    ++reachable_targets;
}
static void boundary_checks(unsigned motion,unsigned part) {
    static const int direction[4][2]={{1,0},{-1,0},{0,1},{0,-1}};
    unsigned i,old_total;int dx,dy;
    for(i=0;i<4;++i){
        enter_guns(motion);
        if(part==3){giant_phase=3;giant_left_hp=giant_right_hp=0;giant_sync();world_boss_display_state=3;}
        old_total=boss_hp;
        dx=direction[i][0]*(part==3?15:14);dy=direction[i][1]*(part==3?13:11);
        point_at(part,dx,dy);player_fire();
        check(boss_hp==old_total,"shot exactly outside weakpoint rectangle misses");++hit_boundaries;
        if(dx>0)--dx;else if(dx<0)++dx;
        if(dy>0)--dy;else if(dy<0)++dy;
        point_at(part,dx,dy);player_fire();
        check(boss_hp==old_total-1,"shot one pixel inside weakpoint rectangle hits");++hit_boundaries;
    }
}
static void complete_fight(unsigned motion,unsigned reverse) {
    unsigned first=reverse?2:1,second=reverse?1:2,t,score_before,win_score;
    enter_guns(motion);confirm_closed(180);
    for(t=0;t<32;++t){point_at(first,0,0);player_fire();}
    check(giant_phase==1&&boss_hp==148,"one destroyed gun keeps central armor closed");
    check((first==1?giant_left_hp:giant_right_hp)==0,"selected gun destroyed");
    confirm_closed(148);
    for(t=0;t<32;++t){point_at(second,0,0);player_fire();}
    check(boss_hp==116&&world_boss_state==3,"destroyed guns request open PCG state");
    wait_gate();
    for(t=0;t<115;++t){point_at(3,0,0);player_fire();}
    check(mode==BOSS&&giant_core_hp==1&&boss_hp==1,"core has exactly one hit remaining");
    score_before=score;point_at(3,0,0);player_fire();
    check(mode==TRANSIT&&giant_phase==4&&boss_hp==0,"final shot starts giant destruction");
    check(score==score_before+702,"final hit and 700-point boss reward occur once");
    win_score=score;
    for(t=0;t<6;++t){point_at(3,0,0);player_fire();}
    check(score==win_score,"continued shooting cannot duplicate death reward");
    shield=4;bombs=2;
    for(t=0;t<90;++t){
        host_keys=0;host_dispatch();
        check(mode==(t==89?CLEAR:TRANSIT),"final destruction lasts 90 transition ticks");
    }
    check(score==win_score+800,"clear adds surviving shields and novas once");++clear_rewards;
    win_score=score;
    for(t=0;t<45;++t){host_keys=0;host_dispatch();}
    check(score==win_score&&mode==CLEAR,"clear idles without duplicating reward");
    host_keys=16;host_dispatch();
    check(mode==PLAY&&stage==0&&score==0&&shield==6&&bombs==3,"clear retry starts clean campaign");
    check(giant_phase==0&&giant_left_hp==0&&giant_right_hp==0&&giant_core_hp==0&&
          world_loaded==255&&world_boss_state==0,"retry clears giant state and invalidates world");
    ++giant_retries;++complete_fights;
}
static void nova_and_pause(unsigned motion) {
    unsigned phase,t,clock,hp,gate,frames,px,py;
    giant_fresh(motion);use_bomb();
    check(giant_left_hp==32&&giant_right_hp==32&&giant_core_hp==116,"warning nova cannot skip boss");++nova_cases;
    enter_guns(motion);use_bomb();
    check(bombs==2&&giant_left_hp==20&&giant_right_hp==20&&giant_core_hp==116,
          "nova damages each gun while armor protects core");++nova_cases;
    use_bomb();use_bomb();
    check(bombs==0&&giant_phase==2&&giant_left_hp==0&&giant_right_hp==0&&giant_core_hp==116,
          "three novas open guns without skipping protected core");++nova_cases;
    bombs=1;use_bomb();check(giant_core_hp==116,"opening-phase nova leaves core health intact");++nova_cases;
    wait_gate();bombs=3;use_bomb();
    check(giant_core_hp==91,"exposed core takes 25 nova damage");++nova_cases;
    giant_core_hp=2;giant_sync();use_bomb();
    check(giant_core_hp==1&&mode==BOSS,"nova cannot bypass required final aimed shot");++nova_cases;
    bombs=0;hp=boss_hp;use_bomb();check(boss_hp==hp,"empty nova stock cannot damage boss");++nova_cases;
    for(phase=0;phase<4;++phase){
        giant_fresh(motion);giant_phase=phase;
        if(phase>=2){giant_left_hp=giant_right_hp=0;giant_sync();}
        if(phase==3)world_boss_display_state=3;
        host_keys=64;host_dispatch();
        clock=boss_clock;hp=boss_hp;gate=giant_gate_clock;frames=frame_counter;px=player_x;py=player_y;
        for(t=0;t<15;++t){host_keys=16|32|2|8;host_dispatch();}
        check(mode==PAUSED&&boss_clock==clock&&boss_hp==hp&&giant_gate_clock==gate&&
              giant_phase==phase&&frame_counter==frames&&player_x==px&&player_y==py,
              "giant pause freezes clock, phase, damage, craft and frame counter");++giant_pauses;
        host_keys=64;host_dispatch();check(mode==BOSS,"giant pause resumes the boss mode");
        shield=1;hurt_clock=bomb_flash=0;damage();
        check(mode==OVER&&shield==0,"live giant fight can cause player loss");
        for(t=0;t<42;++t){host_keys=0;host_dispatch();}
        host_keys=16;host_dispatch();
        check(mode==PLAY&&stage==0&&giant_phase==0&&world_loaded==255,
              "loss in every giant phase retries Episode 0 with no giant state");++giant_retries;
    }
}
int main(void) {
    unsigned motion,part,order;
    for(motion=0;motion<16;++motion){
        for(part=1;part<=3;++part){target_reachable(motion,part);boundary_checks(motion,part);}
        for(order=0;order<2;++order)complete_fight(motion,order);
        nova_and_pause(motion);
    }
    printf("{\"passed\":true,\"assertions\":%u,\"motion_positions\":16,"
           "\"complete_fights\":%u,\"weakpoint_boundary_checks\":%u,"
           "\"gated_shot_checks\":%u,\"reachable_targets\":%u,\"nova_checks\":%u,"
           "\"pause_checks\":%u,\"clear_reward_checks\":%u,\"retry_checks\":%u}\n",
           assertions,complete_fights,hit_boundaries,gated_shots,reachable_targets,
           nova_cases,giant_pauses,clear_rewards,giant_retries);
    return 0;
}
'''


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def simulation(source, source_directory=None):
    marker = "/* 64 resident 16x16 patterns"
    if source.count(marker) != 1:
        raise RuntimeError("Cannot locate reviewed simulation/renderer boundary")
    prefix = source.split(marker)[0]
    dependencies = ""
    if '#include "boss_layout.h"' in prefix:
        if source_directory is None:
            raise RuntimeError("Current giant simulation requires its actual header directory")
        # Compile the generated production target table, not a fake hitbox map.
        layout = (source_directory / "boss_layout.h").read_text(encoding="utf-8")
        layout = re.sub(r'^#include "[^"\n]+"\s*$', "", layout, flags=re.M)
        dependencies += layout + "\n"
        world_header = (source_directory / "world_load.h").read_text(encoding="utf-8")
        world_globals = re.findall(r'^extern volatile u8 [^;]+;', world_header, flags=re.M)
        if not world_globals:
            raise RuntimeError("Missing actual world-phase state declarations")
        dependencies += "\n".join(item.removeprefix("extern ") for item in world_globals) + "\n"
        # Collision code calls the exact renderer coordinate map. Keep the
        # table and video_y body; no sprite submission or VRAM routine is run.
        video_start = source.index("static const u8 video_rows[256]=")
        video_end = source.index("void sprite(", video_start)
        prefix += "\n" + source[video_start:video_end]
    prefix = re.sub(r'^#include "[^"\n]+"\s*$', "", prefix, flags=re.M)
    prefix = prefix.replace("typedef signed int s16;", "typedef int16_t s16;")
    # Extract the real production input/pause/retry dispatch, excluding VDP.
    start = source.index("keys=input_read();", source.index("void main(void)"))
    end = source.index("draw_frame();", start)
    dispatch = source[start:end]
    if "update_play();" not in dispatch or "mode==PAUSED" not in dispatch:
        raise RuntimeError("Unexpected main-loop dispatch; review harness boundary")
    return dependencies + prefix + "\nvoid host_dispatch(void) {\n" + dispatch + "\n}\n"


def schema():
    fields = ["scenario", "campaign_stage", "seed", "step", "stage"] + SCALARS + ["sound_hash"]
    fields += [f"sound_events[{i}]" for i in range(7)]
    fields += ["mute_hash", "mute_events", "music_hash", "music_events"]
    fields += [f"foes[{i}].{name}" for i in range(6)
               for name in ("active", "kind", "z", "hp", "wx", "wy", "x", "y")]
    fields += [f"shots[{i}].{name}" for i in range(8) for name in ("active", "x", "y", "dx", "dy")]
    fields += [f"fx[{i}].{name}" for i in range(4) for name in ("active", "age", "size", "x", "y")]
    return fields


def run(command, env, work):
    result = subprocess.run([str(arg) for arg in command], env=env, text=True,
                            capture_output=True, cwd=work)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n"
                           f"{result.stdout}\n{result.stderr}")
    return result.stdout


def execute(name, source, gcc, env, work, fields, source_directory=None):
    harness = HARNESS.replace("/* SCALAR_SNAPSHOT */", "\n".join(f"APPEND({key});" for key in SCALARS))
    generated = work / f"{name}-simulation.c"
    generated.write_text(PREAMBLE + f"\n#define SCHEMA_COUNT {len(fields)}\n" +
                         simulation(source, source_directory) + harness, encoding="utf-8")
    executable = work / f"{name}-simulation.exe"
    run([gcc, "-std=c99", "-O2", "-fno-strict-aliasing", generated, "-o", executable], env, work)
    stats = json.loads(run([executable, work / f"{name}-trace.bin"], env, work))
    return stats, (work / f"{name}-trace.bin").read_bytes()


def trace_difference(before, after, fields):
    if before == after:
        return None
    word = next((i for i in range(min(len(before), len(after)) // 4)
                 if before[4*i:4*i+4] != after[4*i:4*i+4]), None)
    if word is None:
        return f"Trace lengths differ: {len(before)} != {len(after)}"
    frame, field = divmod(word, len(fields))
    context = struct.unpack_from("<5i", before, frame * len(fields) * 4)
    old_value = struct.unpack_from("<i", before, word * 4)[0]
    new_value = struct.unpack_from("<i", after, word * 4)[0]
    return (f"First mismatch snapshot {frame}, context={context}, "
            f"{fields[field]}: {old_value} != {new_value}")


def verify_registry(registry, baseline, allow_changed=()):
    """Original asset files and the archived output ROM must not be replaced."""
    items = json.loads(registry.read_text(encoding="utf-8-sig"))
    checked = []
    allowed = []
    baseline_seen = False
    for item in items:
        path = Path(item["path"])
        if path.resolve() == baseline.resolve():
            baseline_seen = True
        if not path.is_file():
            raise AssertionError(f"Archived preservation input disappeared: {path}")
        actual = sha256(path)
        if actual != item["sha256"] or path.stat().st_size != item["bytes"]:
            if path.parent.resolve() == (ROOT / "assets").resolve() and path.name in allow_changed:
                allowed.append({"path": str(path), "baseline_sha256": item["sha256"], "current_sha256": actual})
                continue
            raise AssertionError(f"Archived preservation input changed: {path}")
        checked.append({"path": str(path), "sha256": actual, "bytes": path.stat().st_size})
    if not baseline_seen:
        raise AssertionError("Registry does not authenticate the selected baseline C source")
    return checked, allowed


def giant_checks(path, gcc, env, work, fields):
    common = HARNESS.split("static void regression(void) {")[0]
    common = common.replace("/* SCALAR_SNAPSHOT */", "\n".join(f"APPEND({key});" for key in SCALARS))
    generated = work / "giant-scenarios.c"
    generated.write_text(PREAMBLE + f"\n#define SCHEMA_COUNT {len(fields)}\n" +
                         simulation(path.read_text(encoding="utf-8"), path.parent) +
                         common + GIANT_HARNESS, encoding="utf-8")
    executable = work / "giant-scenarios.exe"
    run([gcc, "-std=c99", "-O2", "-fno-strict-aliasing", generated, "-o", executable], env, work)
    result = json.loads(run([executable], env, work))
    result["scope"] = "Production host C scenarios with seeded final-stage clocks, health, displayed PCG state and motion positions; this is not an input-only full playthrough or a VDP test."
    return result


def self_test(source, original_trace, gcc, env, work, fields):
    """Known gameplay regressions must be rejected, rather than silently masked."""
    mutations = {
        "damage": ("if(shield)--shield;", "if(shield)shield-=2;"),
        "pause": ("mode=pause_previous;sound_mute(0);", "mode=PLAY;sound_mute(0);"),
        "spawn": ("((u16)32-difficulty*5)", "((u16)31-difficulty*5)"),
        "final_play": ("++stage_clock;", "++stage_clock;if(stage==4)++stage_clock;"),
    }
    rejected = {}
    for name, (old, new) in mutations.items():
        if source.count(old) != 1:
            raise RuntimeError(f"Mutation {name} requires one exact baseline location")
        try:
            _, mutated_trace = execute(f"control-{name}", source.replace(old, new),
                                       gcc, env, work, fields)
            difference = trace_difference(original_trace, mutated_trace, fields)
            if difference is None:
                raise AssertionError(f"Known {name} regression was not detected")
            rejected[name] = difference
        except RuntimeError as exc:
            if "CHECK FAILED:" not in str(exc):
                raise
            rejected[name] = "A production scenario assertion rejected the mutation"
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True,
                        help="Unmodified v1.2 game.c, archived before giant-boss implementation")
    parser.add_argument("--current", type=Path, default=ROOT / "src/game.c")
    parser.add_argument("--gcc", type=Path, default=Path("C:/msys64/ucrt64/bin/gcc.exe"))
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--report", type=Path,
                        help="Defaults to giant-preservation-verification.json in work directory")
    parser.add_argument("--registry", type=Path,
                        help="Optional pre-change asset/baseline/output ROM hash registry")
    parser.add_argument("--allow-changed-asset", action="append", default=[],
                        choices=("title.bin", "manifest.json", "pcg-manifest.json"),
                        help="Explicitly exempt a versioned title or metadata file; every world/frame/packet/sprite stays protected")
    parser.add_argument("--giant-checks", action="store_true",
                        help="Also exercise new giant mechanics at all 16 motion positions under host C")
    parser.add_argument("--self-test", action="store_true",
                        help="Also demonstrate detection of four intentional host-source regressions")
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    destination = args.report or work / "giant-preservation-verification.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(args.gcc.parent) + os.pathsep + env.get("PATH", "")
    fields = schema()
    sources = {"baseline": args.baseline.resolve(), "current": args.current.resolve()}
    report = {
        "passed": False,
        "method": "Execute archived v1.2 and current production C simulation plus extracted main-loop input dispatch under the same GCC host ABI; compare every original state field after identical seeded inputs.",
        "baseline": str(sources["baseline"]),
        "current": str(sources["current"]),
        "source_sha256": {key: sha256(path) for key, path in sources.items()},
        "compared_stages": [0, 1, 2, 3],
        "final_stage_scope": "Stage 4 PLAY through stage_clock 1199, ordinary attacks/damage/pickups/pause/retry; no changed final-boss state or entry tick.",
        "seeds": SEEDS,
        "schema": fields,
        "limits": [
            "No renderer, ROM bank layout, VDP transfers, controller hardware or native timing is exercised.",
            "16-bit object storage is used; expression promotion follows GCC, not the SDCC Z80 ABI.",
            "Sound-effect, mute and music command arguments are recorded; synthesized audio is not evaluated.",
            "New giant-only state has no v1.2 counterpart; all pre-existing simulation state is retained in comparison.",
            "Renderer-only state outside the simulation boundary is not serialized; original world_loaded and world_camera are included.",
        ],
        "execution": {},
    }
    try:
        if args.registry:
            checked, allowed = verify_registry(args.registry, sources["baseline"], args.allow_changed_asset)
            report["preserved_input_files"] = len(checked)
            report["preserved_input_registry_sha256"] = sha256(args.registry)
            report["explicit_versioned_asset_exceptions"] = allowed
        traces = {}
        for name, path in sources.items():
            report["execution"][name], traces[name] = execute(name, path.read_text(encoding="utf-8"),
                                                             args.gcc, env, work, fields, path.parent)
        if '#include "boss_layout.h"' in sources["current"].read_text(encoding="utf-8"):
            report["current_dependency_sha256"] = {
                name: sha256(sources["current"].parent / name)
                for name in ("boss_layout.h", "world_load.h")
            }
        difference = trace_difference(traces["baseline"], traces["current"], fields)
        if difference:
            raise AssertionError(difference)
        if args.self_test:
            report["positive_controls"] = self_test(sources["baseline"].read_text(encoding="utf-8"),
                                                     traces["baseline"], args.gcc, env, work, fields)
        if args.giant_checks:
            report["giant_mechanics"] = giant_checks(sources["current"], args.gcc, env, work, fields)
        report.update(passed=True, compared_snapshots=report["execution"]["current"]["snapshots"],
                      fields_per_snapshot=len(fields), trace_bytes=len(traces["current"]),
                      identical_trace_sha256=hashlib.sha256(traces["current"]).hexdigest())
    except Exception as exc:
        report["error"] = str(exc)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "schema"}, indent=2))


if __name__ == "__main__":
    main()
