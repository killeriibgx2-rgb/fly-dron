Option Explicit
Dim shell, fso, root, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(pythonw) Then
  MsgBox "Сначала один раз запусти setup_windows.bat, чтобы установить программу.", vbInformation, "Мастерская модели"
  WScript.Quit 1
End If

shell.CurrentDirectory = root
command = Chr(34) & pythonw & Chr(34) & " -m app"
shell.Run command, 0, False
