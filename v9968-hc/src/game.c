/* NEON REVENANT - original 1 MiB ASCII8 game for MSX turbo R + V9990.
 * All simulation/render code executes from RAM. No host-side game engine.
 */
#include "hardware.h"
#include "assets.h"
#include "sound.h"
#include "world_load.h"
#include "feature_assets.h"
typedef signed char s8;
typedef signed int s16;

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
u16 page_y(void){return ((u16)draw_page)<<8;}

void rect(s16 x,s16 y,s16 w,s16 h,u8 color){
    if(x<0){w+=x;x=0;}if(y<0){h+=y;y=0;}
    if(x+w>256)w=256-x;if(y+h>212)h=212-y;
    if(w>0&&h>0)gfx_fill(x,page_y()+y,w,h,color);
}
void sprite(const Sprite *s,s16 x,s16 y){
    s16 sx=s->x,sy=s->y,w=s->w,h=s->h;
    if(x<0){sx-=x;w+=x;x=0;}if(y<0){sy-=y;h+=y;y=0;}
    if(x+w>256)w=256-x;if(y+h>198)h=198-y;
    if(w>0&&h>0)gfx_blit(sx,sy,x,page_y()+y,w,h,1);
}
void text(s16 x,s16 y,const char *p){
    while(*p){u8 c=*p++;if(c>=32&&c<128){const Sprite *s=&font[c-32];
        if(x>=0&&x<251&&y>=0&&y<205)gfx_blit(s->x,s->y,x,page_y()+y,6,8,1);
        }x+=6;}
}
void centered(s16 y,const char *p){const char *q=p;u8 n=0;while(*q++){++n;}text(128-(s16)n*3,y,p);}
void number(s16 x,s16 y,u16 value,u8 digits){char b[6];u8 n=digits;b[n]=0;while(n){--n;b[n]='0'+value%10;value/=10;}text(x,y,b);}
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
        if(boss_hp){--boss_hp;boss_flash=2;add_score(2);if(!boss_hp){
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
        s16 spread=stage==4?92:25;
        fire_enemy(boss_x-spread,boss_y+22,0);fire_enemy(boss_x+spread,boss_y+22,0);
    }
    if(stage>=2&&boss_clock%73==0){fire_enemy(boss_x,boss_y,1);fire_enemy(boss_x,boss_y,2);}
    if(stage==3&&boss_clock%140==0)spawn_foe();
    if(stage==4&&final_phase>0&&boss_clock%120==0)spawn_wave();
    if(stage==4&&final_phase==2&&boss_clock%91==0){fire_enemy(boss_x,boss_y+28,0);fire_enemy(boss_x,boss_y+28,1);fire_enemy(boss_x,boss_y+28,2);}
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
void draw_world(u8 scene){
    u16 sy,dy; s16 shift,target;u8 band;
    if(world_loaded!=scene){
        /* No framebuffer is overwritten during the stage's asset transfer. */
        audio_mute(1);world_load(scene);world_loaded=scene;audio_mute(0);
    }
    if(mode!=PAUSED){
        target=(128-player_x)/16;
        if(world_camera<target)++world_camera;
        if(world_camera>target)--world_camera;
    }
    /* Building silhouettes, all facade texture, and pavement share one 3D
     * camera advance. These are complete projected world frames, not lights
     * painted over a static road. Lateral inertia is applied at runtime. */
    sy=1152+(frame_counter&15)*180;
    dy=page_y()+18;
    shift=world_camera+wave[(u8)(frame_counter>>3)&63]/24;
    /* Keep long facades continuous. Exposed edge is dark peripheral space;
     * the two unrelated street sides must never wrap onto each other. */
    if(shift>0){
        gfx_blit(0,sy,shift,dy,256-shift,180,0);
        gfx_fill(0,dy,shift,180,1);
    }else if(shift<0){
        gfx_blit(-shift,sy,0,dy,256+shift,180,0);
        gfx_fill(256+shift,dy,-shift,180,1);
    }else gfx_blit(0,sy,0,dy,256,180,0);
}
void draw_giant_boss(void){
    s16 x=boss_x-88,y=boss_y-30;
    s16 arm=wave[(u8)(boss_clock*2)&63]/10;
    u8 recoil=boss_clock&15;
    if(recoil>5)recoil=0;else recoil=5-recoil;
    sprite(&feature_arm_left,x+FEATURE_ARM_LEFT_X,y+arm+recoil);
    sprite(&feature_arm_right,x+FEATURE_ARM_RIGHT_X,y-arm+recoil);
    sprite(&feature_hull,x,y);
    sprite(&feature_core[(boss_clock>>2)&1],x+FEATURE_HULL_CORE_X,y+FEATURE_HULL_CORE_Y);
    if(boss_flash){rect(boss_x-5,boss_y+7,10,3,0xFF);}
    /* Lit weapon ports announce each volley while the pods recoil. */
    if((boss_clock&15)>11){
        rect(x-11,y+47+arm,6,2,0xFF);
        rect(x+183,y+47-arm,6,2,0xFF);
    }
}
void draw_objects(void){
    u8 i,j;Foe *e;const Sprite *s;
    // Depth buckets maintain far-to-near painter order without sorting RAM.
    for(j=0;j<6;j++)for(i=0;i<ENEMIES;i++)if(foes[i].active){e=&foes[i];u8 scale=e->z/40;if(scale>5)scale=5;
        if(scale==j){s=&enemy[e->kind][scale];sprite(s,e->x-s->w/2,e->y-s->h/2);}}
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        if(stage==4)draw_giant_boss();
        else{
            s=&bosses[boss_sprite[stage]];sprite(s,boss_x-s->w/2,boss_y-s->h/2);
            if(boss_flash)rect(boss_x-9,boss_y-2,18,3,0xFF);
        }
    }
    if(pickup_on){sprite(&pickup,pickup_x-pickup.w/2,pickup_y-pickup.h/2);}
    for(i=0;i<BULLETS;i++)if(shots[i].active){s16 x=shots[i].x/4,y=shots[i].y/4;
        rect(x-3,y-4,7,8,0x24);rect(x-1,y-3,3,6,0x3C);rect(x,y-1,1,3,0xFF);
    }
    if((keys&16)&&shot_clock){
        u8 age=4-shot_clock; s16 x,y;
        x=player_x+((aim_x-player_x)*(age+1))/4;y=player_y+((aim_y-player_y)*(age+1))/4;
        rect(x-7,y-6,2,11,0xF3);rect(x+6,y-6,2,11,0xF3);
        if(age==0){rect(player_x-13,player_y-20,3,12,0xFF);rect(player_x+10,player_y-20,3,12,0xFF);}
    }
    // Visible, generous targeting box; changes color while a target is inside.
    {u8 lock=0;for(i=0;i<ENEMIES;i++)if(foes[i].active&&abs16(foes[i].x-aim_x)<24&&abs16(foes[i].y-aim_y)<24)lock=1;
     if(mode==BOSS&&abs16(aim_x-boss_x)<43&&abs16(aim_y-boss_y)<27)lock=1;
     {
         sprite(&reticle,aim_x-10,aim_y-10);
         if(lock){rect(aim_x-2,aim_y-2,5,5,0xFC);rect(aim_x,aim_y,1,1,0xFF);}
     }
    }
    if(!hurt_clock||(frame_counter&2)){
        s=&player[(keys&1)?0:((keys&2)?2:1)];
        rect(player_x-9,player_y+9,4,5+(frame_counter&3),0x23);
        rect(player_x+5,player_y+9,4,5+(frame_counter&3),0x23);
        rect(player_x-8,player_y+9,2,4+(frame_counter&3),0xF3);
        rect(player_x+6,player_y+9,2,4+(frame_counter&3),0xF3);
        sprite(s,player_x-s->w/2,player_y-s->h/2);
    }
    for(i=0;i<FXMAX;i++)if(fx[i].active){s=&explosion[fx[i].age>>2][fx[i].size];sprite(s,fx[i].x-s->w/2,fx[i].y-s->h/2);}
}
void hud(void){u8 i;u16 progress;
    gfx_blit(0,HUD_TOP_Y,0,page_y(),256,18,0);
    number(41,5,score,5);number(106,5,highscore,5);number(218,5,stage+1,1);
    gfx_blit(0,HUD_BOTTOM_Y,0,page_y()+198,256,14,0);
    for(i=0;i<6;i++)rect(24+i*7,203,5,5,i<shield?0xE3:0x24);
    for(i=0;i<3;i++)rect(104+i*7,203,5,5,i<bombs?0x3F:0x24);
    number(168,202,520+(frame_counter&31)*3+stage*60,3);
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        rect(44,21,168,4,0x24);progress=(u16)boss_hp*166/boss_health[stage];rect(45,22,progress,2,0x3C);
    }else{progress=(stage_clock*42)/(stage_times[stage]/5);if(progress>210)progress=210;rect(22,20,212,2,0x24);rect(22,20,progress,2,0x83);}
    if(combo>1){text(4,29,"X");number(10,29,combo,1);}
    if(stage_banner){rect(15,38,226,29,1);rect(15,38,226,1,0xF3);
        centered(43,mode==BOSS?boss_names[stage]:sector_names[stage]);
        centered(55,mode==BOSS?"WARNING - HEAVY CONTACT":"BREAK THROUGH THE NIGHT");}
    if(stage==4&&mode==BOSS){text(190,29,"PHASE");number(226,29,final_phase+1,1);}

}
void draw_title(void){
    const Sprite *s=&player[1];
    sprite(&titleLogo,(256-titleLogo.w)/2,27);
    rect(38,84,180,13,1);centered(88,"HC / HARD CORE");
    rect(38,105,180,51,1);rect(38,105,180,1,0xF3);
    centered(112,"ARROWS / JOYSTICK : MOVE");centered(123,"FIRE : SPACE    NOVA : X");centered(134,"ESC : PAUSE / RESUME");centered(145,"UP + FIRE : BOSS TEST");
    sprite(s,110,162);
    if(frame_counter&16)centered(188,"PRESS FIRE TO LAUNCH");
    text(8,4,"MSX TURBO R + V9968");text(190,4,"2MB DEV");
    rect(0,203,256,9,1);centered(204,"ORIGINAL CODE / ART / MUSIC  2026");
}
void draw_frame(void){
    u8 scene=stage;if(mode==TITLE)scene=0;
    gfx_palette_select(0);
    draw_world(scene);
    if(mode==TITLE){rect(0,0,256,18,0);rect(0,198,256,14,0);}
    if(mode==TITLE)draw_title();
    else{
        draw_objects();hud();
        if(bomb_flash){u8 h=(bomb_flash&7)+1;rect(0,26,256,h,0xFF);rect(0,193-h,256,h,0xF3);if(bomb_flash&2){rect(0,26,5,170,0xF3);rect(251,26,5,170,0x3F);}}
        if(mode==TRANSIT){rect(23,70,210,44,1);centered(79,"SECTOR LIBERATED");centered(97,"ACCELERATING TO NEXT ZONE");}
        if(mode==OVER){rect(30,69,196,65,1);rect(30,69,196,2,0x3F);centered(79,"SIGNAL LOST");centered(94,"REVENANT UNIT DOWN");text(76,109,"SCORE");number(118,109,score,5);if(frame_counter&16)centered(122,"FIRE TO RETRY");}
        if(mode==CLEAR){rect(18,65,220,91,1);rect(18,65,220,2,0xF3);centered(75,"THE NIGHT BELONGS TO YOU");centered(91,"ALL FIVE SECTORS LIBERATED");text(70,111,"FINAL SCORE");number(142,111,score,5);centered(130,"THANK YOU FOR PLAYING");if(frame_counter&16)centered(145,"FIRE : FLY AGAIN");}
        if(mode==PAUSED){rect(42,81,172,37,1);centered(87,"PAUSED");centered(104,"ESC : RESUME");}
    }
    gfx_wait();gfx_flip(draw_page);draw_page^=1;
}
void main(void){
    // SDCC no-CRT build: explicitly initialize every persistent state field.
    u8 *p=(u8*)0xE000;while(p<(u8*)0xF200)*p++=0;
    rng=0x7A31;player_x=128;player_y=166;aim_x=128;aim_y=119;
    gfx_init();hardware_upload();world_load(0);world_loaded=0;world_camera=0;sound_init();audio_setup();
    for(;;){
        keys=input_read();edge=keys&~old_keys;old_keys=keys;
        if(mode==TITLE){if(edge&16){
            new_game();
            if(keys&INPUT_UP){stage=4;mode=BOSS;boss_hp=boss_health[4];boss_x=128;boss_y=82;stage_banner=90;}
        }}
        else if(mode==OVER||mode==CLEAR){if(transition_clock<40)++transition_clock;else if(edge&16)new_game();}
        else if(mode==PAUSED){if(edge&64){mode=pause_previous;audio_mute(0);}}
        else if(edge&64){pause_previous=mode;mode=PAUSED;audio_mute(1);}
        else update_play();
        audio_stage=stage_music[stage];audio_playing=mode!=TITLE&&mode!=OVER;
        if(mode!=PAUSED){++frame_counter;}
        draw_frame();
    }
}
