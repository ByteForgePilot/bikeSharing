# 清理 System PATH 中的死链接和过时条目（需管理员运行）
# 备份当前 System PATH 到桌面
$oldPath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
$backupPath = "$env:USERPROFILE\Desktop\system_path_backup.txt"
$oldPath | Out-File -FilePath $backupPath -Encoding UTF8
Write-Host "已备份原 System PATH 到: $backupPath`n"

# 解析 PATH
$entries = $oldPath -split ';' | Where-Object { $_ -ne '' }
Write-Host "当前 System PATH 共 $($entries.Count) 条`n"

# 要删除的条目
$toRemove = @(
    'C:\Python314\Scripts\',
    'C:\Python314\'
)

$newEntries = @()
foreach ($entry in $entries) {
    $normalized = $entry.TrimEnd('\') + '\'
    $shouldRemove = $false
    foreach ($bad in $toRemove) {
        if ($normalized -eq ($bad.TrimEnd('\') + '\')) {
            Write-Host "  删除: $entry"
            $shouldRemove = $true
            break
        }
    }
    if (-not $shouldRemove) {
        $newEntries += $entry
    }
}

$newPath = $newEntries -join ';'
[Environment]::SetEnvironmentVariable('PATH', $newPath, 'Machine')
Write-Host "`n已更新 System PATH: $($newEntries.Count) 条"
Write-Host "删除了 Python314 死链接（目录已不存在）"
