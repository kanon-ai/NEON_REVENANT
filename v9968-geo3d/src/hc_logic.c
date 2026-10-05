/* HC v1.2 combat routines copied without rule edits; render/audio adapters below. */
typedef unsigned char u8; typedef unsigned int u16;
#include "sound.h"
void audio_effect(u8 value) __naked {
 value;
 __asm
 ld c,a
 ld a,i
 di
 push af
 ld a,c
 call _sound_effect
 pop af
 ret po
 ei
 ret
 __endasm;
}
typedef signed char s8;
typedef signed int s16;
void boss_hit_particles(s16 x,s16 y);
u8 boss_volley;

#define TITLE 0
#define PLAY 1
#define BOSS 2
#define TRANSIT 3
#define OVER 4
#define CLEAR 5
#define PAUSED 6
#define ENEMIES 9
#define BULLETS 14
#define FXMAX 7
#define STAGES 5

typedef struct { u8 active,kind,z,hp,pattern,age; s16 wx,wy,x,y; } Foe;
typedef struct { u8 active; s16 x,y,dx,dy; } Shot;
typedef struct { u8 active,age,size; s16 x,y; } Effect;
// Exposed symbols intentionally make native emulator validation repeatable.
volatile u8 mode,stage,shield,bombs;
volatile u16 score,highscore,stage_clock,frame_counter,boss_hp;
volatile s16 player_x,player_y;
u8 old_keys,keys,edge,draw_page,shot_clock,bomb_flash,hurt_clock;
u8 stage_banner,transition_clock,boss_phase,boss_flash,combo,combo_clock;
u16 rng,boss_clock,frames_played,frame_ticks;
s16 aim_x,aim_y,boss_x,boss_y;
Foe foes[ENEMIES];
Shot shots[BULLETS];
Effect fx[FXMAX];
u8 pickup_on,pickup_z;
s16 pickup_x,pickup_y;
u8 pause_previous;
/* Visual state only: the simulation and collision coordinates are unchanged. */
u8 world_loaded;
s16 world_camera;

static const s8 wave[64]={0,6,12,18,24,30,35,40,45,49,53,56,59,61,63,64,64,64,63,61,59,56,53,49,45,40,35,30,24,18,12,6,0,-6,-12,-18,-24,-30,-35,-40,-45,-49,-53,-56,-59,-61,-63,-64,-64,-64,-63,-61,-59,-56,-53,-49,-45,-40,-35,-30,-24,-18,-12,-6};
static const char * const sector_names[]={"00 BREAKWATER APPROACH","01 CHROME DISTRICT","02 SKYWAY ASSAULT","03 THE BLACK SPIRE","04 DAWN EXODUS"};
static const char * const boss_names[]={"SENTRY / HARBOR GUARD","WARDEN / INTERCEPTOR","RAZOR / SIEGE CARRIER","NOX / CENTRAL CORE","DAWN LEVIATHAN"};
static const u8 speed_colors[]={0xF3,0x3F,0xFC,0x3F,0xFC};
static const u16 stage_times[5]={675,1200,1320,1440,1560};
static const u16 boss_health[5]={70,100,140,180,240};
static const u16 approach_waves[28]={24,48,72,96,132,150,168,192,228,246,264,288,324,342,360,384,420,438,456,480,516,534,552,576,612,630,648,666};
static const u8 spawn_period[5]={24,22,18,15,15};
static const u8 bullet_speed[5]={11,11,14,17,17};
static const u8 fire_depth[5]={114,114,114,114,114};
static const u8 stage_music[5]={0,0,1,2,2};
static const u8 boss_sprite[5]={0,0,1,2,2};
u16 wave_number;
u8 final_phase;
/* Fractional extra movement: player +15%, foe approach +10%. */
u8 player_x_fraction,player_y_fraction,foe_fraction[ENEMIES];

