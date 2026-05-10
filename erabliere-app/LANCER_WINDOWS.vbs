' Lanceur silencieux Érablière — Windows
' Double-cliquez sur ce fichier pour démarrer le logiciel.
' Aucune fenêtre noire n'apparaît.

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

' Trouver le dossier de ce script
ScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Chercher Python portable ou Python système
PythonPortable = ScriptDir & "\..\python_win\python.exe"
PythonSystem   = ""

If objFSO.FileExists(PythonPortable) Then
    PythonExe = PythonPortable
    LibsPath  = ScriptDir & "\..\libs_win"
Else
    ' Chercher Python dans le PATH
    For Each candidate In Array("python.exe", "python3.exe")
        On Error Resume Next
        result = objShell.Run("where " & candidate, 0, True)
        If result = 0 Then
            PythonExe = candidate
        End If
        On Error GoTo 0
    Next
    LibsPath = ""
End If

If PythonExe = "" Then
    MsgBox "Python n'est pas installé." & vbCrLf & _
           "Veuillez installer Python depuis python.org", _
           vbExclamation, "Érablière"
    WScript.Quit
End If

' Arrêter une instance déjà en cours
objShell.Run "taskkill /F /IM python.exe /FI ""WINDOWTITLE eq Erabliere*""", 0, False

' Démarrer Flask en arrière-plan (sans fenêtre)
Dim cmd
If LibsPath <> "" Then
    cmd = "cmd /c set PYTHONPATH=" & LibsPath & " && cd /d """ & ScriptDir & """ && """ & PythonExe & """ app.py"
Else
    cmd = "cmd /c cd /d """ & ScriptDir & """ && """ & PythonExe & """ app.py"
End If
objShell.Run cmd, 0, False

' Attendre que Flask démarre (3 secondes)
WScript.Sleep 3000

' Ouvrir le navigateur
objShell.Run "http://localhost:5000", 1, False
