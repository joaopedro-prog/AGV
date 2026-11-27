param(
    [string]$RpiHost = "",
    [string]$RpiUser = "",
    [switch]$SkipBuild,
    [switch]$SkipDownloadDebs
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

# Carrega destino padrao de scripts/rpi/rpi_target.env
$envFile = Join-Path $PSScriptRoot "rpi_target.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -eq 'RPI_HOST' -and -not $RpiHost) { $RpiHost = $v }
            if ($k -eq 'RPI_USER' -and -not $RpiUser) { $RpiUser = $v }
        }
    }
}
if (-not $RpiHost) { $RpiHost = "192.168.0.101" }
if (-not $RpiUser) { $RpiUser = "agv" }

$CacheDir   = Join-Path $PSScriptRoot "offline_cache"
$DebDir     = Join-Path $CacheDir "docker_debs"
$ImgTarGz   = Join-Path $CacheDir "agv-eletron-rpi.tar.gz"
$CodeTarGz  = Join-Path $CacheDir "agv_code_bundle.tar.gz"
New-Item -ItemType Directory -Force -Path $DebDir | Out-Null

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ELETRON AGV — INSTALACAO 100% OFFLINE NA RASPBERRY PI (ARM64)" -ForegroundColor Cyan
Write-Host "  Destino: ${RpiUser}@${RpiHost} (SEM SIMULACAO / SEM GAZEBO)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Baixa pacotes .deb oficiais do Docker Engine ARM64 para Ubuntu 22.04 (Jammy)
if (-not $SkipDownloadDebs) {
    Write-Host "`n[1/5] Verificando pacotes .deb ARM64 do Docker Engine (Ubuntu 22.04)..." -ForegroundColor Yellow
    $baseUrl = "https://download.docker.com/linux/ubuntu/dists/jammy/pool/stable/arm64/"
    $html = (Invoke-WebRequest -Uri $baseUrl -UseBasicParsing).Content
    $links = [regex]::Matches($html, 'href="([^"]+\.deb)"') | ForEach-Object { $_.Groups[1].Value }
    $pkgs = @('containerd.io_', 'docker-ce-cli_', 'docker-ce_', 'docker-buildx-plugin_', 'docker-compose-plugin_')
    foreach ($prefix in $pkgs) {
        $existing = Get-ChildItem $DebDir -Filter "$prefix*.deb" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existing) {
            Write-Host "  [OK] Em cache: $($existing.Name)"
            continue
        }
        $latest = ($links | Where-Object { $_ -like "$prefix*" } | Sort-Object)[-1]
        $dest = Join-Path $DebDir $latest
        Write-Host "  Baixando $latest ..."
        Invoke-WebRequest -Uri ($baseUrl + $latest) -OutFile $dest -UseBasicParsing
    }
}

# 2. Compila imagem ARM64 enxuta (Dockerfile.rpi) e exporta compactada
if (-not $SkipBuild) {
    Write-Host "`n[2/5] Compilando imagem Docker ARM64 (agv-eletron-rpi:latest, sem simulacao)..." -ForegroundColor Yellow
    docker buildx build --platform linux/arm64 -f Dockerfile.rpi -t agv-eletron-rpi:latest --load .
    if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar Dockerfile.rpi para linux/arm64." }
}

Write-Host "`n[3/5] Exportando imagem agv-eletron-rpi:latest e empacotando codigo (sem mundos/simulacao)..." -ForegroundColor Yellow
if (-not (Test-Path $ImgTarGz) -or -not $SkipBuild) {
    $imgTar = Join-Path $CacheDir "agv-eletron-rpi.tar"
    docker save -o $imgTar agv-eletron-rpi:latest
    if ($LASTEXITCODE -ne 0) { throw "Falha no docker save." }

    # Compacta em .tar.gz via .NET GZipStream para envio rapido na rede local
    $inStream  = [System.IO.File]::OpenRead($imgTar)
    $outStream = [System.IO.File]::Create($ImgTarGz)
    $gzip      = New-Object System.IO.Compression.GzipStream($outStream, [System.IO.Compression.CompressionLevel]::Fastest)
    try {
        $inStream.CopyTo($gzip)
    } finally {
        $gzip.Dispose(); $outStream.Dispose(); $inStream.Dispose()
    }
    Remove-Item $imgTar -Force
}
$imgMb = [math]::Round((Get-Item $ImgTarGz).Length / 1MB, 1)
Write-Host "  [OK] Imagem compactada: $ImgTarGz ($imgMb MB)"

# Empacota apenas codigo de producao do robo real (sem worlds, meshes, .git ou simulacao)
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
    scripts/rpi/99-agv-devices.rules `
    scripts/rpi/rpi_remote_setup_offline.sh
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar codigo de producao." }

# 4. Envia tudo via SSH/SCP para a Raspberry Pi
Write-Host "`n[4/5] Enviando pacotes para ${RpiUser}@${RpiHost}..." -ForegroundColor Yellow
ssh "${RpiUser}@${RpiHost}" "mkdir -p ~/AGV ~/agv_offline_bundle/docker_debs"
if ($LASTEXITCODE -ne 0) { throw "Falha de conexao SSH com ${RpiUser}@${RpiHost}." }

scp (Join-Path $DebDir "*.deb") "${RpiUser}@${RpiHost}:~/agv_offline_bundle/docker_debs/"
scp $ImgTarGz "${RpiUser}@${RpiHost}:~/agv_offline_bundle/agv-eletron-rpi.tar.gz"
scp $CodeTarGz "${RpiUser}@${RpiHost}:~/agv_offline_bundle/agv_code_bundle.tar.gz"

# 5. Descompacta e roda instalacao offline na Raspberry Pi
Write-Host "`n[5/5] Executando instalacao offline do Docker e subindo AGV na Raspberry Pi..." -ForegroundColor Yellow
$extractScript = @'
set -e
mkdir -p ~/AGV
tar --warning=no-timestamp -xzf ~/agv_offline_bundle/agv_code_bundle.tar.gz -C ~/AGV
sed -i 's/\r$//' ~/AGV/scripts/rpi/*.sh ~/AGV/scripts/teleop_joy_receiver.py ~/AGV/docker-compose.rpi.yml
chmod +x ~/AGV/scripts/rpi/*.sh ~/AGV/scripts/teleop_joy_receiver.py
'@ -replace "`r", ""

$extractScript | ssh "${RpiUser}@${RpiHost}" "bash -s"
if ($LASTEXITCODE -ne 0) { throw "Falha ao extrair codigo na Raspberry Pi." }

ssh -t "${RpiUser}@${RpiHost}" "sudo bash ~/AGV/scripts/rpi/rpi_remote_setup_offline.sh"
if ($LASTEXITCODE -ne 0) { throw "Falha na execucao remota na Raspberry Pi." }

Write-Host "`n[CONCLUIDO] Robo pronto em http://${RpiHost}:8080" -ForegroundColor Green
Write-Host "Para atualizacoes futuras de codigo (1 clique, ~15s), use: deploy_rpi.bat" -ForegroundColor Green
