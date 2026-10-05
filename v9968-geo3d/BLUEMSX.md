# blueMSX Plus / Geo3D 検証環境

2026年10月5日に使用したのは、[Hesoten氏のGeo3D対応実験版](https://github.com/Hesoten/blueMSX-plus/releases/tag/V9968-geo3d-experimental-2)です。通常版とは配布ファイルが異なります。

- リリース: `V9968-geo3d-experimental-2`（2026年10月3日 JST）
- コミット: `2090cd265928e5290b7939d7447cf76184dd6d07`
- 配布ファイル: `blueMSX+-v3.1.1-experimental-v9968-geo3d-2090cd2-x64.zip`
- 配布ZIP SHA-256: `71ac2533d8f4af4dd61ac2f3179514ab30c804829ba7409eae5520ef41c840dd`

## 設定

検証では専用フォルダーに展開し、同梱の `MSXturboR - C-BIOS FDD` を使用しました。そのマシンの `config.ini` の `[Video]` を以下に設定します。

```ini
[Video]
version=V9968
vram size=256kB
```

カートリッジは **ASCII16** を明示指定し、MSX-MUSICを有効にします。エミュレーション速度・VDPコマンド速度はともに100%です。

```text
blueMSX+.exe /machine "MSXturboR - C-BIOS FDD" /rom1 "NEON_REVENANT-HC-Geo3D-256-v0.2.0.rom" /romtype1 ASCII16 /speed 100 /vdpspeed 100 /msxmusic on
```

ROMのパスは保存場所に合わせて指定してください。既存環境を使用する場合は、設定を保存・退避してから変更してください。エミュレータ・BIOSはゲームに同梱していません。

## 確認範囲

タイトル、全5区域の背景と敵弾、全ボス、ゲームオーバー表示、録音による音声出力を確認しました。全区域を確認するため、検証用RAMでシールド補充、区間タイマー短縮、ボス戦後の遷移指定を行っています。手操作での全編クリアや全操作の再検証、ピクセル単位の一致、両エミュレータの厳密な速度比較は含みません。詳細は[検証記録](outputs/verification-v0.2.0/bluemsx.json)を参照してください。

検証対象は公開済みの4 MiB ROM（SHA-256: `e50dbaf58c62c4c25e57532682341ba14ceabc205abc3558026a9bd8a3dc2444`）です。今回の追加検証に伴うROMの変更はありません。

## English

Use the linked **Geo3D experimental build**, not the standard blueMSX Plus release. The tested machine is the bundled `MSXturboR - C-BIOS FDD`, configured for V9968 and 256 kB VRAM, with explicit ASCII16 mapping and MSX-MUSIC enabled. Both emulation and VDP command speed are set to 100%. The command above uses the unchanged public v0.2.0 ROM. Keep this evaluation environment separate from existing settings. Emulator and BIOS files are not included. Physical hardware/FPGA validation is not implied.
