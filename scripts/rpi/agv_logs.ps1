param(
    [string]$RpiHost = "",
    [int]$Tail = 50
)

$ErrorActionPreference = "Stop"
$discScript = Join-Path $PSScriptRoot "agv_discover.ps1"
$discParams = @{ Json = $true; Quiet = $true }
if ($RpiHost) { $discParams["PreferredHost"] = $RpiHost }

$discOut = & $discScript @discParams
if ($LASTEXITCODE -ne 0 -or -not $discOut) {
    Write-Host "[AGVLog] Robo nao encontrado na rede Eletron-AGV." -ForegroundColor Red
    exit 1
}
$target = $discOut | ConvertFrom-Json
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  AGVLog (estilo RioLog) — $($target.User)@$($target.Host) (Ctrl+C para sair)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
ssh -t "$($target.User)@$($target.Host)" "docker logs -f --tail $Tail agv_eletron_real"
