# NEON REVENANT — V9990 Feature Lab v0.1

V9990固有の描画機能と512 KiB ROMの容量活用を試す、独立した試験版です。下位機種への移植を前提にせず、通常の全3ステージに専用演出を加えています。既存の安定版は別に保護しています。

An independent experimental edition exploring V9990 drawing features and efficient use of a 512 KiB ROM. It adds dedicated effects to the normal three-stage game without targeting lower hardware. The existing stable edition is preserved separately.

## 起動 / Setup

- **MSX turbo R + V9990/GFX9000、512 KiB ASCII8 ROM。** 起動時にR800 DRAM高速モードを選択します。エミュレーターではCart 1にV9990/GFX9000、Cart 2にゲームROMを設定してください。
- **MSX turbo R + V9990/GFX9000, 512 KiB ASCII8 ROM.** Startup selects R800 DRAM mode. In an emulator, use Cart 1 for V9990/GFX9000 and Cart 2 for the game ROM.
- ROM: [NEON_REVENANT-V9990-FeatureLab-v0.1.rom](outputs/NEON_REVENANT-V9990-FeatureLab-v0.1.rom)

## 操作 / Controls

| 入力 / Input | 動作 / Action |
| --- | --- |
| 矢印キー / Arrow keys・Joystick 1 | 移動 / Move |
| Space・Joystick trigger 1 | Fire、開始 / Fire, start |
| X・Joystick trigger 2 | NOVA |
| Esc | 一時停止・再開 / Pause, resume |
| Tab | 試験演出の切り替え / Toggle experimental effects |
| タイトルで上＋Fire / Up + Fire at the title | ステージ3のボス戦から開始 / Start at the stage 3 boss |

Tabで切り替わるのは背景バンド変形、投影ゲート、パレット演出、ネイティブ照準です。ステージ3の巨大ボスと戦闘処理は切り替わりません。演出OFFでも、この試験版のままです。

Tab toggles background band distortion, projected gates, palette effects, and the native cursor reticle. The giant stage 3 boss and combat logic remain active in either setting. Effects OFF still runs this experimental edition.

## 試験内容 / Experiments

- **背景 / Background:** B1 256×212・4bppを維持。各ステージの既存16背景位相を使い、10本の帯をLMMMで位置を変えてコピーします。 / Retains B1 256×212 at 4bpp and the existing 16 background phases per stage, copying ten bands with different offsets through LMMM.
- **投影ゲート / Projected gates:** ステージ2に接近する2つのエネルギーゲートをLINEで描画。見た目のみで、衝突する壁ではありません。 / Two approaching energy gates in stage 2 are drawn with LINE. They are visual scenery with no collision walls.
- **ネイティブ照準 / Native reticle:** 2枚の32×32ハードウェアカーソルを組み合わせ、属性を画面切り替え時のVBlankで反映します。 / Combines two native 32×32 hardware cursors, publishing their attributes at VBlank with the framebuffer change.
- **環境色 / Environment colors:** RGB5の16色パレットを4バンク用意し、フレーム単位で選択します。パレットは共有されるため、同じ色番号の背景・物体・HUDも影響を受けます。カーソルの固定色61–63も第4バンクの一部です。 / Selects among four 16-color RGB5 banks per frame. Palette storage is shared: backgrounds, objects, and HUD using those indices change together. Fixed cursor colors 61–63 also belong to the fourth bank.
- **巨大ボス / Giant boss:** ステージ3に複数パーツが動く大型ボスを追加しています。 / Adds a large stage 3 boss with moving component parts.

帯の位置と投影座標はソフトウェアで計算します。LRMMや任意角度のハードウェア回転は使用していません。

Band offsets and projected coordinates are calculated in software. This edition uses neither LRMM nor arbitrary-angle hardware rotation.

## ROM容量 / ROM packing

既存LZSS形式で画像を可逆圧縮し、展開後の背景位相や画像データを保持します。以下は[ビルド記録](outputs/build-manifest.json)の値です。

Assets use the existing lossless LZSS format, preserving the decoded images and background phases. Figures below come from the [build manifest](outputs/build-manifest.json).

| 項目 / Item | 元データ / Raw | ROM内 / Packed |
| --- | ---: | ---: |
| 既存アトラス / Existing atlas | 81,920 bytes | 16,054 bytes |
| 追加画像 / Feature assets | 8,192 bytes | 2,674 bytes |

512 KiB ROMの空き領域は**136,079 bytes**です。 / Unallocated space in the 512 KiB ROM: **136,079 bytes**.

## ビルド / Build

Python 3、Pillow、NumPy、SDCC、Pasmoが必要です。このディレクトリで実行してください。SDCC/Pasmoの場所は`SDCC_BIN`、`SDCC`、`PASMO`で指定できます。

Requires Python 3, Pillow, NumPy, SDCC, and Pasmo. Run from this directory. Tool locations can be set through `SDCC_BIN`, `SDCC`, and `PASMO`.

```sh
python tools/build.py
```

生成済み画像を再利用する場合は`python tools/build.py --pack-only`を使用します。この場合も現在のソースをコンパイルしてROMを作成します。

Use `python tools/build.py --pack-only` to reuse generated assets; it still compiles the current source and builds the ROM.

開発用検証にはNode.js、openMSX、ローカル制御ブリッジを使用します。BIOSは各自で用意してください。エミュレーター本体やBIOSは同梱しません。

Developer checks use Node.js, openMSX, and a local control bridge. Supply your own BIOS files. Emulator binaries and BIOS files are not included.

## 状態・参考資料 / Status and references

openMSXで63項目を確認し、追加ボスは約30更新/秒、ゲート区間は約29更新/秒でした。[検証記録と実動作GIF](VALIDATION.md)を参照してください。試作版であり、動作・性能は保証しません。実機では未確認です。個人制作の非公式ソフトウェアであり、ハードウェアメーカーやエミュレータープロジェクトとの公式な提携・承認を示すものではありません。

63 checks passed in openMSX. The added boss measured about 30 updates/second and the gate scene about 29. See [validation and native GIFs](VALIDATION.md). This is a prototype with no guarantee of operation or performance. Physical hardware has not been tested. This independently developed, unofficial software does not imply affiliation with or endorsement by hardware manufacturers or emulator projects.

- [Yamaha V9990 application manual](https://map.grauw.nl/resources/video/yamaha_v9990.pdf)
- [openMSX V9990 bitmap and cursor renderer — source snapshot](https://github.com/openMSX/openMSX/blob/25179d6b8d5ec69ad68252f3854721c9a02594eb/src/video/v9990/V9990BitmapConverter.cc)
