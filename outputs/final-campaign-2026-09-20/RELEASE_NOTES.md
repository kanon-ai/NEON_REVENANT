# NEON REVENANT — Final campaign / 全機種最終リリース

本作の基本的な機能開発を締めくくるリリースです。全機種で5区域を遊べます。

- **Turbo R + V9990：1 MiB ASCII8**。湾岸と夜明けの追加面、敵の編隊・交差・急降下、段階的な難易度、可動巨大ボス、発光ゲート。
- **Turbo R単体 / MSX2 / MSX初代：512 KiB ASCII8**。機種に合わせたPCG背景と全5面。
- **全機種のフォントを更新**。既存中間3面の背景とV9990市街の青灰色の色味を維持。
- **MSX1：RAM32 KiB / VRAM16 KiB**。MSX2：RAM64 KiB / VRAM128 KiB。

MSX2・Turbo R単体版はステージ切替時の背景展開に約9～10秒／約2～3秒かかります。この2版のボスは通常スプライトで、V9990・MSX1の巨大ボスとは異なります。

操作：方向キー／ジョイスティック、SPACE／トリガー1で射撃、X／トリガー2でNOVA、ESCで一時停止。V9990はCart.1にGFX9000、Cart.2にROMを設定し、1 MiB ASCII8を扱える環境でお使いください。

**ROMs ZIP**に4機種のROM、日英ガイド、比較画像、検証結果を収録しています。**Source ZIP**はソース・素材・生成／ビルドツール一式です。個別ROMもダウンロードできます。SHA256SUMS.txtでファイルを照合できます。

openMSXで258項目のシナリオ検証、再ビルド一致、既存V9990パレット維持を確認しました。RAMで場面を設定した検証を含み、手操作の全編通しプレイではありません。この最終版は実機未確認です。過去版への実機報告と区別しています。

**試作ソフト・現状のまま・無保証。最終リリースは基本的な機能開発の区切りを示し、無欠陥やサポートを保証するものではありません。不具合修正への対応可否・時期も保証しません。** 詳細は同梱README、DISCLAIMER、COPYRIGHTをご確認ください。旧リリースは残しています。

---

Final feature release for all four targets, with five sectors and revised custom typography. V9990: 1 MiB ASCII8. Standalone Turbo R, MSX2 and MSX1: 512 KiB ASCII8. The original middle-stage artwork and V9990 city colours are preserved. MSX1 retains the 32 KiB RAM / 16 KiB VRAM target.

MSX2 and standalone Turbo R decompress each stage, taking roughly 9–10 / 2–3 seconds. Their bosses use ordinary sprites rather than the V9990/MSX1 giant artwork. ROMs ZIP includes all four binaries, guides, screenshots and verification records; Source ZIP includes source code and build assets/tools. Individual ROMs are also provided.

258 openMSX scenario checks passed and all four ROM rebuild hashes matched. Tests use RAM-seeded scenarios, not a complete manual playthrough. These final ROMs have not been tested on physical hardware. **Experimental, AS IS, WITHOUT WARRANTY. Final refers to completion of planned feature development; maintenance, bug fixes and support are not promised.**
