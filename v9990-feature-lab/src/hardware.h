#ifndef NEON_HARDWARE_H
#define NEON_HARDWARE_H

typedef unsigned char u8;
typedef unsigned int u16;

#define INPUT_LEFT  1
#define INPUT_RIGHT 2
#define INPUT_UP    4
#define INPUT_DOWN  8
#define INPUT_FIRE  16
#define INPUT_BOMB  32
#define INPUT_PAUSE 64
#define INPUT_LAB   128

/* All runtime code runs in RAM with interrupts disabled. B1 is 256 x 212,
 * 16 programmable colors, with a 256 x 4096 pixel VRAM image space.
 * The game uses image rows 0..4031. Fill colors use the original GRB byte
 * interface and are translated through the generated color_map table. */
void gfx_init(void);
void hardware_upload(void);
void gfx_wait(void);
void gfx_rect(u16 x, u16 y, u16 w, u16 h, u8 color);
void gfx_copy(u16 sx, u16 sy, u16 dx, u16 dy, u16 w, u16 h, u8 transparent);
/* Fast paths: caller clips all coordinates; source and destination must not
 * overlap for gfx_blit. Width and height zero are still rejected. */
void gfx_fill(u16 x, u16 y, u16 w, u16 h, u8 color);
void gfx_blit(u16 sx, u16 sy, u16 dx, u16 dy, u16 w, u16 h, u8 transparent);
/* Endpoints must be inside the image space. Both endpoints are included. */
void gfx_line(u16 x0, u16 y0, u16 x1, u16 y1, u8 color);
/* Waits for a fresh blank, switches to page 0/1 and returns in active display.
 * It is then safe to draw into the previous display page. */
void gfx_flip(u8 page);
void gfx_vblank(void);
/* B1 hardware cursors and four 16-color palette banks; lab edition only. */
void gfx_cursor(u16 x, u16 y, u8 visible, u8 locked);
void gfx_palette_select(u8 bank);
u8 input_read(void);

#endif
