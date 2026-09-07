/* Original "Night Current" PSG arrangement for the standard 3.58 MHz MSX.
 * A: bass, B: melody, C: arpeggio / priority sound effects.
 * No FM hardware, sample data, BIOS music service, or runtime division.
 * Call sound_tick at 30 Hz independently of background redraw frequency.
 */
#include "sound.h"
typedef unsigned char u8;
typedef unsigned int u16;

#ifdef SOUND_HOST_TEST
extern void sound_test_psg(u8 reg,u8 value);
extern u8 sound_test_psg_read(u8 reg);
#define raw_write sound_test_psg
#define raw_read sound_test_psg_read
#else
__sfr __at (0xa0) sound_psg_address;
__sfr __at (0xa1) sound_psg_data;
__sfr __at (0xa2) sound_psg_read_port;
static void raw_write(u8 reg,u8 value){sound_psg_address=reg;sound_psg_data=value;}
static u8 raw_read(u8 reg){sound_psg_address=reg;return sound_psg_read_port;}
#endif

/* Original Night Current themes, arranged for three PSG voices. */
static const u8 roots[8] = {33,33,29,29,36,36,31,28};
static const u8 thirds[8] = {3,3,4,4,4,4,4,3};
/* Indices 0..2 retain the original tunes; 3 and 4 frame the campaign. */
static const u8 lead[5][32] = {
    {12,19,24,19,15,19,22,19,12,19,15,22,19,15,10,7,
     12,15,19,24,22,19,15,19,24,22,19,15,14,10,7,10},
    {24,19,15,19,22,19,15,12,19,24,27,24,22,19,15,19,
     24,22,19,15,19,22,26,22,24,19,15,12,14,19,22,19},
    {12,24,19,24,15,27,22,19,24,22,19,15,22,26,29,26,
     24,19,22,27,24,22,19,15,19,22,24,31,29,26,22,19},
    {7,12,15,19,12,15,19,22,7,12,19,15,10,14,17,19,
     12,19,22,24,19,15,12,19,15,22,19,15,14,10,7,12},
    {24,27,31,27,22,26,29,26,24,19,22,27,31,29,27,24,
     19,24,27,31,29,26,22,19,22,26,29,31,24,22,19,24}
};
static const u8 arpeggio[8] = {0,7,12,7,3,7,15,7};
static const u8 bass_pattern[8] = {0,0,12,0,7,0,12,7};
static const u8 effect_priority[7] = {0,1,2,3,4,2,5};
static const u8 effect_length[7] = {0,5,12,10,24,18,30};
static const u16 note_period[96]={
4095,4095,4095,4095,4095,4095,4095,4095,4095,4068,3839,3624,
3420,3229,3047,2876,2715,2562,2419,2283,2155,2034,1920,1812,
1710,1614,1524,1438,1357,1281,1209,1141,1077,1017,960,906,
855,807,762,719,679,641,605,571,539,508,480,453,
428,404,381,360,339,320,302,285,269,254,240,226,
214,202,190,180,170,160,151,143,135,127,120,113,
107,101,95,90,85,80,76,71,67,64,60,57,
53,50,48,45,42,40,38,36,34,32,30,28
};


static u8 registers[14],muted_flag,song_stage,song_step,song_tick;
static u8 shot_left,effect_id,effect_left,effect_age;
static u16 bass_period,lead_period,arp_period;

static void psg_write(u8 reg,u8 value){
    if(registers[reg]!=value){registers[reg]=value;raw_write(reg,value);}
}
static void mixer(u8 bits){
    /* Keyboard/joystick polling may also touch the mixer. Always reread it;
     * never cache its I/O direction bits or write joystick registers 14/15. */
    u8 old=raw_read(7),value=(old&0xc0)|bits;
    registers[7]=value;if(old!=value)raw_write(7,value);
}
static void tone(u8 channel,u16 period,u8 volume){
    psg_write(channel<<1,(u8)period);
    psg_write((channel<<1)+1,(u8)(period>>8));
    psg_write(8+channel,volume);
}
static void music_step(u8 stage){
    u8 chord=song_step>>4,root=roots[chord];
    u8 interval=arpeggio[song_step&7],tune=lead[stage][song_step&31];
    if(thirds[chord]==4){
        if(interval==3||interval==15)++interval;
        if(tune==15||tune==27)++tune;
    }
    bass_period=note_period[root+bass_pattern[song_step&7]];
    lead_period=note_period[root+tune];
    arp_period=note_period[root+12+interval];
    song_step=(song_step+1)&127;
}
void sound_init(void){
    u8 i;
    for(i=0;i<14;i++)registers[i]=255;
    muted_flag=0;song_stage=255;song_step=song_tick=0;
    shot_left=effect_id=effect_left=effect_age=0;
    bass_period=lead_period=arp_period=1;
    psg_write(8,0);psg_write(9,0);psg_write(10,0);mixer(0x3f);
}
void sound_mute(u8 muted){
    muted=muted?1:0;if(muted_flag==muted)return;muted_flag=muted;
    if(muted){psg_write(8,0);psg_write(9,0);psg_write(10,0);mixer(0x3f);}
    else song_tick=0;
}
void sound_effect(u8 id){
    if(muted_flag||!id||id>6)return;
    if(id==1)shot_left=5;
    else if(!effect_left||effect_priority[id]>=effect_priority[effect_id]){
        effect_id=id;effect_left=effect_length[id];effect_age=0;
    }
}
void sound_tick(u8 stage,u8 playing){
    u8 bits=0x38,volume;
    u16 period;
    if(muted_flag)return;if(stage>4)stage=4;
    if(stage!=song_stage){song_stage=stage;song_step=song_tick=0;}
    if(!song_tick)music_step(stage);
    tone(0,bass_period,song_tick?9:12);
    tone(1,lead_period,playing?(song_tick?10:12):8);
    period=arp_period;volume=song_tick?6:9;
    if(effect_left){
        switch(effect_id){
        case 2: /* Explosion: noise replaces only the arpeggio channel. */
            bits=0x1c;psg_write(6,(8+effect_age*2)&31);
            volume=effect_left+2;break;
        case 3: /* Damage: alternating tone with noise. */
            bits=0x18;period=(effect_age&1)?220:380;
            psg_write(6,12);volume=effect_left+4;break;
        case 4:
            bits=0x18;period=450+(u16)effect_age*48;
            psg_write(6,31);volume=3+(effect_left>>1);break;
        case 5:
            period=effect_age<6?214:(effect_age<12?170:127);
            volume=effect_age<6?12:(effect_age<12?10:8);break;
        default:
            period=(effect_age&4)?640:880;volume=(effect_age&3)?10:13;break;
        }
        if(volume>15)volume=15;
        ++effect_age;--effect_left;
    }else if(shot_left){
        period=24+(u16)(5-shot_left)*44;volume=shot_left*2+2;
    }
    if(shot_left)--shot_left;
    tone(2,period,volume);mixer(bits);
    if(++song_tick>=3)song_tick=0; /* 150 BPM at 30 Hz. */
}
