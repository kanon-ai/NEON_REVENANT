#ifndef NEON_SOUND_H
#define NEON_SOUND_H

/* Call once per rendered frame (nominally 30 Hz). Stage is 0, 1 or 2.
   Built-in turbo R MSX-MUSIC supplies music; PSG supplies all effects. */
void sound_init(void);
void sound_tick(unsigned char stage, unsigned char playing);
/* 1=shot, 2=explosion, 3=damage, 4=bomb, 5=start, 6=boss warning. */
void sound_effect(unsigned char id);
void sound_mute(unsigned char muted);

#endif
