#include "hardware.h"
#include "palette.h"

__sfr __at (0x60) hw_vram;
__sfr __at (0x61) hw_palette;
__sfr __at (0x63) hw_reg_data;
__sfr __at (0x64) hw_reg_select;
__sfr __at (0x65) hw_status;
__sfr __at (0x66) hw_irq_flags;
__sfr __at (0x67) hw_system;
__sfr __at (0xA0) hw_psg_select;
__sfr __at (0xA1) hw_psg_write;
__sfr __at (0xA2) hw_psg_read;
__sfr __at (0xA9) hw_key_data;
__sfr __at (0xAA) hw_key_select;

static void reg_write(u8 reg, u8 value)
{
    hw_reg_select = reg;
    hw_reg_data = value;
}

/* Arguments below are side-effect-free variables; expand in place to avoid
 * four to six extra C calls for every small command or font character. */
#define word_write(value) do { \
    hw_reg_data = (u8)(value); \
    hw_reg_data = (u8)((value) >> 8); \
} while (0)

void gfx_wait(void)
{
    while (hw_status & 0x01) { }
}

void gfx_vblank(void)
{
    /* A previous blank must end first: never consume a stale blank level. */
    while (hw_status & 0x40) { }
    while (!(hw_status & 0x40)) { }
}

void gfx_init(void)
{
    u8 i;
    __asm di __endasm;
    hw_system = 0x02;
    hw_system = 0x00;
    /* R0..R28 are the defined writeable control registers. */
    hw_reg_select = 0;
    for (i = 0; i != 29; ++i) hw_reg_data = 0;
    hw_irq_flags = 0x07;
    reg_write(6, 0x81);
    reg_write(7, 0x00);
    reg_write(8, 0x42);       /* 512 KiB VRAM, no display or hardware cursors. */
    reg_write(13, 0x00);      /* 4bpp palette mode, palette entries 0..15. */
    reg_write(14, 0);
    for (i = 0; i != 48; ++i) hw_palette = v9990_palette[i];
    hw_reg_select = 44;
    hw_reg_data = 0x00;      /* ARG */
    hw_reg_data = 0x0C;      /* COPY logical operation */
    hw_reg_data = 0xFF;
    hw_reg_data = 0xFF;      /* BOTH even and odd VRAM write masks. */
    /* Changes to the screen mode are not immediate. This also works with
     * display disabled because status VR reports the scan timing. */
    gfx_vblank();
    gfx_rect(0, 0, 256, 512, 0);
    gfx_wait();
}

/* The source is always the ASCII8 window at 6000h. Only bank register 6800h
 * is used, leaving 4000h bank 0 and the executing RAM pages untouched. */
static void upload_bank(void) __naked
{
    __asm
        ld hl,#0x6000
        ld c,#0x60
        ld e,#32
hw_upload_bank_loop:
        ld b,#0
        otir
        dec e
        jr nz,hw_upload_bank_loop
        ret
    __endasm;
}

void hardware_upload(void)
{
    u8 bank;
    gfx_wait();
    hw_reg_select = 0;
    hw_reg_data = 0;
    hw_reg_data = 0;
    hw_reg_data = 1;         /* 4bpp: logical y=512 is byte address 10000h. */
    for (bank = 4; bank != 14; ++bank) {
        *((volatile u8 *)0x6800) = bank;
        upload_bank();
    }
    reg_write(8, 0xC2);
    gfx_vblank();
}

void gfx_rect(u16 x, u16 y, u16 w, u16 h, u8 color)
{
    /* Zero means 2048/4096 to the V9990, so reject empty rectangles here. */
    if (!w || !h || x >= 256 || y >= 2048) return;
    if (w > 256 - x) w = 256 - x;
    if (h > 2048 - y) h = 2048 - y;
    gfx_fill(x, y, w, h, color);
}

void gfx_fill(u16 x, u16 y, u16 w, u16 h, u8 color)
{
    if (!w || !h) return;
    color = color_map[color];
    color |= color << 4;
    gfx_wait();
    hw_reg_select = 36;
    word_write(x);
    word_write(y);
    word_write(w);
    word_write(h);
    hw_reg_data = 0;
    hw_reg_data = 0x0C;
    hw_reg_data = 0xFF;
    hw_reg_data = 0xFF;
    hw_reg_data = color;
    hw_reg_data = color;     /* Four identical palette indices per word. */
    reg_write(52, 0x20);     /* LMMV */
}

void gfx_copy(u16 sx, u16 sy, u16 dx, u16 dy, u16 w, u16 h, u8 transparent)
{
    u8 arg = 0;
    if (!w || !h || sx >= 256 || dx >= 256 || sy >= 2048 || dy >= 2048) return;
    if (w > 256 - sx) w = 256 - sx;
    if (w > 256 - dx) w = 256 - dx;
    if (h > 2048 - sy) h = 2048 - sy;
    if (h > 2048 - dy) h = 2048 - dy;
    /* memmove-like direction for overlapping rectangles; harmless for assets. */
    if (dy > sy && dy < sy + h) {
        sy += h - 1;
        dy += h - 1;
        arg |= 8;
    }
    if (dx > sx && dx < sx + w) {
        sx += w - 1;
        dx += w - 1;
        arg |= 4;
    }
    gfx_wait();
    hw_reg_select = 32;
    word_write(sx);
    word_write(sy);
    word_write(dx);
    word_write(dy);
    word_write(w);
    word_write(h);
    hw_reg_data = arg;
    hw_reg_data = transparent ? 0x1C : 0x0C;
    hw_reg_data = 0xFF;
    hw_reg_data = 0xFF;
    reg_write(52, 0x40);     /* LMMM */
}

void gfx_blit(u16 sx, u16 sy, u16 dx, u16 dy, u16 w, u16 h, u8 transparent)
{
    if (!w || !h) return;
    gfx_wait();
    hw_reg_select = 32;
    word_write(sx);
    word_write(sy);
    word_write(dx);
    word_write(dy);
    word_write(w);
    word_write(h);
    hw_reg_data = 0;
    hw_reg_data = transparent ? 0x1C : 0x0C;
    hw_reg_data = 0xFF;
    hw_reg_data = 0xFF;
    reg_write(52, 0x40);
}

void gfx_line(u16 x0, u16 y0, u16 x1, u16 y1, u8 color)
{
    u16 dx, dy, major, minor;
    u8 arg = 0;
    if (x0 >= 256 || x1 >= 256 || y0 >= 2048 || y1 >= 2048) return;
    if (x1 < x0) { dx = x0 - x1; arg |= 4; }
    else dx = x1 - x0;
    if (y1 < y0) { dy = y0 - y1; arg |= 8; }
    else dy = y1 - y0;
    if (!dx && !dy) { gfx_rect(x0, y0, 1, 1, color); return; }
    if (dy > dx) { major = dy; minor = dx; arg |= 1; }
    else { major = dx; minor = dy; }
    color = color_map[color];
    color |= color << 4;
    gfx_wait();
    hw_reg_select = 36;
    word_write(x0);
    word_write(y0);
    word_write(major);
    word_write(minor);
    hw_reg_data = arg;
    hw_reg_data = 0x0C;
    hw_reg_data = 0xFF;
    hw_reg_data = 0xFF;
    hw_reg_data = color;
    hw_reg_data = color;
    reg_write(52, 0xB0);     /* LINE */
}

void gfx_flip(u8 page)
{
    gfx_wait();
    gfx_vblank();
    reg_write(18, page & 1);
    /* R18 high Y is frame-latched. Do not recycle the old front buffer
     * until active display has begun with the new page selected. */
    while (hw_status & 0x40) { }
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
