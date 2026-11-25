Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\MyAPP\Sec\BurpSuitePro\Burp.bat" & Chr(34), 0
Set WshShell = Nothing