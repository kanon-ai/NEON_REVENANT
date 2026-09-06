# NEON REVENANT — MSX1 PCG Drive v1.1

**初代MSXのZ80 3.58MHz・RAM64KiB・VRAM16KiBで動く、512KiB ASCII8 MegaROMの試作版です。無保証、実機・実カートリッジ未検証です。**

v1.0の線を中心にした背景から、PCGをROMから入れ替える背景へ作り直しました。建物の面、窓、看板、路面の反射、高架、トンネルが遠近法に従って手前へ迫ります。3区域・3ボス、機体・敵のスプライト、ゲーム進行、PSGの音楽と効果音は引き継いでいます。

![初代MSXで動くPCG Drive](../outputs/msx1/v1.1/stage-1-native.gif)

このGIFはopenMSXのC-BIOS MSX1 JP上でROMを実行した96描画フレームです。表示時間はMSX側の実測値に合わせています。PC上の参考アニメーションとは区別しています。

## 起動と操作

| 項目 | 条件 |
|---|---|
| 本体 | 初代MSX、Z80 3.58MHz、RAM64KiB |
| VDP | TMS9918A系、VRAM16KiB、SCREEN 2 |
| 画面 | 256×192、固定15色＋透明 |
| ROM | [NEON_REVENANT-MSX1-v1.1.rom](../outputs/msx1/v1.1/NEON_REVENANT-MSX1-v1.1.rom)、ASCII8、524,288バイト |
| 音源 | 本体標準PSGのみ |
| 確認環境 | openMSX 21.0、C-BIOS_MSX1_JP、60Hz、スプライト制限有効 |

PCGという表現は本体VDPのパターン書き換えを指します。拡張PCGカートリッジ、V9990、FM音源、MSX-DOSは必要ありません。RAM16KiBだけの機種は対象外です。PAL/50Hz機は未検証です。

openMSXで機種を `C-BIOS_MSX1_JP`、カートリッジをこのROM、種類を **ASCII8** にします。映像ソースは **MSX** です。ROMと同じフォルダーの `launch-openmsx.ps1` も使えます。

```powershell
openmsx -machine C-BIOS_MSX1_JP -cart NEON_REVENANT-MSX1-v1.1.rom -romtype ASCII8
```

| 操作 | キーボード | ジョイスティック1 |
|---|---|---|
| 自機・照準移動 | カーソルキー | 十字方向 |
| 開始・連射・再挑戦 | Space | トリガー1 |
| NOVAボム | X | トリガー2 |
| ポーズ・再開 | Esc | キーボードのEsc |

照準に敵を捉えて撃ち、接近する敵機と敵弾を避けます。シールドを失うとゲームオーバー、3区域のボスを倒すとクリアです。

## PCGで強化した部分

原画の立体的な背景を128×80相当の形状へ変換し、256×160のプレイ領域へ展開しました。陰影には1ピクセルの黒・青・紫のディザを使い、窓や発光は明るい色で残しています。SCREEN 2の横8ドットごとに最大2色という条件も守ります。

各区域は8位相から**16位相**へ増加しました。開発時には各64走査線帯に512種類の候補タイルを作り、1位相あたりの使用数を上帯96・中帯128・下帯96以内に整理します。この512種類は開発時の辞書で、同時にVRAMへ置く数ではありません。

同じ画面と次の画面で使うPCGが衝突しないよう、開発時にスロットを割り当てます。現在表示中のPCGは変更せず、次のPCGをROMから2回に分けて先読みし、非表示側のネームテーブルを完成させてから切り替えます。先読み途中にポーズしても背景は変わりません。

Z80上では画像生成や圧縮展開を行わず、ROM内の転送パケットを短いアセンブリ処理でVDPへ送ります。HUDの数値表示から繰り返し除算を減らし、敵の描画順も同じ順序を保ったまま計算を軽くしました。

## 速度と制限

| 実行条件 | 描画・ゲーム更新 |
|---|---:|
| 通常進行の3秒測定 | 26.56fps |
| 区域1・移動＋連射96フレーム | 26.58fps |
| 区域2・移動＋連射96フレーム | 26.59fps |
| 区域3・移動＋連射96フレーム | 24.61fps |

背景は2描画フレームに1回更新するので、上記区間では約12～13Hzです。停止したボス・過密配置の描画試験では29.96fpsでしたが、そちらはPCGの前進とゲーム進行が停止した条件です。通常戦闘の性能とは区別してください。

v1.0の撮影区間は約28～29fpsでした。v1.1は背景の情報量を増やした分の負荷があり、全場面の30fpsを保証しません。ゲームと音楽はフレーム単位で進むため、処理落ちすると速度とテンポも遅くなります。

