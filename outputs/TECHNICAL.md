# NEON REVENANT v1.2: implementation and verification

> **試作中・無保証 / Experimental prototype — AS IS, WITHOUT WARRANTY.** 実機・実カートリッジは未検証です。利用前に[免責事項](../DISCLAIMER.md)と、リポジトリ直下の利用条件・第三者ライセンスを確認してください。

An original cartridge game written in C and Z80 assembly, running natively on
the MSX. The PC tools generate art, build the ROM and exercise openMSX; they
are not the game engine. No PC renderer, browser, disk operating system or
external asset loader is needed by the cartridge at runtime.

The PC build tools require Python, Pillow and NumPy, plus SDCC and Pasmo.
The packaged `requirements.txt` lists the Python packages; install them with
`python -m pip install -r requirements.txt`. Pillow and NumPy generate and
verify assets offline and are not runtime dependencies of the MSX game.

Version 1.2 redesigns the world, sprites and shared palette around an imagined
"MSX3" art direction: illuminated architecture, metal surfaces and reflections
expressed in 16 colors. The existing forward movement, lateral camera inertia,
atlas coordinates, gameplay, input, music and sound effects are retained.
The target remains actual MSX turbo R + V9990 specifications. "MSX3" describes
the visual concept, not an existing machine or modern PC 3D capabilities.
Material and lighting cues are baked into indexed images offline; the MSX
does not execute a physically based renderer.

## Cartridge layout

The current `build-manifest.json` identifies the 524288-byte ASCII8 ROM and
its SHA-256. `allocated_bytes` gives the end of the occupied region; trailing
FF padding is `rom_bytes - allocated_bytes`. Each `worlds` entry records the
final compressed size and ROM offset. These values depend on the final art.

| ROM region, hexadecimal | Contents | Bytes |
|---|---|---:|
| 00000-01FFF | ASCII8 bank 0: AB header, RAM slot setup, loader | 8192 |
| 02000-07FFF | Banks 1-3: runtime copied to MSX RAM 8000-DFFF | 24576 reserved |
| 08000-1BFFF | Banks 4-13: packed sprite/font/UI atlas | 81920 |
| 1C000 onward | Three concatenated LZSS world streams | See manifest |
| End of allocated region-7FFFF | FF padding | See manifest |

Each world stream expands to 368640 bytes: 16 complete frames, each 256x180
at 4bpp. Compressed streams may
cross ASCII8 bank boundaries; they are not padded to separate banks.

The cartridge keeps bank 0 visible at 4000h. Bank register 6800h maps asset
data through the 6000h window while the game executes in RAM. RAM page 2 is
selected using the BIOS slot table for page 3. On turbo R the loader selects
R800 DRAM mode using CHGCPU. The game disables interrupts and polls V9990 and
input ports. Game data occupies E000-E7FF; the LZSS decoder uses a 2048-byte
history ring at E800-EFFF. The stack begins at F300h.

## Video and world animation

- V9990 B1, 256x212, 4bpp, with a redesigned 16-color RGB5 palette shared
  through `tools/art_palette.py`.
- Display/drawing pages begin at logical image Y=0 and Y=256.
- Sprite/font/UI atlas occupies Y=512-1151, CPU VRAM 10000h-23FFFh.
- The current stage's 16 world frames occupy Y=1152-4031, CPU VRAM
  24000h-7DFFFh. Frame `n` starts at Y=`1152 + n * 180`.
- The world viewport covers screen Y=18-197. The HUD is drawn separately
  above and below it.
- The original geometry is projected offline by `tools/generate_world.py`.
  Filled and shaded faces, attached windows/signs and road texture are defined
  in world coordinates. The camera advances through a periodic 384-unit world
  segment over 16 frames. This is a precomputed perspective animation, not
  real-time polygon rasterization by the MSX CPU.
- At startup and stage changes, the native LZSS decoder reads the selected
  compressed ROM stream and writes it directly to V9990 VRAM. All 16 frames
  then remain resident for that stage; gameplay does not stream them from PC.
- Gameplay cycles through the resident images. A continuous lateral camera
  shift gradually follows player movement, with a small curve offset. Long
  facades remain continuous; the opposite street edge is never wrapped in.
- Enemies retain six pregenerated sprite sizes. Sprites and game objects are
  composited over the moving world using V9990 LMMM copies and LMMV fills.
- Indexed zero is transparent for sprite copies. Packed pixels use even X in
  the high nibble and odd X in the low nibble.

