# Create or update a CMD shortcut that loads cmdrc.bat

$WshShell = New-Object -ComObject WScript.Shell

# Define desktop path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "CMD with GCM.lnk"

# Define the shortcut destination
$CmdPath = "$env:ComSpec"
$CmdArgs = "/k `"$env:USERPROFILE\cmdrc.bat`""

# Create or update the shortcut
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $CmdPath
$Shortcut.Arguments = $CmdArgs
$Shortcut.WorkingDirectory = "$env:USERPROFILE"
$Shortcut.WindowStyle = 1
$Shortcut.IconLocation = "$CmdPath, 0"
$Shortcut.Save()

Write-Output "✅ Shortcut created on the Desktop: 'CMD with GCM.lnk'"
Write-Output "   It will run CMD with your cmdrc.bat automatically loaded."