u16 random16(void){ rng^=rng<<7; rng^=rng>>9; rng^=rng<<8; return rng; }
s16 abs16(s16 n){return n<0?-n:n;}
s16 clamp(s16 n,s16 lo,s16 hi){if(n<lo)return lo;if(n>hi)return hi;return n;}
void add_score(u16 points){score+=points;if(score>highscore)highscore=score;}
void explode(s16 x,s16 y,u8 size){u8 i;for(i=0;i<FXMAX;i++)if(!fx[i].active){fx[i].active=1;fx[i].age=0;fx[i].x=x;fx[i].y=y;fx[i].size=size;break;}}
void reset_entities(void){u8 i;for(i=0;i<ENEMIES;i++)foes[i].active=0;for(i=0;i<BULLETS;i++)shots[i].active=0;for(i=0;i<FXMAX;i++)fx[i].active=0;pickup_on=0;}
void new_game(void){
    reset_entities();stage=0;shield=6;bombs=3;score=0;stage_clock=0;
    wave_number=0;final_phase=0;player_x_fraction=0;player_y_fraction=0;
    mode=PLAY;player_x=128;player_y=166;aim_x=128;aim_y=119;shot_clock=0;hurt_clock=0;
    bomb_flash=0;stage_banner=90;transition_clock=0;combo=0;combo_clock=0;
    frames_played=0;boss_clock=0;boss_hp=0;boss_flash=0;
    audio_effect(5);
}
void damage(void){
    if(hurt_clock||bomb_flash||mode==TRANSIT)return;
    if(shield)--shield;hurt_clock=45;combo=0;combo_clock=0;audio_effect(3);
    explode(player_x,player_y-6,3);
    if(!shield){mode=OVER;transition_clock=0;audio_effect(2);}
}
void fire_enemy(s16 x,s16 y,u8 variant){
    u8 i; s16 dx,dy,den;
    for(i=0;i<BULLETS;i++)if(!shots[i].active){
        shots[i].active=1;shots[i].x=x*4;shots[i].y=y*4;
        dx=player_x-x;dy=player_y-y;
        if(variant==1)dx-=42;if(variant==2)dx+=42;
        den=abs16(dx);if(abs16(dy)>den)den=abs16(dy);if(den<1)den=1;
        shots[i].dx=dx*(bullet_speed[stage])/den;shots[i].dy=dy*(bullet_speed[stage])/den;
        if(!shots[i].dy)shots[i].dy=2;
        return;
    }
}
void kill_foe(Foe *e){
    e->active=0;explode(e->x,e->y,2+(e->z>120));
    if(combo<9)++combo;combo_clock=65;add_score(20+(u16)combo*5);audio_effect(2);
    if((random16()&15)==0&&!pickup_on&&shield<6){pickup_on=1;pickup_x=e->x;pickup_y=e->y;pickup_z=0;}
}
void player_fire(void){
    u8 i;Foe *best=0;u8 nearest=0;
    audio_effect(1);
    for(i=0;i<ENEMIES;i++)if(foes[i].active){
        Foe *e=&foes[i];s16 range=12+e->z/12;
        if(abs16(e->x-aim_x)<range&&abs16(e->y-aim_y)<range&&e->z>=nearest){best=e;nearest=e->z;}
    }
    if(best){if(best->hp)--best->hp;if(!best->hp)kill_foe(best);else explode(best->x,best->y,0);}
    if(mode==BOSS&&abs16(aim_x-boss_x)<43&&abs16(aim_y-boss_y)<27){
        if(boss_hp){boss_hit_particles(aim_x,aim_y);--boss_hp;boss_flash=2;add_score(2);if(!boss_hp){
            reset_entities();explode(boss_x,boss_y,4);audio_effect(4);bomb_flash=30;
            add_score(500+100*stage);mode=TRANSIT;transition_clock=0;
        }}
    }
}
void use_bomb(void){u8 i;if(!bombs)return;--bombs;bomb_flash=18;audio_effect(4);
    for(i=0;i<ENEMIES;i++)if(foes[i].active)kill_foe(&foes[i]);
    for(i=0;i<BULLETS;i++)shots[i].active=0;
    if(mode==BOSS){if(boss_hp>25)boss_hp-=25;else boss_hp=1;boss_flash=12;}
}
void spawn_foe(void){u8 i;u16 r=random16();for(i=0;i<ENEMIES;i++)if(!foes[i].active){
    Foe *e=&foes[i];e->active=1;e->kind=(u8)(r%(stage?3:2));e->z=6;e->age=0;foe_fraction[i]=0;
    e->pattern=wave_number%(stage<2?stage+2:6);
    e->wx=(s16)(r&127)*2-127;e->wy=18+(u8)((r>>8)&63);
    if(e->pattern==2)e->wx=(wave_number&1)?-200:200;
    if(e->pattern==3)e->wy=-20;
    e->hp=(stage==0?1:2)+(e->kind==2)+(stage>=3);e->x=128;e->y=84;return;
}}
void spawn_wave(void){
    ++wave_number;spawn_foe();
    /* Alternate breathing room with paired and three-ship encounters. */
    /* More frequent single arrivals avoid the cost of stacked waves. */

}
void update_objects(void){u8 i;
    for(i=0;i<ENEMIES;i++)if(foes[i].active){Foe *e=&foes[i];u8 old_z=e->z;
        u8 advance=(e->pattern==5&&e->z>100)?1:3;
        ++e->age;
        if(e->pattern==5&&e->z>100){foe_fraction[i]+=5;if(foe_fraction[i]>=10){foe_fraction[i]-=10;++advance;}}
        e->z+=advance;
        e->x=128+(e->wx*(s16)(e->z+16))/256;
        e->y=82+(e->wy*(s16)(e->z+16))/256;
        switch(e->pattern){
        case 1:e->x+=wave[(e->age+i*7)&63]/3;break;
        case 2:e->x+=(e->wx<0?1:-1)*(s16)e->z/2;break;
        case 3:e->y+=(s16)e->age*e->age/150;break;
        case 4:e->x+=wave[(e->age*2+i*8)&63]/2;e->y+=wave[(e->age+i*8)&63]/4;break;
        case 5:e->x+=wave[(e->age+i*9)&63]/2;break;
        }
        if(old_z<fire_depth[stage]&&e->z>=fire_depth[stage]){
            fire_enemy(e->x,e->y,0);
            /* First volley is aimed; later volley introduces spread. */
        }
        if(stage>=2&&old_z<174&&e->z>=174){
            if(e->kind==2){fire_enemy(e->x-5,e->y,1);fire_enemy(e->x+5,e->y,2);}
            else fire_enemy(e->x,e->y,0);
        }
        if(e->z>232){if(abs16(e->x-player_x)<30&&abs16(e->y-player_y)<26)damage();e->active=0;}
    }
    for(i=0;i<BULLETS;i++)if(shots[i].active){Shot *s=&shots[i];s->x+=s->dx;s->y+=s->dy;
        if(s->x<0||s->x>1020||s->y<60||s->y>780)s->active=0;
        else if(abs16(s->x/4-player_x)<9&&abs16(s->y/4-(player_y-3))<8){s->active=0;damage();}
    }
    for(i=0;i<FXMAX;i++)if(fx[i].active){if(++fx[i].age>=16)fx[i].active=0;}
    if(pickup_on){pickup_y+=2;++pickup_z;if(abs16(pickup_x-player_x)<23&&abs16(pickup_y-player_y)<20){if(shield<6)++shield;pickup_on=0;add_score(50);audio_effect(5);}if(pickup_y>194)pickup_on=0;}
}
void update_boss(void){
    u8 cadence=32-stage*4;
    ++boss_clock;boss_x=128+wave[(u8)(boss_clock>>1)&63];
    boss_y=92+wave[((u8)(boss_clock>>2)+16)&63]/4;
    if(stage==4){
        final_phase=boss_hp>160?0:(boss_hp>80?1:2);
        boss_x=128+wave[(u8)(boss_clock>>1)&63]/3;
        boss_y=82+wave[((u8)(boss_clock>>2)+16)&63]/8;
        cadence=26-final_phase*4;
    }
    /* Alternating windows make every volley escapable instead of constant fire. */
    if(boss_clock%cadence==0 && (boss_clock%160)<116){
        boss_volley|=1;
    }
    if(stage>=2&&boss_clock%73==0)boss_volley|=2;
    if(stage==3&&boss_clock%140==0)spawn_foe();
    if(stage==4&&final_phase>0&&boss_clock%120==0)spawn_wave();
    if(stage==4&&final_phase==2&&boss_clock%91==0)boss_volley|=4;
}
void update_play(void){
    u8 move_x=4,move_y=3;
    ++frames_played;++frame_ticks;
    if((keys&3)==1||(keys&3)==2){player_x_fraction+=12;if(player_x_fraction>=20){player_x_fraction-=20;++move_x;}}else player_x_fraction=0;
    if((keys&12)==4||(keys&12)==8){player_y_fraction+=9;if(player_y_fraction>=20){player_y_fraction-=20;++move_y;}}else player_y_fraction=0;
    if(keys&1)player_x-=move_x;if(keys&2)player_x+=move_x;if(keys&4)player_y-=move_y;if(keys&8)player_y+=move_y;
    player_x=clamp(player_x,20,236);player_y=clamp(player_y,119,181);
    aim_x=128+((player_x-128)*3)/4;aim_y=84+((player_y-119)*3)/4;
    if(shot_clock)--shot_clock;
    if(hurt_clock)--hurt_clock;if(bomb_flash)--bomb_flash;if(boss_flash)--boss_flash;
    if(stage_banner)--stage_banner;
    if(combo_clock){if(!--combo_clock)combo=0;}
    if(edge&32)use_bomb();
    if(mode==PLAY){
        ++stage_clock;
        if(stage==0){if(wave_number<28&&stage_clock==approach_waves[wave_number])spawn_wave();}
        else if(stage_clock%spawn_period[stage]==0)spawn_wave();
        if(stage_clock>=stage_times[stage]){mode=BOSS;boss_hp=boss_health[stage];boss_clock=0;boss_x=128;boss_y=108;stage_banner=90;audio_effect(6);}
    }else if(mode==BOSS)update_boss();
    update_objects();
    if((keys&16)&&!shot_clock&&(mode==PLAY||mode==BOSS)){shot_clock=4;player_fire();}
    if(mode==TRANSIT){
        ++transition_clock;
        if(transition_clock==90){
            if(stage==STAGES-1){mode=CLEAR;transition_clock=0;add_score(shield*100+bombs*200);}
            else{++stage;stage_clock=0;wave_number=0;mode=PLAY;stage_banner=90;shield=shield<5?shield+2:6;if(bombs<3)++bombs;reset_entities();}
        }
    }
}

#include "geo_adapter.h"
