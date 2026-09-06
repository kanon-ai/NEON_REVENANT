/* NEON REVENANT - original 512 KiB ASCII8 game for MSX2 / V9938.
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
/* SCREEN4 resident worlds, double-buffered mode-2 sprite tables. */
u8 sprite_count, sprite_page, selected_frame;
u8 color_buffer[512], attr_buffer[128], hud_buffer[128];
/* Each inactive sprite page retains 64 pattern templates. The generated
 * template ID avoids dividing an offset by 50 on the Z80. */
u8 cache_slot[2][113], cache_id[2][64], cache_lock[64], cache_next[2];
u8 sprite_ids[32], pattern_uploads, logic_steps, sprite_tint;
u8 last_hud_mode,last_hud_stage,last_hud_shield,last_hud_bombs;
u16 last_hud_score,last_hud_frame;
void sprite_cache_reset(void){
    u16 i;u8 *p=(u8*)cache_slot;
    for(i=0;i<sizeof(cache_slot);i++)p[i]=255;
    p=(u8*)cache_id;for(i=0;i<sizeof(cache_id);i++)p[i]=255;
    cache_next[0]=cache_next[1]=0;last_hud_mode=255;
}
u8 pattern_slot(u8 id,const u8 *record){
    u8 slot=cache_slot[sprite_page][id],old;
    if(slot==255){
        slot=cache_next[sprite_page];while(cache_lock[slot])slot=(slot+1)&63;
        cache_next[sprite_page]=(slot+1)&63;
        old=cache_id[sprite_page][slot];if(old!=255)cache_slot[sprite_page][old]=255;
        cache_id[sprite_page][slot]=id;cache_slot[sprite_page][id]=slot;
        gfx_write((sprite_page?0x9800UL:0x1800UL)+(u16)slot*32,record,32);
        ++pattern_uploads;
    }
    cache_lock[slot]=1;return slot;
}
/* Most records need no recoloring or clipping. This replaces SDCC's
 * per-byte C loop with a 16-byte transfer while preserving IX/IY. */
void color_copy16(const u8 *source,u8 *destination) __sdcccall(1) __naked{
    (void)source;(void)destination;
    __asm
        ld bc,#16
        ldir
        ret
    __endasm;
}
void color_tint16(const u8 *source,u8 *destination) __sdcccall(1) __naked{
    (void)source;(void)destination;
    __asm
        ld a,(_sprite_tint)
        ld c,a
        ld b,#16
msx2_color_tint:
        ld a,(hl)
        inc hl
        or a
        jr z,msx2_color_store
        ld a,c
msx2_color_store:
        ld (de),a
        inc de
        djnz msx2_color_tint
        ret
    __endasm;
}
volatile u8 sprite_dropped;
u8 source_bank;
const u8 *source_ptr;

u8 asset_read(void) __naked{
    __asm
        ld hl,(_source_ptr)
        ld b,(hl)
        inc hl
        ld a,h
        cp #0x80
        jr nz,tr_asset_read_ready
        ld a,(_source_bank)
        inc a
        ld (_source_bank),a
        ld (0x6800),a
        ld hl,#0x6000
tr_asset_read_ready:
        ld (_source_ptr),hl
        ld a,b
        ret
    __endasm;
}
/* Every descriptor points into the one-bank hardware-sprite atlas. Refuse a
 * larger generated atlas rather than silently crossing the ASCII8 window. */
