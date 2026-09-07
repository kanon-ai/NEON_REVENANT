[最新版 v1.3：巨大最終ボス Dawn Leviathan の起動・操作・検証](GIANT_BOSS-v1.3.md) — 以下はv1.2の記録です。

# NEON REVENANT — MSX1 PCG Drive v1.2

**ASTRAからの有難うエディション / ASTRA Thank-You Edition**

遊んでくださった方、動画を見てくださった方、コメントや実機確認を届けてくださった方へ。ありがとうございます。皆さんへのお礼として、この5区域版を公開します。

[ASTRAから皆さんへ](../docs/ASTRA_THANK_YOU_EDITION.md)

**Breakwater to Dawn：湾岸から侵入し、3区域を突破して夜明けへ脱出する、初代MSX用の5区域シューティングです。512KiB ASCII8 ROM、RAM32KiB、VRAM16KiB、標準PSGで動く試作版です。無保証、v1.2の実機・実フラッシュカートリッジ動作は未検証です。**

[English documentation](README-en.md)

## v1.2の構成

| 順番 | 区域 | ボス |
|---|---|---|
| Episode 0 | BREAKWATER APPROACH：湾岸から都市へ | SENTRY / HARBOR PATROL |
| 01 | CHROME DISTRICT | WARDEN / INTERCEPTOR |
| 02 | SKYWAY ASSAULT | RAZOR / SIEGE CARRIER |
| 03 | THE BLACK SPIRE | NOX / CENTRAL CORE |
| 04 | DAWN EXODUS：夜明けへの脱出路 | ECHO / LAST PURSUER |

新しい導入・脱出背景と、それぞれのPSGメロディを追加しました。ボス戦は5回ありますが、画像は既存の3種類を使用します。導入はWARDEN、脱出はNOXの形状を色替えしています。背景は各区域16位相の循環アニメーションです。都市が連続して拡大する長編映像や、建物が一度だけ倒れる物理演出ではありません。

既存3区域の背景データ、敵・弾・ボスの戦闘設定、元3曲は維持しています。Episode 0を終えるとシールド6・ボム3へ全補給し、その後は従来の区域間回復です。全5区域のボスを倒すとクリアします。導入・脱出の区間は既存区域より短く、途中で失敗した場合はEpisode 0から再挑戦します。

![Episode 0のROM実行映像](../outputs/msx1/v1.2/ntsc/stage-1-native.gif)

openMSXの32KiB RAM・NTSC構成で撮影した、移動と連射を含む96描画フレームです。GIFの表示時間はMSX側の実測値に合わせています。

## 起動と操作

| 項目 | 条件 |
|---|---|
| 本体 | 初代MSX、Z80 3.58MHz |
| RAM | 32KiB以上。8000h～FFFFhを同一RAMスロットに持つ構成 |
| VDP | TMS9918A／TMS9929A系、VRAM16KiB、SCREEN 2 |
| 画面 | 256×192、固定15色＋透明 |
| ROM | [NEON_REVENANT-MSX1-v1.2.rom](../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom)、ASCII8、524,288バイト |
| 音源 | 本体標準PSGのみ |

RAM16KiB機は対象外です。PCGは本体VDPのパターン書き換えを指します。追加のPCGカートリッジ、V9990、FM音源、MSX-DOSは不要です。エミュレーターではROM形式を **ASCII8**、映像ソースを **MSX** に指定します。

```powershell
openmsx -machine C-BIOS_MSX1_JP -cart NEON_REVENANT-MSX1-v1.2.rom -romtype ASCII8
```

この起動例はopenMSX付属の通常C-BIOS機種を使います。32KiBだけのRAM構成で検証する手順は後述します。BIOSとopenMSX本体は配布物に含めません。

| 操作 | キーボード | ジョイスティック1 |
|---|---|---|
| 自機・照準移動 | カーソルキー | 十字方向 |
| 開始・連射・再挑戦 | Space | トリガー1 |
| NOVAボム | X | トリガー2 |
| ポーズ・再開 | Esc | キーボードのEsc |

照準へ敵を捉えて射撃し、敵機と敵弾を避けます。ボムは押した瞬間に1個消費し、押し続けても連続消費しません。

## 動きと表示の制限

