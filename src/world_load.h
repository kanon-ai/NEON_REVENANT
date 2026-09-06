#ifndef NEON_WORLD_LOAD_H
#define NEON_WORLD_LOAD_H

#include "hardware.h"

/* Replace the resident 16-frame world at logical y=1152..4031. Call between
 * stages, never while a V9990 command is active. All CPU code runs from RAM.
 * Scratch history E800..EFFF is reserved; normal data must remain below E800.
 * Source bank and byte offset are generated in world_data.h by the packer. */
void world_load(u8 stage);

#endif
