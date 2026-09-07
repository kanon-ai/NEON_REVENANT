[Current v1.3: Dawn Leviathan giant-boss guide](GIANT_BOSS-v1.3.md) — The document below records v1.2.

# NEON REVENANT — MSX1 PCG Drive v1.2

**ASTRA Thank-You Edition / ASTRAからの有難うエディション**

Thank you for playing, watching, sharing your thoughts, and testing on real hardware. This five-zone edition is our thank-you to the community.

[A note from ASTRA](../docs/ASTRA_THANK_YOU_EDITION.md)

**Breakwater to Dawn is a five-zone shooter for the original MSX: enter through the harbor, cross the city, and escape into dawn. This prototype uses a 512 KiB ASCII8 ROM, 32 KiB RAM, 16 KiB VRAM and the standard PSG. Provided without warranty. Version 1.2 has not been tested on physical MSX hardware or flash cartridges.**

[日本語](README.md)

## Campaign

| Order | Zone | Boss encounter |
|---|---|---|
| Episode 0 | BREAKWATER APPROACH | SENTRY / HARBOR PATROL |
| 01 | CHROME DISTRICT | WARDEN / INTERCEPTOR |
| 02 | SKYWAY ASSAULT | RAZOR / SIEGE CARRIER |
| 03 | THE BLACK SPIRE | NOX / CENTRAL CORE |
| 04 | DAWN EXODUS | ECHO / LAST PURSUER |

Version 1.2 adds harbor and escape backgrounds plus two PSG melodies. There are five boss encounters using the existing three boss silhouettes: the opening reuses WARDEN and the finale reuses NOX with different colors. Each background is a repeating 16-phase animation, not a continuous cinematic journey or a one-time physical collapse simulation.

The original three zones retain their background data, combat settings and music. Finishing Episode 0 restores all six shield points and three bombs; later transitions use the original recovery rules. Defeat all five bosses to clear the campaign. The opening and escape routes are shorter than the original zones. A retry starts at Episode 0.

![Episode 0 running from the ROM](../outputs/msx1/v1.2/ntsc/stage-1-native.gif)

Captured in openMSX with 32 KiB RAM and NTSC timing: 96 rendered frames with movement and firing. GIF durations follow measured emulated time.

## Requirements and controls

- Original MSX, Z80 at 3.58 MHz; at least **32 KiB RAM covering 8000h–FFFFh in one RAM slot**. A 16 KiB RAM machine is insufficient.
- TMS9918A/TMS9929A family VDP, **16 KiB VRAM**, SCREEN 2 at 256×192, fixed palette.
- [512 KiB ASCII8 ROM](../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom), exactly 524,288 bytes.
- Standard PSG sound. No V9990, FM cartridge, additional PCG hardware or MSX-DOS is required.

| Action | Keyboard | Joystick port 1 |
|---|---|---|
| Move craft and aim | Arrow keys | Directions |
| Start, fire, retry | Space | Trigger 1 |
| NOVA bomb | X | Trigger 2 |
| Pause/resume | Esc | Use keyboard Esc |

Aim the reticle at enemies and fire while avoiding incoming craft and shots. Bombs activate on a new press; holding the button does not consume more bombs.

For a standard openMSX C-BIOS machine, select **ASCII8** and the **MSX** video source:

```powershell
openmsx -machine C-BIOS_MSX1_JP -cart NEON_REVENANT-MSX1-v1.2.rom -romtype ASCII8
```

That command uses the standard installed machine. The development procedure below tests an explicit 32 KiB configuration. BIOS images and openMSX itself are not included.

## Animation and performance

The next background is uploaded in two parts to unused pattern slots and a hidden name table. The display switches only after the next image is ready. There is no runtime image generation or decompression. Backgrounds advance every two game frames; the HUD updates every four.

