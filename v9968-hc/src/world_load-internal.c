#include "world_load.h"
#include "world_offsets.h"
__sfr __at (0x98) data_port;
__sfr __at (0x99) control_port;
__sfr __at (0x9B) cache_command;
void reg_write(u8 r,u8 v);
static const u8 *source;
static u8 bank,current_stage,cached_frame;
static void upload(u8 pages) __naked {
 __asm
 ld d,a
 ld hl,(_source)
 ld c,#0x98
upload_page:
 ld b,#0
 otir
 ld a,h
 cp #0x80
 jr nz,upload_ready
 ld a,(_bank)
 inc a
 ld (_bank),a
 ld (0x6800),a
 ld hl,#0x6000
upload_ready:
 dec d
 jr nz,upload_page
 ld (_source),hl
 ret
 __endasm;
}
static void load(u8 b,u16 offset,u16 y,u8 pages){gfx_wait();bank=b;*((volatile u8*)0x6800)=bank;source=(const u8*)(0x6000+offset);vram_address(y);upload(pages);}
void assets_load(void){u8 i;for(i=0;i<10;i++)load(4+i,0,512+(u16)i*64,32);}
void feature_load(void){load(14,0,1984,32);}
static u8 last_high;
static void execute_delta(void) __naked {
 __asm
 ld hl,(_source)
 ld c,#0x98
 ld a,#255
 ld (_last_high),a
next_run:
 ld a,h
 cp #0x7F
 jr nz,fast_header
 ld a,l
 cp #253
 jr c,fast_header
 call read_stream
 ld b,a
 or a
 jp z,delta_end
 call read_stream
 ld e,a
 call read_stream
 ld d,a
 jr header_done
fast_header:
 ld b,(hl)
 inc hl
 ld a,b
 or a
 jp z,delta_end
 ld e,(hl)
 inc hl
 ld d,(hl)
 inc hl
header_done:
 push de
 ld a,d
 and #0x40
 rlca
 rlca
 add a,#9
 ld e,a
 ld a,(_last_high)
 cp e
 jr z,high_ready
 ld a,e
 ld (_last_high),a
 out (0x99),a
 ld a,#142
 out (0x99),a
high_ready:
 ; Header low address is re-read from the two bytes immediately before HL.
 ; Preserve DE offset across high register calculation instead (see push below).
 pop de
 ld a,e
 out (0x99),a
 ld a,d
 and #63
 or #64
 out (0x99),a
 ld a,h
 cp #0x7F
 jr nz,delta_fast
 ld a,l
 add a,b
 jr nc,delta_fast
slow_data:
 outi
 ld a,h
 cp #0x80
 jr nz,slow_continue
 ld a,(_bank)
 inc a
 ld (_bank),a
 ld (0x6800),a
 ld hl,#0x6000
slow_continue:
 ld a,b
 or a
 jr nz,slow_data
 jp next_run
delta_fast:
 otir
 jp next_run
read_stream:
 ld a,(hl)
 inc hl
 push af
 ld a,h
 cp #0x80
 jr nz,read_done
 ld a,(_bank)
 inc a
 ld (_bank),a
 ld (0x6800),a
 ld hl,#0x6000
read_done:
 pop af
 ret
delta_end:
 ld (_source),hl
 ret
 __endasm;
}
static void delta(u8 frame){bank=delta_banks[current_stage][frame];*((volatile u8*)0x6800)=bank;source=(const u8*)(0x6000+delta_offsets[current_stage][frame]);execute_delta();}
/* 16 x 40-row strips occupy y=1332..1971, below feature y=1984.
 * All phases are retained. Only this band uses a VRAM-resident source. */
static void copy_cached_band(u8 frame){
 u16 sy=1332+(u16)frame*40,dy=1152+band_tops[current_stage];
 gfx_wait();reg_write(17,32);
 cache_command=0;cache_command=0;
 cache_command=(u8)sy;cache_command=sy>>8;
 cache_command=0;cache_command=0;
 cache_command=(u8)dy;cache_command=dy>>8;
 cache_command=0;cache_command=1;
 cache_command=40;cache_command=0;
 cache_command=0;cache_command=0;cache_command=0xD0;
}
void world_load(u8 s){current_stage=s;cached_frame=255;}
u16 world_resolve(u16 sy){u16 relative=sy-1152;u8 frame=relative/180,i;
 if(cached_frame!=frame){gfx_wait();if(cached_frame==255){
  for(i=0;i<10;i++)load(cache_banks[current_stage]+i,0,1332+(u16)i*64,32);
  load(raw_banks[current_stage],0,1152,90);cached_frame=0;}
 while(cached_frame!=frame){cached_frame=(cached_frame+1)&15;delta(cached_frame);}
 copy_cached_band(frame);}
 return 1152+relative%180;
}
