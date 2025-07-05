# install_cmdrc.ps1 - Crea o actualiza un acceso directo al CMD que cargue cmdrc.bat

$WshShell = New-Object -ComObject WScript.Shell

# Definir ruta del escritorio
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "CMD with GCM.lnk"

# Definir el destino del acceso directo
$CmdPath = "$env:ComSpec"
$CmdArgs = "/k `"$env:USERPROFILE\cmdrc.bat`""

# Crear o actualizar el acceso directo
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $CmdPath
$Shortcut.Arguments = $CmdArgs
$Shortcut.WorkingDirectory = "$env:USERPROFILE"
$Shortcut.WindowStyle = 1
$Shortcut.IconLocation = "$CmdPath, 0"
$Shortcut.Save()

Write-Output "✅ Acceso directo creado en el Escritorio: 'CMD with GCM.lnk'"
Write-Output "   Ejecutará CMD con tu cmdrc.bat cargado automáticamente."
