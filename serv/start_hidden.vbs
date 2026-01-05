Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Caminho\Para\SeuPrograma.exe" & Chr(34), 0
Set WshShell = Nothing
