#include "hardware.h"
#include "sound.h"
#include "palette.h"
#include "world_load.h"
void reg_write(u8 r,u8 v);
__sfr __at (0x98) hw_vram;
__sfr __at (0x99) ctl;
__sfr __at (0x9A) pal;
__sfr __at (0x9B) cmd;
__sfr __at (0x9C) unlock;
__sfr __at (0xA0) hw_psg_select;
__sfr __at (0xA1) hw_psg_write;
__sfr __at (0xA2) hw_psg_read;
__sfr __at (0xA9) hw_key_data;
__sfr __at (0xAA) hw_key_select;
static u8 palette_pending,palette_current,cursor_on,cursor_lock;
static u16 cursor_x,cursor_y;
__sfr __at (0x99) audio_vdp;
volatile u8 audio_frames;
static u8 audio_irq_ready, audio_consumed;

/* Audio owns the sound engine in IRQ context; foreground requests are atomic. */
volatile u8 audio_stage, audio_playing;
volatile u16 audio_ticks;
static u8 audio_divider;
void audio_service(void) {
    if (++audio_divider == 2) {
        audio_divider=0;
        sound_tick(audio_stage,audio_playing);
        ++audio_ticks;
    }
}
void audio_effect(u8 id) { __asm di __endasm; sound_effect(id); __asm ei __endasm; }
void audio_mute(u8 value) { __asm di __endasm; sound_mute(value); __asm ei __endasm; }

