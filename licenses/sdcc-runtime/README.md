# SDCC runtime source and license

These are unmodified copies of the four Z80 library source files linked into
the V9990 v1.2 and Turbo R v1.0 ROM editions. They were retrieved from the
official SDCC Subversion repository at revision **16555** on 2026-09-06.

Each source file contains its copyright notice, the **GPL version 2 or later**
terms, and the **SDCC linking exception**. The full GPL version 2 text is in
[`GPL-2.0.txt`](GPL-2.0.txt). The exception is reproduced in full in each source
header; please read it together with the GPL. These third-party files retain
their own license regardless of the project's copyright policy.

| Module | Corresponding source |
|---|---|
| `divunsigned.rel` | [`src/divunsigned.s`](src/divunsigned.s) |
| `modunsigned.rel` | [`src/modunsigned.s`](src/modunsigned.s) |
| `mul.rel` | [`src/mul.s`](src/mul.s) |
| `divsigned.rel` | [`src/divsigned.s`](src/divsigned.s) |

`PROVENANCE.json` records exact source URLs, sizes, and SHA-256 hashes.
`OBJECT_VERIFICATION.json` records the comparison with the library actually
used to link the ROMs. All four object files match after normalizing CRLF to LF
in the textual ASxxxx `.rel` format. This verifies the library objects, not a
claim that arbitrary compiler versions reproduce an identical ROM.

## Reassemble the included source

Install SDCC separately and place its tools on `PATH`. From the repository
root, in PowerShell:

```powershell
New-Item -ItemType Directory -Force work/sdcc-runtime | Out-Null
foreach ($moduleName in @('divunsigned', 'modunsigned', 'mul', 'divsigned')) {
    sdasz80 -og "work/sdcc-runtime/$moduleName.rel" "licenses/sdcc-runtime/src/$moduleName.s"
    if ($LASTEXITCODE -ne 0) { throw "Assembly failed: $moduleName" }
}
```

There are no additional source includes for these four modules. Their
cross-module references are resolved together by the SDCC linker. The game
build scripts normally obtain the same modules from SDCC's `lib/z80/z80.lib`;
they do not need to reassemble these archival copies.

For a comparison with your separately installed SDCC library, `sdar p
<path-to-z80.lib> divunsigned.rel` prints the original library object. Compare
its text with the rebuilt `.rel`, ignoring only CRLF/LF differences. Repeat
for the other three modules. A different SDCC version or library build may
legitimately differ.

## Provenance of the tested toolchain

- Compiler identification: `SDCC 4.6.0 #16555 (MINGW64)`.
- Official runtime source: <https://sourceforge.net/p/sdcc/code/16555/tree/trunk/sdcc/device/lib/z80/>.
- Windows binaries and `z80.lib` used during the game build were obtained from
  MSXgl commit `ab4b26feda36189e677aa23b56acfdc3218f7953`, directory `tools/sdcc`:
  <https://github.com/aoineko-fr/MSXgl/tree/ab4b26feda36189e677aa23b56acfdc3218f7953/tools/sdcc>.
- `z80.lib` SHA-256:
  `800f7f0544352ac9f0bbadc7cb15a95ededbc62acab7f1ed948616961b8b479e`.

The compiler executables and the complete library archive are not included
here. The game uses its own startup code (`--no-std-crt0`); SDCC's `crt0.rel`
is not linked. No MSXgl game engine or MSXgl library code is linked.
