param(
    [string]$PreferredHost = "",
    [string]$PreferredUser = "",
    [int]$TimeoutMs = 900,
    [switch]$Json,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot "rpi_target.env"

$savedHost = ""
$savedUser = "agv"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -eq 'RPI_HOST') { $savedHost = $v }
            if ($k -eq 'RPI_USER' -and $v) { $savedUser = $v }
        }
    }
}

$targetUser = if ($PreferredUser) { $PreferredUser } else { $savedUser }

function Test-TcpPortFast([string]$TargetHost, [int]$Port = 22, [int]$WaitMs = 450) {
    $tcp = $null
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($TargetHost, $Port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne($WaitMs, $false) -and $tcp.Connected) {
            return $true
        }
    } catch {}
    finally {
        if ($tcp) { $tcp.Close() }
    }
    return $false
}

function Save-DiscoveredTarget([string]$FoundHost, [string]$FoundUser) {
    $lines = @(
        "RPI_HOST=$FoundHost"
        "RPI_USER=$FoundUser"
        "RPI_DIR=/home/$FoundUser/AGV"
    )
    Set-Content -Path $envFile -Value ($lines -join "`r`n") -Encoding UTF8
}

function Find-ViaUdpBeacon([int]$WaitMs) {
    $payload = [System.Text.Encoding]::UTF8.GetBytes("AGV_DISCOVER_V1")
    $broadcastTargets = New-Object System.Collections.Generic.HashSet[string]
    [void]$broadcastTargets.Add("255.255.255.255")

    # Calcula broadcast dirigido de cada sub-rede IPv4 ativa (funciona mesmo com multiplas placas de rede)
    try {
        $ifaces = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
            Where-Object { $_.OperationalStatus -eq 'Up' -and $_.NetworkInterfaceType -ne 'Loopback' }
        foreach ($nic in $ifaces) {
            foreach ($uni in $nic.GetIPProperties().UnicastAddresses) {
                if ($uni.Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
                    $ipBytes = $uni.Address.GetAddressBytes()
                    $maskBytes = $uni.IPv4Mask.GetAddressBytes()
                    if ($maskBytes -and $maskBytes.Length -eq 4) {
                        $bcast = [byte[]](
                            ($ipBytes[0] -bor ($maskBytes[0] -bxor 255)),
                            ($ipBytes[1] -bor ($maskBytes[1] -bxor 255)),
                            ($ipBytes[2] -bor ($maskBytes[2] -bxor 255)),
                            ($ipBytes[3] -bor ($maskBytes[3] -bxor 255))
                        )
                        [void]$broadcastTargets.Add(([System.Net.IPAddress]::new($bcast)).ToString())
                    }
                }
            }
        }
    } catch {}

    # Também tenta unicast direto no IP salvo caso broadcast seja filtrado
    if ($PreferredHost) { [void]$broadcastTargets.Add($PreferredHost) }
    if ($savedHost)     { [void]$broadcastTargets.Add($savedHost) }

    $udp = $null
    try {
        $udp = New-Object System.Net.Sockets.UdpClient(0)
        $udp.EnableBroadcast = $true
        $udp.Client.ReceiveTimeout = $WaitMs

        foreach ($dest in $broadcastTargets) {
            try {
                [void]$udp.Send($payload, $payload.Length, $dest, 5800)
            } catch {}
        }

        $deadline = [DateTime]::UtcNow.AddMilliseconds($WaitMs)
        while ([DateTime]::UtcNow -lt $deadline) {
            $remMs = [int]([Math]::Max(50, ($deadline - [DateTime]::UtcNow).TotalMilliseconds))
            $udp.Client.ReceiveTimeout = $remMs
            $remoteEP = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
            try {
                $respBytes = $udp.Receive([ref]$remoteEP)
                $respText = [System.Text.Encoding]::UTF8.GetString($respBytes)
                $parsed = $respText | ConvertFrom-Json
                if ($parsed -and $parsed.robot -eq 'ELETRON-AGV') {
                    return [pscustomobject]@{
                        Host        = $remoteEP.Address.ToString()
                        User        = if ($PreferredUser) { $PreferredUser } elseif ($parsed.ssh_user) { $parsed.ssh_user } else { $targetUser }
                        Hostname    = $parsed.hostname
                        WebPort     = if ($parsed.web_port) { [int]$parsed.web_port } else { 8080 }
                        Method      = 'UDP_BEACON_5800'
                        UptimeSec   = $parsed.uptime_s
                        DeployInfo  = $parsed.deploy_info
                    }
                }
            } catch [System.Net.Sockets.SocketException] {
                break
            } catch {}
        }
    } finally {
        if ($udp) { $udp.Close() }
    }
    return $null
}