The final v1.2 ROM measured 29.96 updates/second in each stage across 64
consecutive native draw frames. World replacement took 4.906, 4.039 and
3.705 emulated seconds in stages 1-3. These are samples, not a fixed-rate
guarantee for every scene or physical hardware.
Startup loads stage 1; firmware boot adds its own delay. Simulation and audio
pause during replacement. The native decoder uses a register-based assembly
match-copy loop.

## Verification

The world generator independently renders absolute camera positions 0 and
384 and requires byte-identical pixels. It also reopens every generated GIF
and compares all 16 decoded frames with their source RGB images. A tracked
wall feature changes both screen position and projected width as the camera
approaches. The frame-15 to frame-0 change remains within the normal range of
adjacent-frame changes. These checks establish generated animation behavior;
they are separate from native execution verification.

The ROM build verifies Python-side LZSS decompression against each complete
raw stage stream before packing it. Native verification compares all three
368640-byte world streams and the 81920-byte sprite atlas against VRAM
readback.

`verification-v1.2.json` and `world-verification-v1.2.json` are the report
files for successful openMSX 21.0 / Panasonic FS-A1ST / GFX9000 checks,
with the ASCII8 ROM in Cart 2. Startup, R800 DRAM mode, movement, shooting,
bombs, pause/resume, damage, retry, all three boss encounters and transitions,
the ending, and resumed FM register updates after replacement passed.
All three 368640-byte world streams and the 81920-byte sprite atlas matched
native VRAM readback byte for byte. Every frame of the three native capture
GIFs matched its captured image exactly after saving and reopening.
Each stage's capture sequence samples 64 consecutive native draw frames
and lateral camera movement. PNGs and GIFs are saved in the `v1.2` directory.

Hit, damage, distant boss/transition tests and capture starting states use
explicit RAM scenario setup; subsequent behavior and rendering execute in
the ROM. These are not represented as a complete controller-only playthrough.
`visual-scope-review-v1.2.json` records the independent review of preserved
gameplay, input, audio and atlas coordinates against v1.1. Sprite pixel data,
world artwork and the palette are deliberately redesigned for this release.
Verification and packaging derive release names from the build manifest,
check the ROM hash, and refuse a pre-v1.2 manifest before replacing evidence.
The v1.1 ROM, ZIP, reports and captures are preserved separately.

Physical MSX hardware and flash-cartridge writeback are untested. The build
and distribution omit machine BIOS files and emulator/tool executables.

## Running in openMSX

The included PowerShell launcher retains the previous launch behavior and
targets the new ROM filename. Version 1.2 uses
`NEON_REVENANT-v1.2.rom`. For direct
configuration, select a turbo R machine, put V9990/GFX9000 in Cart 1 and the
game ROM in Cart 2 with mapper ASCII8. Open the console with F10 and enter
`set videosource GFX9000`, then close the console with F10. The user supplies
the machine's existing system ROMs.

## Primary technical references

- [Yamaha V9990 application manual](https://map.grauw.nl/resources/video/yamaha_v9990.pdf)
- [openMSX V9990 command engine](https://github.com/openMSX/openMSX/blob/master/src/video/v9990/V9990CmdEngine.cc)
- [openMSX V9990 VRAM addressing](https://github.com/openMSX/openMSX/blob/master/src/video/v9990/V9990VRAM.hh)
- [MSXgl V9990 register definitions](https://github.com/aoineko-fr/MSXgl/blob/main/engine/src/v9990_reg.h)
- [Yamaha YM2413 application manual](https://map.grauw.nl/resources/sound/yamaha_ym2413.pdf)

The runtime driver and game are original code; MSXgl was used as a technical
reference and the source of a portable SDCC toolchain, not linked as a game
library. Standard SDCC arithmetic support routines are linked into the ROM.
Runtime source and license notices are included in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) and `licenses/sdcc-runtime/`.
Compiler provenance can also be retrieved with `python tools/download_sdcc.py`. Pasmo 0.5.4.beta2 assembled the bootstrap.
All game graphics, the logo and music were created for this game. No images,
music, characters, levels, BIOS files or game ROMs from Night Striker are included.

When present, `msx3-concept.png` and `msx3-concept-prompt.txt` are an ImageGen
art-direction reference and its generation prompt. The reference is not an
actual gameplay screenshot. Runtime indexed assets are generated separately
by the project tools. The `v1.2` native captures show the implemented result.
