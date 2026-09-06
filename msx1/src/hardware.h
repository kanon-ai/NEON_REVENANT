#ifndef NEON_MSX1_HARDWARE_H
#define NEON_MSX1_HARDWARE_H

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

/* TMS9918A SCREEN 2, 256x192, fixed palette, 16 KiB VRAM. */
void gfx_init(void);
void gfx_display(u8 on);
void gfx_palette(void); /* Fixed hardware palette; intentionally empty. */
void gfx_wait_vblank(void);
void gfx_bg(u8 frame);
void gfx_sprite_page(u8 page);
void gfx_write(u16 address,const void *source,u16 length);
void gfx_patch(const void *source) __sdcccall(0);
u8 input_read(void);
#endif
