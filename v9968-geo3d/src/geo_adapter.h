
/* Five-sector Geo3D adapter. HC music and PSG effects run at 30 Hz from VBlank. */
__sfr __at(0x99) vc;
__sfr __at(0x9A) vp;
__sfr __at(0x9B) vi;
__sfr __at(0x9D) gi;
__sfr __at(0x9F) gd;
__sfr __at(0xAA) kr;
__sfr __at(0xA9) kd;
#define REC ((u8*)0xC000)
#define PAGE (*(u8*)0xE200)
static u8 paused,prev_escape,cached_model,scene_stage,scene_hud,title_loaded;
/* P#4 reads also reset the emulator's VDP control latch. Keep pairs atomic. */
void vr(u8 r,u8 v) __naked {
 r;v;
 __asm
 ld c,a
 ld a,i
 di
 push af
 ld a,l
 out (0x99),a
 ld a,c
 or #128
 out (0x99),a
 pop af
 ret po
 ei
 ret
 __endasm;
}
void va(u8 low,u8 high) __naked {
 low;high;
 __asm
 ld c,a
 ld a,i
 di
 push af
 ld a,c
 out (0x99),a
 ld a,l
 out (0x99),a
 pop af
 ret po
 ei
 ret
 __endasm;
}
void wait_vdp(void){vr(15,2);while(vc&1);}
void gw(s16 v){gd=(u8)v;gd=(u16)v>>8;}
void vw(s16 v){vi=(u8)v;vi=(u16)v>>8;}
void fill(s16 x,s16 y,s16 w,s16 h,u8 c){
 if(x<0){w+=x;x=0;}if(y<14){h-=14-y;y=14;}
 if(x+w>256)w=256-x;if(y+h>198)h=198-y;if(w<=0||h<=0)return;
 /* hc_draw's geometry wait selected S#2. The audio ISR does not change R#15. */
 while(vc&1);vr(17,36);vw(x);vw(y+((u16)PAGE<<8));vw(w);vw(h);vi=c;vi=0;vi=0x80;
 /* Next command waits before submitting; hc_draw drains the last fill. */
}
void transfer(const u8 *p,u16 n) __naked {
 p;n;
 __asm
 ld c,#0x9F
 ld a,d
 or a
 jr z,00982$
00981$:
 ld b,#0
 otir
 dec a
 jr nz,00981$
00982$:
 ld a,e
 or a
 ret z
 ld b,e
 otir
 ret
 __endasm;
}
void vtransfer(const u8 *p,u16 n) __naked {
 p;n;
 __asm
 ld c,#0x98
 ld a,d
 or a
 jr z,00992$
00991$:
 ld b,#0
 otir
 dec a
 jr nz,00991$
00992$:
 ld a,e
 or a
 ret z
 ld b,e
 otir
 ret
 __endasm;
}
/* SCREEN8 uses one byte per pixel; descriptors live in palette bank 239. */
void resource_load(u8 resource,u8 count,u8 block,u8 high){
 u8 i,banks[8];const u8 *p;
 *(u8*)0x6000=239;p=(const u8*)(0x5000+(u16)resource*8);
 for(i=0;i<count;i++)banks[i]=p[i];
 vr(14,block);va(0,high);
 for(i=0;i<count;i++){*(u8*)0x6000=banks[i];vtransfer((const u8*)0x5FFE,8192);}
}
void assets_init(void){resource_load(5,8,12,0x40);resource_load(6,4,12,0x70);}
void scene_update(void){
 u8 i,key,bank;const u8 *p;u16 n;
 if(scene_stage!=stage){
  wait_vdp();*(u8*)0x6000=239;p=(const u8*)(0x4000+(u16)stage*768);
  vr(16,0);for(n=0;n<768;n++)vp=*p++;
  resource_load(stage,8,8,0x40);
  scene_stage=stage;scene_hud=255;
 }
 key=stage*2+(mode==BOSS);
 if(scene_hud!=key){
  wait_vdp();*(u8*)0x6000=239;bank=*(const u8*)(0x5040+(key>>1));
  *(u8*)0x6000=bank;p=(const u8*)(0x5FFE+(u16)(key&1)*4096);
  vr(14,12);va(0,0x50);vtransfer(p,4096);scene_hud=key;
 }
 for(i=168;i<172;i++)if(stage&&REC[i]!=255)REC[i]=101+(stage-1)*32+REC[i]-8;
}
void model(u8 bank,s16 x,s16 y,s16 z,u8 rotation,u8 scale){
 u16 i,n;const u8 *p;const s16 *m=(const s16*)(REC+(rotation==1?96:120));
 *(u8*)0x6000=bank;p=(u8*)0x4000;
 if(cached_model!=bank){
 cached_model=bank;
 gi=0x40;gd=0;gd=0;gd=p[0];gd=0;gd=15;gd=0;
 n=p[2]|((u16)p[3]<<8);gi=0x50;transfer(p+6,n);
 gi=0x58;gd=0;gd=p[1];gi=0x52;p+=6+n;n=*(u16*)0x4004;transfer(p,n);p+=n;gi=0x65;gd=0;gi=0x53;n=*(const u16*)0x7FFE;if(n)transfer(p,n);
 }
 gi=0;
#ifdef NEON_FAST
 {static const s16 identity[9]={16384,0,0,0,16384,0,0,0,16384};
  static const s16 small[9]={10649,0,0,0,10649,0,0,0,10649};
  transfer((const u8*)(rotation?m:scale?small:identity),18);}
#else
 for(i=0;i<9;i++)gw(rotation?m[i]:((i==0||i==4||i==8)?(scale?10649:16384):0));
#endif
#ifdef NEON_FAST
 {
  u16 row=(u16)z/5;u8 table;const s16 *values;s16 dx=x-128,dy=106-y,ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
  if(row<288 && ax<256 && ay<256 && z%5==0){
   *(u8*)0x6000=239;table=*(const u8*)(0x5068+(row>>4));
   *(u8*)0x6000=table;values=(const s16*)(0x5FFE+((row&15)<<9));
   gw(dx<0?-values[ax]:values[ax]);gw(dy<0?-values[ay]:values[ay]);
  }else{gw((s16)(((long)dx*z)/170));gw((s16)(((long)dy*z)/170));}
  gw(z);
 }
#else
 gw((s16)(((long)(x-128)*z)/170));gw((s16)(((long)(106-y)*z)/170));gw(z);
#endif
 gi=0x46;gw((u16)PAGE<<8);gi=0x48;gd=7;while(gi&1);wait_vdp();
}
/* Camera-space clipped road prevents near-plane holes exposing the skyline. */
void near_ground(void){
 const u8 *p;u16 n,f;u8 i;
 *(u8*)0x6000=REC[189];p=(const u8*)(0x4000+*(u16*)(REC+190));
 if(!p[0])return;
 gi=0x40;gd=0;gd=0;gd=p[0];gd=0;gd=15;gd=0;
 n=*(const u16*)(p+2);f=*(const u16*)(p+4);
 gi=0x50;transfer(p+6,n);gi=0x58;gd=0;gd=p[1];
 gi=0x52;transfer(p+6+n,f);
 gi=0;for(i=0;i<9;i++)gw((i==0||i==4||i==8)?16384:0);
 gw(0);gw(0);gw(0);gi=0x46;gw((u16)PAGE<<8);
 gi=0x48;gd=3;while(gi&1);wait_vdp();
}
#include "geo_audio.h"
void hc_init(void){sound_init();rng=0x6A3D;new_game();mode=TITLE;paused=0;prev_escape=0;scene_stage=255;scene_hud=255;}
u8 muzzle_flash;
s16 muzzle_x[3],muzzle_y[3];
void boss_emit(void){
 u8 i;const s16 *p=(const s16*)(REC+192+(stage==4?18:stage==3?36:0));
 s16 tx=(s16)(((long)(boss_x-128)*555)/170),ty=(s16)(((long)(129-boss_y)*555)/170),z;
 for(i=0;i<3;i++,p+=3){
  if((i<2 && (boss_volley&3)) || (i==2 && (boss_volley&4))){
   z=555+p[2];
   muzzle_x[i]=128+(s16)(((long)(tx+p[0])*170)/z);
   muzzle_y[i]=106-(s16)(((long)(ty+p[1])*170)/z);
   muzzle_flash|=1<<i;
   if(i<2){
    if(boss_volley&1)fire_enemy(muzzle_x[i],muzzle_y[i],0);
    if(boss_volley&2)fire_enemy(muzzle_x[i],muzzle_y[i],i+1);
   }else{fire_enemy(muzzle_x[i],muzzle_y[i],0);fire_enemy(muzzle_x[i],muzzle_y[i],1);fire_enemy(muzzle_x[i],muzzle_y[i],2);}
  }
 }
}
void hc_tick(void){
 u8 a,b;boss_volley=0;muzzle_flash=0;kr=(kr&0xF0)|8;a=~kd;keys=0;
 if(a&16)keys|=1;if(a&128)keys|=2;if(a&32)keys|=4;if(a&64)keys|=8;if(a&1)keys|=16;
 kr=(kr&0xF0)|5;if(!(kd&32))keys|=32;
 kr=(kr&0xF0)|7;b=!(kd&4);if(b&&!prev_escape&&mode!=TITLE){paused^=1;audio_pause(paused);}prev_escape=b;
 audio_stage=stage_music[stage];audio_playing=(mode==PLAY||mode==BOSS||mode==TRANSIT);
 edge=keys&~old_keys;old_keys=keys;
 if(mode==TITLE){
  if(!title_loaded){u16 n;const u8 *p;wait_vdp();
   *(u8*)0x6000=239;p=(const u8*)0x4000;vr(16,0);for(n=0;n<768;n++)vp=*p++;
   resource_load(7,8,8,0x40);title_loaded=1;}
  if(edge&16){new_game();scene_stage=255;scene_update();}return;
 }
 if(paused){scene_update();return;}
 if(mode==OVER||mode==CLEAR){if(edge&16)new_game();scene_update();return;}
 spark_tick();
 update_play();
 /* 30 Hz nominal simulation over the prototype's 20 Hz presentation. */
 if((frame_counter++&1)==0){edge=0;update_play();}
 if(mode==BOSS && boss_volley)boss_emit();
 scene_update();
}
void game_over_panel(void){
 wait_vdp();vr(17,32);vw(32);vw(944);vw(32);vw(88+((u16)PAGE<<8));
 vw(192);vw(32);vi=0;vi=0;vi=0xD0;wait_vdp();
}
void hc_draw(void){
 static u16 bar_hp;static u8 bar_stage,bar_width;
 *(u16*)(REC+186)=784;
 u8 i,j,depth_band[ENEMIES]; s16 z;
 if(mode==TITLE){wait_vdp();vr(17,32);vw(0);vw(512);vw(0);vw((u16)PAGE<<8);
  vw(256);vw(212);vi=0;vi=0;vi=0xD0;wait_vdp();return;}
 near_ground();
 cached_model=255;
 /* Sort approaching enemies by the HC depth bands, then draw the player last. */
 for(i=0;i<ENEMIES;i++)depth_band[i]=foes[i].active?foes[i].z/40:255;
 for(j=0;j<6;j++)for(i=0;i<ENEMIES;i++)if(depth_band[i]==j){
  z=1400-(s16)foes[i].z*5;model(foes[i].kind==2?250:2+foes[i].kind,foes[i].x,foes[i].y,z,0,0);
 }
 if(mode==BOSS){u8 bank=stage?229+(stage-1)*2:64;model(bank,boss_x,boss_y,560,1,0);model(bank+1,boss_x,boss_y-23,555,2,0);}
 model(1,player_x,player_y,250,0,1);
 for(i=0;i<3;i++)if(muzzle_flash&(1<<i)){fill(muzzle_x[i]-3,muzzle_y[i]-1,7,3,8);fill(muzzle_x[i]-1,muzzle_y[i]-3,3,7,5);}
 for(i=0;i<BULLETS;i++)if(shots[i].active){fill(shots[i].x/4-2,shots[i].y/4-3,4,6,7);fill(shots[i].x/4-1,shots[i].y/4-2,2,3,8);}
 /* Advance tracer positions with the HC firing cycle, not fixed screen marks. */
 if(shot_clock&&(mode==PLAY||mode==BOSS)){
  for(i=0;i<3;i++){
   s16 t=(s16)i*4+5-shot_clock;
   s16 x=player_x+(aim_x-player_x)*t/12;
   s16 y=player_y+(aim_y-player_y)*t/12;
   fill(x-1,y-2,2,4,13);
  }
 }
 for(i=0;i<FXMAX;i++)if(fx[i].active){s16 d=fx[i].age/2+2;fill(fx[i].x-d,fx[i].y,2,2,7);fill(fx[i].x+d,fx[i].y,2,2,8);fill(fx[i].x,fx[i].y-d,2,2,7);}
 for(i=0;i<8;++i)if(sparks[i].life)fill(sparks[i].x,sparks[i].y,2,2,sparks[i].life>3?8:7);
 /* Open-center, four-corner sight: visible silhouette without covering targets. */
 fill(aim_x-9,aim_y-7,5,1,12);fill(aim_x+5,aim_y-7,5,1,12);
 fill(aim_x-9,aim_y-6,1,3,12);fill(aim_x+9,aim_y-6,1,3,12);
 fill(aim_x-9,aim_y+7,5,1,12);fill(aim_x+5,aim_y+7,5,1,12);
 fill(aim_x-9,aim_y+4,1,3,12);fill(aim_x+9,aim_y+4,1,3,12);
 for(i=0;i<6;i++)fill(5+i*7,18,5,3,i<shield?12:3);
 for(i=0;i<3;i++)fill(55+i*7,18,5,3,i<bombs?7:3);
 if(mode==BOSS){
  if(bar_hp!=boss_hp||bar_stage!=stage){bar_hp=boss_hp;bar_stage=stage;bar_width=(boss_hp*140u)/boss_health[stage];}
  fill(85,18,140,3,3);fill(85,18,bar_width,3,7);
 }
 if(paused)fill(124,93,3,13,13),fill(131,93,3,13,13);
 if(mode==CLEAR)fill(108,95,40,3,12);
 if(mode==OVER)game_over_panel();
 wait_vdp();
}

