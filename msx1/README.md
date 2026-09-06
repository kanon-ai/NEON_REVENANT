# NEON REVENANT — MSX1 Challenge v1.0

初代MSXの **Z80 3.58 MHz / TMS9918系VDP / VRAM 16 KB** で、夜のサイバー都市を駆ける疑似3Dシューティングに挑戦した独立版です。V9990版、turbo R単体版、MSX2版のROMとソースは変更していません。

**開発中の試作版です。無保証（AS IS / WITHOUT WARRANTY）で提供します。実機は未検証です。** 動作確認はopenMSX上で行っています。BIOSや他社ゲームのROMは同梱しません。ナイトストライカーに着想を得た独自の試作であり、TAITOその他の権利者の公式作品ではありません。

![初代MSXで実行した画面](../outputs/msx1/stage-1-native.gif)

このGIFはC-BIOS MSX1 JPでROMを実行して採取した64フレームです。速度はエミュレートされた時間から設定しています。PCで作った参考画像の再生ではありません。

## 何を再現できたか

- 3区域・3ボス、照準に合わせる連射、敵弾回避、シールド、NOVAボム、スコア、回復アイテム、ポーズ、ゲームオーバー／再挑戦、全区域クリア。
- 道路の帯が手前に迫り、側壁の灯りとビルの窓も動く8位相の背景。初代用に固定色の青い面、シアン／紫／赤の輪郭を組み合わせました。
- 元の機体・敵・ボスの形を縮約したハードウェアスプライト。自機はシアンと白、敵は種類別の1色、ボスは最大6枚で構成します。
- 標準PSGの3音で原曲の旋律・ベース・アルペジオを再構成。効果音時は第3音を一時的に共有します。FM音源は不要です。

SCREEN 2の固定パターン辞書に全アニメ位相のタイルを登録し、通常の背景更新では **640バイトのネームテーブルだけ** を送ります。スプライトの55パターンもVRAMへ常駐させ、毎フレームの画像転送をなくしました。高速CPUや拡張VDPを仮定せず、TMS9918のVRAM転送間隔も確保しています。

## 必要環境と起動

| 項目 | 条件 |
|---|---|
| 対象 | 初代MSX、Z80 3.58 MHz、RAM 64 KB |
| VDP | TMS9918A / TMS9928A / TMS9929A系、VRAM 16 KB |
| 画面 | SCREEN 2、256×192、固定15色＋透明 |
| カートリッジ | ASCII8、512 KiB MegaROM |
| 音源 | 標準PSGのみ |
| 検証機種 | openMSX `C-BIOS_MSX1_JP`、TMS99X8A、60 Hz |

配布先は `outputs/msx1/NEON_REVENANT-MSX1-v1.0.rom` です。openMSXでは機種に **C-BIOS MSX1 JP**、ROM種別に **ASCII8** を指定してください。V9990等の拡張は必要ありません。拡張VDPではなくMSX本体側の映像を表示します。

```powershell
openmsx -machine C-BIOS_MSX1_JP -cart NEON_REVENANT-MSX1-v1.0.rom -romtype ASCII8
```

ROMと同じフォルダの `launch-openmsx.ps1` でも起動できます。16 KB RAMのみの初代MSXは対象外です。PAL／50 Hz機は同系統の描画機能を備えますが、この版のテンポと操作速度は60 Hz環境で評価しており、PALの実行検証は行っていません。

## 操作

| キーボード | ジョイスティック1 | 動作 |
|---|---|---|
| カーソルキー | 方向 | 自機移動／照準位置の調整 |
| SPACE | トリガー1 | 開始・連射・再挑戦 |
| X | トリガー2 | NOVAボム（押した瞬間に1個使用） |
| ESC | — | ポーズ／再開 |

照準を敵やボスに重ねて撃ちます。連射は押し続けられます。敵弾や目前に迫った敵機との接触でシールドを失います。

## 制約と測定結果

| 実行場面 | 実測描画／更新速度 |
|---|---:|
| 通常の進行・3秒測定 | 27.86 fps |
| 区域1・左右移動＋連射64フレーム | 29.47 fps |
| 区域2・左右移動＋連射64フレーム | 29.02 fps |
| 区域3・左右移動＋連射64フレーム | 28.34 fps |
| 停止したボス描画の試験 | 29.96 fps |
| 停止した過密配置の描画試験 | 29.96 fps |

過密配置はRAMで敵・弾を並べた**描画のみの負荷試験**です。多数の弾の運動や衝突計算を含む通常ゲームプレイの性能を示すものではありません。背景は2描画フレームに1回更新するため、上記プレイ区間では約14～15 Hzです。HUDは通常約7 Hz、状態変更時はすぐに更新します。

初代MSXのスプライトは **画面全体32枚・走査線4枚・1枚につき1色** です。重なると5枚目以降が欠けます。近距離の敵、自機、ボス、弾が重なる場面では消え・ちらつきが発生します。エミュレーターの枚数制限を無効にして隠すことはしていません。通常のボス配置は最大4枚／走査線、意図的な過密試験では最大19枚／走査線で制限による欠けを確認しました。

