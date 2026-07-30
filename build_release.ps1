[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
if (-not $SkipInstall) {
    & $Python -m pip install -r (Join-Path $projectRoot "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

& $Python (Join-Path $projectRoot "tools\build_release.py")
if ($LASTEXITCODE -ne 0) {
    throw "Release build failed."
}
