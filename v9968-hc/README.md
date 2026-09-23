# NEON REVENANT HC v1.2 — V9968 Edition

**V9968の現行レジスタ仕様に対応しました。** HCはHard Coreの略です。全5区域の夜景と、敵の出現・接近・射撃を調整した戦闘をお楽しみいただけます。既存の他機種版は変更していません。

**v1.2の更新は内蔵98h版の描画最適化です。** 元の絵柄・全5区域・敵パターン・音楽・背景の全16位相を維持しています。画像を画素単位で保持したまま詰め直し、背景57行×16位相の常駐、差分転送の短縮、HUDと見出しの再利用を組み合わせました。フレーム間引きや敵の削減は行っていません。外付け88h版のROMはv1.1と同一です。

エミュレータの検証や実機開発にもご利用いただけるよう、接続方式別のROMとソースを収録しました。V9968と各エミュレータの開発・保守に携わる皆様に感謝します。

## ダウンロードと確認環境

[ROM・ソース一式／v1.2リリース](https://github.com/kanon-ai/NEON_REVENANT/releases/tag/hc-v9968-v1.2)

| ROM | 接続方式 | 確認環境 |
|---|---|---|
| [INTERNAL.rom](outputs/NEON_REVENANT-HC-V9968-INTERNAL.rom) | 内蔵VDP・98h系 | V9968対応blueMSX Plus |
| [V9968.rom](outputs/NEON_REVENANT-HC-V9968.rom) | 外付けカートリッジ想定・88h系 | 現行仕様向け暫定openMSXローカルビルド |

両版とも **MSX turbo R（R800）／2 MiB ASCII8／V9968 VRAM 256KB** 向けです。R#21=3Ah（V58=0）、R#20=11hを使用します。接続方式に合うROMを選んでください。

**内蔵98h版は、2026年9月23日時点ではblueMSX Plusで確認しています。実行にはV9968対応のblueMSX Plusをご使用ください。** 外付け88h版は、上記の暫定openMSXで確認した開発・検証用候補です。通常配布ビルドでの確認を意味しません。暫定エミュレータは同梱しません。

**旧バージョンのゲームは、V9968対応openMSXの互換モードで動作可能です。** [旧版v1.0](https://github.com/kanon-ai/NEON_REVENANT/releases/tag/hc-v9968-v1.0)も引き続き利用できます。

## 起動

### 内蔵98h版：blueMSX Plus

検証には[blueMSX Plus](https://github.com/Hesoten/blueMSX-plus)の `experimental/v9968`、コミット `7f7a2572604dcd3dc82ba4cc7a8b7f6c9b3a9d92` のビルドを使用しました。

1. ご自身のBIOSを使ったTurbo R機種設定を用意します。
2. 機種設定の `[Video]` を `version=V9968`、`vram size=256kB` にします。
3. INTERNAL ROMをASCII8で読み込みます。速度とVDPコマンド速度は100%を使用します。

`run-v9968-hc-bluemsx.cmd`も利用できます。`BLUEMSX_EXE`に対応実行ファイル、`BLUEMSX_MACHINE`に用意した機種設定名を指定してください。既定の機種名は `NEON-V9968-TEST` です。エミュレータやBIOSは同梱していません。

### 外付け88h版：暫定openMSX

確認した暫定ビルドは、buppu3/openMSXの `1d0ac55757dd4477bdf48c017a12ee1071fc82c7` を基にしたローカル版です。exeのSHA-256は `3877c51210dd91fcc39d61b0ccb322ad46d782a4dd840c557d0a4b96db3eff41` です。

この環境を用意した場合は、`OPENMSX_EXE`を実行ファイル、`OPENMSX_SYSTEM_DATA`をshareディレクトリへ設定し、`run-v9968-hc.cmd`を実行します。Panasonic_FS-A1ST用BIOSは利用者側で準備してください。同梱の `HRA_V9968_CURRENT.xml` は外付け88h系・現行V9968設定です。

## 操作

矢印キー／ジョイスティック：移動、SPACE／トリガー1：開始・射撃、X／トリガー2：NOVA、ESC：一時停止・再開。タイトルで上＋射撃は最終ボスの確認用です。

## ビルドと確認範囲

Python 3、SDCC 4.6.0 #16555（Z80）、Pasmoを用意します。`SDCC_BIN`にSDCCのbinフォルダー、`PASMO`にPasmo実行ファイルを指定し、`newbuild.cmd`で両版を生成できます。

```text
python tools/build.py --target=external
python tools/build.py --target=internal
```

内蔵版では起動・タイトル表示、専用診断によるID切り替え、256KB内の8領域の読み書き、上位VRAMコピー、5区域各96フレームのゲーム更新・描画を確認しました。外付け版は起動、背景全5区域×16位相のVRAM照合と操作シナリオで確認しています。診断や場面設定を使った確認を含み、手操作での全編クリアや実機確認を意味しません。通常ROMに診断用自動操作は含めていません。

v1.2内蔵版はblueMSX Plusで起動・タイトル表示と計測用ゲームシナリオを確認しました。別途、混戦・各面ボス・タイトル・一時停止・クリア等の2,080更新／場面について、最適化前後の画面の画素一致を確認しています。開始・移動・射撃・NOVA・一時停止／再開と音楽更新周期も確認しました。これらは診断・場面設定を含む検証であり、手操作での全編クリアや実機検証ではありません。

追加確認：2026年9月23日に更新されたopenMSXでも、内蔵98h版の起動・操作・音楽更新と全5区域を含む160場面の画素一致を確認しました（実行ファイルSHA-256：`0528593dc9c71f40dcca00193c1b3ea8d745b833c3c7c0fd38cebc651ef1a62d`）。実行案内は引き続きblueMSX Plusを基本とします。

配布ソースからの再ビルドとROMの一致を確認しています。[SHA256SUMS.txt](SHA256SUMS.txt)を参照してください。`game-internal.c` / `hardware-internal.c` / `world_load-internal.c` は内蔵用です。`tools/pack_internal.py` は元の画像から内蔵用配置を生成し、全スプライトの画素一致を検査します。

**試作版・無保証。実機・現行FPGAでの動作は未検証です。修正や継続サポートは保証しません。** [免責事項](DISCLAIMER.md)・[利用条件](COPYRIGHT.md)・[第三者ライセンス](THIRD_PARTY_NOTICES.md)

## English

NEON REVENANT HC v1.2 optimizes internal-98h rendering through lossless sprite packing, a larger background cache, shorter transfers and cached HUD/banner rendering. Artwork, all 16 background phases, music and combat rules are preserved. The external ROM is byte-identical to v1.1. Other editions are unchanged. Two 2 MiB ASCII8 ROMs are provided for turbo R/R800 with 256KB V9968 VRAM:

- **INTERNAL.rom:** internal VDP at 98h. As of September 23, 2026, this edition has been validated with V9968-enabled blueMSX Plus. Please use that emulator to run it. Tested source: experimental/v9968 at `7f7a2572604dcd3dc82ba4cc7a8b7f6c9b3a9d92`.
- **V9968.rom:** external cartridge configuration at 88h, a development/testing candidate checked with the provisional local openMSX build identified above. This is not a claim of validation with a standard distributed emulator build.

Earlier releases can be played using compatibility mode in V9968-enabled openMSX. The v1.0 release remains available. Emulator executables and BIOS files are not included. Thanks to the V9968 and emulator developers and maintainers.

Use your own turbo R BIOS and V9968 machine profile. The internal launcher accepts BLUEMSX_EXE and BLUEMSX_MACHINE; the external launcher requires OPENMSX_EXE and the appropriate system-data directory. Build either target using the commands above with Python 3, SDCC and Pasmo.

Arrows/joystick: move; SPACE/trigger 1: start/fire; X/trigger 2: NOVA; ESC: pause/resume. Up+fire at the title starts the final-boss test.

Checks include dedicated diagnostics and scripted scenarios, not a complete manual playthrough. Physical hardware/current FPGA are untested. Experimental, AS IS, WITHOUT WARRANTY; fixes and continuing support are not guaranteed.

Additional check: the September 23 updated openMSX executable (SHA-256 above) passed internal-edition controls, music update cadence and 160 pixel-matched scenes spanning all five sectors. The primary execution guide remains blueMSX Plus.
