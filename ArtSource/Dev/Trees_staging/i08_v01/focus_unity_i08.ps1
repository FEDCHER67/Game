Start-Sleep -Seconds 3
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class G23FocusOnce { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }'
$g23EditorProcess = Get-Process Unity | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
[G23FocusOnce]::SetForegroundWindow($g23EditorProcess.MainWindowHandle)
