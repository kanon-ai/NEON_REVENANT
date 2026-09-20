#include "hardware.h"
#include "sound.h"
__sfr __at (0x98) hw_vram;
__sfr __at (0x99) hw_control;
__sfr __at (0xA0) hw_psg_select;
__sfr __at (0xA1) hw_psg_write;
__sfr __at (0xA2) hw_psg_read;
__sfr __at (0xA9) hw_key_data;
__sfr __at (0xAA) hw_key_select;
volatile u8 irq_frames,audio_stage,audio_playing,audio_ready;
volatile u16 audio_ticks;
static u8 audio_accumulator,audio_rate;
static u8 consumed_vblank;
void audio_service(void) {
    u8 status=hw_control;
    if(!(status&0x80))return;
    ++irq_frames;
    if(audio_ready){
        audio_accumulator+=30;
        if(audio_accumulator>=audio_rate){
            audio_accumulator-=audio_rate;
            sound_tick(audio_stage,audio_playing);++audio_ticks;
        }
    }
}
void audio_irq(void) __naked {
    __asm
        push af
        push bc
        push de
        push hl
        push ix
        push iy
        call _audio_service
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
void audio_setup(void){
    u16 n;u8 *v=(u8*)0xEC00;
    __asm di __endasm;
    for(n=0;n<257;++n)v[n]=0xED;
    *((u8*)0xEDED)=0xC3;*((u16*)0xEDEE)=(u16)audio_irq;
    /* BIOS ID byte 002B bit 7: standard 50 Hz machine. */
    audio_rate=(*((const u8*)0x002B)&0x80)?50:60;
    __asm ld a,#0xEC
        ld i,a
        im 2
    __endasm;
}
void audio_effect(u8 id){__asm di __endasm;sound_effect(id);__asm ei __endasm;}
void audio_mute(u8 value){__asm di __endasm;sound_mute(value);__asm ei __endasm;}
static void reg_write(u8 reg,u8 value){
    __asm di __endasm;
    hw_control=value;hw_control=reg|0x80;
    __asm ei __endasm;
}
void gfx_palette(void){}
void gfx_display(u8 on){reg_write(1,on?0xE3:0xA3);}
void gfx_bg(u8 page){reg_write(2,14+(page&1));}
void gfx_sprite_page(u8 page){reg_write(5,0x76+(page&1));}
/* Preserve a VBlank that arrived during rendering, just like the old VDP
 * status latch. Waiting only for future IRQs would add one idle frame. */
void gfx_wait_vblank(void){while(irq_frames==consumed_vblank){};consumed_vblank=irq_frames;}
void gfx_init(void){
    __asm di __endasm;
    gfx_display(0);reg_write(0,2);reg_write(2,14);reg_write(3,255);
    reg_write(4,3);reg_write(5,0x76);reg_write(6,3);reg_write(7,1);

}
/* TMS9918A active-display VRAM access spacing: OUTI(16)+NOP(4)+JP(10)
 * gives 30 Z80 T-states, meeting the 29 T-state worst-case spacing.
 * Never replace this loop with OTIR (21T). Preserve IX/IY and use the
 * explicit stack calling convention independent of SDCC version. */
static void vram_copy(const void *source,u16 length) __sdcccall(0) __naked{
    (void)source;(void)length;
    __asm
        ld hl,#2
        add hl,sp
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        ex de,hl
        ld a,c
        ld c,#0x98
        or a
        jr z,msx1_copy_full_blocks
        push bc
        ld b,a
msx1_copy_tail:
        outi
        nop
        jp nz,msx1_copy_tail
        pop bc
msx1_copy_full_blocks:
        ld a,b
        or a
        ret z
msx1_copy_block:
        ld b,#0
msx1_copy_loop:
        outi
        nop
        jp nz,msx1_copy_loop
        dec a
        jr nz,msx1_copy_block
        ret
    __endasm;
}
void gfx_write(u16 address,const void *source,u16 length){
    if(!length)return;
    __asm di __endasm;
    hw_control=(u8)address;hw_control=((u8)(address>>8)&63)|0x40;
    __asm ei __endasm;
    vram_copy(source,length);
}
/* Direct ROM packet reader: avoid a C call and stack locals for every small
 * PCG burst. Records are (VRAM address u16, length u16, bytes), length 0 ends.
 * OUTI/NOP/JP spacing remains 30T; IX and IY are preserved. */
void gfx_patch(const void *source) __sdcccall(0) __naked{
    (void)source;
    __asm
        ld hl,#2
        add hl,sp
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
pcg_record:
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld a,b
        or c
        ret z
        di
        ld a,e
        out (#0x99),a
        ld a,d
        or #0x40
        out (#0x99),a
        ei
        ld a,c
        ld c,#0x98
        or a
        jr z,pcg_full_blocks
        push bc
        ld b,a
pcg_tail:
        outi
        nop
        jp nz,pcg_tail
        pop bc
pcg_full_blocks:
        ld a,b
        or a
        jr z,pcg_record
pcg_block:
        ld b,#0
pcg_bytes:
        outi
        nop
        jp nz,pcg_bytes
        dec a
        jr nz,pcg_block
        jr pcg_record
    __endasm;
}
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
