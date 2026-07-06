' launch_dish_silent.vbs
Option Explicit

Dim fso, sh
Dim scriptDir, basePath, currentFolder
Dim nodeDir, nodeExe
Dim backendDir, frontendDir, electronDir, electronCli
Dim userdataDir, tempDir, cacheDir, pycacheDir
Dim env, electronCmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' Figure out where this script lives
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
currentFolder = LCase(fso.GetFileName(scriptDir))

' If launched from dish-electron, move up to SAFU NOVA root
If currentFolder = "dish-electron" Then
    basePath = fso.GetParentFolderName(scriptDir)
Else
    basePath = scriptDir
End If

backendDir  = fso.BuildPath(basePath, "safu_dish_backend")
frontendDir = fso.BuildPath(basePath, "safu_dish_frontend")
electronDir = fso.BuildPath(basePath, "dish-electron")
nodeDir     = fso.BuildPath(basePath, "node")
userdataDir = fso.BuildPath(basePath, "userdata")

nodeExe     = fso.BuildPath(nodeDir, "node.exe")
electronCli = fso.BuildPath(electronDir, "node_modules\electron\cli.js")

tempDir    = fso.BuildPath(userdataDir, "temp")
cacheDir   = fso.BuildPath(userdataDir, "cache")
pycacheDir = fso.BuildPath(userdataDir, "pycache")

' Create userdata folders if missing
If Not fso.FolderExists(userdataDir) Then fso.CreateFolder(userdataDir)
If Not fso.FolderExists(tempDir) Then fso.CreateFolder(tempDir)
If Not fso.FolderExists(cacheDir) Then fso.CreateFolder(cacheDir)
If Not fso.FolderExists(pycacheDir) Then fso.CreateFolder(pycacheDir)

' Validate required folders/files
If Not fso.FolderExists(backendDir) Then
    MsgBox "Backend folder not found: " & backendDir, vbCritical, "DISH Error"
    WScript.Quit 1
End If

If Not fso.FolderExists(frontendDir) Then
    MsgBox "Frontend folder not found: " & frontendDir, vbCritical, "DISH Error"
    WScript.Quit 1
End If

If Not fso.FolderExists(electronDir) Then
    MsgBox "Electron folder not found: " & electronDir, vbCritical, "DISH Error"
    WScript.Quit 1
End If

If Not fso.FileExists(nodeExe) Then
    MsgBox "Portable Node not found: " & nodeExe, vbCritical, "DISH Error"
    WScript.Quit 1
End If

If Not fso.FileExists(electronCli) Then
    MsgBox "Electron CLI not found: " & electronCli, vbCritical, "DISH Error"
    WScript.Quit 1
End If

' Portable environment
Set env = sh.Environment("PROCESS")

env("DISH_PORTABLE") = "1"
env("DISH_ROOT") = basePath
env("DISH_USERDATA") = userdataDir

env("PYTHONNOUSERSITE") = "1"
env("PYTHONPYCACHEPREFIX") = pycacheDir

env("TEMP") = tempDir
env("TMP") = tempDir

env("HF_HOME") = fso.BuildPath(cacheDir, "huggingface")
env("TRANSFORMERS_CACHE") = fso.BuildPath(cacheDir, "huggingface\transformers")
env("TORCH_HOME") = fso.BuildPath(cacheDir, "torch")
env("XDG_CACHE_HOME") = cacheDir

' Critical: make portable Node available to npm/npx/electron child processes
env("PATH") = nodeDir & ";" & fso.BuildPath(backendDir, "venv\Scripts") & ";" & env("PATH")

' Launch Electron silently.
' Electron main.js handles backend and frontend startup.
electronCmd = "cmd /c cd /d """ & electronDir & """ && """ & nodeExe & """ """ & electronCli & """ ."

sh.Run electronCmd, 0, False