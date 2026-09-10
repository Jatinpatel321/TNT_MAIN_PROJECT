@echo off
cd /d c:\TNT_MAIN_PROJECT-main\tnt-user-frontend
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set PATH=%JAVA_HOME%\bin;%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%
echo [ADB] Setting up reverse port tunnels...
adb reverse tcp:8000 tcp:8000
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8082 tcp:8082
echo [Metro] Starting TNT User App Metro Server on port 8081...
npx react-native start --port 8081
