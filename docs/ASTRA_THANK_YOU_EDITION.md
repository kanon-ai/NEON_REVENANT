# ASTRAからの有難うエディション

**NEON REVENANT — MSX1 PCG Drive v1.2 / ASTRA Thank-You Edition**

遊んでくださった皆さん、動画を見てくださった皆さん、コメントや感想を寄せてくださった皆さん、実機で試してくださった皆さんへ。有難うございます。

初代MSXの小さな画面を走るこの作品に、時間を使って付き合っていただけたことを嬉しく思います。もう一度飛び立ってもらえるように、街へ入る道と、街を抜けた先の朝を加えました。湾岸から夜の都市へ、そして夜明けへ。新しい2区域も楽しんでいただけたら幸いです。

この名称は、検証済みのMSX1 PCG Drive v1.2を公開する際のエディション名です。ROM内のタイトルやバイナリを変更した別ビルドではありません。V9990版、turbo R単体版、MSX2版は従来の内容を保っています。

## 追加したもの、引き継いだもの

| 順番 | 区域 | 内容 |
|---|---|---|
| Episode 0 | BREAKWATER APPROACH | 新しい湾岸の導入背景・PSGメロディ |
| 01 | CHROME DISTRICT | 既存区域 |
| 02 | SKYWAY ASSAULT | 既存区域 |
| 03 | THE BLACK SPIRE | 既存区域 |
| 04 | DAWN EXODUS | 新しい夜明けの脱出背景・PSGメロディ |

元3区域の背景データ、戦闘設定、曲を維持しています。導入を終えるとシールド6・ボム3へ全補給し、その後は従来の区域間回復です。5回のボス戦には既存3種類の画像を使用し、導入と脱出の相手は色を変えています。各区域の背景は16位相の循環アニメーションです。

[ROMをダウンロード](../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom) · [リリース一覧](https://github.com/kanon-ai/NEON_REVENANT/releases) · [起動・操作・ビルドの日本語ガイド](../msx1/README.md)

## 512KiBのままで5区域にした工夫

ROM内のPCG転送パケットを、1個につき1バンク置く方式から、複数個を同じ8KiBバンクへ詰める方式へ変えました。各パケットをバンク内に収め、バンク番号とオフセットで読み出します。表示中のパターンを避けて次の画面を用意する仕組みと、実行時に画像を圧縮展開しない方式は維持しています。

| メモリー | v1.2の条件・使用量 |
|---|---|
| ROM | 512KiB ASCII8。368KiB割当、末尾144KiB未使用 |
| RAM | 32KiB以上。8000h～FFFFhが同じRAMスロットにあること |
| VRAM | 16KiB。SCREEN 2、2面のネームテーブル、常駐スプライト |

ROMの空きはRAMの空きとは別です。ROMを詰め直すことで背景を追加しても、動作に必要なRAMを増やさずに済みました。[ビルドマニフェスト](../outputs/msx1/v1.2/build-manifest.json)と[ROMからの独立デコード検証](../outputs/msx1/v1.2/layout-verification.json)に配置と検証結果があります。

## 確認できた範囲

openMSX上で32KiB RAMのNTSC／PAL各127項目と、64KiB構成の基本動作11項目、計265項目が成功しました。5区域の遷移・クリア・再挑戦、全区域の背景位相、VRAM転送を検証しています。NTSC／PAL合わせて960描画フレームをVRAMから照合しました。

既存3区域は同じ初期状態・乱数・操作から28,066スナップショットが旧版と一致しました。PSGは5曲・6効果音を確認し、元3曲のレジスター出力も維持しています。素材を全再生成した独立ビルドでも、配布ROMとバイト単位で一致しました。

後半区域やボスの検証にはRAMへ開始状態を設定する試験を含みます。最初から最後までの手動プレイによるクリアではありません。ゲームと音楽はフレームに同期し、PALでは進行とテンポが遅くなります。実機・実フラッシュカートリッジでのv1.2の動作は、開発側では未検証です。寄せていただく実機の感想や報告へのお礼と、開発側が確認済みとする範囲を分けて記録しています。

[検証環境](../outputs/msx1/v1.2/validation-environment.json) · [既存戦闘の比較](../outputs/msx1/v1.2/campaign-verification.json) · [PSG検証](../outputs/msx1/v1.2/sound-verification.json) · [再ビルド一致](../outputs/msx1/v1.2/reproducibility.json)

開発途中・無保証のプロトタイプです。[免責事項](../DISCLAIMER.md)、[著作権・ライセンスの状態](../COPYRIGHT.md)、[第三者ソフトウェアの表示](../THIRD_PARTY_NOTICES.md)はこれまでと同じです。

## English — ASTRA Thank-You Edition

To everyone who played NEON REVENANT, watched a video, shared a comment, or tried it on real hardware: thank you. We are glad you spent time with this little MSX journey. We added a way into the city and a morning on the other side. We hope the harbor approach and dawn escape give you another reason to take off.

**ASTRA Thank-You Edition** is the publication name for the verified **MSX1 PCG Drive v1.2** release. Its ROM is byte-identical to that build; this name does not designate a separate executable or an in-ROM title change. The V9990, Turbo R and MSX2 editions retain their existing content.

- Five zones: Episode 0 / Breakwater Approach, the original three zones, then Dawn Exodus.
- Two new backgrounds and two PSG melodies. Original background data, combat settings and music are preserved.
- Five boss encounters use the existing three silhouettes, with different colors for the opening and finale. Backgrounds repeat through 16 phases per zone.
- 512 KiB ASCII8 ROM, 32 KiB RAM at 8000h–FFFFh in one slot, and 16 KiB VRAM. No V9990 or FM expansion is needed.
- Packing whole transfer packets together leaves 144 KiB unused in the ROM, without runtime decompression or a larger RAM requirement.

All 265 native checks passed: complete scenario suites on both 32 KiB NTSC/PAL configurations, plus basic startup and control checks with 64 KiB RAM. Background readback matched 960 rendered frames. Seeded combat comparisons preserved the original three zones, original PSG traces matched, and full asset regeneration produced the same ROM.

These checks include RAM-seeded scenarios, not a complete manual playthrough. PAL gameplay and music run more slowly because both are frame-bound. Version 1.2 remains an experimental prototype without warranty; the development team has not verified this version on physical MSX hardware or flash cartridges. Thanks for community hardware testing do not expand those verification claims.

[Download the ROM](../outputs/msx1/v1.2/NEON_REVENANT-MSX1-v1.2.rom) · [Releases](https://github.com/kanon-ai/NEON_REVENANT/releases) · [English requirements, controls and build guide](../msx1/README-en.md) · [Disclaimer](../DISCLAIMER.md) · [Copyright](../COPYRIGHT.md)
