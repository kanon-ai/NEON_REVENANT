#ifndef NEON_TURBOR_HARDWARE_H
#define NEON_TURBOR_HARDWARE_H

typedef unsigned char u8;
typedef unsigned int u16;
typedef unsigned long u32;
typedef signed int s16;

#define INPUT_LEFT  1
#define INPUT_RIGHT 2
#define INPUT_UP    4
#define INPUT_DOWN  8
#define INPUT_FIRE  16
#define INPUT_BOMB  32
#define INPUT_PAUSE 64

/* V9958 SCREEN 4, 256 x 192, 16 RGB3 colors, eight resident 16 KiB
 * background banks. The runtime keeps interrupts disabled. */
void gfx_init(void);             /* Initializes with the display OFF. */
void gfx_display(u8 on);
void gfx_palette(void);          /* Restore the game's RGB3 palette. */
void gfx_wait_vblank(void);       /* Consume one pending/next frame event. */
void gfx_bg(u8 frame);            /* Select 0..7, call during vertical blank. */
void gfx_sprite_page(u8 page);   /* Select 0/1 buffered sprite tables. */
/* Byte address is 17-bit. Caller keeps source mapped for the entire copy.
 * No command-engine operation may run concurrently with this transfer. */
void gfx_write(u32 address, const void *source, u16 length);
/* Maps ASCII8 banks through 6000h, leaving 4000h bank 0 unchanged. */
void rom_copy_to_vram(u8 bank, u8 count8k, u32 address);
u8 input_read(void);

#endif
