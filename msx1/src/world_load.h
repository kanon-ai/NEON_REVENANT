#ifndef MSX1_WORLD_LOAD_H
#define MSX1_WORLD_LOAD_H
#include "hardware.h"
void world_load(u8 stage);
void title_load(void);
/* PCG uploads target slots unused by the current displayed frame. */
extern volatile u8 world_phase,world_page,world_pending,world_target;
void world_prepare(void);
void world_commit(void);
#endif
