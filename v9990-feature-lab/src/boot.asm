; ASCII8 cartridge, bank 0. C runtime is copied into fast internal RAM.
    org 04000h
    db "AB"
    dw start
    dw 0,0,0,0,0,0
start:
    di
    ld sp,0F300h
    xor a
    ld (06000h),a
    ; Use the same RAM slot as page 3. BIOS slot tables describe expansion.
    in a,(0A8h)
    rlca
    rlca
    and 3
    ld c,a
    ld b,0
    ld hl,0FCC1h
    add hl,bc
    ld a,(hl)
    and 080h
    jr z,primary_ram
    ld hl,0FCC5h
    add hl,bc
    ld a,(hl)
    and 0C0h
    rrca
    rrca
    rrca
    rrca
    or 080h
primary_ram:
    or c
    ld h,080h
    call 0024h
    di
    ; Three 8KiB banks -> 8000..DFFF; data area is cleared by main.
    ld a,1
    ld de,08000h
copy_bank:
    ld (06800h),a
    ld hl,06000h
    ld bc,02000h
    ldir
    inc a
    cp 4
    jr nz,copy_bank
    ; Only call turbo R CPU switching BIOS when supported.
    ld a,(0002Dh)
    cp 3
    jr c,no_turbo
    ld a,082h
    call 0180h
no_turbo:
    di
    ld sp,0F300h
    jp ENTRY_POINT
    defs 02000h-($-04000h),0FFh
