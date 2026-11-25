Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir
WshShell.Run Chr(34) & currentDir & "\Burp.bat" & Chr(34), 0, False
Set WshShell = Nothing
Set fso = Nothing