$found = $null

# 1. Se o usuario informou explicitamente um IP/host, tenta direto primeiro
if ($PreferredHost) {
    if (Test-TcpPortFast -TargetHost $PreferredHost -Port 22 -WaitMs 500) {
        $found = [pscustomobject]@{
            Host       = $PreferredHost
            User       = $targetUser
            Hostname   = $PreferredHost
            WebPort    = 8080
            Method     = 'EXPLICIT_HOST'
            UptimeSec  = $null
            DeployInfo = $null
        }
    }
}

# 2. Beacon UDP porta 5800 (padrao FRC — acha o robo automaticamente na rede Eletron-AGV)
if (-not $found) {
    $found = Find-ViaUdpBeacon -WaitMs $TimeoutMs
}

# 3. Fallback deterministico (mDNS + ultimo IP conhecido) caso container ainda esteja parado
if (-not $found) {
    $candidates = @()
    if ($savedHost) { $candidates += @{ Host = $savedHost; Method = 'CACHED_ENV' } }
    $candidates += @{ Host = 'agv-raspberry.local'; Method = 'MDNS_LOCAL' }
    $candidates += @{ Host = 'agv-eletron.local';   Method = 'MDNS_LOCAL' }

    foreach ($cand in $candidates) {
        if (Test-TcpPortFast -TargetHost $cand.Host -Port 22 -WaitMs 500) {
            $resolvedIp = $cand.Host
            try {
                $addrs = [System.Net.Dns]::GetHostAddresses($cand.Host) |
                    Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork }
                if ($addrs -and $addrs.Count -gt 0) { $resolvedIp = $addrs[0].ToString() }
            } catch {}
            $found = [pscustomobject]@{
                Host       = $resolvedIp
                User       = $targetUser
                Hostname   = $cand.Host
                WebPort    = 8080
                Method     = $cand.Method
                UptimeSec  = $null
                DeployInfo = $null
            }
            break
        }
    }
}

if (-not $found) {
    if (-not $Quiet) {
        Write-Host "[DISCOVERY] Nenhum robo ELETRON-AGV encontrado na rede." -ForegroundColor Red
        Write-Host "            Verifique se seu PC esta conectado no Wi-Fi/cabo do roteador Eletron-AGV." -ForegroundColor Yellow
    }
    exit 1
}

# Atualiza rpi_target.env se o IP mudou
if ($found.Host -and $found.Host -ne $savedHost) {
    Save-DiscoveredTarget -FoundHost $found.Host -FoundUser $found.User
}

if ($Json) {
    $found | ConvertTo-Json -Depth 4
} elseif (-not $Quiet) {
    $depStr = ""
    if ($found.DeployInfo -and $found.DeployInfo.commit) {
        $depStr = " | Deploy: $($found.DeployInfo.commit) ($($found.DeployInfo.deployed_at))"
    }
    Write-Host "[DISCOVERY] Robo encontrado: $($found.User)@$($found.Host) via $($found.Method) | Dashboard: http://$($found.Host):$($found.WebPort)$depStr" -ForegroundColor Green
}
