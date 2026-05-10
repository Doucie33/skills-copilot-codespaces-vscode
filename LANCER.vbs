' ════════════════════════════════════════════════════════
'  ÉRABLIÈRE — Lanceur Windows
'  Double-cliquez sur ce fichier pour démarrer le logiciel.
'  Aucune fenêtre noire. Le navigateur s'ouvre automatiquement.
' ════════════════════════════════════════════════════════
Option Explicit

Dim WshShell, FSO, strDir, pythonExe, strCmd, result

Set WshShell = WScript.CreateObject("WScript.Shell")
Set FSO      = WScript.CreateObject("Scripting.FileSystemObject")

' Dossier de la clé USB (là où se trouve ce fichier)
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' ── Trouver Python ────────────────────────────────────────────────────────────
pythonExe = ""

' Essayer pythonw.exe en premier (pas de fenêtre noire du tout)
Dim candidates(5)
candidates(0) = "pythonw"
candidates(1) = "pythonw.exe"
candidates(2) = "python3"
candidates(3) = "python"
candidates(4) = "py -3"
candidates(5) = "py"

Dim i
For i = 0 To 5
    On Error Resume Next
    result = WshShell.Run("cmd /c " & candidates(i) & " --version >nul 2>&1", 0, True)
    If Err.Number = 0 And result = 0 Then
        pythonExe = candidates(i)
        Exit For
    End If
    Err.Clear
    On Error GoTo 0
Next

' ── Python introuvable → message d'aide ───────────────────────────────────────
If pythonExe = "" Then
    Dim msg
    msg = "Python n'est pas installé sur cet ordinateur." & vbCrLf & vbCrLf & _
          "Pour installer Python gratuitement :" & vbCrLf & _
          "  1. Cliquez OK pour ouvrir le site officiel" & vbCrLf & _
          "  2. Téléchargez Python 3" & vbCrLf & _
          "  3. IMPORTANT : cochez ""Add Python to PATH""" & vbCrLf & _
          "  4. Relancez LANCER.vbs" & vbCrLf & vbCrLf & _
          "Installation unique (~2 minutes)"

    WshShell.Popup msg, 0, "Érablière — Python requis", 48 + 1
    WshShell.Run "https://www.python.org/downloads/", 1, False
    WScript.Quit
End If

' ── Lancer lancer.py sans fenêtre noire ──────────────────────────────────────
' windowStyle = 0 → fenêtre cachée
' bWaitOnReturn = False → ne pas bloquer VBS pendant que l'app tourne
strCmd = pythonExe & " """ & strDir & "\lancer.py"""
WshShell.Run strCmd, 0, False

WScript.Quit
