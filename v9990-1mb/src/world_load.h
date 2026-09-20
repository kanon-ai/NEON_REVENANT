#ifndef NEON_WORLD_LOAD_H
#define NEON_WORLD_LOAD_H

#include "hardware.h"

/* Replace the resident 16-frame world at logical y=1152..4031. Call between
 * stages, never while a V9990 command is active. All CPU code runs from RAM.
 * Scratch history E800..EFFF is reserved; normal data must remain below E800.
 * Source bank and byte offset are generated in world_data.h by the packer. */
void world_load(u8 stage);

/* Lossless atlas upload to the original 10000h..23FFFh VRAM range. */
void assets_load(void);

/* Upload the optional 8 KiB feature strip to 7E000h..7FFFFh exactly once.
 * world_load never overwrites this range. No-op when feature.bin was absent
 * at build time. All loaders wait for the V9990 command engine; callers own
 * display enable and music muting. They share the existing E800..EFFF ring. */
void feature_load(void);

#endif
