param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

# This script is CI-friendly and can also be reused locally on Windows.
# It builds a one-folder PyInstaller package and additionally creates one ZIP
# artifact so non-technical users can download/extract/run in one step.

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$specFile = Join-Path $projectRoot "packaging\pyinstaller\EBBING_HOUSE.windows.spec"
$distDir = Join-Path $projectRoot "dist\windows"
$workDir = Join-Path $projectRoot "build\pyinstaller\windows"
$appDir = Join-Path $distDir "EBBING_HOUSE"
$exePath = Join-Path $appDir "EBBING_HOUSE.exe"
$zipPath = Join-Path $distDir "EBBING_HOUSE-windows-x64.zip"

if (-not (Test-Path $specFile)) {
    throw "Windows spec file not found: $specFile"
}

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $distDir `
    --workpath $workDir `
    $specFile

if (-not (Test-Path $exePath)) {
    throw "Expected executable not found: $exePath"
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# We zip only the packaged runtime folder content. The user gets one archive,
# extracts it, then launches EBBING_HOUSE.exe.
Compress-Archive -Path "$appDir\*" -DestinationPath $zipPath -CompressionLevel Optimal -Force

Write-Host "Windows executable created: $exePath"
Write-Host "Windows artifact zip created: $zipPath"
