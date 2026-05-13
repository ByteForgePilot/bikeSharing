# 将虚拟内存从 C 盘移到 D 盘（不重启）
$computer = Get-WmiObject -Class Win32_ComputerSystem
$computer.AutomaticManagedPagefile = $false
$computer.Put() | Out-Null
Write-Host "已禁用自动管理..."

# 删除 C 盘现有页面文件
$old = Get-WmiObject -Class Win32_PageFileSetting | Where-Object { $_.Name -like 'C:*' }
if ($old) {
    $old.Delete()
    Write-Host "已移除 C 盘页面文件"
}

# 在 D 盘创建系统管理的页面文件
$result = (Get-WmiObject -Class Win32_PageFileSetting -List).Create("D:\pagefile.sys", 0, 0)
Write-Host "已在 D 盘创建页面文件（系统管理大小）"

Write-Host "`n当前页面文件设置:"
Get-WmiObject -Class Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize | Format-List

Write-Host "`n重启后生效 — C 盘将释放约 13GB"
