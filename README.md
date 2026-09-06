# NEON REVENANT

**開発途中の実験的なプロトタイプです。無保証で公開しており、MSX実機・実カートリッジでの動作確認はしていません。** 動作確認はopenMSX上で行っています。利用前に[免責事項](DISCLAIMER.md)と[著作権・ライセンスの状態](COPYRIGHT.md)を確認してください。

夜のサイバー都市を疾走する、MSX用512 KiB ASCII8 MegaROMの疑似3Dシューティングです。『ナイトストライカー』に着想を得て、3区域・3ボス、連射とNOVAボムを実装しています。V9990版・turbo R単体版はMSX-MUSIC＋PSG、MSX2版・初代MSX版は標準PSGで音楽と効果音を鳴らします。本作はタイトーやMSX関連各社の公式作品ではありません。

「もしMSX3が存在したら」を出発点に、V9990から初代MSXまで、機種の制約に合わせた4種類のROMを公開しています。ゲームはMSX上のネイティブプログラムとして動きます。背景画像やパターンを開発時に生成し、実行時はMSXのVDPで表示・切り替え・合成します。

[試作版のダウンロード / Releases](https://github.com/kanon-ai/NEON_REVENANT/releases)

## ASTRAとMSXゲームを作るには

[制作ノウハウ：ASTRAとMSXゲームを作る — NEON REVENANT開発ノート](docs/ASTRA_MSX_GAMEDEV_JA.md)

機種とROM容量を指定する依頼から、背景の疾走感、素材の作り込み、turbo R・MSX2・初代MSXへの移植、openMSXでの検証までを紹介しています。再構成したプロンプト例と実装へのリンクを載せ、人間の方向づけとAIによる実装・修正をどう往復したかをまとめました。

## MSX2版・初代MSXチャレンジ版

| 項目 | MSX2 Edition v1.0 | MSX1 PCG Drive v1.1 |
| --- | --- | --- |
| CPU・RAM | 標準Z80 3.58MHz、RAM64KiB | 標準Z80 3.58MHz、RAM64KiB |
| VDP・VRAM | V9938、128KiB | TMS9918A系、16KiB |
| 表示 | SCREEN 4、256×192、512色から16色 | SCREEN 2、256×192、固定色 |
| 前進する背景 | turbo R単体版の8枚の背景を保持 | ROMからPCGを先読みし、面のある街・高架・トンネルを16位相で前進させる |
| 自機・敵 | 絵柄をVRAMへキャッシュして転送を削減 | 絵柄を常駐させ、1枚1色・走査線4枚のスプライト制限へ縮約 |
| 音源 | 標準PSGのみ。FM拡張不要 | 標準PSGのみ。FM拡張不要 |
| ROM | [MSX2版ROM](outputs/msx2/NEON_REVENANT-MSX2-v1.0.rom) | [初代MSX版ROM](outputs/msx1/v1.1/NEON_REVENANT-MSX1-v1.1.rom) |
| 起動・操作・性能・制限 | [MSX2版ガイド](msx2/README.md) | [初代MSX版ガイド](msx1/README.md) |

両版とも3区域・3ボス、キーボードとジョイスティック、ポーズ・再挑戦を収録しています。初代MSX版の対象は**RAM64KiB・VRAM16KiBの構成**です。描画速度と表示制約、試験条件は各ガイドに記録しています。

初代MSX版v1.1ではPCGの書き換えとネームテーブル2面を使い、立体的な背景へ強化しました。openMSXでの移動・連射は約25～27fps、背景は約12～13Hzです。v1.0も以前のリリースに残しています。

### MSX2版の実行画面

![MSX2版：openMSXでのROM実行映像](outputs/msx2/stage-1-native.gif)

### 初代MSX版の実行画面

![MSX1 PCG Drive：openMSXでのROM実行映像](outputs/msx1/v1.1/stage-1-native.gif)

## V9990版・turbo R単体版

| 項目 | V9990版 v1.2 | Turbo R単体版 v1.0 |
| --- | --- | --- |
| 必要なグラフィックス機器 | turbo R + V9990 / GFX9000 | turbo R内蔵V9958のみ |
| 表示 | B1、256×212、16色 | SCREEN 4、256×192、16色 |
| 色の選択範囲 | RGB5、32,768色 | RGB3、512色 |
| 区域ごとの前進背景 | 16フレーム、LZSS圧縮からVRAMへ展開 | 8フレーム、SCREEN 4ページをVRAMに保持 |
| 移動演出 | 前進背景と左右移動に追従するカメラの慣性 | 前進背景。背景の横揺れは省略 |
| openMSXでの更新速度 | 約30 fps（各区域29.96更新/秒） | 通常のゲーム・スプライト約30 fps、背景約15 fps |
| 負荷・表示上の制限 | 区域の展開中は数秒間、進行と音が停止 | 過密場面は約20 fps。スプライト集中時に部分欠落・ちらつき |
| ROM | [NEON_REVENANT-v1.2.rom](outputs/NEON_REVENANT-v1.2.rom) | [NEON_REVENANT-TurboR-v1.0.rom](outputs/turbor/NEON_REVENANT-TurboR-v1.0.rom) |
| 起動・ビルドの詳細 | [V9990版ガイド](outputs/README-ja.md) | [Turbo R単体版ガイド](turbor/README.md) |

いずれもROMは524,288バイトで、MSX-DOSは不要です。フレームレートはopenMSXのMSX側時間で測った更新速度であり、実機性能の保証ではありません。Turbo R単体版では、ボスを含む17枚のハードウェアスプライト使用時に29.96更新/秒、32枚を使う過密試験で19.97更新/秒でした。背景の横8×縦1ピクセルごとの最大2色、全画面32枚・走査線ごと最大8枚のスプライト制約があります。

### V9990版の実行画面

![V9990版：openMSXで撮影した市街地の実行映像](outputs/v1.2/stage-1-native.gif)

### Turbo R単体版の実行画面

![Turbo R単体版：openMSXで撮影した市街地の実行映像](outputs/turbor/stage-1-native.gif)

上のGIFはROMを実行したopenMSXの画面を撮影したものです。コンセプト画像やPC用の再現映像ではありません。

## openMSXで起動する

V9990版・turbo R単体版の確認済み機種設定は**Panasonic_FS-A1ST**、エミュレーターは**openMSX 21.0**です。MSX2版と初代MSX版の設定はそれぞれのガイドを参照してください。必要なBIOS・システムROMは利用者が用意してください。このリポジトリには同梱していません。

| 設定 | V9990版 | Turbo R単体版 |
| --- | --- | --- |
| Machine | `Panasonic_FS-A1ST` | `Panasonic_FS-A1ST` |
| Cart 1 | V9990 / GFX9000拡張（`gfx9000`） | `NEON_REVENANT-TurboR-v1.0.rom`、ASCII8 |
| Cart 2 | `NEON_REVENANT-v1.2.rom`、ASCII8 | 空 |
| V9990拡張 | 必要 | 追加しない |
| 映像ソース | `GFX9000` | `MSX` |

F10でコンソールを開き、使用する版に対応したコマンドを入力します。

```tcl
# V9990版
set videosource GFX9000
```

```tcl
# Turbo R単体版
set videosource MSX
```

F10でコンソールを閉じ、背景の準備が終わったらSpaceまたはトリガー1で開始します。Windows用の起動方法とツールの配置は、各版のガイドを参照してください。

## 操作

| 操作 | キーボード | ジョイスティックポート1 |
| --- | --- | --- |
| 自機・照準の移動 | カーソルキー | 十字方向 |
| ショット・開始・再挑戦 | Space | トリガー1 |
| NOVAボム | X | トリガー2 |
| ポーズ・再開 | Esc | キーボードのEsc |

ショットは押し続けると連射します。ボムは1回押すごとに1発使用します。敵を照準に捉えて撃ち、敵弾と接近する敵機を避けて、3区域のボスを突破してください。

## ビルドと検証

ビルドにはPython、Pillow、NumPy、Z80用SDCC、Pasmoを使います。PC側の素材生成ツールはゲーム実行時には不要です。手順と環境変数は[V9990版のビルド説明](outputs/README-ja.md#ソースからビルド)と[Turbo R単体版のビルド説明](turbor/README.md#ソースからビルドする)にあります。ツールや第三者由来のコードの条件は[第三者ソフトウェアの表示](THIRD_PARTY_NOTICES.md)を参照してください。

openMSX上で起動、操作、射撃、ボム、ポーズ、被弾、再挑戦、全3区域のボスと区域遷移、最終クリアを確認し、背景やスプライトのVRAM読み戻しも照合しています。後半区域や過密場面などはRAMに開始状態を設定した試験で、最初から最後までの手動プレイスルーではありません。

- V9990版：[動作検証](outputs/verification-v1.2.json)、[背景・速度の検証](outputs/world-verification-v1.2.json)
- Turbo R単体版：[動作検証](outputs/turbor/verification.json)、[背景検証](outputs/turbor/world-verification.json)、[スプライト・速度の検証](outputs/turbor/sprite-verification.json)
- MSX2版：[動作検証](outputs/msx2/verification.json)、[背景検証](outputs/msx2/world-verification.json)、[スプライト・速度の検証](outputs/msx2/sprite-verification.json)
- 初代MSX版：[動作検証](outputs/msx1/v1.1/verification.json)、[描画・速度の検証](outputs/msx1/v1.1/world-verification.json)

**実機、各種ROMローダー、フラッシュカートリッジへの書き込み後の動作は未検証です。** エミュレーターでの確認は、それらの互換性や安全性を保証しません。

## 配布パッケージの再作成

4版をビルドした後、リポジトリ直下で `python tools/package.py` を実行すると、全ROM・ソース・素材・開発ノート・検証結果・免責事項・第三者ライセンスをまとめた `outputs/NEON_REVENANT-public-prototype.zip` とSHA-256一覧を生成します。コンパイラー、エミュレーター、BIOSは同梱しません。

## 公開条件

公開者は **kanon-ai** です。本プロジェクト固有部分のライセンスは現時点で **UNSPECIFIED（未設定）** です。ソースを公開していますが、オープンソースライセンスに基づく公開ではありません。第三者のライセンス、GitHub上での扱いを含め、[COPYRIGHT.md](COPYRIGHT.md)と[DISCLAIMER.md](DISCLAIMER.md)を確認してください。

## English summary

NEON REVENANT is an experimental, native MSX pseudo-3D rail shooter with three stages and three bosses. Four 512 KiB ASCII8 ROM editions are available: V9990/GFX9000 v1.2, Turbo R v1.0 using V9958, MSX2 v1.0 using V9938, and MSX1 PCG Drive v1.1 using the TMS9918A family. MSX2 and MSX1 use standard PSG music and effects without an FM expansion. They target 64 KiB RAM; MSX2 requires 128 KiB VRAM and MSX1 requires 16 KiB VRAM. See their guides for measured performance and limitations.

The V9990 edition measured about 30 updates/s in openMSX. The Turbo R edition normally updates gameplay and sprites at about 30/s and backgrounds at about 15/s; a crowded test dropped to about 20/s. Sprite overlap can cause missing parts and flicker. **Physical hardware has not been tested. This prototype is provided AS IS, without warranty. Its project-specific license is currently unspecified; public source availability is not an open-source license grant.** See [DISCLAIMER.md](DISCLAIMER.md), [COPYRIGHT.md](COPYRIGHT.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
