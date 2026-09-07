# NEON REVENANT — MSX1 v1.3: Dawn Leviathan

**夜明けを塞ぐ巨大戦艦 / The giant battleship blocking the dawn**

最終区域 **DAWN EXODUS** のボスを、画面の大部分を占める巨大戦艦に変更しました。左右の砲台をそれぞれ破壊すると中央装甲が開き、露出したコアを攻撃できます。船体は左右・上下へ8ドット単位で移動し、砲身は独立して2ドット反動、コアは明滅します。橋の流れを残し、小さな自機との大きさの対比を狙っています。

最初の4区域と最終区域の通常道中はv1.2の構成・戦闘を維持しています。v1.2の有難うエディションから続く、初代MSX用の追加チャレンジです。

**開発途中・無保証の試作版です。v1.3は実機MSX・実フラッシュカートリッジでは未検証です。** [免責事項](../DISCLAIMER.md)、[著作権](../COPYRIGHT.md)、[第三者ライセンス](../THIRD_PARTY_NOTICES.md)を確認してください。

## 起動と操作

| 項目 | 条件 |
|---|---|
| ROM | [NEON_REVENANT-MSX1-v1.3.rom](../outputs/msx1/v1.3/NEON_REVENANT-MSX1-v1.3.rom)、524,288バイト、ASCII8 |
| RAM | 32KiB以上。8000h–FFFFhに同一RAMスロットのRAMが必要 |
| VDP | TMS9918A/TMS9929A系、VRAM16KiB、SCREEN 2 |
| 音源 | 本体標準PSG |
| 操作 | 矢印／ジョイスティック1：移動、Space／トリガー1：発射、X／トリガー2：NOVA、Esc：一時停止 |

RAM16KiB機は対象外です。V9990、追加PCGカートリッジ、FM音源、MSX-DOSは不要です。エミュレーターのROM形式は **ASCII8**、映像ソースは **MSX** を選びます。タイトル画面で発射ボタンを押すとEpisode 0から開始し、5番目の区域の最後に巨大戦艦が出現します。

```powershell
openmsx -machine C-BIOS_MSX1_JP -cart NEON_REVENANT-MSX1-v1.3.rom -romtype ASCII8
```

Windows用の[起動補助](../outputs/msx1/v1.3/launch-openmsx.ps1)も同梱しています。必要なら `-OpenMSXPath 'C:/path/to/openmsx.exe'` を指定します。エミュレーター、BIOS、外部コンパイラーの実行ファイルは同梱していません。

## 表現と検証

ROM実行から撮影した [船体・砲台の動作GIF](../outputs/msx1/v1.3/ntsc/giant-native.gif) と [破壊状態の比較GIF](../outputs/msx1/v1.3/ntsc/giant-damage-states-native.gif) を同梱しています。前者は連続フレーム、後者は検証用に4状態を設定して撮影した比較映像です。/ Included native ROM captures show continuous hull motion and a separate montage of four seeded damage states.

船体はPCG背景、弱点表示・弾・自機はスプライトを使います。固定パレットの黒と青のディザで装甲を暗くし、暖色の夜明けと分離しました。8ドット移動ではPCGの配置を変えて船体を再利用し、破壊状態用の小さなPCGをVRAMに常駐させます。16位相の背景と4段階の損傷状態を組み合わせる構成です。

検証結果は [v1.3出力ディレクトリ](../outputs/msx1/v1.3/) のJSONに記録します。NTSC/PALの `verification.json`、`world-verification.json`、`transfer-verification.json`、`giant-verification.json` はROM実行の検証です。`layout-verification.json` はROM配置とPCG状態遷移、`sound-verification.json` はホスト上のPSGレジスター処理、`giant-preservation-verification.json` はv1.2とのC処理比較、`reproducibility.json` は再ビルドの一致を扱います。試験ごとの条件・対象ROMのハッシュ・個別結果を確認してください。

巨大ボス専用のROM実行試験はNTSC/PALとも69項目に合格しました。砲台段階を約3秒間動かした測定では、更新速度はNTSC約29.96回/秒、PAL約25.07回/秒です。4損傷状態×16位相のVRAM読み戻し、実入力による攻撃・ポーズ・撃破・再挑戦、VRAM転送タイミングを確認しています。/ The giant-specific suite passes 69 checks on each video standard. A roughly three-second free-running cannon-phase sample measures 29.96 updates/s NTSC and 25.07 updates/s PAL. These are game updates, not new PCG poses; PCG phases advance every two updates.

RAMや時計を設定して特定場面を再現する試験は、通常入力だけによる全編プレイとは区別します。ホストCの比較はZ80の演算時間やVDPタイミングを証明せず、エミュレーターの検証も実機確認とは区別します。

## English

