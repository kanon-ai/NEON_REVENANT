# MSX1 v1.4 — PSG・タイトル・戦闘の改良

**開発途中の試作版・無保証です。v1.4 の開発側の実機確認は未実施です。**
[免責事項](../DISCLAIMER.md)が適用されます。修正・サポートの可否や時期は保証しません。

## ダウンロードと動作環境

[ROM](../outputs/msx1/v1.4/NEON_REVENANT-MSX1-v1.4.rom) ·
[検証記録](../outputs/msx1/v1.4/VALIDATION.md)

MSX初代、RAM 32 KiB以上、VRAM 16 KiB、標準PSG。512 KiB ASCII8 MegaROMです。
V9990・V9968・FM音源・MSX-DOSは不要です。マッパーを指定する場合は ASCII8 を選びます。

## 変更内容

- PSG を VBlank 割り込みから更新し、描画負荷で音楽の速度が変わる問題を改善。
- 専用タイトル画面と大きなロゴを追加。
- 蛇行・横切り・上下回り込みの敵進入、後半の重い敵の拡散攻撃を追加。
- 0面と中間3面の背景・陰影を維持。最終面は夜明けの色面を調整。
- 全5区域、巨大最終ボス、512 KiB ROM / 32 KiB RAMを維持。

旧v1.3のROMとリリースは残しています。

## 操作

SPACE / トリガー1：開始・ショット。カーソル / ジョイスティック：移動。
X / トリガー2：NOVA。ESC：ポーズ・再開。

## ビルド

Python 3、requirements.txt の NumPy/Pillow、SDCC、Pasmo を使用します。
`SDCC_BIN` に SDCC の bin ディレクトリ、`PASMO` に Pasmo の実行ファイルを設定します。
リポジトリ直下で `python msx1/tools/build.py --pack-only` を実行すると、同梱済みの
PCG素材からソースを再コンパイルしROMを生成します。`--pack-only` を省くと素材も生成します。
`python msx1/tools/package_v14.py` でROM・ソース・検証記録入りZIPを作成できます。
生成先は `outputs/msx1/v1.4` です。BIOS、コンパイラ、エミュレーターは同梱しません。

## English

MSX1 v1.4 adds VBlank-driven PSG
scheduling, a dedicated title screen, additional enemy motion and attacks,
and revised dawn colors. Five stages and the giant final boss remain.
Requires 32 KiB RAM, 16 KiB VRAM and a 512 KiB ASCII8 cartridge/loader.

Validation is on openMSX NTSC with a standard Z80 and sprite limits enabled.
Tests include seeded RAM scenarios, not a manual-only playthrough. Physical
hardware and PAL runtime are not newly verified for v1.4. The previous release's
PAL and community hardware reports do not establish v1.4 compatibility.
Experimental prototype, AS IS, WITHOUT WARRANTY; future support is not guaranteed.
