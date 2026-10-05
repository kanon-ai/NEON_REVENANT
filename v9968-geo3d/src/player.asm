; NEON REVENANT - isolated Geo3D playable visual prototype.
.module skyweave
.area ROM (ABS)
.org 0x4000
.ascii "AB"
.dw boot,0,0,0
.ds 6
boot:
 di
 ld sp,#0xF300
 ld hl,#0x4100
 ld de,#0xE800
 ld bc,#0x800
 ldir
 jp start
PAGE = 0xE200
FRAME = 0xE202
REC = 0xC000
CMD = 0xE400
PTR = 0xE410
COUNT = 0xE412
DONE = 0xE420
MODEL = 0xE414
MODEL_PTR = 0xE416
SOUND = 0xE418
SOUND_KIND = 0xE419
SKY = 0xE430
WALL = 0xE450
WCOUNT = 0xE470
PX = 0xE480
PY = 0xE482
SHOT = 0xE484
KEYS = 0xE485
SHOTX = 0xE486
SHOTY = 0xE488
SHOTS = 0xE48A
.include "hc_symbols.inc"
.org 0xE800
start:
 di
 ld sp,#0xF300
 call 0x0138
 rlca
 rlca
 and #3
 ld c,a
 ld b,#0
 ld hl,#0xFCC1
 add hl,bc
 ld a,(hl)
 and #0x80
 or c
 ld c,a
 inc hl
 inc hl
 inc hl
 inc hl
 ld a,(hl)
 rrca
 rrca
 rrca
 rrca
 and #12
 or c
 ld h,#0x80
 call 0x0024
 di
 in a,(0xFF)
 xor #1
 out (0xFE),a
 ld a,(0x002D)
 cp #3
 jr c,cpu_ready
 ld a,#0x81
 call 0x0180
 di
cpu_ready:
 ld hl,#0x4900
 ld de,#0x8000
 ld bc,#0x3700
 ldir
 ld hl,#0xD000
 ld de,#0xD001
 ld bc,#0x0FFF
 ld (hl),#0
 ldir
 call hc_init
 xor a
 ld (PAGE),a
 ld hl,#0
 ld (FRAME),hl
 ld (DONE),hl
 ld (PX),hl
 ld (PY),hl
 ld (SHOTX),hl
 ld (SHOTS),hl
 ld (SHOT),a
 out (0x9C),a
 ld hl,#regs
regloop:
 ld b,(hl)
 inc hl
 ld a,b
 cp #255
 jr z,regdone
 ld a,(hl)
 inc hl
 call wreg
 jr regloop
regdone:
 xor a
 ld b,#16
 call wreg
 ld hl,#palette
 ld bc,#0x309A
 otir
 call assets_init
 ld a,#0x60
 out (0x9D),a
 xor a
 out (0x9F),a
 out (0x9F),a
 ld a,#48
 out (0x9F),a
 ld a,#3
 out (0x9F),a
 xor a
 out (0x9F),a
 ld a,#0x18
 out (0x9D),a
 ld hl,#camera
 ld bc,#0x0C9F
 otir
 ld a,#0x40
 ld b,#1
 call wreg
 call audio_setup
main:
 xor a
 out (0xE6),a
 ld hl,(FRAME)
 ld a,l
 and #63
 add a,#0x40
 ld h,a
 ld l,#0
 push hl
 ld hl,(FRAME)
 add hl,hl
 add hl,hl
 ld a,h
 add a,#40
 ld (0x6000),a
 pop hl
 ld de,#REC
 ld bc,#256
 ldir
 call hc_tick
 ld a,(PAGE)
 xor #1
 ld (PAGE),a
 ld a,(mode)
 or a
 jr nz,game_scene
 call hc_draw
 jp frame_pace
game_scene:
 ld hl,#background
 call load15
 ld hl,(REC+176)
 ld (CMD),hl
 ld hl,(REC+178)
 ld (CMD+2),hl
 ld a,(PAGE)
 ld (CMD+7),a
 ld a,#32
 ld b,#17
 call wreg
 ld hl,#CMD
 ld bc,#0x0E9B
 otir
 ld a,#47
 ld b,#17
 call wreg
 ld hl,#REC+180
 ld bc,#0x049B
 otir
 ld a,#0x30
 ld b,#46
 call wreg
 call waitce
 ld a,#0x46
 out (0x9D),a
 xor a
 out (0x9F),a
 ld a,(PAGE)
 out (0x9F),a
 ld hl,#REC
 ld (PTR),hl
 ld a,#4
 ld (COUNT),a
object_loop:
 ld a,(COUNT)
 ld e,a
 ld d,#0
 ld hl,#REC+172
 or a
 sbc hl,de
 ld a,(hl)
 cp #255
 jr z,skip_object
 ld (0x6000),a
 call load_geometry
 xor a
 out (0x9D),a
 ld hl,(PTR)
 ld bc,#0x189F
 otir
 ld (PTR),hl
 ld a,#0x48
 out (0x9D),a
 ld a,#7
 out (0x9F),a
geo_wait:
 in a,(0x9D)
 and #1
 jr nz,geo_wait
 jr next_object
skip_object:
 ld hl,(PTR)
 ld de,#24
 add hl,de
 ld (PTR),hl
next_object:
 ld a,(COUNT)
 dec a
 ld (COUNT),a
 jr nz,object_loop
 call hc_draw
 ld hl,#hudtop
 call load15
 ld hl,(REC+184)
 ld (CMD+2),hl
 ld a,(PAGE)
 ld (CMD+7),a
 call send15
 call waitce
 ld hl,#hudbottom
 call load15
 ld hl,(REC+186)
 ld (CMD+2),hl
 ld a,(PAGE)
 ld (CMD+7),a
 call send15
 call waitce