現在の画面で使わないPCGスロットへ次の背景を2回に分けて転送し、非表示側のネームテーブルを完成させてから切り替えます。Z80上で背景画像の生成・圧縮展開は行いません。背景更新は2ゲームフレームに1回、HUD更新は4フレームに1回です。

ゲームとPSG音楽はフレームに同期します。NTSCは60Hz、PALは50Hzで、PALの進行と音楽は基本的に遅くなります。処理落ちでも速度・テンポが変わり、常時30fpsやNTSC/PAL同一速度は保証しません。

openMSX 21.0系、Z80 3.58MHz・RAM32KiB・VRAM16KiB、スプライト制限有効で測定しました。各区域の移動と連射を含む96描画フレームを、MSX側の経過時間から計算しています。

| 区域 | NTSC・60Hz | PAL・50Hz |
|---|---:|---:|
| Episode 0 / BREAKWATER APPROACH | 26.58fps | 23.92fps |
| 01 / CHROME DISTRICT | 26.08fps | 23.12fps |
| 02 / SKYWAY ASSAULT | 25.96fps | 23.23fps |
| 03 / THE BLACK SPIRE | 24.09fps | 22.46fps |
| 04 / DAWN EXODUS | 25.16fps | 22.89fps |

測定根拠は[NTSC描画検証](../outputs/msx1/v1.2/ntsc/world-verification.json)と[PAL描画検証](../outputs/msx1/v1.2/pal/world-verification.json)です。この区間で背景は約11～13Hz更新です。停止した描画シナリオの値を通常戦闘の速度として扱っていません。

スプライトは55個の常駐16×16パターンを使用します。全画面32枚・走査線4枚・1枚1色の制約により、密集時には欠けやちらつきが発生します。自由な3D視点移動や背景の横スクロールはありません。

## 容量と転送

[ビルド結果](../outputs/msx1/v1.2/build-manifest.json)では、ROM512KiBのうち368KiBを割り当て、末尾144KiBを未使用として残しています。実行コードと定数の範囲は11,138バイト、静的データ終端はE211hです。32KiBはRAMの必要容量で、ROMやVRAMの容量とは別です。

| 8KiB ROMバンク | 用途 |
|---|---|
| 0 | 起動処理 |
| 1～3 | RAMへコピーする実行コード領域 |
| 4～5 | スプライト記述と常駐パターン |
| 6～15 | 5区域の初期VRAM、各16KiB |
| 16～17 | タイトル画面 |
| 18～45 | 80個のPCG転送パケット |
| 46～63 | 未使用 |

複数パケットを同じバンクに詰め、バンク番号とオフセットで参照します。各パケットはバンクをまたぎません。パケット実データは合計213,556バイトです。v1.1の「1パケットに1バンク」の余白を減らしたため、5区域でも512KiB内に収まります。

1ゲームフレームで行うPCG転送は最大1,352バイトです（ネーム転送を含む。導入区域は最大1,208バイト）。VRAMはパターン0000h～17FFh、スプライトパターン1800h～1FFFh、色2000h～37FFh、ネーム3800h／3C00h、スプライト属性3B00h／3B80hに配置します。表示中PCGとHUDフォントを保護して転送します。VDP書き込みループの30 Z80クロック間隔を短縮しないでください。

## ソースからビルド

この `msx1/` フォルダーを作業ディレクトリにします。素材は `assets/source/` にあり、他の版の作業フォルダーに依存せず再生成できます。Python 3、Pillow、NumPy、Z80用SDCC、Pasmoが必要です。開発ではSDCC 4.6.0を使用しています。

```powershell
python -m pip install -r requirements.txt
$env:SDCC_BIN = 'C:/path/to/sdcc/bin'
$env:PASMO = 'C:/path/to/pasmo.exe'
python tools/build.py
```

ROM・マニフェストの出力先は `../outputs/msx1/v1.2/` です。`python tools/build.py --pack-only` は素材の再生成だけを省き、現在のC／ASMとパケット配置表を再コンパイルします。

[独立ディレクトリでの全素材再生成・再ビルド](../outputs/msx1/v1.2/reproducibility.json)でも、配布ROMとバイト単位で一致しました。

## 検証の再実行

エミュレーターを使わない検証です。PSGと戦闘比較にはホスト用Cコンパイラーも必要です。