スプライトはv1.0と同じ55個の常駐パターンです。1枚1色、全画面32枚・走査線4枚の制限があり、敵・弾・自機が集中すると欠けやちらつきが発生します。背景の横揺れや自由な3D視点移動はありません。

## ROM・VRAMの使い方

| 領域 | 用途 |
|---|---|
| ROM bank 0 | 起動処理 |
| bank 1～3 | RAMへコピーする実行コード |
| bank 4～5 | スプライト記述と常駐パターン |
| bank 6～11 | 3区域の初期VRAM、各16KiB |
| bank 12～13 | タイトル画面 |
| bank 14～61 | 3区域×16位相のPCG転送パケット |
| bank 62～63 | 未使用 |

8KiBずつの**62バンク・496KiBは割当量**です。各パケットは1バンク内に置いて直接読むため、バンクの内部にはFFの余白があります。実PCGパケットは3区域合計131,656バイトで、ROM全域を画像データで埋めた意味ではありません。

PCG更新は1回につき最大1,340バイト（ネーム転送を含む）です。VRAMはパターン0000h～17FFh、スプライトパターン1800h～1FFFh、色2000h～37FFh、ネーム3800h/3C00h、スプライト属性3B00h/3B80hに配置します。フォント用PCGは上帯・下帯の192番以降に保護しています。

VRAM転送の `OUTI`＋`NOP`＋`JP NZ` は次のアクセスまで30 Z80クロックを確保します。21クロックの`OTIR`へ置き換えないでください。VDPの配置仕様は[Texas Instrumentsのデータマニュアル](https://www.bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf)も参照できます。

## 再ビルドと検証

この `msx1/` フォルダーを作業ディレクトリにします。素材は `assets/source/` に収録し、他の版やBIOSから読み出さずに再生成できます。Python、Pillow、NumPy、Z80用SDCC、Pasmoが必要です。

```powershell
python -m pip install -r requirements.txt
$env:SDCC_BIN = 'SDCCのbinフォルダー'
$env:PASMO = 'pasmo.exeのパス'
python tools/build.py
```

出力先は `../outputs/msx1/v1.1/` です。`--pack-only` は素材の再生成だけを省き、現在のC/ASMソースをコンパイルします。v1.0 ROMは上書きしません。

開発用のローカルブリッジを起動して検証する例です。Node.jsとopenMSXは別途必要です。BIOSは配布しません。

```powershell
$env:OPENMSX_EXE = 'openmsx.exeのパス'
$env:OPENMSX_SYSTEM_DATA = 'openMSXのshareフォルダー'
New-Item -ItemType Directory -Force work/profile | Out-Null
$env:OPENMSX_USER_DATA = "$PWD/work/profile"
Copy-Item ../outputs/msx1/v1.1/NEON_REVENANT-MSX1-v1.1.rom work/test.rom
node tools/emulator_host.mjs -cart work/test.rom -romtype ASCII8
# 別ターミナルをmsx1/で開き、順に実行
python tools/emu.py "set power on"
python tools/emu.py "set renderer SDLGL-PP"
python tools/emu.py "set videosource MSX"
python tools/emu.py "set pause off"
python tools/verify_rom.py
python tools/verify_world.py
python tools/verify_transfer.py
```

- [ゲーム検証36項目](../outputs/msx1/v1.1/verification.json)：起動、入力、戦闘、3ボス、区域遷移、クリア、再挑戦。
- [描画検証47項目](../outputs/msx1/v1.1/world-verification.json)：全3区域の16位相、先読み途中を含む288回のVRAM背景照合、両面HUD、実行GIF、PSG、ポーズ、スプライト。
- [転送処理の実行検証8項目](../outputs/msx1/v1.1/transfer-verification.json)：0～768バイトの境界条件とIX/IYの保持。
- [PCGの独立デコード検証](../outputs/msx1/v1.1/codec-verification.json)：3区域それぞれ3周、表示中PCG・保護領域の非破壊、位相15→0の一致。
- [既存動作の維持](../outputs/msx1/v1.1/scope-verification.json)／[描画順705,894通りの比較](../outputs/msx1/v1.1/enemy-order-verification.json)／[PSGロジック検証](../outputs/msx1/v1.1/sound-verification.json)。

後半区域、被弾、過密配置などはRAMへ開始状態を設定する試験です。その後の処理はROMが実行していますが、手動操作だけでの全編通しプレイとは区別しています。`*-reference`は素材の参考画像、`*-native`はROM実行映像です。

本作は開発途中の独自作品です。TAITOやMSX関連各社の公式作品ではありません。実機・実カートリッジ・PAL機は未検証で、動作、互換性、今後の対応を保証しません。利用前に配布物の免責事項・著作権・第三者ソフトウェアの表示を確認してください。
