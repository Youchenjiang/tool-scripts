@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: 優先檢測本地綠色版 JDK，否則使用系統安裝的 JDK 21
if exist "%~dp0jdk-21\bin\java.exe" (
    set "JAVA_EXE=%~dp0jdk-21\bin\java.exe"
) else (
    set "JAVA_EXE=C:\Program Files\Java\jdk-21\bin\java.exe"
)

:: 動態搜尋目錄下的 Burp 主程式 JAR
set "BURP_JAR="
for %%f in ("%~dp0burpsuite_pro*.jar") do (
    set "BURP_JAR=%%f"
)
if not defined BURP_JAR set "BURP_JAR=%~dp0burpsuite_pro_v2025.jar"

:: JVM 記憶體與模組參數
set "JAVA_MEM=-Xms1024m -Xmx4096m -XX:+UseG1GC"
set "VM_OPTIONS=--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"

:: 啟動 Burp Suite Pro
start "" "!JAVA_EXE!" !JAVA_MEM! !VM_OPTIONS! -javaagent:"%~dp0loader.jar" -noverify -jar "!BURP_JAR!"
