param([string]$OpenMSXPath = '', [string]$Machine = 'C-BIOS_MSX1_JP')
$ErrorActionPreference = 'Stop'
if (-not $OpenMSXPath) {
    $found = Get-Command openmsx.exe -ErrorAction SilentlyContinue
    if ($found) { $OpenMSXPath = $found.Source }
    elseif (Test-Path -LiteralPath "$env:ProgramFiles/openMSX/openmsx.exe") {
        $OpenMSXPath = "$env:ProgramFiles/openMSX/openmsx.exe"
    }
}
if (-not $OpenMSXPath -or -not (Test-Path -LiteralPath $OpenMSXPath)) {
    throw 'openMSXが見つかりません。-OpenMSXPath に openmsx.exe の場所を指定してください。'
}
$rom = Join-Path $PSScriptRoot 'NEON_REVENANT-MSX1-v1.0.rom'
if (-not (Test-Path -LiteralPath $rom)) { throw "ROMが見つかりません: $rom" }
& $OpenMSXPath -machine $Machine -cart $rom -romtype ASCII8
