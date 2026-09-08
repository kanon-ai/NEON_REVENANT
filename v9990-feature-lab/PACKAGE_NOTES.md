# V9990 Feature Lab v0.1 — package notes / 配布物について

本配布物は独立した機能試験版です。無保証で、実機での動作は未検証です。
将来の修正・サポートを保証しません。著作権・利用条件は COPYRIGHT.md、
免責事項は DISCLAIMER.md、第三者コードは THIRD_PARTY_NOTICES.md と
licenses/ を参照してください。公開ソースであることは、プロジェクト全体に
オープンソースライセンスを付与する意味ではありません。

README.md の手順に従い、外部の Python、Pillow、NumPy、SDCC、Pasmo を用意すれば、
このソース一式から素材を再生成し ROM をビルドできます。コンパイラ、
エミュレーター、MSX BIOS は同梱していません。

tools/verify_repro.py は再生成ビルドに加え、開発元の従来版 71 ファイルと
work/baseline-sha256.json を使用する保全検査も行います。この baseline 検査は
開発ワークスペース限定です。元のワークスペースと registry は本 ZIP に含まれず、
このスクリプト全体を ZIP 単体でそのまま実行できるという保証はありません。
素材再生成と ROM ビルドそのものは、同梱 tools/build.py で独立して行えます。

outputs/feature-lab-v0.1/ の画像・GIF は openMSX 上で実際の ROM を動かした
検証時の記録です。特定場面を選ぶための RAM 設定は検証 JSON に明記しています。
assets/ 配下の画像・GIF は素材や生成プレビューであり、native と名の付く
既存プレビューも含めて実行速度や実機動作を証明するものではありません。

This is an independent experimental feature build, supplied without warranty.
Physical hardware has not been tested. Future fixes or support are not promised.
See COPYRIGHT.md, DISCLAIMER.md, THIRD_PARTY_NOTICES.md and licenses/ for the
unchanged project-specific rights and third-party terms. Publishing source does
not grant an open-source license to the project as a whole.

With the external Python/Pillow/NumPy and SDCC/Pasmo tools described in README.md,
the included sources can regenerate the assets and build the ROM. Compilers,
emulators and machine BIOS files are not bundled.

tools/verify_repro.py also checks 71 original-edition files using the development
workspace's work/baseline-sha256.json. That baseline protection check requires the
original workspace and registry, neither of which is bundled. Its full combined
verification workflow is therefore not standalone; asset regeneration and ROM
building through tools/build.py are standalone with the required external tools.

outputs/feature-lab-v0.1/ contains captures of the ROM running in openMSX. The
verification reports disclose RAM-seeded targeted scenarios. Images and GIFs
under assets/ are generated artwork/previews, including historical files named
native, and do not establish execution speed or physical-hardware compatibility.
