/* NEON REVENANT - original 512 KiB ASCII8 game for MSX1 / TMS9918A.
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
#define ENEMIES 6
#define BULLETS 8
#define FXMAX 4
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
/* 64 resident 16x16 patterns, two buffered mode-1 SATs. No per-frame
 * sprite pattern upload. Higher-priority player/shots are submitted first;
 * rotating enemy order distributes unavoidable 4-sprite scanline loss. */
u8 attr_buffer[128],hud_buffer[128];
u8 sprite_count,sprite_page,selected_frame,world_phase,hud_last_mode;
volatile u8 sprite_dropped;
static const u8 video_rows[256]={0,1,2,3,4,5,6,7,8,8,9,10,11,12,13,14,15,16,16,16,17,18,19,20,21,22,23,24,24,25,26,27,28,29,30,31,32,32,33,34,35,36,37,38,39,40,40,41,42,43,44,45,46,47,48,48,49,50,51,52,53,54,55,56,56,57,58,59,60,61,62,63,64,64,65,66,67,68,69,70,71,72,72,73,74,75,76,77,78,79,80,80,81,82,83,84,85,86,87,88,88,89,90,91,92,93,94,95,96,96,97,98,99,100,101,102,103,104,104,105,106,107,108,109,110,111,112,112,113,114,115,116,117,118,119,120,120,121,122,123,124,125,126,127,128,128,129,130,131,132,133,134,135,136,136,137,138,139,140,141,142,143,144,144,145,146,147,148,149,150,151,152,152,153,154,155,156,157,158,159,160,160,161,162,163,164,165,166,167,168,168,169,170,171,172,173,174,175,176,176,177,178,179,180,181,182,183,184,184,185,186,187,188,189,190,191,192,192,193,194,195,196,197,198,199,200,200,201,202,203,204,205,206,207,208,208,209,210,211,212,213,214,215,216,216,217,218,219,220,221,222,223,224,224,225,226};
s16 video_y(s16 y){if(y<0||y>255)return y;return video_rows[(u8)y];}
void sprite(const Sprite *s,s16 x,s16 y,u8 tint){
    u8 i,early,pattern,color; s16 dx,dy;
    const u8 *record=(const u8*)(0x6000+s->offset);
    u8 *attributes=attr_buffer+((u16)sprite_count<<2);
    *((volatile u8*)0x6800)=4;
    y=video_y(y);
    for(i=0;i<s->count;i++){
        dx=x+(s8)*record++;dy=y+(s8)*record++;
        pattern=*record++;color=*record++;
        if(sprite_count==32){sprite_dropped+=s->count-i;return;}
        if(dx<=-32||dx>255||dy<16||dy>175){++sprite_dropped;continue;}
        early=0;if(dx<0){dx+=32;early=128;}
        *attributes++=(u8)(dy-1);*attributes++=(u8)dx;
        *attributes++=pattern;*attributes++=(tint?tint:color)|early;
        ++sprite_count;
    }
}
void hud_text(u8 col,u8 row,const char *p){
    u8 c;u8 *dest=hud_buffer+(u16)row*32+col;
    while(*p&&col<32){c=*p++;if(c<32||c>95)c=32;*dest++=192+c-32;++col;}
}
void hud_number(u8 col,u8 row,u16 v,u8 n){
    char b[6];u8 i=n;u16 q;b[n]=0;
    while(i){--i;q=v/10;b[i]='0'+(u8)(v-q*10);v=q;}hud_text(col,row,b);
}
void hud(void){
    u8 i,n;for(i=0;i<128;i++)hud_buffer[i]=192;
    hud_text(0,0,"SCORE");hud_number(6,0,score,5);
    hud_text(13,0,"HI");hud_number(16,0,highscore,5);
    hud_text(24,0,"ZONE");hud_number(29,0,stage+1,1);hud_text(30,0,"/3");
    hud_text(0,2,"SH");for(i=0;i<6;i++)hud_buffer[64+3+i]=192+(i<shield?'#':'.')-32;
    hud_text(11,2,"NOVA");for(i=0;i<3;i++)hud_buffer[64+16+i]=192+(i<bombs?'*':'.')-32;
    hud_text(22,2,"SPD");hud_number(26,2,620+(frame_counter&31)*3+stage*70,3);
    if(mode==PAUSED){hud_text(5,1,"PAUSED / ESC TO RESUME");}
    else if(mode==OVER){hud_text(10,1,"SIGNAL LOST");hud_text(4,3,"UNIT DOWN / FIRE TO RETRY");}
    else if(mode==CLEAR){hud_text(3,1,"THE NIGHT BELONGS TO YOU");hud_text(2,3,"ALL ZONES CLEAR / FIRE:RETRY");}
    else if(mode==TRANSIT){hud_text(8,1,"SECTOR LIBERATED");hud_text(5,3,"ACCELERATING TO NEXT ZONE");}
    else if(mode==BOSS){
        hud_text(0,1,"BOSS");n=(u16)boss_hp*25/(100+40*stage);
        for(i=0;i<25;i++)hud_buffer[32+6+i]=192+(i<n?'#':'.')-32;
        hud_text(0,3,boss_names[stage]);
    }else{
        hud_text(0,1,sector_names[stage]);
        hud_text(0,3,"ROUTE");n=stage_clock/63;if(n>24)n=24;
        for(i=0;i<24;i++)hud_buffer[96+7+i]=192+(i<n?'=':'.')-32;
    }
    if(combo>1&&mode==PLAY){hud_text(24,1,"CHAIN");hud_number(30,1,combo,1);}
    if(bomb_flash&&(mode==PLAY||mode==BOSS)){hud_text(8,1,"NOVA DISCHARGE");}
}
void draw_objects(void){
    u8 i,j,index,scale,rotation,scales[ENEMIES];const Sprite *s;Foe *e;
    /* Rotate equal-priority objects to avoid permanent scanline starvation. */
    if(!hurt_clock||(frame_counter&2)){
        s=&player[(keys&1)?0:((keys&2)?2:1)];sprite(s,player_x-s->w/2,player_y-s->h/2,0);
    }
    i=(u8)(frame_counter%BULLETS);
    for(j=0;j<BULLETS;j++){
        if(shots[i].active)sprite(&bullet,shots[i].x/4-2,shots[i].y/4-5,11);
        if(++i==BULLETS)i=0;
    }
    sprite(&reticle,aim_x-10,aim_y-10,7);
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        s=&bosses[stage];sprite(s,boss_x-s->w/2,boss_y-s->h/2,boss_flash?15:0);
    }
    rotation=(u8)(frame_counter%ENEMIES);
    for(i=0;i<ENEMIES;i++){
        if(foes[i].active){scale=foes[i].z/40;scales[i]=scale>5?5:scale;}
        else scales[i]=255;
    }
    for(j=6;j>0;j--){
        i=rotation;
        for(index=0;index<ENEMIES;index++){
            scale=scales[i];
            if(scale==j-1){e=&foes[i];s=&enemy[e->kind][scale];sprite(s,e->x-s->w/2,e->y-s->h/2,0);}
            if(++i==ENEMIES)i=0;
        }
    }
    if(pickup_on)sprite(&pickup,pickup_x-pickup.w/2,pickup_y-pickup.h/2,0);
    if((keys&16)&&shot_clock){
        u8 age=4-shot_clock;s16 x,y;
        x=player_x+((aim_x-player_x)*(age+1))/4;y=player_y+((aim_y-player_y)*(age+1))/4;
        sprite(&bullet,x-7,y-6,7);sprite(&bullet,x+5,y-6,7);
    }
    for(i=0;i<FXMAX;i++)if(fx[i].active){s=&explosion[fx[i].age>>2][fx[i].size];sprite(s,fx[i].x-s->w/2,fx[i].y-s->h/2,0);}
}
void draw_frame(void){
    if(mode==TITLE){gfx_wait_vblank();gfx_wait_vblank();return;}
    if(world_loaded!=stage){sound_mute(1);world_load(stage);world_loaded=stage;world_phase=255;hud_last_mode=255;sound_mute(0);}
    selected_frame=(frame_counter>>1)&7;
    sprite_count=0;sprite_dropped=0;draw_objects();
    if(sprite_count<32)attr_buffer[sprite_count*4]=208;
    gfx_write(sprite_page?0x3B80:0x3B00,attr_buffer,sprite_count<32?(u16)sprite_count*4+1:128);
    if(selected_frame!=world_phase){
        *((volatile u8*)0x6800)=14+stage;
        gfx_write(0x3840,(const u8*)(0x6000+(u16)selected_frame*640),640);world_phase=selected_frame;
    }
    /* HUD changes at 7.5 Hz; this preserves budget for input and combat. */
    if((mode!=PAUSED&&(frame_counter&3)==1)||hud_last_mode!=mode){
        hud();hud_last_mode=mode;
        gfx_write(0x3800,hud_buffer,64);gfx_write(0x3AC0,hud_buffer+64,64);
    }
    gfx_wait_vblank();gfx_wait_vblank();gfx_sprite_page(sprite_page);gfx_display(1);sprite_page^=1;
}
void main(void){
    u8 *p=(u8*)0xE000;while(p<(u8*)0xF200)*p++=0;
    rng=0x7A31;player_x=128;player_y=166;aim_x=128;aim_y=119;
    gfx_init();title_load();world_loaded=255;sprite_page=0;world_camera=0;sound_init();
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
