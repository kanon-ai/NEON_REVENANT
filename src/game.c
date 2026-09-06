/* NEON REVENANT - original 512 KiB ASCII8 game for MSX turbo R + V9990.
 * All simulation/render code executes from RAM. No host-side game engine.
 */
#include "hardware.h"
#include "assets.h"
#include "sound.h"
#include "world_load.h"
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
#define STAGE_TIME 1500

typedef struct { u8 active,kind,z,hp; s16 wx,wy,x,y; } Foe;
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
static const char * const sector_names[]={"01  CHROME DISTRICT","02  SKYWAY ASSAULT","03  THE BLACK SPIRE"};
static const char * const boss_names[]={"WARDEN / INTERCEPTOR","RAZOR / SIEGE CARRIER","NOX / CENTRAL CORE"};
static const u8 speed_colors[]={0xF3,0x3F,0xFC};

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
    mode=PLAY;player_x=128;player_y=166;aim_x=128;aim_y=119;shot_clock=0;hurt_clock=0;
    bomb_flash=0;stage_banner=90;transition_clock=0;combo=0;combo_clock=0;
    frames_played=0;boss_clock=0;boss_hp=0;boss_flash=0;
    sound_effect(5);
}
void damage(void){
    if(hurt_clock||bomb_flash||mode==TRANSIT)return;
    if(shield)--shield;hurt_clock=45;combo=0;combo_clock=0;sound_effect(3);
    explode(player_x,player_y-6,3);
    if(!shield){mode=OVER;transition_clock=0;sound_effect(2);}
}
void fire_enemy(s16 x,s16 y,u8 variant){
    u8 i; s16 dx,dy,den;
    for(i=0;i<BULLETS;i++)if(!shots[i].active){
        shots[i].active=1;shots[i].x=x*4;shots[i].y=y*4;
        dx=player_x-x;dy=player_y-y;
        if(variant==1)dx-=42;if(variant==2)dx+=42;
        den=abs16(dx);if(abs16(dy)>den)den=abs16(dy);if(den<1)den=1;
        shots[i].dx=dx*(7+stage*2)/den;shots[i].dy=dy*(7+stage*2)/den;
        if(!shots[i].dy)shots[i].dy=2;
        return;
    }
}
void kill_foe(Foe *e){
    e->active=0;explode(e->x,e->y,2+(e->z>120));
    if(combo<9)++combo;combo_clock=65;add_score(20+(u16)combo*5);sound_effect(2);
    if((random16()&15)==0&&!pickup_on&&shield<6){pickup_on=1;pickup_x=e->x;pickup_y=e->y;pickup_z=0;}
}
void player_fire(void){
    u8 i;Foe *best=0;u8 nearest=0;
    sound_effect(1);
    for(i=0;i<ENEMIES;i++)if(foes[i].active){
        Foe *e=&foes[i];s16 range=12+e->z/12;
        if(abs16(e->x-aim_x)<range&&abs16(e->y-aim_y)<range&&e->z>=nearest){best=e;nearest=e->z;}
    }
    if(best){if(best->hp)--best->hp;if(!best->hp)kill_foe(best);else explode(best->x,best->y,0);}
    if(mode==BOSS&&abs16(aim_x-boss_x)<43&&abs16(aim_y-boss_y)<27){
        if(boss_hp){--boss_hp;boss_flash=2;add_score(2);if(!boss_hp){
            reset_entities();explode(boss_x,boss_y,4);sound_effect(4);bomb_flash=30;
            add_score(500+100*stage);mode=TRANSIT;transition_clock=0;
        }}
    }
}
void use_bomb(void){u8 i;if(!bombs)return;--bombs;bomb_flash=18;sound_effect(4);
    for(i=0;i<ENEMIES;i++)if(foes[i].active)kill_foe(&foes[i]);
    for(i=0;i<BULLETS;i++)shots[i].active=0;
    if(mode==BOSS){if(boss_hp>25)boss_hp-=25;else boss_hp=1;boss_flash=12;}
}
void spawn_foe(void){u8 i;u16 r=random16();for(i=0;i<ENEMIES;i++)if(!foes[i].active){
    Foe *e=&foes[i];e->active=1;e->kind=(u8)(r%3);e->z=6;
    e->wx=(s16)(r&127)*2-127;e->wy=12+(u8)((r>>8)&63);
    e->hp=e->kind==2?3:2;e->x=128;e->y=84;return;
}}
void update_objects(void){u8 i;
    for(i=0;i<ENEMIES;i++)if(foes[i].active){Foe *e=&foes[i];
        e->z+=2;
        e->x=128+(e->wx*(s16)(e->z+16))/256;
        e->y=82+(e->wy*(s16)(e->z+16))/256;
        if(e->kind==1)e->x+=wave[(u8)(frame_counter+i*7)&63]/5;
        if(e->z==114||((stage>0)&&e->z==174))fire_enemy(e->x,e->y,0);
        if(e->z>232){if(abs16(e->x-player_x)<30&&abs16(e->y-player_y)<26)damage();e->active=0;}
    }
    for(i=0;i<BULLETS;i++)if(shots[i].active){Shot *s=&shots[i];s->x+=s->dx;s->y+=s->dy;
        if(s->x<0||s->x>1020||s->y<60||s->y>780)s->active=0;
        else if(abs16(s->x/4-player_x)<9&&abs16(s->y/4-(player_y-3))<8){s->active=0;damage();}
    }
    for(i=0;i<FXMAX;i++)if(fx[i].active){if(++fx[i].age>=16)fx[i].active=0;}
    if(pickup_on){pickup_y+=2;++pickup_z;if(abs16(pickup_x-player_x)<23&&abs16(pickup_y-player_y)<20){if(shield<6)++shield;pickup_on=0;add_score(50);sound_effect(5);}if(pickup_y>194)pickup_on=0;}
}
void update_boss(void){
    ++boss_clock;boss_x=128+wave[(u8)(boss_clock>>1)&63];
    boss_y=92+wave[(u8)(boss_clock>>2)+16&63]/4;
    if(boss_clock%(24-stage*4)==0){fire_enemy(boss_x-25,boss_y+12,0);fire_enemy(boss_x+25,boss_y+12,0);}
    if(stage>0&&boss_clock%57==0){fire_enemy(boss_x,boss_y,1);fire_enemy(boss_x,boss_y,2);}
    if(stage==2&&boss_clock%105==0)spawn_foe();
}
void update_play(void){
    ++frames_played;++frame_ticks;
    if(keys&1)player_x-=4;if(keys&2)player_x+=4;if(keys&4)player_y-=3;if(keys&8)player_y+=3;
    player_x=clamp(player_x,20,236);player_y=clamp(player_y,119,181);
    aim_x=128+((player_x-128)*3)/4;aim_y=84+((player_y-119)*3)/4;
    if(shot_clock)--shot_clock;
    if(hurt_clock)--hurt_clock;if(bomb_flash)--bomb_flash;if(boss_flash)--boss_flash;
    if(stage_banner)--stage_banner;
    if(combo_clock){if(!--combo_clock)combo=0;}
    if(edge&32)use_bomb();
    if(mode==PLAY){
        ++stage_clock;
        if(stage_clock%((u16)32-stage*5)==0)spawn_foe();
        if(stage_clock>=STAGE_TIME){mode=BOSS;boss_hp=100+40*stage;boss_clock=0;boss_x=128;boss_y=108;stage_banner=90;sound_effect(6);}
    }else if(mode==BOSS)update_boss();
    update_objects();
    if((keys&16)&&!shot_clock&&(mode==PLAY||mode==BOSS)){shot_clock=4;player_fire();}
    if(mode==TRANSIT){
        ++transition_clock;
        if(transition_clock==90){
            if(stage==2){mode=CLEAR;transition_clock=0;add_score(shield*100+bombs*200);}
            else{++stage;stage_clock=0;mode=PLAY;stage_banner=90;shield=shield<5?shield+2:6;if(bombs<3)++bombs;reset_entities();}
        }
    }
}
void draw_world(u8 scene){
    u16 sy,dy; s16 shift,target;
    if(world_loaded!=scene){
        /* No framebuffer is overwritten during the stage's asset transfer. */
        sound_mute(1);world_load(scene);world_loaded=scene;sound_mute(0);
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
void draw_objects(void){
    u8 i,j;Foe *e;const Sprite *s;
    // Depth buckets maintain far-to-near painter order without sorting RAM.
    for(j=0;j<6;j++)for(i=0;i<ENEMIES;i++)if(foes[i].active){e=&foes[i];u8 scale=e->z/40;if(scale>5)scale=5;
        if(scale==j){s=&enemy[e->kind][scale];sprite(s,e->x-s->w/2,e->y-s->h/2);}}
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        s=&bosses[stage];sprite(s,boss_x-s->w/2,boss_y-s->h/2);
        if(boss_flash)rect(boss_x-9,boss_y-2,18,3,0xFF);
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
     sprite(&reticle,aim_x-10,aim_y-10);
     if(lock){rect(aim_x-2,aim_y-2,5,5,0xFC);rect(aim_x,aim_y,1,1,0xFF);}
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
    number(168,202,620+(frame_counter&31)*3+stage*70,3);
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        rect(44,21,168,4,0x24);progress=(u16)boss_hp*166/(100+40*stage);rect(45,22,progress,2,0x3C);
    }else{progress=stage_clock/7;if(progress>212)progress=212;rect(22,20,212,2,0x24);rect(22,20,progress,2,0x83);}
    if(combo>1){text(4,29,"X");number(10,29,combo,1);}
    if(stage_banner){const Sprite *s=(mode==BOSS?&bossBanner[stage]:&stageBanner[stage]);gfx_blit(s->x,s->y,20,page_y()+41,216,24,0);}
}
void draw_title(void){
    const Sprite *s=&player[1];
    sprite(&titleLogo,(256-titleLogo.w)/2,27);
    rect(38,84,180,13,1);centered(88,"MIDNIGHT INTERCEPTION");
    rect(38,105,180,51,1);rect(38,105,180,1,0xF3);
    centered(112,"ARROWS / JOYSTICK : MOVE");centered(123,"SPACE / TRIGGER 1 : FIRE");centered(134,"X / TRIGGER 2 : NOVA");centered(145,"ESC : PAUSE");
    sprite(s,110,162);
    if(frame_counter&16)centered(188,"PRESS FIRE TO LAUNCH");
    text(8,4,"MSX TURBO R + V9990");text(190,4,"512K ROM");
    rect(0,203,256,9,1);centered(204,"ORIGINAL CODE / ART / MUSIC  2026");
}
void draw_frame(void){
    u8 scene=stage;if(mode==TITLE)scene=0;
    draw_world(scene);
    if(mode==TITLE){rect(0,0,256,18,0);rect(0,198,256,14,0);}
    if(mode==TITLE)draw_title();
    else{
        draw_objects();hud();
        if(bomb_flash){u8 h=(bomb_flash&7)+1;rect(0,26,256,h,0xFF);rect(0,193-h,256,h,0xF3);if(bomb_flash&2){rect(0,26,5,170,0xF3);rect(251,26,5,170,0x3F);}}
        if(mode==TRANSIT){rect(23,70,210,44,1);centered(79,"SECTOR LIBERATED");centered(97,"ACCELERATING TO NEXT ZONE");}
        if(mode==OVER){rect(30,69,196,65,1);rect(30,69,196,2,0x3F);centered(79,"SIGNAL LOST");centered(94,"REVENANT UNIT DOWN");text(76,109,"SCORE");number(118,109,score,5);if(frame_counter&16)centered(122,"FIRE TO RETRY");}
        if(mode==CLEAR){rect(18,65,220,91,1);rect(18,65,220,2,0xF3);centered(75,"THE NIGHT BELONGS TO YOU");centered(91,"ALL THREE SECTORS LIBERATED");text(70,111,"FINAL SCORE");number(142,111,score,5);centered(130,"THANK YOU FOR PLAYING");if(frame_counter&16)centered(145,"FIRE : FLY AGAIN");}
        if(mode==PAUSED){rect(42,81,172,37,1);centered(87,"PAUSED");centered(104,"ESC : RESUME");}
    }
    gfx_wait();gfx_flip(draw_page);draw_page^=1;
}
void main(void){
    // SDCC no-CRT build: explicitly initialize every persistent state field.
    u8 *p=(u8*)0xE000;while(p<(u8*)0xF200)*p++=0;
    rng=0x7A31;player_x=128;player_y=166;aim_x=128;aim_y=119;
    gfx_init();hardware_upload();world_load(0);world_loaded=0;world_camera=0;sound_init();
    for(;;){
        keys=input_read();edge=keys&~old_keys;old_keys=keys;
        if(mode==TITLE){if(edge&16)new_game();}
        else if(mode==OVER||mode==CLEAR){if(transition_clock<40)++transition_clock;else if(edge&16)new_game();}
        else if(mode==PAUSED){if(edge&64){mode=pause_previous;sound_mute(0);}}
        else if(edge&64){pause_previous=mode;mode=PAUSED;sound_mute(1);}
        else update_play();
        if(mode!=PAUSED){++frame_counter;sound_tick(stage,mode!=TITLE&&mode!=OVER);}
        draw_frame();
    }
}
