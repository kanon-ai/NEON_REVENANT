#include "world_load.h"
#include "world_data.h"

__sfr __at (0x60) world_vram;
__sfr __at (0x63) world_reg_data;
__sfr __at (0x64) world_reg_select;

#define WORLD_HISTORY ((u8 *)0xE800)
#define WORLD_HISTORY_MASK 2047
#define WORLD_FRAME_BYTES 23040
#define WORLD_FRAME_COUNT 16

static const u8 *world_source;
static u8 world_bank;
static u8 world_length;

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
        or #0xE8
        ld h,a
        ld a,d
        or #0xE8
        ld d,a
        ld a,(_world_length)
        ld b,a
world_copy_byte:
        ld a,(hl)
        ld (de),a
        out (0x60),a
        inc l
        jr nz,world_copy_source_ready
        inc h
        ld a,h
        and #0x07
        or #0xE8
        ld h,a
world_copy_source_ready:
        inc e
        jr nz,world_copy_destination_ready
        inc d
        ld a,d
        and #0x07
        or #0xE8
        ld d,a
world_copy_destination_ready:
        djnz world_copy_byte
        ld a,d
        and #0x07
        ld d,a
        ret
    __endasm;
}

/* Atlas, feature strip and world streams use the same byte-exact decoder.
 * Starting a stream resets only the ring position, not its contents: valid
 * streams never reference bytes preceding their own first output byte. */
static void stream_start(u8 bank, u16 offset, u8 vram_high, u8 vram_middle)
{
    gfx_wait();
    world_bank = bank;
    *((volatile u8 *)0x6800) = world_bank;
    world_source = (const u8 *)(0x6000 + offset);
    world_reg_select = 0;
    world_reg_data = 0x00;
    world_reg_data = vram_middle;
    world_reg_data = vram_high;
}

static void stream_frames(u16 frame_bytes, u8 frame_count)
{
    u8 frame, flags, mask, length, value;
    u16 remaining, token, position = 0, source;
    for (frame = 0; frame != frame_count; ++frame) {
        remaining = frame_bytes;
        while (remaining) {
            flags = world_read();
            mask = 1;
            do {
                if (flags & mask) {
                    token = world_read();
                    token |= (u16)world_read() << 8;
                    length = (token >> 11) + 3;
                    world_length = length;
                    source = (position - (token & WORLD_HISTORY_MASK) - 1) & WORLD_HISTORY_MASK;
                    remaining -= length;
                    position = world_copy(source, position);
                } else {
                    value = world_read();
                    WORLD_HISTORY[position] = value;
                    world_vram = value;
                    position = (position + 1) & WORLD_HISTORY_MASK;
                    --remaining;
                }
                mask <<= 1;
            } while (mask && remaining);
        }
    }
}

void assets_load(void)
{
    /* Existing atlas: logical y=512..1151, byte addresses 10000h..23FFFh. */
    stream_start(ASSET_BANK, ASSET_OFFSET, 0x01, 0x00);
    stream_frames(ASSET_FRAME_BYTES, ASSET_FRAME_COUNT);
}

void feature_load(void)
{
#if FEATURE_FRAME_COUNT
    /* The 8 KiB feature strip occupies y=4032..4095, above all 16 worlds. */
    stream_start(FEATURE_BANK, FEATURE_OFFSET, 0x07, 0xE0);
    stream_frames(FEATURE_FRAME_BYTES, FEATURE_FRAME_COUNT);
#endif
}

void world_load(u8 stage)
{
    if (stage >= 3) return;
    /* Unchanged destination: y=1152..4031, bytes 24000h..7DFFFh. */
    stream_start(world_banks[stage], world_offsets[stage], 0x02, 0x40);
    stream_frames(WORLD_FRAME_BYTES, WORLD_FRAME_COUNT);
}
