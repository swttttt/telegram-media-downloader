[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$distDir = Join-Path $projectRoot "dist"
$workDir = Join-Path $projectRoot "build"
$assetDir = Join-Path $projectRoot "assets"
$appName = "TelegramMediaDownloader"
$env:PYGAME_HIDE_SUPPORT_PROMPT = "1"
$version = & $Python -c "import telegram_media_downloader as app; print(app.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read application version."
}

if (-not $SkipInstall) {
    & $Python -m pip install -r (Join-Path $projectRoot "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

& $Python (Join-Path $projectRoot "tools\build_marketing_assets.py")
if ($LASTEXITCODE -ne 0) {
    throw "Asset generation failed."
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --noupx `
    --name $appName `
    --icon (Join-Path $assetDir "app.ico") `
    --version-file (Join-Path $projectRoot "packaging\windows-version-info.txt") `
    --hidden-import cryptg `
    --exclude-module PIL `
    --distpath $distDir `
    --workpath $workDir `
    --specpath $workDir `
    (Join-Path $projectRoot "telegram_media_downloader.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$exePath = Join-Path $distDir "$appName.exe"
$packageName = "$appName-v$version-windows-x64"
$stageDir = Join-Path $workDir $packageName
$zipPath = Join-Path $distDir "$packageName.zip"
$checksumPath = Join-Path $distDir "$packageName.sha256"

if (Test-Path -LiteralPath $stageDir) {
    Remove-Item -LiteralPath $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stageDir | Out-Null
Copy-Item -LiteralPath $exePath -Destination $stageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "start.bat") -Destination $stageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $stageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "README_EN.md") -Destination $stageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $stageDir

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
"$hash  $([System.IO.Path]::GetFileName($zipPath))" |
    Set-Content -LiteralPath $checksumPath -Encoding ascii

Write-Host ""
Write-Host "Release build complete:" -ForegroundColor Cyan
Write-Host "  $exePath"
Write-Host "  $zipPath"
Write-Host "  $checksumPath"
