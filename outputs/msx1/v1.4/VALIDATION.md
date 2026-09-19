# MSX1 v1.4 validation / 検証範囲

Published ROM SHA-256:
`77aa5eabcd4f1bd6510e344570b440fc57f6d0816b747476c676fb41499dd691`

公開用ソース・素材からのフルビルドが、採用された A-original と全バイト一致しました。
ROM は524,288 bytes、使用434,176 bytes、空き90,112 bytesです。

## 実行時の確認

- openMSX NTSC、標準Z80、RAM32 KiB、VRAM16 KiB、スプライト制限あり。
- 5面それぞれ96回の実行中VRAM読戻し。全16位相、隠れたPCGへの転送、表示ページを確認。
- ポーズ・再開、NOVA後のポーズ、HUD、通常・過密場面のスプライト配置を確認。
- VRAMアクセス間隔違反は0。通常場面は約23.6～26.6更新/秒。背景位相は2更新で1回進みます。
- PSGは5面の連射中も平均約33.38ms間隔。描画ループを2秒止めても60回更新。
- 最終タイトルのVRAM読戻しと、実入力による開始を確認。
- PSGのエミュレーターPCM録音を波形として確認。実機音声測定や聴感評価ではありません。

`ntsc/world-verification.json` はタイトル可読性修正前のA版を記録しています。
`title-only-change.json` に変更前後のROMハッシュとタイトル領域を記録し、
それ以外の全バイトが同一であることを確認しています。
`final-boot-verification.json` は最終ROM（公開v1.4と同じハッシュ）の起動・タイトル・開始検証です。
検証記録内の `A-original` はこの採用候補の当時の名称です。

ステージや過密場面をRAMに設定するシナリオ試験を含みます。
手操作だけの通しプレイ、実機・実カートリッジでの検証ではありません。
v1.4のPAL実行試験は未実施です。旧版の検証結果をv1.4の実機/PAL保証として扱いません。
試作中・無保証。詳しくは[免責事項](../../../DISCLAIMER.md)をご覧ください。

## English

The full public-source build reproduces the approved A-original ROM byte for byte.
Native openMSX NTSC checks covered five stages, all 16 background phases, pause,
HUD, sprite pressure, PSG cadence and final title/start input. The world tests
precede a title-legibility-only change; all bytes outside the recorded title
banks are identical, and the final title/start tests use the published ROM hash.
Recorded filenames preserve their original candidate names for traceability.
Tests include RAM-seeded scenarios. Physical hardware, PAL runtime, and analog
audio quality have not been newly verified. Experimental and without warranty.
