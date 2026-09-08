# V9990 Feature Lab v0.1 — 検証記録 / Validation

2026-09-08。対象ROMのSHA-256:

```text
4298a3579ff53a1ad861b4523b74b08f3340fee358c82c51aaca9d64c58ea904
```

## 動作確認 / Native execution

openMSX 21.0-unknown、Panasonic_FS-A1ST、gfx9000、ASCII8で確認しました。R800 DRAMモードとV9990 B1の設定を読み戻し、実行中のRAMコード17,400 bytesが配布ROMと一致することも確認しました。今回の試験版は実機未確認です。

Tested in openMSX 21.0-unknown with Panasonic_FS-A1ST, gfx9000 and ASCII8. The R800 DRAM and V9990 B1 settings were read back, and 17,400 bytes of executing RAM code matched the packaged ROM. This edition has not been tested on physical hardware.

- [ゲーム動作34項目 / 34 gameplay checks](outputs/verification-feature-lab-v0.1.json): 起動、移動4方向、照準射撃、NOVA、停止・再開、被弾、ゲームオーバー、リトライ、3面のボス出現・撃破・面遷移・エンディング。 / Startup, movement, targeting, NOVA, pause/resume, collision, retry, and boss/transition/ending states for all three stages.
- [追加機能29項目 / 29 feature checks](outputs/feature-verification.json): アトラスと各16位相背景のVRAM全量照合、追加画像照合、2枚のカーソル、照準座標、パレット、停止中の表示と演出切り替え、演出後の素材保全、FMレジスターの活動、連続描画フレーム。 / VRAM image readback, all 16 world phases per stage, feature art, two cursor planes, aim position, palette selection, pause/toggle behavior, retained artwork, FM register activity, and consecutive rendered frames.

遠い面・最終一撃・被弾条件などはRAMに場面を設定し、その後の描画・入力・判定をROMに実行させています。通常操作だけで最初から最後まで完走したという意味ではありません。検証用音声出力はdummyで、FMレジスターの変化を確認しています。スピーカー出力の確認ではありません。

RAM seeds select distant stages, last-hit and collision scenarios; the ROM then performs input, rendering and gameplay. This is not an uninterrupted manual playthrough. The development audio driver is dummy: FM register activity was checked, not speaker output.

## 連続フレーム / Captured motion

| 場面 / Scene | フレーム数 / Frames | 実測更新頻度 / Updates per emulated second | GIF時間 / Duration |
| --- | ---: | ---: | ---: |
| ステージ2・発光ゲート / Stage 2 energy gates | 96 | 29.19 | 3.29 s |
| ステージ3・巨大ボス / Stage 3 giant boss | 128 | 29.96 | 4.27 s |

通常の3面でも約29～30更新/秒を確認しました。60Hz表示に対して、おおむね2フレームに1回のゲーム更新です。ゲート区間では一部の更新に3フレームを使います。常時30更新/秒の保証や実機の性能値ではありません。

The three regular stages measured about 29–30 updates per emulated second, usually one update per two 60Hz display frames. Some gate-scene updates take three display frames. These are sampled emulator measurements, not guaranteed or physical-hardware rates.

GIFはROMの連続描画フレームから作成しました。取得した画像を2倍に拡大し、表示時間はエミュレーター内の時刻から10ms単位に丸めています。加速・補間はしていません。全フレームをGIFから読み戻し、取得画像と画素一致を確認しました。

GIFs contain consecutive native ROM frames, enlarged 2×. Timing follows emulated timestamps rounded to 10ms. No motion interpolation or speed-up is used. Every decoded GIF frame was checked against its captured source pixels.

- [巨大ボスの実動作 / Giant boss](outputs/feature-lab-v0.1/giant-siege-carrier-native.gif)
- [発光ゲートの実動作 / Energy gates](outputs/feature-lab-v0.1/skyway-energy-gates-native.gif)

`assets/feature-motion-preview.gif` は素材配置の作画プレビューです。ROMの動画は `outputs/feature-lab-v0.1/*-native.gif` です。

