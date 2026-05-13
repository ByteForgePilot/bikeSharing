# 紧急恢复 System PATH（去除 Python314 死链接）
$restoredPath = @(
    'C:\Program Files (x86)\Common Files\Oracle\Java\java8path',
    'C:\Program Files (x86)\Common Files\Oracle\Java\javapath',
    'D:\Rational\Common',
    'D:\VMware\VMware Workstation\bin\',
    'C:\WINDOWS\system32',
    'C:\WINDOWS',
    'C:\WINDOWS\System32\Wbem',
    'C:\WINDOWS\System32\WindowsPowerShell\v1.0\',
    'C:\WINDOWS\System32\OpenSSH\',
    'C:\Program Files\Microsoft SQL Server\170\Tools\Binn\',
    'C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\',
    'D:\Cmake\bin',
    'C:\Program Files\Microsoft SQL Server\110\Tools\Binn\',
    'D:\Git\cmd',
    'C:\Program Files (x86)\Windows Kits\10\Windows Performance Toolkit\',
    'D:\Process Lasso\',
    'D:\nodejs\',
    'C:\ProgramData\chocolatey\bin',
    'D:\GitHub CLI\'
) -join ';'

[Environment]::SetEnvironmentVariable('PATH', $restoredPath, 'Machine')
Write-Host "System PATH restored (Python314 removed, all others intact)"
Write-Host "Entries: $($restoredPath.Split(';').Count)"
