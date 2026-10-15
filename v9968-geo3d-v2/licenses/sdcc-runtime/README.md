# SDCC runtime source notices

The Geo3D ROM links divunsigned, modunsigned, mul, divsigned, __muluint2ulong, __mulsint2slong, _divslong and _divulong from SDCC 4.6.0 #16555. Unmodified corresponding sources and required headers are included under src/, with their original copyright and GPL-2.0-or-later plus linking-exception notices. See GPL-2.0.txt and PROVENANCE.json.

The inherited OBJECT_VERIFICATION.json covers only the original four assembly objects; it does not claim verification of the four additional Geo3D runtime objects. Reassemble .s files with sdasz80 -plosgff and compile .c files with SDCC -mz80 using the same SDCC release and included headers. External compiler tools are not bundled.