```powershell
python tools/verify_layout.py
$env:CC = 'C:/path/to/gcc.exe'
python tools/verify_sound.py
# 任意：別途保存したv1.1の素材・ソースとの比較
python tools/verify_layout.py --baseline 'C:/archive/v1.1/msx1/assets'
python tools/verify_campaign.py --baseline 'C:/archive/v1.1/msx1/src/game.c' --gcc 'C:/path/to/gcc.exe'
```

`verify_campaign.py` は外部の旧ソースを明示指定する比較試験です。旧版はv1.2のソース一式に含みません。`verify_sound.py` の元3曲との比較は、兄弟フォルダーに旧v1.1 complete ZIPがある場合のみ追加実行されます。

32KiB機種でのROM実行検証には、Node.js、openMSXとそのC-BIOSが必要です。`OPENMSX_EXE` と `OPENMSX_SYSTEM_DATA` は同じopenMSX配布物の実行ファイルとshareを指定してください。以下のブリッジはWindows向けで、専用設定を `work/ram32-profile-ntsc/` または `work/ram32-profile-pal/` に作り、描画なし・電源OFFで起動します。既定の音声出力先はdummyです。この手順ではPSGレジスターを調べ、音声出力装置そのものは検証しません。

```powershell
$env:OPENMSX_EXE = 'C:/path/to/openmsx.exe'
$env:OPENMSX_SYSTEM_DATA = 'C:/path/to/openMSX/share'
$env:MSX_RAM_KIB = '32'
$env:MSX_VIDEO_STANDARD = 'ntsc'
node tools/emulator_ram32.mjs -cart ../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom -romtype ASCII8
```

別ターミナルを同じ `msx1/` で開きます。

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

PALは旧ブリッジの終了とターミナルのプロンプト復帰を確認してから、両ターミナルの値を `pal` に変えて再起動し、同じ順序で実行します。ブリッジは同時に1つだけ使います。結果は `../outputs/msx1/v1.2/ntsc/` と `pal/` に分けて出力されます。

32KiB構成のNTSC／PALは、それぞれゲーム57項目・描画61項目・転送9項目、合計254項目が成功しました。[NTSCゲーム](../outputs/msx1/v1.2/ntsc/verification.json)／[PALゲーム](../outputs/msx1/v1.2/pal/verification.json)で5区域の遷移、クリア、再挑戦を確認し、背景は両方式合計960描画フレームをVRAMから照合しました。各方式で全5区域×16位相を確認し、通常処理のVRAMアクセス間隔違反は0でした。[NTSC転送](../outputs/msx1/v1.2/ntsc/transfer-verification.json)／[PAL転送](../outputs/msx1/v1.2/pal/transfer-verification.json)では境界条件・レジスター保持とタイミング監視の検出動作も確認しています。

[64KiB RAM構成の基本動作11項目](../outputs/msx1/v1.2/ram64-smoke.json)も成功し、ネイティブ検証は合計265項目です。64KiB側はキーボード入力によるEpisode 0の起動・移動・ポーズ・ボムの確認で、全5区域の検証は32KiB側です。[検証環境](../outputs/msx1/v1.2/validation-environment.json)に実行ファイルの版・SHA-256、RAM／VDP設定と検証範囲を記録しています。

[ROM配置検証](../outputs/msx1/v1.2/layout-verification.json)では80パケットをROMから読み戻して独立デコードし、元3区域の54素材ファイルの一致、表示中PCGと保護領域の非破壊を確認しました。[戦闘比較](../outputs/msx1/v1.2/campaign-verification.json)では同じ初期状態・乱数・入力を使った28,066スナップショット×157項目が旧3区域と一致しました。[PSG検証](../outputs/msx1/v1.2/sound-verification.json)では5曲・6効果音と、元3曲のレジスター出力維持を確認しました。

ホストの戦闘比較は16bit変数を使いますが、式の整数昇格はGCCに従います。Z80命令の時間やVDPを再現する試験ではありません。ROM実行の後半区域・被弾・ボスなどにはRAMへ開始状態を設定したシナリオ試験を含み、その後を実際のROMで処理します。手動操作だけによる全編通しクリアとは区別しています。`*-reference`は素材の参考画像、`*-native`はROM実行映像です。

本作は開発途中の独自作品です。実機・実フラッシュカートリッジの互換性、動作、今後の対応は保証しません。配布物の免責事項、著作権、第三者ソフトウェアの表示も確認してください。
