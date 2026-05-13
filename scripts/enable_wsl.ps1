# 启用 WSL 和虚拟机平台（需管理员，需重启）
Write-Host "正在启用 Windows Subsystem for Linux..."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart | Out-Null
Write-Host "WSL 功能已启用"

Write-Host "正在启用 Virtual Machine Platform..."
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart | Out-Null
Write-Host "虚拟机平台已启用"

Write-Host ""
Write-Host "=== 完成！请重启电脑 ==="
Write-Host "重启后运行: wsl --list --verbose"
Write-Host "然后运行: E:\Project\bikeSharing\scripts\wsl_import.ps1 (管理员)"
Write-Host "Ubuntu rootfs 已下载在: D:\ubuntu-wsl-rootfs.tar.gz (326MB)"
