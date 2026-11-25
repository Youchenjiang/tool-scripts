@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Check local portable JDK first, fallback to system JDK 21 (use javaw.exe for pure GUI without console)
if exist "%~dp0jdk-21\bin\javaw.exe" (
    set "JAVA_EXE=%~dp0jdk-21\bin\javaw.exe"
) else (
    set "JAVA_EXE=C:\Program Files\Java\jdk-21\bin\javaw.exe"
)

:: Dynamically search for burpsuite_pro*.jar
set "BURP_JAR="
for %%f in ("%~dp0burpsuite_pro*.jar") do (
    set "BURP_JAR=%%f"
)
if not defined BURP_JAR set "BURP_JAR=%~dp0burpsuite_pro_v2025.jar"

:: JVM memory and module options
set "JAVA_MEM=-Xms1024m -Xmx4096m -XX:+UseG1GC"
set "VM_OPTIONS=--enable-native-access=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED --add-opens=java.base/jdk.internal.org.objectweb.asm.Opcodes=ALL-UNNAMED"

:: Launch Burp Suite Pro silently with javaw
start "" "!JAVA_EXE!" !JAVA_MEM! !VM_OPTIONS! -javaagent:"%~dp0loader.jar" -noverify -jar "!BURP_JAR!"
