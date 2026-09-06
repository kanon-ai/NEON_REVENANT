#include "sound.h"

typedef unsigned char u8;
typedef unsigned int u16;

#ifdef SOUND_HOST_TEST
extern void sound_test_opll(u8 reg, u8 value);
extern void sound_test_psg(u8 reg, u8 value);
extern u8 sound_test_psg_read(u8 reg);
#define fm_write sound_test_opll
#define psg_write sound_test_psg
#define psg_read sound_test_psg_read
#else
__sfr __at (0x7c) sound_fm_address;
__sfr __at (0x7d) sound_fm_data;
__sfr __at (0xa0) sound_psg_address;
__sfr __at (0xa1) sound_psg_data;
__sfr __at (0xa2) sound_psg_read_port;

/* Yamaha YM2413 Application Manual, bus timing: wait >=12 OPLL clocks
   after address and >=84 after data. At the fastest supported CPU,
   R800 7.16 MHz, these 32/192 NOPs take >=4.47/26.8 us, safely above
   3.36/23.52 us. The delays are also sufficient on the 3.58 MHz Z80.
   The game owns the OPLL with interrupts disabled. */
static void fm_write(u8 reg, u8 value)
{
    sound_fm_address = reg;
    __asm
        .rept 32
        nop
        .endm
    __endasm;
    sound_fm_data = value;
    __asm
        .rept 192
        nop
        .endm
    __endasm;
}

static void psg_write(u8 reg, u8 value)
{
    sound_psg_address = reg;
    sound_psg_data = value;
}

static u8 psg_read(u8 reg)
{
    sound_psg_address = reg;
    return sound_psg_read_port;
}
#endif

/* Original composition "Night Current": A minor with changing bass,
   lead and arpeggio arrangements across three districts. No sampled music. */
static const u16 note_fnum[12] = {
    172, 182, 193, 205, 217, 230, 244, 258, 274, 290, 307, 326
};
static const u8 roots[8] = {33,33,29,29,36,36,31,28};
static const u8 thirds[8] = {3,3,4,4,4,4,4,3};
static const u8 lead[3][32] = {
    {12,19,24,19,15,19,22,19,12,19,15,22,19,15,10,7,
     12,15,19,24,22,19,15,19,24,22,19,15,14,10,7,10},
    {24,19,15,19,22,19,15,12,19,24,27,24,22,19,15,19,
     24,22,19,15,19,22,26,22,24,19,15,12,14,19,22,19},
    {12,24,19,24,15,27,22,19,24,22,19,15,22,26,29,26,
     24,19,22,27,24,22,19,15,19,22,24,31,29,26,22,19}
};
static const u8 arpeggio[8] = {0,7,12,7,3,7,15,7};
static const u8 bass_pattern[8] = {0,0,12,0,7,0,12,7};
static const u8 effect_priority[7] = {0,1,2,3,4,2,5};
static const u8 effect_length[7] = {0,5,12,10,24,18,30};

static u8 muted_flag, song_stage, song_step, song_tick, song_started;
static u8 shot_left, effect_id, effect_left, effect_age;

static void fm_off(u8 channel)
{
    fm_write((u8)(0x20 + channel), 0);
}

static void fm_note(u8 channel, u8 note, u8 instrument, u8 volume)
{
    u16 fnum = note_fnum[note % 12];
    u8 octave = note / 12;
    fm_off(channel);
    fm_write((u8)(0x30 + channel), (u8)((instrument << 4) | volume));
    fm_write((u8)(0x10 + channel), (u8)fnum);
    fm_write((u8)(0x20 + channel),
             (u8)(0x10 | (octave << 1) | (fnum >> 8)));
}

static void music_silence(void)
{
    u8 i;
    /* Channels 6-8 retain the rhythm tuning across pause/resume. */
    for (i = 0; i < 6; ++i) fm_off(i);
    fm_write(0x0e, 0x20);
}

/* Preserve both joystick direction bits on every mixer update, including
   initialization and pause. Never touch PSG I/O registers 14 and 15. */
static void mixer(u8 channel_bits)
{
    psg_write(7, (u8)((psg_read(7) & 0xc0) | channel_bits));
}

static void psg_tone(u8 channel, u16 period, u8 volume)
{
    psg_write((u8)(channel << 1), (u8)period);
    psg_write((u8)((channel << 1) + 1), (u8)((period >> 8) & 15));
    psg_write((u8)(8 + channel), volume);
}

void sound_init(void)
{
    u8 i;
    muted_flag = 0;
    song_stage = 0xff;
    song_step = song_tick = song_started = 0;
    shot_left = effect_id = effect_left = effect_age = 0;
    for (i = 0x10; i < 0x39; ++i) fm_write(i, 0);
    fm_write(0x0e, 0x20); /* built-in rhythm voices */
    fm_write(0x16, 0x20); fm_write(0x26, 0x05);
    fm_write(0x17, 0x50); fm_write(0x27, 0x05);
    fm_write(0x18, 0xc0); fm_write(0x28, 0x01);
    fm_write(0x36, 0x04);
    fm_write(0x37, 0x65);
    fm_write(0x38, 0x76);
    psg_write(8, 0); psg_write(9, 0); psg_write(10, 0);
    mixer(0x3f);
}

