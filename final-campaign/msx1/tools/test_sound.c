#include <stdio.h>
#include <string.h>
#include "sound.h"
#ifndef SOUND_TEST_STAGE_COUNT
#define SOUND_TEST_STAGE_COUNT 5
#endif
static unsigned char psg[16],direction;
static unsigned long hash,writes,failures,checks;
static void check(int condition,const char *message){++checks;if(!condition){++failures;fprintf(stderr,"FAIL %s\n",message);}}
void sound_test_psg(unsigned char reg,unsigned char value){
    check(reg<14,"Never write joystick data ports");
    if(reg>=14)return;
    if(reg==7)check((value&192)==direction,"Preserve joystick mixer direction");
    if(reg==1||reg==3||reg==5)check(value<16,"Tone is a 12-bit period");
    if(reg>=8&&reg<=10)check(value<16,"Fixed volume in range");
    if(reg==6)check(value<32,"Noise period in range");
    psg[reg]=value;hash=(hash*33u)^((reg<<8)|value);++writes;
}
unsigned char sound_test_psg_read(unsigned char reg){return psg[reg];}
static void fresh(unsigned char mode){
    memset(psg,0,sizeof(psg));direction=mode;psg[7]=mode|63;sound_init();
}
int main(void){
    unsigned long stages[SOUND_TEST_STAGE_COUNT],stage_hashes[4][SOUND_TEST_STAGE_COUNT],effects[6],before;
    unsigned char reference[36][7],snapshot[7];
    int mode,stage,i,j,e;
    for(mode=0;mode<4;++mode){
        fresh((unsigned char)(mode<<6));
        check(psg[8]==0&&psg[9]==0&&psg[10]==0,"Initialization is silent");
        for(stage=0;stage<SOUND_TEST_STAGE_COUNT;++stage){
            hash=0;
            for(i=0;i<384;++i){
                sound_tick((unsigned char)stage,1);
                check(psg[8]>0&&psg[9]>0&&psg[10]>0,"Three musical voices active");
                check((psg[7]&63)==56,"Music enables tones only");
            }
            stages[stage]=hash;
            stage_hashes[mode][stage]=hash;
        }
        for(stage=0;stage<SOUND_TEST_STAGE_COUNT;++stage)for(j=stage+1;j<SOUND_TEST_STAGE_COUNT;++j)
            check(stages[stage]!=stages[j],"Distinct full stage arrangements");
        fresh((unsigned char)(mode<<6));
        for(i=0;i<36;++i){
            sound_tick(0,1);
            reference[i][0]=psg[0];reference[i][1]=psg[1];reference[i][2]=psg[2];reference[i][3]=psg[3];
            reference[i][4]=psg[8];reference[i][5]=psg[9];reference[i][6]=psg[10];
        }
        for(e=1;e<=6;++e){
            fresh((unsigned char)(mode<<6));sound_effect((unsigned char)e);effects[e-1]=0;
            for(i=0;i<36;++i){
                sound_tick(0,1);
                snapshot[0]=psg[0];snapshot[1]=psg[1];snapshot[2]=psg[2];snapshot[3]=psg[3];snapshot[4]=psg[8];snapshot[5]=psg[9];
                check(memcmp(snapshot,reference[i],6)==0,"Effects leave bass and melody uninterrupted");
                effects[e-1]=effects[e-1]*33u+psg[4]+psg[5]*3+psg[6]*5+psg[7]*7+psg[10]*11;
            }
            check((psg[7]&63)==56&&psg[10]==reference[35][6],"Effects end and music channel returns");
        }
        for(e=0;e<6;++e)for(j=e+1;j<6;++j)check(effects[e]!=effects[j],"Six distinct effects");
        fresh((unsigned char)(mode<<6));sound_effect(4);sound_tick(0,1);
        sound_effect(1);sound_tick(0,1);check((psg[7]&32)==0,"Bomb priority survives a shot");
        sound_mute(1);check(psg[8]==0&&psg[9]==0&&psg[10]==0,"Mute silences all channels");
        before=writes;for(i=0;i<100;++i){sound_effect(3);sound_tick(1,1);}
        check(writes==before,"Muted tick and effect issue no sound writes");
        sound_mute(0);sound_tick(0,1);check(writes>before&&psg[8]>0&&psg[9]>0,"Unmute restores music");
        /* Input polling can change mixer direction after sound's cache fill. */
        direction=(unsigned char)(((mode+1)&3)<<6);psg[7]=direction|63;
        sound_tick(0,1);check((psg[7]&192)==direction,"Read live I/O direction after external mixer change");
        sound_effect(255);sound_tick(255,1);
    }
    printf("{\"passed\":%s,\"assertions\":%lu,\"writes\":%lu,\"failures\":%lu,\"joystick_direction_variants\":4,\"stage_arrangements\":%d,\"effect_types\":6,\"stage_hashes\":[",failures?"false":"true",checks,writes,failures,SOUND_TEST_STAGE_COUNT);
    for(mode=0;mode<4;++mode){
        printf("%s[",mode?",":"");
        for(stage=0;stage<SOUND_TEST_STAGE_COUNT;++stage)printf("%s%lu",stage?",":"",stage_hashes[mode][stage]);
        printf("]");
    }
    printf("]}\n");
    return failures?1:0;
}
