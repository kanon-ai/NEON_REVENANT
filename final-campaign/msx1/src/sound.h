#ifndef NEON_SOUND_H
#define NEON_SOUND_H
/* Standard PSG: three original musical voices; effects temporarily use C.
 * Call at 30 Hz, independently of the renderer. No MSX-MUSIC is required. */
void sound_init(void);
/* Tune ids: 0..2 original sectors, 3 breakwater, 4 dawn exodus. */
void sound_tick(unsigned char stage,unsigned char playing);
/* 1=shot,2=explosion,3=damage,4=bomb,5=start,6=boss warning. */
void sound_effect(unsigned char id);
void sound_mute(unsigned char muted);
#endif