frame_pace:
 in a,(0xE7)
 cp #22
 jr c,frame_pace
 call vblank
 ld a,(PAGE)
 rrca
 rrca
 rrca
 or #31
 ld b,#2
 call wreg
 ld hl,(DONE)
 inc hl
 inc hl
 inc hl
 ld (DONE),hl
 ld a,(mode)
 or a
 jp z,main
 cp #4
 jp z,main
 ld hl,(FRAME)
 inc hl
 inc hl
 inc hl
 ld a,h
 cp #6
 jr c,frame_ok
 ld hl,#0
frame_ok:
 ld (FRAME),hl
 jp main
controls:
 in a,(0xAA)
 and #0xF0
 or #8
 out (0xAA),a
 in a,(0xA9)
 cpl
 ld (KEYS),a
 ld c,a
 ld hl,(PX)
 bit 4,c
 jr z,no_left
 ld de,#-5
 add hl,de
no_left:
 bit 7,c
 jr z,no_right
 ld de,#5
 add hl,de
no_right:
 ; Clamp signed X to -100..100.
 bit 7,h
 jr nz,x_negative
 ld a,l
 cp #101
 jr c,x_ok
 ld hl,#100
 jr x_ok
x_negative:
 ld a,l
 cp #156
 jr nc,x_ok
 ld hl,#-100
x_ok:
 ld (PX),hl
 ld de,(REC+162)
 add hl,de
 ld (REC+162),hl
 ld hl,(PY)
 bit 5,c
 jr z,no_up
 ld de,#4
 add hl,de
no_up:
 bit 6,c
 jr z,no_down
 ld de,#-4
 add hl,de
no_down:
 bit 7,h
 jr nz,y_negative
 ld a,l
 cp #81
 jr c,y_ok
 ld hl,#80
 jr y_ok
y_negative:
 ld a,l
 cp #232
 jr nc,y_ok
 ld hl,#-24
y_ok:
 ld (PY),hl
 ld de,(REC+164)
 add hl,de
 ld (REC+164),hl
 ld a,(SHOT)
 or a
 ret nz
 bit 0,c
 ret z
 ld a,#12
 ld (SHOT),a
 ld hl,(PX)
 sra h
 rr l
 ld de,#128
 add hl,de
 ld (SHOTX),hl
 ld hl,(PY)
 sra h
 rr l
 ex de,hl
 ld hl,#169
 or a
 sbc hl,de
 ld (SHOTY),hl
 ld hl,(SHOTS)
 inc hl
 ld (SHOTS),hl
 ret
draw_shot:
 ld a,(SHOT)
 or a
 ret z
 dec a
 ld (SHOT),a
 ld hl,#shotcmd
 call load15
 ld hl,(SHOTX)
 ld (CMD+4),hl
 ld hl,(SHOTY)
 ld de,#-5
 add hl,de
 ld (SHOTY),hl
 ld a,(PAGE)
 add a,h
 ld h,a
 ld (CMD+6),hl
 call send15
 call waitce
 ret
shotcmd:
 .dw 0,0,128,169,2,7
 .db 0xDD,0,0xC0
load_geometry:
 ld a,#0x40
 out (0x9D),a
 xor a
 out (0x9F),a
 out (0x9F),a
 ld a,(0x4000)
 out (0x9F),a
 xor a
 out (0x9F),a
 ld a,#15
 out (0x9F),a
 xor a
 out (0x9F),a
 ld a,#0x50
 out (0x9D),a
 ld hl,#0x4006
 ld de,(0x4002)
 call geoblock
 ld a,#0x58
 out (0x9D),a
 xor a
 out (0x9F),a
 ld a,(0x4001)
 out (0x9F),a
 ld a,#0x52
 out (0x9D),a
 ld de,(0x4004)
 call geoblock
 ld a,#0x65
 out (0x9D),a
 xor a
 out (0x9F),a
 ld de,(0x7FFE)
 ld a,d
 or e
 ret z
 ld a,#0x53
 out (0x9D),a
 call geoblock
 ret
wreg:
 push de
 ld e,a
 ld a,i
 di
 push af
 ld a,e
 out (0x99),a
 ld a,b
 or #0x80
 out (0x99),a
 pop af
 pop de
 ret po
 ei
 ret
status2:
 ld a,#2
 ld b,#15
 call wreg
 in a,(0x99)
 ret
waitce:
 call status2
 and #1
 jr nz,waitce
 ret
vblank:
 ; A page flip already inside vertical blank need not wait another frame.
 call status2
 and #0x40
 jr z,vblank
 ret
load15:
 ld de,#CMD
 ld bc,#15
 ldir
 ret
send15:
 ld a,#32
 ld b,#17
 call wreg
 ld hl,#CMD
 ld bc,#0x0F9B
 otir
 ret
geoblock:
 ld c,#0x9F
 jr block
vramblock:
 ld c,#0x98
block:
 ld a,d
 or a
 jr z,tail
blockloop:
 ld b,#0
 otir
 dec a
 jr nz,blockloop
tail:
 ld a,e
 or a
 ret z
 ld b,e
 otir
 ret
regs:
 .db 0,14,1,0,2,31,7,0,8,10,9,128,21,0,20,17,51,0,52,0,53,0,54,0,55,255,56,0,57,255,58,3,255
camera:
 .dw 170,128,106,4,256,212
light:
 .dw -5000,10500,-11500
background:
 .dw 0,512,0,14,256,184
 .db 0,0,0x30
hudtop:
 .dw 0,512,0,0,256,14
 .db 0,0,0xD0
hudbottom:
 .dw 0,710,0,198,256,14
 .db 0,0,0xD0
.include "palette.inc"

