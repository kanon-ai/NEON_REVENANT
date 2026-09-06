#include "world_load.h"
volatile u8 world_phase,world_page,world_pending,world_target;
static u8 stream_stage;
static void load(u8 bank){
    u8 end=208;
    gfx_display(0);
    *((volatile u8*)0x6800)=bank;gfx_write(0,(const u8*)0x6000,8192);
    *((volatile u8*)0x6800)=bank+1;gfx_write(8192,(const u8*)0x6000,8192);
    /* The same immutable 2KiB sprite atlas is resident for every scene. */
    *((volatile u8*)0x6800)=5;gfx_write(0x1800,(const u8*)0x6000,2048);
    gfx_write(0x3B00,&end,1);gfx_write(0x3B80,&end,1);gfx_sprite_page(0);
    world_phase=0;world_page=0;world_pending=0;world_target=1;gfx_bg(0);
}
void world_load(u8 stage){stream_stage=stage;load(6+stage*2);}
void title_load(void){load(12);gfx_display(1);}
/* Precompiled VRAM bursts, no runtime image decoding or RAM frame buffer.
 * One 8 KiB bank holds two upload parts and 640 name bytes. Its PCG slots
 * are disjoint from the currently visible tiles until R2 commits the page.
 * Split work across two game frames, including names in the second part. */
void world_prepare(void){
    const u8 *packet=(const u8*)0x6000;
    if(!world_pending)world_target=(world_phase+1)&15;
    *((volatile u8*)0x6800)=14+stream_stage*16+world_target;
    if(!world_pending){gfx_patch(packet+4);world_pending=1;}
    else if(world_pending==1){
        gfx_patch(packet+*(const u16*)packet);
        gfx_write(world_page?0x3840:0x3C40,packet+*(const u16*)(packet+2),640);
        world_pending=2;
    }
}
void world_commit(void){
    if(world_pending==2){
        world_page^=1;gfx_bg(world_page);world_phase=world_target;world_pending=0;
    }
}