Simulation and music are frame-bound. PAL/50 Hz therefore runs more slowly than NTSC/60 Hz, and frame drops also slow gameplay and music. A constant 30 fps and identical speed across both standards are not promised.

Measurements use openMSX 21.0, a 3.58 MHz Z80, 32 KiB RAM, 16 KiB VRAM and enabled sprite limits. Each row covers 96 rendered frames with movement and firing; rates use emulated elapsed time.

| Zone | NTSC / 60 Hz | PAL / 50 Hz |
|---|---:|---:|
| Episode 0 / BREAKWATER APPROACH | 26.58 fps | 23.92 fps |
| 01 / CHROME DISTRICT | 26.08 fps | 23.12 fps |
| 02 / SKYWAY ASSAULT | 25.96 fps | 23.23 fps |
| 03 / THE BLACK SPIRE | 24.09 fps | 22.46 fps |
| 04 / DAWN EXODUS | 25.16 fps | 22.89 fps |

See the [NTSC](../outputs/msx1/v1.2/ntsc/world-verification.json) and [PAL](../outputs/msx1/v1.2/pal/world-verification.json) rendering reports. Background updates are approximately 11–13 Hz in these intervals. Frozen rendering scenarios are excluded from this gameplay table.

Sprites use 55 resident 16×16 patterns. The hardware limits of 32 sprites per screen, four per scanline and one color per sprite can cause flicker or missing parts in crowded scenes. There is no free 3D camera or horizontal background scrolling.

## Memory and ROM layout

The [build manifest](../outputs/msx1/v1.2/build-manifest.json) allocates **368 KiB** and leaves **144 KiB** unused at the end of the 512 KiB ROM. The runtime code and constant span is 11,138 bytes; static data ends at E211h. RAM, ROM and VRAM are separate capacities.

| 8 KiB ROM banks | Contents |
|---|---|
| 0 | Boot code |
| 1–3 | Runtime region copied into RAM |
| 4–5 | Sprite records and resident patterns |
| 6–15 | Five initial VRAM images, 16 KiB each |
| 16–17 | Title screen |
| 18–45 | 80 background transfer packets |
| 46–63 | Unused |

Multiple whole packets share each bank, addressed by bank number and offset. No packet crosses a bank boundary. The packet payload totals 213,556 bytes. Packing removes much of v1.1's one-packet-per-bank padding without introducing runtime decompression.

The largest PCG upload part is 1,352 bytes including name data; the opening zone's maximum is 1,208 bytes. VRAM uses patterns at 0000h–17FFh, sprite patterns at 1800h–1FFFh, colors at 2000h–37FFh, name tables at 3800h/3C00h and sprite attributes at 3B00h/3B80h. Active patterns and HUD font slots remain protected. Preserve the 30-Z80-clock spacing in the VDP write loop.

## Build from source

Work inside `msx1/`. Install Python 3, Pillow, NumPy, Z80 SDCC and Pasmo. Development uses SDCC 4.6.0. Artwork under `assets/source/` allows regeneration without another edition's working directory.

```powershell
python -m pip install -r requirements.txt
$env:SDCC_BIN = 'C:/path/to/sdcc/bin'
$env:PASMO = 'C:/path/to/pasmo.exe'
python tools/build.py
```

Output is written to `../outputs/msx1/v1.2/`. `python tools/build.py --pack-only` skips artwork regeneration but still recompiles the current C/ASM and packet-location tables.

[Full regeneration and rebuilding in an independent directory](../outputs/msx1/v1.2/reproducibility.json) produced a byte-identical ROM.

## Reproduce the checks

Offline checks need Python dependencies; sound and combat comparisons also need a host C compiler:

```powershell
python tools/verify_layout.py
$env:CC = 'C:/path/to/gcc.exe'
python tools/verify_sound.py
# Optional comparisons with a separately retained v1.1 source release:
python tools/verify_layout.py --baseline 'C:/archive/v1.1/msx1/assets'
python tools/verify_campaign.py --baseline 'C:/archive/v1.1/msx1/src/game.c' --gcc 'C:/path/to/gcc.exe'
```

