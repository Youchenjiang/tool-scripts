@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: 檢測系統安裝的 JDK 21
set "JAVA_EXE=C:\Program Files\Java\jdk-21\bin\java.exe"

:: 動態搜尋目錄下的 Burp 主程式 JAR
set "BURP_JAR="
for %%f in ("%~dp0burpsuite_pro*.jar") do (
    set "BURP_JAR=%%f"
)
if not defined BURP_JAR set "BURP_JAR=%~dp0burpsuite_pro_v2025.jar"

set "VM_OPTIONS=--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"

start "" "!JAVA_EXE!" !VM_OPTIONS! -javaagent:"%~dp0loader.jar" -noverify -jar "!BURP_JAR!"