そのため同時出現枠を敵6体、敵弾8発、爆発4個へ縮小しました。大型爆発は共有の小さな絵へ置き換え、背景は横へ傾く映像や自由な3D形状変化を省いています。画面全体の色数・敵の陰影・ボスの多色表現はV9990版やturbo R版と異なります。

処理が30 Hzを下回るとゲーム進行とPSG音楽も少し遅くなります。この試作はフレーム単位で進行し、壁時計基準の追い付き処理は入れていません。測定値は今回のシナリオの結果で、全場面の最低フレームレートを保証するものではありません。

## 構造と容量

| 項目 | 容量／方式 |
|---|---|
| ROMファイル | 524,288バイト |
| ROMの割当範囲 | 155,648バイト、残りはFF埋め |
| RAM実行コード | 9,926バイト、8000hから実行 |
| 静的RAM領域の末尾 | E207h（スタックはF300hから下向き） |
| 背景 | 3区域、各16 KBの初期VRAM＋5,120バイトの位相ネーム表 |
| スプライト | 55個の16×16パターン、1,760バイト。表示は2倍拡大 |

VRAM配置はパターン0000h～17FFh、スプライトパターン1800h～1FFFh、色2000h～37FFh、ネーム3800h～3AFFh、スプライト属性3B00h／3B80hです。属性だけを2組用意し、垂直帰線の区切りで切り替えます。

TMS9918の表示中VRAM転送では、`OUTI`＋`NOP`＋`JP NZ`で次のアクセスまで30 Z80クロックを確保します。21クロック間隔の`OTIR`へ置き換えないでください。VDPレジスタは0～7だけを使い、V9938以降のパレットレジスタやR800のBIOSは呼びません。

## ソースから作る

このフォルダ内のコピー済み素材だけで再生成できます。元のV9990プロジェクトの出力やBIOSを素材生成時に読み直すことはありません。Python、Pillow、NumPy、Z80用SDCCとPasmoが必要です。

```powershell
cd msx1
python -m pip install -r requirements.txt
$env:SDCC_BIN = 'SDCCのbinフォルダ'
$env:PASMO = 'pasmo.exeのパス'
python tools/build.py
```

`--pack-only`を付けると画像の再生成を省き、現在の素材からCコードのコンパイルとROM構成を行います。ビルド成果物は兄弟の `outputs/msx1/` に作成します。エミュレーターがROMを読み込んでいるとWindowsで書き換えが拒否される場合があるため、開発時は `msx1/work/test.rom` のような別コピーを読み込んでください。

## 検証の再実行

`tools/emulator_host.mjs` は開発用のローカル制御ブリッジです。Node.jsとopenMSXを別途用意し、対象のROMをASCII8として読み込ませてから検証スクリプトを実行します。ポート18801、初代用の独立したユーザープロファイルを使用します。共有マシンではなく自分のPC上でのみ使用してください。

```powershell
$env:OPENMSX_EXE = 'openmsx.exeのパス'
$env:OPENMSX_SYSTEM_DATA = 'openMSXのshareフォルダ'
New-Item -ItemType Directory -Force work/profile | Out-Null
$env:OPENMSX_USER_DATA = "$PWD/work/profile"
Copy-Item ../outputs/msx1/NEON_REVENANT-MSX1-v1.0.rom work/test.rom
node tools/emulator_host.mjs -cart work/test.rom -romtype ASCII8
# 別ターミナルをmsx1フォルダで開いて、順に実行します。
python tools/emu.py "set power on; set renderer SDLGL-PP; set videosource MSX; set pause off"
python tools/verify_rom.py
python tools/verify_world.py
python tools/verify_sound.py
```

新しいプロファイルではブリッジ起動後、HTTP POSTで `set power on`、`set renderer SDLGL-PP`、`set videosource MSX`、`set pause off` を順に送ります。`verify_rom.py`はタイトル画面から開始してください。各検証はPC上の画面描画で代用せず、ROM内のCPUコードを実行します。

- [ゲーム検証36項目](../outputs/msx1/verification.json)：起動、VRAM/RAM容量、入力、照準への射撃、衝突、ボム、3ボスと遷移、クリア、リトライ。
- [描画検証43項目](../outputs/msx1/world-verification.json)：実行中ROMのSHA-256、Z80周波数、VRAM読戻し、全8位相、全3区域の実行GIF、PSG変化、ポーズの全4位相と表示文字、NOVA直後のポーズ表示、SAT読戻し、ハードウェア枚数制限。
- [PSGホスト検証](../outputs/msx1/sound-verification.json)：レジスタ範囲、音楽・効果音の優先度／復帰、ミュート、I/O方向。これは音源のロジック検証であり実機試験ではありません。
- [ビルド明細](../outputs/msx1/build-manifest.json)／[素材生成検証](assets/manifest.json)。`*-reference.png/gif` は素材の独立デコードによる参考画像、`*-native.gif` はROM実行画像です。

物理カートリッジへの書込み、実機での長時間プレイ、異なるTMS系統／PAL機、すべての入力機器は未検証です。今後の修正・対応・サポートは保証しません。
