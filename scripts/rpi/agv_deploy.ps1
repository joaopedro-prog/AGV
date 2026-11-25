param(
    [string]$RpiHost = "",
    [string]$RpiUser = "",
    [switch]$ForceBuild,
    [switch]$FollowLogs,
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

$CacheDir       = Join-Path $PSScriptRoot "offline_cache"
$CodeTarGz      = Join-Path $CacheDir "agv_code_update.tar.gz"
$ManifestCache  = Join-Path $CacheDir "last_deploy_manifest.json"
$DeployInfoFile = Join-Path $RepoRoot "src\agv_dashboard\agv_dashboard\static\deploy_info.json"
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

$swTotal = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ELETRON AGV — DEPLOY ESTILO FRC / GRADLERIO (SEM SIMULACAO)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# FASE 1: PRE-VALIDACAO LOCAL (FAIL-FAST — NUNCA QUEBRA O ROBO COM ERRO DE SINTAXE)
# ------------------------------------------------------------------------------
if (-not $SkipValidation) {
    Write-Host "`n[1/4] Validando sintaxe Python e JavaScript localmente..." -ForegroundColor Yellow
    $pyFiles = @()
    foreach ($dir in @("src\agv_brain", "src\agv_hardware", "src\agv_dashboard")) {
        $pyFiles += Get-ChildItem $dir -Recurse -Filter "*.py" | Select-Object -ExpandProperty FullName
    }
    $pyFiles += (Join-Path $RepoRoot "scripts\teleop_joy_receiver.py")
    $pyFiles += (Join-Path $RepoRoot "scripts\rpi\agv_beacon.py")

    & python -m py_compile $pyFiles
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ABORTADO] Erro de sintaxe Python encontrado! O robo NAO foi alterado." -ForegroundColor Red
        exit 1
    }

    if (Get-Command node -ErrorAction SilentlyContinue) {
        $htmlPath = Join-Path $RepoRoot "src\agv_dashboard\agv_dashboard\static\index.html"
        $html = Get-Content -Raw -Encoding UTF8 $htmlPath
        $m = [regex]::Match($html, '<script>([\s\S]*)</script>')
        if ($m.Success) {
            $tmpJs = Join-Path $env:TEMP "agv_dash_syntax_check.js"
            Set-Content -Path $tmpJs -Value $m.Groups[1].Value -Encoding UTF8
            & node --check $tmpJs
            $nodeRc = $LASTEXITCODE
            Remove-Item $tmpJs -Force -ErrorAction SilentlyContinue
            if ($nodeRc -ne 0) {
                Write-Host "`n[ABORTADO] Erro de sintaxe JavaScript no Dashboard! O robo NAO foi alterado." -ForegroundColor Red
                exit 1
            }
        }
    }
    Write-Host "  [OK] Validacao local aprovada ($($pyFiles.Count) arquivos Python + Dashboard JS)." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# FASE 2: AUTO-DISCOVERY ESTILO ROBORIO (UDP BEACON :5800 -> mDNS -> CACHE)
# ------------------------------------------------------------------------------
Write-Host "`n[2/4] Descobrindo robo ELETRON-AGV na rede..." -ForegroundColor Yellow
$discScript = Join-Path $PSScriptRoot "agv_discover.ps1"
$discParams = @{ Json = $true; Quiet = $true }
if ($RpiHost) { $discParams["PreferredHost"] = $RpiHost }
if ($RpiUser) { $discParams["PreferredUser"] = $RpiUser }

$discOut = & $discScript @discParams
if ($LASTEXITCODE -ne 0 -or -not $discOut) {
    Write-Host "  [ERRO] Robo nao encontrado na rede Eletron-AGV!" -ForegroundColor Red
    Write-Host "         Confira se voce esta conectado ao Wi-Fi/cabo do roteador Eletron-AGV." -ForegroundColor Yellow
    exit 1
}
$target = $discOut | ConvertFrom-Json
$targetHost = $target.Host
$targetUser = $target.User
Write-Host "  [OK] Alvo localizado: ${targetUser}@${targetHost} (via $($target.Method))" -ForegroundColor Green

# ------------------------------------------------------------------------------
# FASE 3: MANIFESTO DE DEPLOY + DETECCAO INTELIGENTE (FAST SYMLINK vs COLCON)
# ------------------------------------------------------------------------------
$gitCommit = "local"
$gitBranch = "unknown"
$gitDirty  = $false
try {
    $gitCommit = (git rev-parse --short HEAD 2>$null).Trim()
    $gitBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    $gitDirty  = [bool](git status --porcelain 2>$null)
} catch {}

