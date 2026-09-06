#include "world_load.h"
static void load(u8 bank){
    u8 end=208;
    gfx_display(0);
    *((volatile u8*)0x6800)=bank;gfx_write(0,(const u8*)0x6000,8192);
    *((volatile u8*)0x6800)=bank+1;gfx_write(8192,(const u8*)0x6000,8192);
    /* The same immutable 2KiB sprite atlas is resident for every scene. */
    *((volatile u8*)0x6800)=5;gfx_write(0x1800,(const u8*)0x6000,2048);
    gfx_write(0x3B00,&end,1);gfx_write(0x3B80,&end,1);gfx_sprite_page(0);
}
void world_load(u8 stage){load(8+stage*2);}
void title_load(void){load(17);gfx_display(1);}
