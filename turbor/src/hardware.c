#include "hardware.h"

__sfr __at (0x98) hw_vram;
__sfr __at (0x99) hw_control;
__sfr __at (0x9A) hw_palette;
__sfr __at (0xA0) hw_psg_select;
__sfr __at (0xA1) hw_psg_write;
__sfr __at (0xA2) hw_psg_read;
__sfr __at (0xA9) hw_key_data;
__sfr __at (0xAA) hw_key_select;

/* RGB3 pairs (R << 4 | B), G; matches tools/art_palette.py. */
static const u8 screen_palette[32] = {
    0x00,0, 0x01,0, 0x01,1, 0x12,2,
    0x23,3, 0x15,5, 0x46,6, 0x77,7,
    0x11,0, 0x34,3, 0x44,2, 0x74,3,
    0x21,1, 0x61,3, 0x72,5, 0x74,6
};

static void reg_write(u8 reg, u8 value)
{
    hw_control = value;
    hw_control = reg | 0x80;
}

void gfx_palette(void)
{
    u8 i;
    reg_write(16, 0);
    for (i = 0; i != 32; ++i) hw_palette = screen_palette[i];
}

void gfx_display(u8 on)
{
    /* No VDP IRQ; 16 x 16 sprites, magnified to 32 x 32. */
    reg_write(1, on ? 0x43 : 0x03);
}

void gfx_bg(u8 frame)
{
    frame &= 7;
    /* R3=FF and R4 low bits=3 retain all three 64-line pattern bands. */
    reg_write(4, (frame << 3) | 3);
    reg_write(10, frame);
    reg_write(2, (frame << 4) | 0x0E);
}

void gfx_sprite_page(u8 page)
{
    page &= 1;
    /* page 0: SPT1800, color5800, SAT5A00.
     * page 1: SPT9800, colorD800, SATDA00. */
    reg_write(6, 3 | (page << 4));
    reg_write(11, page);
}

void gfx_wait_vblank(void)
{
    reg_write(15, 0);
    /* S0 bit7 is a frame-event latch, not the current blanking level.
     * Consume a pending event once, or wait for the next one. Reading
     * clears it, so two calls cannot consume the same VBlank twice. */
    while (!(hw_control & 0x80)) { }
}

void gfx_init(void)
{
    u8 i;
    __asm di __endasm;
    gfx_display(0);
    reg_write(46, 0);        /* Stop any command inherited from firmware. */
    reg_write(0, 0x04);      /* SCREEN 4 / GRAPHIC 3, interrupts disabled. */
    for (i = 2; i != 24; ++i) reg_write(i, 0);
    reg_write(3, 0xFF);
    reg_write(5, 0xB7);      /* Color/SAT base, mode-2 mask bits retained. */
    reg_write(8, 0x08);      /* Color 0 transparent; sprites on; 64K DRAMs. */
    reg_write(9, 0);         /* 192 visible lines, 60 Hz, non-interlaced. */
    reg_write(25, 0);        /* No YJK, multipage scroll or extended cmds. */
    reg_write(26, 0);
    reg_write(27, 0);
    gfx_bg(0);
    gfx_sprite_page(0);
    gfx_palette();
    (void)hw_control;       /* S0 selected above; clear firmware frame flag. */
}

/* Explicit stack ABI prevents dependence on SDCC's default register ABI.
 * This routine preserves IX/IY and consumes arbitrary 1..65535 byte lengths.
 * The turbo R automatically spaces consecutive VDP accesses by 62 R800
 * clocks; OTIR therefore needs no added NOPs in SCREEN 4. */
static void vram_copy(const void *source, u16 length) __sdcccall(0) __naked
{
    (void)source;
    (void)length;
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
        jr z,tr_vram_full_blocks
        push bc
        ld b,a
        otir
        pop bc
tr_vram_full_blocks:
        ld a,b
        or a
        ret z
tr_vram_block:
        ld b,#0
        otir
        dec a
        jr nz,tr_vram_block
        ret
    __endasm;
}

void gfx_write(u32 address, const void *source, u16 length)
{
    if (!length) return;
    reg_write(14, (u8)(address >> 14) & 7);
    hw_control = (u8)address;
    hw_control = ((u8)(address >> 8) & 0x3F) | 0x40;
    vram_copy(source, length);
}

void rom_copy_to_vram(u8 bank, u8 count8k, u32 address)
{
    while (count8k--) {
        *((volatile u8 *)0x6800) = bank++;
        gfx_write(address, (const void *)0x6000, 8192);
        address += 8192UL;
    }
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
    return result;
}