void audio_irq(void) __naked {
    __asm
        push af
        push bc
        push de
        push hl
        push ix
        push iy
        in a,(#0x9C)
        bit 0,a
        jr z,audio_irq_done
        ld a,#1
        out (#0x9C),a
        ld a,(_audio_frames)
        inc a
        ld (_audio_frames),a
        call _audio_service
audio_irq_done:
        pop iy
        pop ix
        pop hl
        pop de
        pop bc
        pop af
        ei
        reti
    __endasm;
}

void audio_setup(void) {
    u16 i;
    __asm di __endasm;
    /* F400..F500 and F5F5..F5F7 replace unused BIOS work areas.
     * Runtime uses direct input/VDP access, no BIOS calls after startup.
     * Keep E800..EFFF LZ history and downward F300 stack untouched. */
    for(i=0;i<257;++i)((u8*)0xF400)[i]=0xF5;
    *((u8*)0xF5F5)=0xC3;*((u16*)0xF5F6)=(u16)audio_irq;
    /* Native V9968 shares graphics and audio; P#4 acknowledges VBlank
     * without disturbing the foreground control latch or S#2 selection. */
    unlock=7;
    reg_write(1,0x60);
    audio_irq_ready=1;
    __asm
        ld a,#0xF4
        ld i,a
        im 2
        ei
    __endasm;
}


/* Preserve SDCC register arguments before reading IFF2; keep each
 * two-byte control write atomic while the audio IRQ remains active. */
void reg_write(u8 r,u8 v) __naked {
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
void vram_address(u16 y) __critical {ctl=y>>7;ctl=142;ctl=(u8)(y<<7);ctl=((y>>1)&63)|64;}
void gfx_wait(void){while(ctl&1){}}
void gfx_vblank(void){while(!(ctl&64)){}}
#define WORD(v) do {cmd=(u8)(v);cmd=(u8)((v)>>8);}while(0)
static void set_palette(u8 bank){u8 i,r,g,b;reg_write(16,0);for(i=0;i<16;i++){
 r=v9990_palette[i*3];g=v9990_palette[i*3+1];b=v9990_palette[i*3+2];
 if(bank==1&&i&&i!=7&&i<13){r=r*3/4;b=b+(31-b)/4;}
 else if(bank==2&&i&&i!=5&&i!=6&&i!=7){r=r+(31-r)/5;g=g*3/4;b=b+(31-b)/8;}
 else if(bank==3&&i){r=r+(31-r)/3;g=g+(31-g)/3;b=b+(31-b)/4;}
 if(bank==3&&i==13){r=7;g=31;b=31;}if(bank==3&&i==14){r=31;g=31;b=31;}if(bank==3&&i==15){r=31;g=22;b=8;}
 pal=r;pal=g;pal=b;
}palette_current=bank;}
void gfx_init(void){
 __asm di __endasm;
 /* Current V9968: V58=0, fixed R21 bits=00111010; HS+EPAL only. */
 unlock=0;reg_write(21,0x3A);reg_write(20,0x11);reg_write(0,6);reg_write(1,0);
 reg_write(2,0x1F);reg_write(7,0);reg_write(8,10);reg_write(9,0x80);
 reg_write(18,0);reg_write(23,0);reg_write(25,0);reg_write(26,0);reg_write(27,0);
 reg_write(15,2);palette_pending=0;set_palette(0);gfx_fill(0,0,256,512,0);gfx_wait();
}
void gfx_fill(u16 x,u16 y,u16 w,u16 h,u8 c){if(!w||!h)return;gfx_wait();reg_write(17,36);WORD(x);WORD(y);WORD(w);WORD(h);cmd=((x|w)&1)?color_map[c]:(color_map[c]*17);cmd=0;cmd=((x|w)&1)?0x80:0xC0;}
void gfx_rect(u16 x,u16 y,u16 w,u16 h,u8 c){gfx_fill(x,y,w,h,c);}
void gfx_blit(u16 sx,u16 sy,u16 dx,u16 dy,u16 w,u16 h,u8 t){
 if(!w||!h)return;
 if(sy>=8192)sy-=8192;
 else if(sy>=4032)sy=1988+sy-4032;
 else if(sy>=1152)sy=world_resolve(sy);
 gfx_wait();reg_write(17,32);WORD(sx);WORD(sy);WORD(dx);WORD(dy);WORD(w);WORD(h);/* SCREEN 5: HMMM is pixel-exact only for byte-aligned opaque spans. */
 cmd=0;cmd=0;cmd=t?0x98:(((sx|dx|w)&1)?0x90:0xD0);
}
void gfx_copy(u16 sx,u16 sy,u16 dx,u16 dy,u16 w,u16 h,u8 t){gfx_blit(sx,sy,dx,dy,w,h,t);}
void gfx_line(u16 x,u16 y,u16 x1,u16 y1,u8 c){u16 dx,dy,tmp;u8 a=0;
 if(x1<x){dx=x-x1;a|=4;}else dx=x1-x;if(y1<y){dy=y-y1;a|=8;}else dy=y1-y;
 if(dy>dx){tmp=dx;dx=dy;dy=tmp;a|=1;}
 gfx_wait();reg_write(17,36);WORD(x);WORD(y);WORD(dx);WORD(dy);cmd=color_map[c];cmd=a;cmd=0x70;
}
void gfx_palette_select(u8 b){palette_pending=b&3;}
void gfx_cursor(u16 x,u16 y,u8 on,u8 lock){cursor_x=x;cursor_y=y;cursor_on=on;cursor_lock=lock;}
void gfx_flip(u8 page){u16 x,y;if(cursor_on){x=cursor_x;y=cursor_y+((u16)page<<8);
 if(x>12&&x<244&&cursor_y>12&&cursor_y<196){
 gfx_blit(232,544,x-10,y-10,21,21,1);
 if(cursor_lock)gfx_fill(x-1,y-1,3,3,0xFF);
 }}gfx_wait();gfx_vblank();if(palette_current!=palette_pending)set_palette(palette_pending);reg_write(2,page?0x3F:0x1F);
}
void hardware_upload(void){assets_load();feature_load();reg_write(1,64);}
u8 input_read(void)
{
    u8 keys, result = 0;
    u8 ppi = hw_key_select;
    u8 joy_control;
    hw_key_select = (ppi & 0xF0) | 8;
    keys = (u8)~hw_key_data;
    if (keys & 0x10) result |= INPUT_LEFT;
    if (keys & 0x80) result |= INPUT_RIGHT;
    if (keys & 0x20) result |= INPUT_UP;
    if (keys & 0x40) result |= INPUT_DOWN;
    if (keys & 0x01) result |= INPUT_FIRE;
    hw_key_select = (ppi & 0xF0) | 5;
    if (!(hw_key_data & 0x20)) result |= INPUT_BOMB;  /* X */
    hw_key_select = (ppi & 0xF0) | 7;
    if (!(hw_key_data & 0x04)) result |= INPUT_PAUSE; /* ESC */
    if (!(hw_key_data & 0x08)) result |= INPUT_LAB;   /* TAB */
    hw_key_select = ppi;

    /* Preserve the current sound mixer while enforcing MSX I/O directions. */
    __asm di __endasm;
    hw_psg_select = 7;
    hw_psg_write = (hw_psg_read & 0x3F) | 0x80;
    hw_psg_select = 15;
    joy_control = hw_psg_read;
    /* Joystick 1, pin 8 low, pins 6/7 released for trigger input. */
    hw_psg_write = (joy_control & 0xAF) | 0x03;
    hw_psg_select = 14;
    keys = (u8)~hw_psg_read;
    if (keys & 0x04) result |= INPUT_LEFT;
    if (keys & 0x08) result |= INPUT_RIGHT;
    if (keys & 0x01) result |= INPUT_UP;
    if (keys & 0x02) result |= INPUT_DOWN;
    if (keys & 0x10) result |= INPUT_FIRE;
    if (keys & 0x20) result |= INPUT_BOMB;
    hw_psg_select = 15;
    hw_psg_write = joy_control;
    __asm ei __endasm;
    return result;
}
