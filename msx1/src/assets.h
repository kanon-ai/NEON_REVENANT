/* Generated resident TMS9918 mode-1 sprite descriptors. */
#ifndef NEON_ASSETS_H
#define NEON_ASSETS_H
typedef struct { unsigned int offset; unsigned char count,w,h; } Sprite;
#define SPRITE_PATTERN_BYTES 1760
#define SPRITE_DATA_BYTES 220
static const Sprite player[3] = {{0,2,32,25},{8,2,32,25},{16,2,32,25}};
static const Sprite enemy[3][6] = {{{24,1,8,7},{28,1,12,9},{32,1,18,14},{36,1,26,18},{40,2,38,27},{48,2,48,36}},{{56,1,8,7},{60,1,12,9},{64,1,18,14},{68,1,26,18},{72,2,38,27},{80,2,48,36}},{{88,1,8,7},{92,1,12,9},{96,1,18,14},{100,1,26,18},{104,2,38,27},{112,2,48,36}}};
static const Sprite explosion[4][5] = {{{120,1,24,25},{120,1,24,25},{120,1,24,25},{120,1,24,25},{120,1,24,25}},{{124,1,24,25},{124,1,24,25},{124,1,24,25},{124,1,24,25},{124,1,24,25}},{{128,1,24,25},{128,1,24,25},{128,1,24,25},{128,1,24,25},{128,1,24,25}},{{132,1,24,25},{132,1,24,25},{132,1,24,25},{132,1,24,25},{132,1,24,25}}};
static const Sprite bosses[3] = {{136,6,96,57},{160,6,96,57},{184,6,96,57}};
static const Sprite bullet = {208,1,6,12};
static const Sprite pickup = {212,1,14,14};
static const Sprite reticle = {216,1,22,23};
#endif
