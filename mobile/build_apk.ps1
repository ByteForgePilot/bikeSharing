$env:ANDROID_HOME='D:\Android\Sdk'
$env:PATH='D:\Android\Sdk\platform-tools;' + $env:PATH
cd E:\Project\bikeSharing\mobile\android
Remove-Item -Recurse -Force .gradle\8.10.2\dependencies-accessors -ErrorAction SilentlyContinue
.\gradlew.bat assembleDebug --no-daemon 2>&1 | Select-Object -Last 50
