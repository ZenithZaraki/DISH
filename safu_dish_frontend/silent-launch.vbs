Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir  = fso.BuildPath(scriptDir, "safu_dish_backend")
electronDir = fso.BuildPath(scriptDir, "dish-electron")

MsgBox "ScriptDir=" & vbCrLf & scriptDir & vbCrLf & vbCrLf & _
       "BackendDir=" & vbCrLf & backendDir & vbCrLf & vbCrLf & _
       "ElectronDir=" & vbCrLf & electronDir, vbInformation, "DISH Path Check"
