# V9968 / V9990 — 次の表現に向けて / Exploring what comes next

2026-09-07 · 準備調査 / Preparatory research

[日本語](#日本語) · [English](#english) · [README](../README.md)

## 日本語

NEON REVENANTは、Turbo R＋V9990で描いた完成像を出発点に、初代MSXまで表現を工夫してきました。遊んでくださった方、動画や感想を広めてくださった方、実機で試してくださった方へ、ありがとうございます。今度は上位の環境へ目を向け、もう一歩先の表現を検討しています。

対象は**Turbo R高速モード＋V9968**、そして既存の**Turbo R＋V9990版**です。V9968への対応については、設計者の方からご了承をいただいています。ASTRAとの制作で得た経験を生かし、それぞれのVDPで画面の動き、奥行き、操作への反応をどこまで豊かにできるかを調べています。

設計者の方からは、**V9968の仕様はほぼ確定しており、微修正の可能性は残る**との説明もいただいています。その前提で対応を検討していきます。

### 調査で見えてきた可能性

V9968の公開資料には、回転・拡大縮小を行う描画コマンド、拡張スプライト、多色表現を支える機能があります。NEON REVENANTの疑似3D表現へ結び付けられる、有力な材料です。ただし、複数の機能を同時に使ったときの速度は、実際の画面負荷で確かめる必要があります。[設計者による機能紹介](https://note.com/thara1129/n/n7f9f293e6066) · [回転・拡大縮小コマンドの解説](https://note.com/thara1129/n/ne83a0af75838)

V9990版についても、現在の実装を読み直しました。既にR800 DRAMモードで動いているため、次の挑戦では描画の組み合わせと素材の使い方が重要になります。背景と動く物体の前後関係や、それぞれの動き方を工夫する余地があります。現在の版を、V9990で到達できる表現の上限とは考えていません。[既存版の技術記録](../outputs/TECHNICAL.md)

目指すのは、**「この機種で、こんな動きが出るのか」と感じられる、遊べる画面**です。各VDPに合った方法を選び、映像の印象と操作感を一緒に磨く方向で検討しています。具体的な場面、キャラクター、演出の内容は、今回は伏せておきます。

### 実現に向けて確かめること

今回の調査では、V9968の公開資料、FPGA実装、対応openMSXの実装を照合しました。確認した版同士には拡張レジスター配置の違いがあり、使用するエミュレーターが対象FPGAの仕様に合っているかを確認する必要があります。この差分は、V9968の仕様が大幅な変更待ちという意味ではありません。公開資料を参照する際も、その版と実装をセットで確認していきます。[確認したFPGA実装](https://github.com/hra1129/V9968_Cartridge/blob/ceeecd7e3c2d25c20045f797617af0f70ca228c1/fpga/V9968_Cartridge_TangNano20K/src/v9968/vdp_cpu_interface.v#L636) · [確認したエミュレーター実装](https://github.com/buppu3/openMSX/blob/4bc4b2ef86923635744f02f6beea0a236ba2f310/src/video/VDP.hh#L153)

また、Turbo RのCPUが高速でも、外付けVDPへの画像転送には接続バスの制約があります。素材をVRAMに置いて描画命令や位置情報を送る構成を軸に、転送量と描画時間の両方を評価する方針です。[設計者によるカートリッジ版の説明](https://note.com/thara1129/n/nf85da0996cb6)

今後試作する際は、対象のCPU・VDP・エミュレーターの版を固定し、背景、物体、入力、音を含めたゲーム全体の負荷で確認します。エミュレーターで確認できたことと、実機で確認できたことも分けて記録します。**各版512 KiB ROM以内**という、これまでの容量方針も維持して検討します。

### 現在の状況

**今回は資料と既存実装の調査までです。V9968版の新規実装や、V9990版の追加機能はまだ作成・検証していません。** 採用する機能、動作速度、完成・公開時期は未定です。今回の更新は文書のみで、公開済みROMの差し替えはありません。

本稿は検討状況の共有です。既存の[試作版・無保証の配布条件](../DISCLAIMER.md)を継続します。続きを楽しみにしていただければ嬉しいです。

## English

NEON REVENANT began with a visual reference on Turbo R and V9990, then explored ways to preserve its appeal down to the original MSX. Thank you to everyone who played, shared footage or impressions, or tried the game on real hardware. We are now looking back toward the more capable configurations and considering another step forward.

The targets under consideration are **Turbo R in R800 mode with V9968**, and further improvements to the existing **Turbo R and V9990 edition**. The V9968 designer has given permission to pursue support. Building on our work with ASTRA, we are exploring how each VDP could enrich movement, depth, and the response to player input.

The designer has also explained that **the V9968 specification is largely finalized, with minor adjustments still possible**. We will consider support on that basis.

### What the research suggests

V9968 provides promising ingredients: drawing commands for rotation and scaling, an extended sprite system, and expanded color capabilities. These offer useful possibilities for NEON REVENANT's pseudo-3D presentation. Their combined performance still needs to be measured under a representative game workload. [Designer’s feature overview](https://note.com/thara1129/n/n7f9f293e6066) · [Rotation and scaling command explanation](https://note.com/thara1129/n/ne83a0af75838)

We also reviewed the existing V9990 code. It already runs in R800 DRAM mode, so the next challenge lies in how drawing operations and artwork are arranged. There is room to explore richer depth relationships and different movement between scenery and objects. We do not regard the current edition as the limit of what V9990 can express. [Existing technical notes](../outputs/TECHNICAL.md)

The aim is a **playable screen that makes people reconsider how this machine can move**. Each VDP will need its own approach, with visual impact and responsive play considered together. Specific scenes, characters, and effects will stay under wraps for now.

### What needs to be established

We compared public V9968 documentation with FPGA and supporting openMSX implementations. The revisions examined use different extended-register layouts, so we need to check that the emulator matches the target FPGA specification. This difference does not mean that V9968 is awaiting major specification changes. Documentation will be checked against its corresponding implementation. [Examined FPGA implementation](https://github.com/hra1129/V9968_Cartridge/blob/ceeecd7e3c2d25c20045f797617af0f70ca228c1/fpga/V9968_Cartridge_TangNano20K/src/v9968/vdp_cpu_interface.v#L636) · [Examined emulator implementation](https://github.com/buppu3/openMSX/blob/4bc4b2ef86923635744f02f6beea0a236ba2f310/src/video/VDP.hh#L153)

A fast CPU also does not remove the transfer limits of an external cartridge bus. Keeping artwork in VRAM and sending drawing commands and positions is a useful starting point; both transfer costs and drawing time must be evaluated. [Designer’s cartridge discussion](https://note.com/thara1129/n/nf85da0996cb6)

Any future prototype will be tested with a defined CPU, VDP, and emulator revision, under the combined load of scenery, objects, input, and sound. Emulator findings and physical-hardware findings will be reported separately. The existing **512 KiB ROM limit per edition** remains a design constraint.

### Current status

**Work so far is limited to reviewing documentation and existing implementations. A new V9968 game implementation and additional V9990 features have not yet been built or validated.** Features, performance, completion, and release timing remain undecided. This update changes documentation only; the published ROMs have not been replaced.

This is a research update. The existing [prototype and no-warranty terms](../DISCLAIMER.md) continue to apply. We hope you will enjoy seeing where the exploration leads.
