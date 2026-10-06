param([string]$At = '08:00')
$ErrorActionPreference = 'Stop'
$MaintenanceScript = Join-Path $PSScriptRoot 'maintenance.py'
$ProjectDirectory = Split-Path -Parent $PSScriptRoot
$TaskName = 'NEXO-Mantenimiento-' + (Split-Path -Leaf (Split-Path -Parent $ProjectDirectory))
$Arguments = '"' + $MaintenanceScript + '"'
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask -and ($ExistingTask.Actions.Arguments -ne $Arguments)) {
    throw 'Ya existe una tarea con ese nombre y otra configuracion; no se reemplazo.'
}
$PythonExecutable = Join-Path $ProjectDirectory '.venv\Scripts\python.exe'
$Action = New-ScheduledTaskAction -Execute $PythonExecutable -Argument $Arguments -WorkingDirectory $ProjectDirectory
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal -UserId $Identity -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Select-Object TaskName, State
Write-Output 'Requiere que este usuario tenga sesion abierta. Consulte OPERACION.md para produccion.'
