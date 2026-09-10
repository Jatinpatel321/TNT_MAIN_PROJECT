@echo off
cd /d c:\TNT_MAIN_PROJECT-main\tnt-vendor-frontend
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set PATH=%JAVA_HOME%\bin;%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%
echo [Metro] Starting TNT Vendor App Expo dev server on port 8083...
npx expo start --dev-client --port 8083 --localhost
