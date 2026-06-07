# Script de Configuração de Inicialização no Boot - ShortBot Webhook Gateway
# Executar este script em um PowerShell aberto como Administrador.

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Este script DEVE ser executado como Administrador para registrar tarefas no sistema."
    Write-Warning "Por favor, abra o PowerShell como Administrador e execute novamente."
    Exit
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Get-Location
}

$pythonwPath = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"
$serverPath = Join-Path $scriptDir "webhook_server.py"

if (-not (Test-Path $pythonwPath)) {
    Write-Error "Não foi possível encontrar o pythonw.exe em: $pythonwPath"
    Exit
}

if (-not (Test-Path $serverPath)) {
    Write-Error "Não foi possível encontrar o webhook_server.py em: $serverPath"
    Exit
}

Write-Host "Caminhos identificados:"
Write-Host "  Python Executável (GUI): $pythonwPath"
Write-Host "  Script do Webhook:       $serverPath"
Write-Host "  Diretório de Trabalho:   $scriptDir"
Write-Host ""

$taskName = "ShortBotWebhook"

# Remove tarefa antiga se existir para evitar conflitos
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "Tarefa antiga '$taskName' encontrada. Removendo..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Write-Host "Registrando nova Tarefa Agendada '$taskName'..."

$Action = New-ScheduledTaskAction -Execute $pythonwPath -Argument "webhook_server.py" -WorkingDirectory $scriptDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force

Write-Host ""
Write-Host "=========================================================="
Write-Host "  Tarefa '$taskName' registrada com sucesso!"
Write-Host "  Ela será iniciada em background no boot do Windows."
Write-Host "=========================================================="
Write-Host "Comandos úteis no PowerShell (Como Administrador):"
Write-Host "  Iniciar o servidor agora:  Start-ScheduledTask -TaskName '$taskName'"
Write-Host "  Parar o servidor:          Stop-ScheduledTask -TaskName '$taskName'"
Write-Host "  Verificar status:          Get-ScheduledTask -TaskName '$taskName'"
Write-Host "  Remover a inicialização:   Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
Write-Host "=========================================================="