void sound_mute(u8 value)
{
    value = value ? 1 : 0;
    if (muted_flag == value) return;
    muted_flag = value;
    if (value) {
        music_silence();
        psg_write(8, 0); psg_write(9, 0); psg_write(10, 0);
        mixer(0x3f);
    } else {
        song_tick = 0;
        song_step &= 0x70; /* restore the pad and groove on a bar */
    }
}

void sound_effect(u8 id)
{
    if (muted_flag || id == 0 || id > 6) return;
    if (id == 1) {
        shot_left = 5; /* independent channel: shots cannot mask impacts */
    } else if (!effect_left || effect_priority[id] >= effect_priority[effect_id]) {
        effect_id = id;
        effect_left = effect_length[id];
        effect_age = 0;
    }
}

static void effects_tick(void)
{
    u8 bits = 0x3f;
    u8 volume = 0;
    u16 period = 0;
    if (shot_left) {
        bits &= 0x3e;
        psg_tone(0, (u16)(24 + (5 - shot_left) * 44), (u8)(shot_left * 2 + 2));
        --shot_left;
    } else psg_write(8, 0);
    if (effect_left) {
        switch (effect_id) {
        case 2: /* noise burst with falling body */
            bits &= 0x2f;
            psg_write(6, (u8)(8 + effect_age * 2));
            volume = (u8)(effect_left + 2);
            break;
        case 3: /* harsh, alternating damage warning */
            bits &= 0x2d;
            period = (effect_age & 1) ? 220 : 380;
            psg_write(6, 12);
            volume = (u8)(effect_left + 4);
            break;
        case 4: /* long low-frequency bomb wash */
            bits &= 0x2d;
            period = (u16)(450 + effect_age * 48);
            psg_write(6, 31);
            volume = (u8)(3 + (effect_left >> 1));
            break;
        case 5: /* three rising launch tones */
            bits &= 0x3d;
            period = effect_age < 6 ? 214 : (effect_age < 12 ? 170 : 127);
            volume = (u8)(12 - (effect_age % 6));
            break;
        default: /* alternating low boss alarm, clear attack every 5 ticks */
            bits &= 0x3d;
            period = ((effect_age / 5) & 1) ? 640 : 880;
            volume = (u8)(13 - (effect_age % 5));
            break;
        }
        psg_tone(1, period, volume);
        ++effect_age;
        --effect_left;
    } else psg_write(9, 0);
    mixer(bits);
}

static void music_step(u8 stage, u8 playing)
{
    u8 chord = song_step >> 4;
    u8 root = roots[chord];
    u8 position = song_step & 15;
    u8 interval = arpeggio[song_step & 7];
    u8 tune = lead[stage][song_step & 31];
    u8 drums = 0x20;

    /* Major chords adjust the minor third in the shared melodic shapes. */
    if (thirds[chord] == 4) {
        if (interval == 3 || interval == 15) ++interval;
        if (tune == 15 || tune == 27) ++tune;
    }
    fm_note(0, (u8)(root + bass_pattern[song_step & 7]), 13,
            (u8)((song_step & 1) ? 6 : 3));
    fm_note(2, (u8)(root + 12 + interval), stage == 1 ? 12 : 11,
            playing ? 8 : 10);
    if (!(song_step & 1) || stage == 2)
        fm_note(1, (u8)(root + tune), stage == 1 ? 7 : 10, playing ? 4 : 7);
    if (!position) {
        fm_note(3, (u8)(root + 12), 8, 11);
        fm_note(4, (u8)(root + 12 + thirds[chord]), 8, 12);
        fm_note(5, (u8)(root + 19), 8, 12);
    }
    if (!(position & 7) || (stage == 2 && position == 14)) drums |= 0x10;
    if ((position & 7) == 4) drums |= 0x08;
    if (!(position & 1) || stage == 2) drums |= 0x01;
    if (position == 15 && chord == 7) drums |= 0x06;
    fm_write(0x0e, 0x20);
    fm_write(0x0e, drums);
    song_step = (u8)((song_step + 1) & 127);
}

void sound_tick(u8 stage, u8 playing)
{
    if (muted_flag) return;
    if (stage > 2) stage = 2;
    if (!song_started || song_stage != stage) {
        song_started = 1;
        song_stage = stage;
        song_step = song_tick = 0;
    }
    effects_tick();
    if (!song_tick) music_step(stage, playing);
    else if (song_tick == 1) fm_write(0x0e, 0x20);
    if (++song_tick >= 3) song_tick = 0; /* 150 BPM at 30 Hz */
}