# Calcula fingerprint estrutural (setup.py, package.xml, launch/*, lista de arquivos e compose)
$structItems = @()
foreach ($pkgDir in @("src\agv_description", "src\agv_brain", "src\agv_hardware", "src\agv_dashboard")) {
    Get-ChildItem $pkgDir -Recurse -File | Where-Object {
        $_.FullName -notmatch '__pycache__' -and
        $_.FullName -notmatch '\\(worlds|meshes)\\' -and
        $_.Name -notin @('deploy_info.json', 'launch_sim.launch.py', 'view_robot.launch.py', 'gazebo_params.yaml', 'sim_robot.rviz', 'view_bot.rviz')
    } | Sort-Object FullName | ForEach-Object {
        $rel = $_.FullName.Substring($RepoRoot.Length + 1).Replace('\', '/')
        $isMeta = ($_.Name -in @('CMakeLists.txt', 'setup.py', 'setup.cfg', 'package.xml')) -or ($rel -match '/launch/')
        if ($isMeta) {
            $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
            $structItems += "${rel}:${h}"
        } else {
            $structItems += "${rel}"
        }
    }
}
$composeHash = (Get-FileHash (Join-Path $RepoRoot "docker-compose.rpi.yml") -Algorithm SHA256).Hash
$structFingerprint = ($structItems -join "`n")

$needColcon = [bool]$ForceBuild
$needComposeUp = $true
if (Test-Path $ManifestCache) {
    try {
        $prev = Get-Content -Raw -Encoding UTF8 $ManifestCache | ConvertFrom-Json
        if (-not $ForceBuild -and $prev.target -eq $targetHost -and $prev.struct_fingerprint -eq $structFingerprint) {
            $needColcon = $false
        } else {
            $needColcon = $true
        }
        if ($prev.target -eq $targetHost -and $prev.compose_hash -eq $composeHash) {
            $needComposeUp = $false
        }
    } catch {
        $needColcon = $true
        $needComposeUp = $true
    }
} else {
    $needColcon = $true
    $needComposeUp = $true
}

$deployMode = if ($needColcon) { "FULL_COLCON" } else { "FAST_SYMLINK" }
$deployInfo = [ordered]@{
    commit      = if ($gitDirty) { "${gitCommit}*" } else { $gitCommit }
    branch      = $gitBranch
    dirty       = $gitDirty
    deployed_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    pc_name     = $env:COMPUTERNAME
    user        = $env:USERNAME
    mode        = $deployMode
}
$deployInfoJson = $deployInfo | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($DeployInfoFile, $deployInfoJson, [System.Text.UTF8Encoding]::new($false))

Write-Host "`n[3/4] Empacotando e enviando codigo [Modo: $deployMode | Commit: $($deployInfo.commit)]..." -ForegroundColor Yellow
if (Test-Path $CodeTarGz) { Remove-Item $CodeTarGz -Force }
tar -czf $CodeTarGz `
    --exclude="__pycache__" --exclude="*.pyc" `
    --exclude="src/agv_description/worlds/*" `
    --exclude="src/agv_description/meshes/*" `
    --exclude="src/agv_description/launch/launch_sim.launch.py" `
    --exclude="src/agv_description/launch/view_robot.launch.py" `
    --exclude="src/agv_description/config/gazebo_params.yaml" `
    --exclude="src/agv_description/config/sim_robot.rviz" `
    --exclude="src/agv_description/config/view_bot.rviz" `
    docker-compose.rpi.yml `
    src/agv_brain `
    src/agv_hardware `
    src/agv_dashboard `
    src/agv_description/CMakeLists.txt `
    src/agv_description/package.xml `
    src/agv_description/config `
    src/agv_description/description `
    src/agv_description/launch/rsp.launch.py `
    scripts/teleop_joy_receiver.py `
    scripts/rpi/entrypoint_rpi.sh `
    scripts/rpi/agv_beacon.py `
    scripts/rpi/99-agv-devices.rules
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar codigo." }

$sizeKb = [math]::Round((Get-Item $CodeTarGz).Length / 1KB, 1)
Write-Host "  Pacote leve: $sizeKb KB -> ${targetUser}@${targetHost}"
scp -q $CodeTarGz "${targetUser}@${targetHost}:~/agv_code_update.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "Falha ao enviar pacote via SCP." }

# ------------------------------------------------------------------------------
# FASE 4: APLICACAO NA RASPBERRY + HEALTH CHECK + AGVLOG OPCIONAL
# ------------------------------------------------------------------------------
Write-Host "`n[4/4] Aplicando no container agv_eletron_real..." -ForegroundColor Yellow
$runColconFlag = if ($needColcon) { "1" } else { "0" }
$runComposeUpFlag = if ($needComposeUp) { "1" } else { "0" }

$remoteScript = @"
set -e
mkdir -p ~/AGV/src/agv_description/worlds ~/AGV/src/agv_description/meshes
rm -rf ~/AGV/src/articubot_one
tar --warning=no-timestamp -xzf ~/agv_code_update.tar.gz -C ~/AGV
rm -f ~/agv_code_update.tar.gz
sed -i 's/\r$//' ~/AGV/scripts/rpi/*.sh ~/AGV/scripts/rpi/*.py ~/AGV/scripts/teleop_joy_receiver.py ~/AGV/docker-compose.rpi.yml
chmod +x ~/AGV/scripts/rpi/*.sh ~/AGV/scripts/rpi/*.py ~/AGV/scripts/teleop_joy_receiver.py

if [ "$runColconFlag" = "1" ]; then
  echo "[RPi] Marcando recompilacao automatica segura (FULL_COLCON) no proximo boot do container..."
  touch ~/AGV/src/agv_dashboard/.needs_colcon_build
else
  rm -f ~/AGV/src/agv_dashboard/.needs_colcon_build
  echo "[RPi] Modo FAST_SYMLINK: arquivos ja refletidos via volume montado!"
fi

cd ~/AGV
if [ "$runComposeUpFlag" = "1" ] || ! docker ps -a --format '{{.Names}}' | grep -qx 'agv_eletron_real'; then
  docker compose -f docker-compose.rpi.yml up -d --no-build --force-recreate
else
  docker compose -f docker-compose.rpi.yml restart >/dev/null
fi
docker ps --filter "name=agv_eletron_real" --format "  [OK] Container: {{.Names}} | {{.Status}}"
"@ -replace "`r", ""

$remoteScript | ssh "${targetUser}@${targetHost}" "bash -s"
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar container na Raspberry Pi." }

# Salva cache do manifesto estrutural apos envio
@{
    target             = $targetHost
    struct_fingerprint = $structFingerprint
    compose_hash       = $composeHash
    deployed_at        = $deployInfo.deployed_at
} | ConvertTo-Json -Depth 3 | Set-Content -Path $ManifestCache -Encoding UTF8

# Health check da Driver Station / Dashboard Web (mais folga quando FULL_COLCON compila no boot)
$maxWaitSec = if ($needColcon) { 100 } else { 30 }
Write-Host "  Aguardando Robot Code & Dashboard responder em http://${targetHost}:8080 (timeout ${maxWaitSec}s)..." -ForegroundColor Yellow
$readyResp = $null
for ($i = 0; $i -lt $maxWaitSec; $i++) {
    try {
        $readyResp = Invoke-RestMethod -Uri "http://${targetHost}:8080/api/status" -Method Get -TimeoutSec 2
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

$swTotal.Stop()
$elapsed = [math]::Round($swTotal.Elapsed.TotalSeconds, 1)

if ($readyResp) {
    $confirmedAt = if ($readyResp.deploy_info -and $readyResp.deploy_info.deployed_at) { $readyResp.deploy_info.deployed_at } else { $deployInfo.deployed_at }
    Write-Host "`n======================================================================" -ForegroundColor Green
    Write-Host "  DEPLOY CONCLUIDO EM ${elapsed}s [$deployMode]" -ForegroundColor Green
    Write-Host "  Robo      : $($readyResp.robot_hostname) (${targetHost})" -ForegroundColor Green
    Write-Host "  Versao    : $($deployInfo.commit) ($($deployInfo.branch)) @ $confirmedAt" -ForegroundColor Green
    Write-Host "  Dashboard : http://${targetHost}:8080" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "`n[AVISO] Container reiniciado em ${elapsed}s, mas Dashboard ainda esta subindo em http://${targetHost}:8080" -ForegroundColor Yellow
}

if ($FollowLogs) {
    Write-Host "`n[AGVLog] Conectando aos logs ao vivo (Ctrl+C para sair)..." -ForegroundColor Cyan
    ssh -t "${targetUser}@${targetHost}" "docker logs -f --tail 35 agv_eletron_real"
}
