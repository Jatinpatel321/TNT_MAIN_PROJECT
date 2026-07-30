@echo off
cd /d c:\TNT_MAIN_PROJECT-main\tnt-vendor-frontend
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set PATH=%JAVA_HOME%\bin;%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%
echo [Metro] Starting TNT Vendor App Metro Server on port 8083...
npx react-native start --port 8083