#if SPRITE_DATA_BYTES > 8192
#error SCREEN4_sprite_atlas_must_fit_one_ASCII8_bank
#endif
/* SDCC call(1): source in HL, destination in DE. IX/IY are preserved. */
void asset_copy32(const u8 *source,u8 *destination) __sdcccall(1) __naked{
    (void)source;(void)destination;
    __asm
        ld bc,#32
        ldir
        ret
    __endasm;
}
s16 video_y(s16 y){if(y>=-32&&y<224)return video_y_table[(u8)(y+32)];return 16+(y-18)*8/9;}
void sprite(const Sprite *s,s16 x,s16 y,u8 tint){
    u8 i,j,early,row_y,id,slot; s16 dx,dy;
    if(sprite_count==32){sprite_dropped+=s->count;return;}
    const u8 *record=(const u8*)(0x6000+s->offset);
    u8 *colors=color_buffer+((u16)sprite_count<<4);
    u8 *attributes=attr_buffer+((u16)sprite_count<<2);
    *((volatile u8*)0x6800)=4;y=video_y(y);id=s->first;
    for(i=0;i<s->count;i++,id++){
        if(sprite_count==32){sprite_dropped+=s->count-i;return;}
        dx=x+(s8)*record++;dy=y+(s8)*record++;
        if(dx<=-32||dx>255||dy<0||dy>175){record+=48;++sprite_dropped;continue;}
        early=0;if(dx<0){dx+=32;early=128;}
        slot=pattern_slot(id,record);record+=32;
        if(tint){sprite_tint=tint;color_tint16(record,colors);}
        else color_copy16(record,colors);
        if(early)for(j=0;j<16;j++)colors[j]|=128;
        j=0;row_y=(u8)dy;
        while(row_y<16){colors[j++]=early;row_y+=2;}
        j=16;row_y=(u8)dy+30;
        while(row_y>174){colors[--j]=early;row_y-=2;}
        record+=16;colors+=16;
        *attributes++=(u8)(dy-1);*attributes++=(u8)dx;
        *attributes++=slot*4;*attributes++=0;
        sprite_ids[sprite_count]=id;++sprite_count;
    }
}
void hud_text(u8 col,u8 row,const char *p){
    u8 c;while(*p&&col<32){c=*p++;if(c<32||c>95)c=32;hud_buffer[row*32+col++]=192+c-32;}
}
void hud_number(u8 col,u8 row,u16 v,u8 n){
    char b[6];u8 i=n;b[n]=0;while(i){--i;b[i]='0'+v%10;v/=10;}hud_text(col,row,b);
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
        if(shots[i].active)sprite(&bullet,shots[i].x/4-2,shots[i].y/4-5,14);
        if(++i==BULLETS)i=0;
    }
    sprite(&reticle,aim_x-10,aim_y-10,6);
    if(mode==BOSS||(mode==PAUSED&&pause_previous==BOSS)){
        s=&bosses[stage];sprite(s,boss_x-s->w/2,boss_y-s->h/2,boss_flash?7:0);
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
        sprite(&bullet,x-7,y-6,6);sprite(&bullet,x+5,y-6,6);
    }
    for(i=0;i<FXMAX;i++)if(fx[i].active){s=&explosion[fx[i].age>>2][fx[i].size];sprite(s,fx[i].x-s->w/2,fx[i].y-s->h/2,0);}
}
void draw_frame(void){
    u32 name;u8 i;
    if(mode==TITLE){logic_steps=gfx_wait_frame();return;}
    if(world_loaded!=stage){
        sound_mute(1);world_load(stage);world_loaded=stage;sound_mute(0);
        sprite_cache_reset();gfx_clock_reset();
    }
    selected_frame=(frame_counter>>1)&7;
    sprite_count=0;sprite_dropped=0;pattern_uploads=0;
    for(i=0;i<64;i++)cache_lock[i]=0;
    draw_objects();
    if(last_hud_mode!=mode||last_hud_stage!=stage||last_hud_score!=score||
       last_hud_shield!=shield||last_hud_bombs!=bombs||(u16)(frame_counter-last_hud_frame)>=8){
        hud();last_hud_mode=mode;last_hud_stage=stage;last_hud_score=score;
        last_hud_shield=shield;last_hud_bombs=bombs;last_hud_frame=frame_counter;
    }
    if(sprite_count<32)attr_buffer[sprite_count*4]=216;
    gfx_write(sprite_page?0xD800UL:0x5800UL,color_buffer,(u16)sprite_count*16);
    gfx_write(sprite_page?0xDA00UL:0x5A00UL,attr_buffer,sprite_count<32?(u16)sprite_count*4+1:128);
    name=((u32)selected_frame<<14)+0x3800;
    gfx_write(name,hud_buffer,64);gfx_write(name+704,hud_buffer+64,64);
    logic_steps=gfx_wait_frame();
    gfx_sprite_page(sprite_page);gfx_bg(selected_frame);gfx_display(1);sprite_page^=1;
}
void main(void){
    u8 step;u8 *p=(u8*)0xE000;while(p<(u8*)0xF200)*p++=0;
    rng=0x7A31;player_x=128;player_y=166;aim_x=128;aim_y=119;
    gfx_init();title_load();world_loaded=255;sprite_page=0;world_camera=0;sound_init();sprite_cache_reset();logic_steps=1;gfx_clock_init();
    for(;;){
        keys=input_read();edge=keys&~old_keys;old_keys=keys;
        for(step=0;step<logic_steps;step++){
        if(mode==TITLE){if(edge&16)new_game();}
        else if(mode==OVER||mode==CLEAR){if(transition_clock<40)++transition_clock;else if(edge&16)new_game();}
        else if(mode==PAUSED){if(edge&64){mode=pause_previous;sound_mute(0);}}
        else if(edge&64){pause_previous=mode;mode=PAUSED;sound_mute(1);}
        else update_play();
        if(mode!=PAUSED){++frame_counter;sound_tick(stage,mode!=TITLE&&mode!=OVER);}
        edge=0;
        }
        draw_frame();
    }
}
