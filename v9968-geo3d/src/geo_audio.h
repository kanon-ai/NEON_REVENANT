/* ISR uses P#4 and sound ports; foreground VDP control pairs are atomic. */
__sfr __at(0x9C) audio_port;
volatile u8 audio_stage,audio_playing,audio_frames;
volatile u16 audio_ticks;
static u8 audio_divider;
void audio_service(void){if(++audio_divider==2){audio_divider=0;sound_tick(audio_stage,audio_playing);++audio_ticks;}}
void audio_irq(void) __naked {
 __asm
 push af
 push bc
 push de
 push hl
 push ix
 push iy
 .db 0x08
 push af
 exx
 push bc
 push de
 push hl
 in a,(#0x9C)
 bit 0,a
 jr z,audio_irq_done
 ld a,#1
 out (#0x9C),a
 ld a,(_audio_frames)
 inc a
 ld (_audio_frames),a
 call _audio_service
audio_irq_done:
 pop hl
 pop de
 pop bc
 exx
 pop af
 .db 0x08
 pop iy
 pop ix
 pop hl
 pop de
 pop bc
 pop af
 ei
 reti
 __endasm;
}
void audio_setup(void){
 u16 i;
 for(i=0;i<257;++i)((u8*)0xF400)[i]=0xF5;
 *(u8*)0xF5F5=0xC3;*(u16*)0xF5F6=(u16)audio_irq;
 audio_port=7;vr(1,0x60);
 __asm
 ld a,#0xF4
 ld i,a
 im 2
 ei
 __endasm;
}
void audio_pause(u8 value) __naked {
 value;
 __asm
 ld c,a
 ld a,i
 di
 push af
 ld a,c
 call _sound_mute
 pop af
 ret po
 ei
 ret
 __endasm;
}
typedef struct {s16 x,y;s8 dx,dy;u8 life;} Spark;
static Spark sparks[8];
static u8 spark_next;
volatile u16 boss_hit_count;
void boss_hit_particles(s16 x,s16 y){
 u8 i;Spark *s;++boss_hit_count;
 for(i=0;i<4;++i){s=&sparks[spark_next];spark_next=(spark_next+1)&7;
 s->dx=(i&1)?3:-3;s->dy=(i&2)?2:-2;s->x=x+s->dx;s->y=y+s->dy;s->life=6;}
}
void spark_tick(void){u8 i;for(i=0;i<8;++i)if(sparks[i].life){--sparks[i].life;sparks[i].x+=sparks[i].dx;sparks[i].y+=sparks[i].dy;}}
