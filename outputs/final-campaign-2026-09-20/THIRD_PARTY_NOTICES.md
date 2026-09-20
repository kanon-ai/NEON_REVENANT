# Third-party notices / 第三者ソフトウェアの表記

本書は、NEON REVENANT の V9990 版 v1.2、Turbo R 単体版 v1.0、MSX2 版 v1.0、MSX1 Challenge v1.0 / PCG Drive v1.1・v1.2 に関する依存物と出典の記録です。本プロジェクト固有のコード・画像・音楽の利用条件については [COPYRIGHT.md](COPYRIGHT.md) を参照してください。以下の第三者コードには、それぞれのライセンスが適用されます。

## ROM にリンクされる SDCC ランタイム

4版とも **SDCC 4.6.0 #16555 / Z80** でビルドしています。各版のリンカーマップを確認したところ、`z80.lib` からリンクされるオブジェクトは次の 4 個です。

| オブジェクト | 用途 | 上流の著作権表示 |
|---|---|---|
| `divunsigned.rel` | 符号なし整数の除算 | Copyright (C) 2000–2021, Michael Hope, Philipp Klaus Krause, Marco Bodrato |
| `modunsigned.rel` | 符号なし整数の剰余 | Copyright (C) 2009–2010, Philipp Klaus Krause |
| `mul.rel` | 整数の乗算 | Copyright (C) 2000, Michael Hope; Copyright (C) 2021, Philipp Klaus Krause |
| `divsigned.rel` | 符号付き整数の除算 | Copyright (C) 2000–2021, Michael Hope, Philipp Klaus Krause |

これらの各ソースファイルには **GNU General Public License, version 2 or later と SDCC のリンク例外**が明記されています。GPL の適用対象となるランタイム自体の条件を維持したうえで、この例外は SDCC でコンパイルしたファイル等とリンクすることだけを理由に実行ファイル全体が GPL の対象になることを免除しています。例外の正確な文言は各ファイルのヘッダーに保存しています。

- [GPL version 2 全文](licenses/sdcc-runtime/GPL-2.0.txt)
- [対象のランタイムソースと再アセンブル手順](licenses/sdcc-runtime/README.md)
- [取得元・revision・SHA-256](licenses/sdcc-runtime/PROVENANCE.json)
- [配布ライブラリとのオブジェクト一致確認](licenses/sdcc-runtime/OBJECT_VERIFICATION.json)

ランタイムソースは [SDCC 公式 SVN revision 16555](https://sourceforge.net/p/sdcc/code/16555/tree/trunk/sdcc/device/lib/z80/) から取得した無改変のコピーです。各ファイルを再アセンブルし、実際に使用した `z80.lib` の該当 `.rel` と、改行形式の差を除いて一致することを確認しました。著作権表示に加え、上流に記載された GBDK / Pascal Felber および z88dk / Spectrum ROM に関する歴史的な出典コメントも、ソース内にそのまま残しています。

使用した Windows 用ツールチェーンの取得元は、[MSXgl リポジトリの固定コミット `ab4b26feda36189e677aa23b56acfdc3218f7953`](https://github.com/aoineko-fr/MSXgl/tree/ab4b26feda36189e677aa23b56acfdc3218f7953/tools/sdcc) です。`z80.lib` の SHA-256 は `800f7f0544352ac9f0bbadc7cb15a95ededbc62acab7f1ed948616961b8b479e` です。MSXgl のゲームエンジンやライブラリは本ゲームにはリンクしていません。

## 開発・検証時だけに使用する外部ツール

次のプログラムは別途利用者が用意するツールです。本リポジトリと公開用配布 ZIP は、これらの実行ファイル、パッケージ本体、MSX の BIOS を同梱しません。ツールを自分で再配布する場合は、その配布物のライセンスを別途確認してください。

| ツール | 本プロジェクトでの用途 | 公式サイト |
|---|---|---|
| SDCC / SDAS / SDLD | C コンパイル、アセンブル、リンク | [SDCC](https://sdcc.sourceforge.net/) |
| Pasmo | ROM 起動コードのアセンブル | [Pasmo](https://pasmo.speccy.org/) |
| Python / Pillow / NumPy | ビルド処理、画像・背景データ生成 | [Python](https://www.python.org/), [Pillow](https://python-pillow.github.io/), [NumPy](https://numpy.org/) |
| Node.js | 開発用エミュレーター制御補助 | [Node.js](https://nodejs.org/) |
| openMSX | 起動・入力・描画などのエミュレーター検証 | [openMSX](https://openmsx.org/) |

## 技術資料・作品名

描画実装の調査では、VDP の仕様書、[MSX Assembly Page](https://map.grauw.nl/) の技術記事、および [openMSX の実装](https://github.com/openMSX/openMSX)を参照しています。これらは技術上の参考資料であり、本ゲームにリンクされる追加ライブラリではありません。資料の全文やエミュレーター本体は同梱していません。

本作は『ナイトストライカー』から着想を得た非公式の試作ゲームです。タイトーその他のメーカーによる承認・監修・提携を示すものではありません。商用ゲームから抽出した画像・音楽・ゲーム ROM、および MSX の BIOS / ファームウェアは同梱していません。作品名・製品名・商標は各権利者に帰属します。

## English summary

The four ROM editions link four SDCC Z80 runtime objects: `divunsigned`, `modunsigned`, `mul`, and `divsigned`. Each is licensed under GPL version 2 or later with the SDCC linking exception stated in its source header. Their unmodified corresponding source, copyright notices, full GPL v2 text, provenance, and object verification results are included under `licenses/sdcc-runtime/`. This notice does not relicense the project's own materials or any third-party material.

Compilers, assemblers, Python packages, Node.js, openMSX, and machine BIOS files are not bundled in the public repository or release archives. External tools retain their respective licenses. This is an unofficial, experimental project, with no endorsement by the owners of the referenced product or game names.
