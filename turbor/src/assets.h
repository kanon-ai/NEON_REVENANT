/* Generated SCREEN4 hardware-sprite descriptors. */
#ifndef NEON_ASSETS_H
#define NEON_ASSETS_H
typedef struct { unsigned int offset; unsigned char count,w,h; } Sprite;
#define SPRITE_RECORD_BYTES 50
#define SPRITE_DATA_BYTES 5650
static const Sprite player[3] = {{0,4,36,24},{200,4,36,24},{400,4,36,24}};
static const Sprite enemy[3][6] = {
 {{600,1,8,6},{650,1,12,8},{700,1,18,12},{750,1,26,17},{800,2,38,25},{900,2,54,36}},
 {{1000,1,8,6},{1050,1,12,8},{1100,1,18,12},{1150,1,26,17},{1200,2,38,25},{1300,2,54,36}},
 {{1400,1,8,6},{1450,1,12,8},{1500,1,18,12},{1550,1,26,17},{1600,2,38,25},{1700,2,54,36}}
};
static const Sprite explosion[4][5] = {
 {{1800,1,8,8},{1850,1,16,16},{1900,1,24,24},{1950,2,40,40},{2050,4,56,56}},
 {{2250,1,8,8},{2300,1,16,16},{2350,1,24,24},{2400,2,40,40},{2500,4,56,56}},
 {{2700,1,8,8},{2750,1,16,16},{2800,1,24,24},{2850,3,40,40},{3000,4,56,56}},
 {{3200,1,8,8},{3250,1,16,16},{3300,1,24,24},{3350,3,40,40},{3500,4,56,56}}
};
static const Sprite bosses[3] = {{3700,12,96,56},{4300,12,96,56},{4900,12,96,56}};
static const Sprite bullet = {5500,1,5,10};
static const Sprite pickup = {5550,1,13,13};
static const Sprite reticle = {5600,1,21,21};
#endif
