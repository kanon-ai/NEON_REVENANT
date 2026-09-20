# NEON REVENANT — Final campaign

2026-09-20 / 本作の基本的な機能開発を締めくくる最終リリースです。試作ソフトとしての無保証・サポート非保証の扱いは継続します。

## 収録ROM

| 機種 | ROM容量 | 内容 |
|---|---:|---|
| MSX Turbo R + V9990 | 1 MiB | 5面、編隊・交差・急降下など6種の移動、段階的な攻撃増加、可動巨大ボス、発光ゲート |
| MSX Turbo R単体 | 512 KiB | 5面、8コマ常駐PCG背景、追加敵パターンと段階的な難易度 |
| MSX2 | 512 KiB | 5面、8コマ常駐PCG背景、追加敵パターンと段階的な難易度。RAM 64 KiB、VRAM 128 KiB |
| MSX初代 | 512 KiB | 5面、16コマPCG背景、可動巨大ボス。RAM 32 KiB、VRAM 16 KiB |

全ROMはASCII8です。V9990版は1 MiBのASCII8に対応するローダー／カートリッジが必要です。
openMSXではTurbo Rを選び、V9990/GFX9000をCart.1、ROMをCart.2に設定してください。
他の3版はV9990不要です。MSX1の32 KiBは8000h–FFFFhが同一RAMスロットにある構成です。

操作：方向キー／ジョイスティック、SPACE／トリガー1で射撃、X／トリガー2でNOVA、ESCで一時停止。
V9990版のみTABで追加エフェクト切替、タイトルで上＋射撃を押すと最終ボステストへ進みます。

## 更新内容

「00 BREAKWATER APPROACH」から始まり、「01 CHROME DISTRICT」「02 SKYWAY ASSAULT」「03 THE BLACK SPIRE」を経て「04 DAWN EXODUS」へ進みます。
従来3面の背景を保ち、湾岸の橋と港湾施設、夜明けの橋梁を追加・更新しました。MSX1の既存中間3面は採用済みの描画を維持しています。

V9990の既存3面は青灰色・シアン・オレンジの基本パレットを維持します。機能試験版にあった通常時の周期的な色調切替は外し、夜明けの別パレットは最終面に限定しました。NOVAの短いフラッシュは残しています。

4機種とも数字・英字のフォントを低めの角張った独自字形へ更新し、白とシアンの濃淡を付けました。PCG版の残機・NOVA記号も変更しています。字送り、文字用PCG枠、転送量は従来どおりです。

MSX2とTurbo R単体は5面分の背景をROM内で可逆圧縮し、ステージ開始時に展開します。表示コマ数を減らす圧縮ではありません。展開中は画面が消え、MSX2では約9～10秒、Turbo R単体では約2～3秒待ちます。これは本版の制限です。
MSX2・Turbo R単体の最終ボスは通常のスプライト方式です。V9990・MSX1と同じ巨大ボス画面ではありません。

## 検証と確認範囲

同梱verificationに、実行したROMのSHA-256と検証結果があります。
V9990 / MSX2 / Turbo RはopenMSXで全5面の背景データ、敵パターン、ボス出現・撃破後の遷移、クリア、再開、移動、NOVA、一時停止、音声クロックを確認しました。
MSX1はNTSC/PALの32 KiB RAM制限で、全5面の16位相PCGを実VRAMから照合し、音声、一時停止、巨大ボスの動きを確認しました。

ステージ・ボスの検証はRAMで場面を設定して実行しています。手操作による全編通しプレイや難易度の楽しさを保証する検証ではありません。
この最終版は実機では未確認です。過去版への実機動作報告とは区別しています。実機での動作・見た目・操作感は、利用する構成でご確認ください。

## ソースからの再ビルド

別添source ZIPは元プロジェクトを上書きせず展開できます。Python 3、NumPy、Pillow、SDCC、Pasmoを別途用意してください。BIOS・コンパイラ・エミュレータは同梱していません。
Windows PowerShellで`PYTHONUTF8=1`、`SDCC_BIN`、`PASMO`の環境変数を設定し、対象フォルダの`tools/build.py --pack-only`をPythonで実行してください。収録済みの画像バイナリからROMを再構築できます。4 ROMとも再ビルド時のSHA-256一致を確認しました。

新キャンペーンの検証入口は`v9990-1mb/tools/verify_campaign.py`、`final-campaign/tools/verify_pcg.py msx2`（またはturbor）、`final-campaign/tools/verify_msx1.py ntsc`（またはpal）です。openMSXの場所・機種定義は環境に合わせて設定してください。その他の継承ツールは旧版用のパス・条件を含む場合があります。

## English

Final feature release: five stages on all four targets. V9990 uses a 1 MiB ASCII8 ROM; the three PCG editions remain 512 KiB. The original middle-stage artwork is preserved, with a new coastal approach and dawn finale. The V9990 city retains its original blue-grey palette. A compact custom font and cyan/white text shading are included.
MSX2 and standalone Turbo R decompress each stage before play; loading takes approximately 9–10 seconds / 2–3 seconds respectively. Their bosses use ordinary sprites, not the giant artwork of the V9990 and MSX1 editions.
Tests use native openMSX with RAM-seeded scenarios, not a complete manual playthrough. These final ROMs have not been validated on physical hardware. Experimental, AS IS, WITHOUT WARRANTY. Maintenance and bug-fix support are not promised. See DISCLAIMER.md and COPYRIGHT.md.