Version 1.3 replaces the final **DAWN EXODUS** boss with a giant PCG battleship. Destroy both cannon pods, wait for the central armour to open, then attack the exposed reactor. The hull shifts horizontally and vertically in 8-pixel steps; individual barrels recoil by 2 pixels and the open reactor pulses. The moving bridge and small player craft establish its scale. The first four zones and ordinary play before the final boss retain the v1.2 campaign and combat behavior.

Requirements: **512 KiB ASCII8 ROM, at least 32 KiB RAM covering 8000h–FFFFh in one RAM slot, a TMS9918A/TMS9929A-family VDP with 16 KiB VRAM, and the standard PSG.** A 16 KiB RAM machine is insufficient. No V9990, additional PCG cartridge, FM sound or MSX-DOS is needed. Select ASCII8 and the MSX video source in your emulator.

Controls: arrow keys or joystick 1 to move, Space/trigger 1 to fire, X/trigger 2 for NOVA, Esc to pause. Start at the title screen and reach the end of the fifth zone to encounter the battleship. The command and Windows launcher above use the current v1.3 ROM.

The hull uses background PCGs, with sprites for the player, projectiles and weak-point indicators. Dark blue/black dithering separates the armour from the warm dawn. Tile-aligned hull movement reuses PCGs through their screen placement; small permanent damage tiles provide four damage states over the sixteen animation phases.

**This is a work-in-progress prototype, provided without warranty. Version 1.3 has not been tested on physical MSX hardware or flash cartridges.** See the [disclaimer](../DISCLAIMER.md), [copyright terms](../COPYRIGHT.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

Recorded JSON results in [outputs/msx1/v1.3](../outputs/msx1/v1.3/) distinguish native NTSC/PAL ROM execution from host-side C/audio checks and binary layout/rebuild verification. Read each report's ROM hash, individual results and scenario limits. Seeded emulator scenarios are not a full input-only playthrough; host C checks do not establish Z80 or VDP timing, and emulator results do not replace physical-hardware validation.

## Build and reproduce / ビルドと再検証

Python 3、Pillow、NumPy、Z80版SDCC、Pasmoが必要です。以下は展開したパッケージのルートから実行します。/ Install Python 3, Pillow, NumPy, Z80 SDCC and Pasmo; run from the extracted package root:

```powershell
python -m pip install -r msx1/requirements.txt
$env:SDCC_BIN = 'C:/path/to/sdcc/bin'
$env:PASMO = 'C:/path/to/pasmo.exe'
python msx1/tools/build.py
python msx1/tools/verify_layout.py
$env:CC = 'C:/path/to/gcc.exe'
python msx1/tools/verify_sound.py
```

出力先は `outputs/msx1/v1.3/` です。`--pack-only` は素材生成を省略し、現行C/ASMとROM配置を再ビルドします。/ Output goes to `outputs/msx1/v1.3/`. `--pack-only` skips artwork generation but still rebuilds the current C/ASM and ROM placement.

v1.2との比較用にソースとハッシュ表を `msx1/tests/baseline-v1.2/`、旧ROMを `outputs/msx1/v1.2/` に同梱します。旧ROMは比較用で、通常プレイにはv1.3を使用してください。ハッシュ表のパスはパッケージルートからの相対パスです。タイトルの版表記変更だけを明示的に除外して検証します。/ The included v1.2 source, portable hash registry and older ROM allow preservation checks without downloading another repository. The older ROM is a comparison baseline; use v1.3 to play. Registry paths are relative to the package root. The title's version-label change is explicitly exempted.

```powershell
python msx1/tools/verify_giant_preservation.py --baseline msx1/tests/baseline-v1.2/baseline-game-v1.2.c --registry msx1/tests/baseline-v1.2/baseline-hashes.json --allow-changed-asset title.bin --gcc C:/path/to/gcc.exe --giant-checks --self-test --report outputs/msx1/v1.3/giant-preservation-verification.json
```

配布済み報告書の元ハッシュ表は開発環境の絶対パスを含んでいたため、同梱表はパスのみ移植可能な形に変更しています。個々のファイルのSHA-256とサイズは保持します。/ The packaged registry rewrites only development-machine paths; individual file hashes and sizes are preserved. Its own JSON hash therefore differs from the original registry hash recorded during development.

配布パッケージ作成は `python msx1/tools/package.py`。対象ROMと一致するNTSC/PALの4種のROM実行報告、および配置・音声・互換性・再現性の合格報告が揃わない場合は停止します。/ `python msx1/tools/package.py` refuses to package until the four NTSC/PAL native reports match the ROM and all required layout, sound, preservation and rebuild checks pass.

v1.2の記録： [日本語](README.md) / [English](README-en.md)。/ The linked v1.2 guides are historical records; use this guide for v1.3.
