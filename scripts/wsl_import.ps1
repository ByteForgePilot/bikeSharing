# 导入 Ubuntu WSL 发行版
$rootfs = "D:\ubuntu-wsl-rootfs.tar.gz"
$installDir = "D:\WSL\Ubuntu-22.04"

if (-not (Test-Path $rootfs)) {
    Write-Host "ERROR: rootfs not found at $rootfs"
    exit 1
}

Write-Host "Creating install directory: $installDir"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host "Importing Ubuntu-22.04..."
wsl --import Ubuntu-22.04 $installDir $rootfs

Write-Host "`nChecking WSL status:"
wsl --list --verbose