The campaign comparison requires the explicit external baseline; the previous release is not bundled in v1.2. The sound verifier additionally compares the original three tunes when the retained v1.1 complete ZIP is available in the sibling release directory.

Native checks require Node.js, openMSX and its separately installed C-BIOS. Point `OPENMSX_EXE` and `OPENMSX_SYSTEM_DATA` at the executable and share directory from the same openMSX distribution. The Windows development bridge creates isolated settings under `work/ram32-profile-ntsc/` or `work/ram32-profile-pal/` and starts with rendering disabled and power off. Its default audio driver is dummy: these checks examine PSG registers, not audio-output hardware.

```powershell
$env:OPENMSX_EXE = 'C:/path/to/openmsx.exe'
$env:OPENMSX_SYSTEM_DATA = 'C:/path/to/openMSX/share'
$env:MSX_RAM_KIB = '32'
$env:MSX_VIDEO_STANDARD = 'ntsc'
node tools/emulator_ram32.mjs -cart ../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom -romtype ASCII8
```

In a second terminal, also inside `msx1/`:

```powershell
$env:MSX_VIDEO_STANDARD = 'ntsc'
python tools/emu.py "set power on"
python tools/emu.py "set renderer SDLGL-PP"
python tools/emu.py "set pause off"
python tools/verify_rom.py
python tools/verify_world.py
python tools/verify_transfer.py
python tools/emu.py "exit"
```

For PAL, first wait for the old bridge to exit and its terminal prompt to return. Change both terminals to `pal`, start a fresh bridge and repeat in the same order. Run only one bridge at a time. Reports are separated into `../outputs/msx1/v1.2/ntsc/` and `pal/`.

Both 32 KiB standards passed 57 gameplay, 61 rendering and nine transfer checks each: **254 native checks total**. The [NTSC](../outputs/msx1/v1.2/ntsc/verification.json) and [PAL](../outputs/msx1/v1.2/pal/verification.json) gameplay reports cover all five transitions, clear and retry. VRAM readback matched 960 rendered frames across both standards, including every zone's 16 phases. Normal game execution produced zero too-fast VRAM accesses. The [NTSC](../outputs/msx1/v1.2/ntsc/transfer-verification.json) and [PAL](../outputs/msx1/v1.2/pal/transfer-verification.json) transfer tests also exercise boundary cases, register preservation and a positive control for the timing detector.

An additional [64 KiB RAM smoke test](../outputs/msx1/v1.2/ram64-smoke.json) passed 11 checks, bringing the native total to **265**. It covers keyboard-controlled Episode 0 startup, movement, pause and bombs; the five-zone scenario tests use 32 KiB. The [environment record](../outputs/msx1/v1.2/validation-environment.json) identifies the emulator version and executable SHA-256, RAM/VDP configuration and test boundaries.

The [layout report](../outputs/msx1/v1.2/layout-verification.json) independently decodes all 80 packets from ROM, checks protected VRAM regions and confirms 54 original-zone asset files are unchanged. The [combat comparison](../outputs/msx1/v1.2/campaign-verification.json) matches 28,066 snapshots with 157 fields each against the original three zones under identical seeded inputs. The [PSG report](../outputs/msx1/v1.2/sound-verification.json) covers five tunes, six effects and unchanged register traces for the original three tunes.

The host combat harness uses 16-bit variable storage, but expression promotion follows GCC; it is not a Z80 timing or VDP emulator. Native checks include RAM-seeded scenarios for later zones, bosses and damage, followed by execution of the actual ROM. They do not establish a complete manual playthrough. `*-reference` images show generated artwork; `*-native` captures show ROM execution.

This is an original work in development. Physical hardware and flash-cartridge compatibility remain unverified for v1.2. See the included disclaimer, copyright and third-party notices before use.