`assets/feature-motion-preview.gif` is an artwork layout preview. Native ROM recordings are the `outputs/feature-lab-v0.1/*-native.gif` files.

## 容量・展開 / Capacity and decoding

| 項目 / Item | Bytes |
| --- | ---: |
| ROM全体 / ROM size | 524,288 |
| 割り当て済み / Allocated | 388,209 |
| 未割り当て / Free | 136,079 |
| 元版の空き / Baseline free | 72,887 |
| 追加素材を含めた空き増加 / Net free-space gain including new art | 63,192 |

画像や背景位相の削減はありません。[圧縮検証](outputs/compression-verification.json)は13種類の境界条件と、実ROM内の5本のストリームを独立したASCII8バンク／2048-byte履歴リングのモデルでも復号しています。実行時には全アトラス81,920 bytes、背景368,640 bytes×3面、追加素材の不変部分7,680 bytesを比較しました。追加領域の末尾512 bytesは実行時にハードウェアカーソルの属性・パターンへ変更します。

No original artwork or background phases were removed. [Compression checks](outputs/compression-verification.json) cover 13 edge cases and all five streams in the actual ROM using an independent ASCII8 bank/history-ring decoder. Native VRAM comparisons cover the full 81,920-byte atlas, three 368,640-byte worlds, and 7,680 immutable feature bytes. The last 512 feature bytes become live cursor attributes and patterns.

VRAMの割り当ては、描画ページ64KiB、既存素材80KiB、背景360KiB、追加素材・カーソル8KiBです。ROMの空きとVRAMの空きは別の制約です。面の背景ロードは約3.7～5.0秒かかり、その間は音楽を一時停止します。展開後に音楽の再開を確認しました。

VRAM allocation is 64KiB for drawing pages, 80KiB for existing art, 360KiB for world frames, and 8KiB for extra art/cursors. Free ROM capacity does not imply free VRAM. World loading takes about 3.7–5.0 emulated seconds and temporarily pauses music; music activity resumes afterward.

## 再現と既存版保全 / Reproduction and baseline

[再現ビルド記録](outputs/repro-verification.json)は別ディレクトリで生成済み入力を削除し、全素材生成→コンパイル→ROM構築を行った結果です。[保全記録](outputs/baseline-protection-verification.json)には既存版71ファイルの前後SHA-256比較を保存しています。単体ZIPには元版や開発用baselineレジストリーを含めていません。

[Reproduction evidence](outputs/repro-verification.json) records a separate full asset regeneration and compile after removing generated ROM inputs. [Baseline evidence](outputs/baseline-protection-verification.json) compares 71 original-edition files before and after. The standalone ZIP does not include the original edition or its development baseline registry.

## 検証の再実行 / Running native checks

ビルド後、別途インストールしたopenMSXと対応するshare、所有するBIOSを用意し、このディレクトリで実行します。

After building, provide an external openMSX installation, its matching share directory, and your own BIOS. Run from this directory:

```powershell
$env:OPENMSX_EXE = 'C:\path\to\openmsx.exe'
$env:OPENMSX_SYSTEM_DATA = 'C:\path\to\share'
node tools/emulator_host.mjs -cartb outputs/NEON_REVENANT-V9990-FeatureLab-v0.1.rom -romtype ASCII8
```

別ターミナルで順に実行 / In another terminal, run sequentially:

```powershell
python tools/verify_rom.py
python tools/verify_lab.py
python tools/verify_compression.py --rom outputs/NEON_REVENANT-V9990-FeatureLab-v0.1.rom
```

ブリッジはローカル18890番を使用し、既定では `work/emulator-profile` に専用設定を作ります。通常のプレイはこのブリッジを必要としません。ROMを再ビルドする前にエミュレーターから取り外してください。Windowsでは読み込み中のROMがロックされる場合があります。

The bridge listens locally on port 18890 and defaults to a dedicated profile in `work/emulator-profile`. It is unnecessary for normal play. Unload the ROM before rebuilding: Windows may lock a cartridge file while it is in use.
