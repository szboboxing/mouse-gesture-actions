param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

try {
    $VersionTag = (python -c "from version import VERSION_TAG; print(VERSION_TAG)").Trim()
    Write-Host "Mouse Gesture Actions $VersionTag - One-file build" -ForegroundColor Cyan

    if (-not $SkipTests) {
        Write-Host "[1/6] Running automated tests..."
        python -m unittest discover -s tests -v
    }
    else {
        Write-Host "[1/6] Tests skipped"
    }

    Write-Host "[2/6] Generating Windows version metadata..."
    python tools\generate_version_info.py

    Write-Host "[3/6] Generating application icon..."
    python tools\generate_icon.py

    Write-Host "[4/6] Building one-file EXE..."
    python -m PyInstaller --noconfirm --clean "mouse_gesture_actions.spec"

    Write-Host "[5/6] Retaining the latest two local versions..."
    python tools\retain_latest_releases.py dist --keep 2

    $ExePath = Get-ChildItem (Join-Path $PSScriptRoot "dist") -Filter "*_$VersionTag.exe" |
        Select-Object -First 1
    if (-not $ExePath) {
        throw "Build artifact was not found in the dist directory"
    }

    Write-Host "[6/6] Calculating SHA-256..."
    $File = Get-Item $ExePath.FullName
    $Hash = Get-FileHash $ExePath.FullName -Algorithm SHA256
    Write-Host "Artifact: $($File.FullName)" -ForegroundColor Green
    Write-Host "Size: $($File.Length) bytes"
    Write-Host "SHA-256: $($Hash.Hash)" -ForegroundColor Green
}
finally {
    Pop-Location
}
