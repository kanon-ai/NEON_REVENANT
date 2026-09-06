#include "world_load.h"
static void load_banks(u8 first,u8 count){
    u8 i;for(i=0;i<count;i++){
        *((volatile u8*)0x6800)=first+i;
        gfx_write((u32)i<<13,(const u8*)0x6000,8192);
    }
}
void world_load(u8 stage){
    gfx_display(0);load_banks(8+stage*16,16);
    {u8 end=216;gfx_write(0x5A00UL,&end,1);gfx_write(0xDA00UL,&end,1);}
    gfx_bg(0);
}
void title_load(void){
    u8 end=216;gfx_display(0);load_banks(56,2);
    gfx_write(0x5A00UL,&end,1);gfx_sprite_page(0);gfx_bg(0);gfx_display(1);
}
