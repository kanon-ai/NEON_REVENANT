[CmdletBinding()]
param(
    [string]$OpenMsxPath,
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$Machine = 'FS-A1ST'
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($OpenMsxPath)) {
    $candidates = @(
        'C:\Program Files\openMSX\openmsx.exe',
        'C:\Program Files (x86)\openMSX\openmsx.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $OpenMsxPath = $candidate
            break
        }
    }
    if ([string]::IsNullOrWhiteSpace($OpenMsxPath)) {
        $installedCommand = Get-Command openmsx.exe -ErrorAction SilentlyContinue
        if ($installedCommand) { $OpenMsxPath = $installedCommand.Source }
    }
}

if ([string]::IsNullOrWhiteSpace($OpenMsxPath) -or
    !(Test-Path -LiteralPath $OpenMsxPath -PathType Leaf)) {
    throw 'openMSX が見つかりません。-OpenMsxPath で openmsx.exe を指定してください。'
}
$OpenMsxPath = (Resolve-Path -LiteralPath $OpenMsxPath).Path
$romPath = Join-Path $PSScriptRoot 'NEON_REVENANT-v1.2.rom'
if (!(Test-Path -LiteralPath $romPath -PathType Leaf)) {
    throw "ROM が見つかりません: $romPath"
}
if ($Machine -eq 'FS-A1ST' -or $Machine -eq 'FS-A1GT') {
    $Machine = 'Panasonic_' + $Machine
}

# Use the installed machine definitions and existing system ROMs with the
# workspace-built emulator. Nothing is copied out of the installation.
$systemDataPath = $null
$dataCandidates = @(
    'C:\Program Files\openMSX\share',
    'C:\Program Files (x86)\openMSX\share',
    (Join-Path (Split-Path -Parent $OpenMsxPath) 'share')
)
foreach ($candidate in $dataCandidates) {
    if ((Test-Path -LiteralPath (Join-Path $candidate 'init.tcl')) -and
        (Test-Path -LiteralPath (Join-Path $candidate 'machines'))) {
        $systemDataPath = $candidate
        break
    }
}
if (!$systemDataPath) {
    throw 'openMSX の share フォルダーが見つかりません。openMSX の配置を確認してください。'
}

$profilePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\work\play-profile'))
$userDataPath = Join-Path $profilePath 'user_data'
foreach ($directory in @($profilePath, $userDataPath,
        (Join-Path $userDataPath 'systemroms'), (Join-Path $userDataPath 'scripts'), (Join-Path $profilePath 'screenshots'))) {
    [IO.Directory]::CreateDirectory($directory) | Out-Null
}

# Process-local environment: the current shell and existing openMSX profile
# are untouched. Paths cannot contain double quotes on Windows.
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $OpenMsxPath
$startInfo.WorkingDirectory = $PSScriptRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.EnvironmentVariables['OPENMSX_SYSTEM_DATA'] = $systemDataPath
$startInfo.EnvironmentVariables['OPENMSX_HOME'] = $profilePath
$startInfo.EnvironmentVariables['OPENMSX_USER_DATA'] = $userDataPath
$startInfo.Arguments = '-machine "{0}" -ext gfx9000 -cart "{1}" -romtype ASCII8 -command "set renderer SDLGL-PP" -command "set power on" -command "after time 5 {{set videosource GFX9000}}"' -f $Machine, $romPath
$gameProcess = [System.Diagnostics.Process]::Start($startInfo)
Write-Output "NEON REVENANT を起動しました (PID: $($gameProcess.Id))。数秒後に V9990 映像へ切り替わります。"
