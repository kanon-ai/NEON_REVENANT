#include "world_load.h"
#include "world_data.h"
__sfr __at (0x98) world_vram;
#define WORLD_HISTORY ((u8*)0xD800)
#define WORLD_HISTORY_MASK 2047
static const u8 *world_source;
static u8 world_bank,world_length;
static u8 world_read(void) __naked
{
    __asm
        ld hl,(_world_source)
        ld b,(hl)
        inc hl
        ld a,h
        cp #0x80
        jr nz,world_reader_in_bank
        ld a,(_world_bank)
        inc a
        ld (_world_bank),a
        ld (0x6800),a
        ld hl,#0x6000
world_reader_in_bank:
        ld (_world_source),hl
        ld a,b
        ret
    __endasm;
}

/* SDCC call(1): source index in HL, destination index in DE; result in DE.
 * IX/IY remain untouched. world_length is 3..34. Keeping the physical ring
 * pointers in registers avoids indexed stack loads for every output byte.
 * Low-byte increments let both rings wrap only on their 256-byte boundaries.
 * Forward byte order deliberately supports overlapping LZ matches. */
static u16 world_copy(u16 source, u16 position) __sdcccall(1) __naked
{
    (void)source;
    (void)position;
    __asm
        ld a,h
        or #0xD8
        ld h,a
        ld a,d
        or #0xD8
        ld d,a
        ld a,(_world_length)
        ld b,a
world_copy_byte:
        ld a,(hl)
        ld (de),a
        out (0x98),a
        inc l
        jr nz,world_copy_source_ready
        inc h
        ld a,h
        and #0x07
        or #0xD8
        ld h,a
world_copy_source_ready:
        inc e
        jr nz,world_copy_destination_ready
        inc d
        ld a,d
        and #0x07
        or #0xD8
        ld d,a
world_copy_destination_ready:
        djnz world_copy_byte
        ld a,d
        and #0x07
        ld d,a
        ret
    __endasm;
}


static void load_banks(u8 first,u8 count){u8 i;for(i=0;i<count;++i){*((volatile u8*)0x6800)=first+i;gfx_write((u32)i<<13,(const u8*)0x6000,8192);}}
void world_load(u8 stage){
    u8 frame,flags,mask,length,value;u16 remaining,token,source,position=0;
    if(stage>=5)return;
    gfx_display(0);world_bank=world_banks[stage];*((volatile u8*)0x6800)=world_bank;
    world_source=(const u8*)(0x6000+world_offsets[stage]);
    for(frame=0;frame<8;++frame){remaining=16384;gfx_stream_address((u32)frame<<14);
        while(remaining){flags=world_read();mask=1;
            do{
                if(flags&mask){token=world_read();token|=(u16)world_read()<<8;length=(token>>11)+3;world_length=length;source=(position-(token&2047)-1)&2047;remaining-=length;position=world_copy(source,position);
                }else{value=world_read();WORLD_HISTORY[position]=value;world_vram=value;position=(position+1)&2047;--remaining;}
                mask<<=1;
            }while(mask&&remaining);
        }
    }
    {u8 end=216;gfx_write(0x5A00UL,&end,1);gfx_write(0xDA00UL,&end,1);}
    gfx_bg(0);
}
void title_load(void){
    u8 end=216;gfx_display(0);load_banks(56,2);
    gfx_write(0x5A00UL,&end,1);gfx_sprite_page(0);gfx_bg(0);gfx_display(1);
}
