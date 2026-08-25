param(
    [string]$Dataset = "AffectNetPlus",
    [string]$Model = "POSTERv2",
    [string]$RunDir = "",
    [string]$OutputLog = "",
    [int]$PollSeconds = 30,
    [int]$TailLines = 60,
    [switch]$Once,
    [switch]$NoClear
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Format-BytesMB {
    param([long]$Bytes)
    if ($Bytes -le 0) { return "0 MB" }
    return ("{0:N1} MB" -f ($Bytes / 1MB))
}

function Format-Age {
    param([datetime]$Time)
    $age = (Get-Date) - $Time
    if ($age.TotalSeconds -lt 60) { return ("{0:N0}s ago" -f $age.TotalSeconds) }
    if ($age.TotalMinutes -lt 60) { return ("{0:N1}m ago" -f $age.TotalMinutes) }
    return ("{0:N1}h ago" -f $age.TotalHours)
}

function Resolve-RunDir {
    if ($RunDir) {
        $resolved = Resolve-Path -Path $RunDir -ErrorAction Stop
        return $resolved.Path
    }

    $base = Join-Path $PSScriptRoot "results\teacher_logs\$Dataset\$Model"
    if (-not (Test-Path $base)) {
        return $null
    }

    $latest = Get-ChildItem -Path $base -Directory |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latest) { return $latest.FullName }
    return $null
}

function Resolve-OutputLog {
    param([string]$SelectedRunDir)

    if ($OutputLog) {
        $resolved = Resolve-Path -Path $OutputLog -ErrorAction Stop
        return $resolved.Path
    }

    $logRoot = Join-Path $PSScriptRoot "run_logs"
    if (-not (Test-Path $logRoot)) {
        return $null
    }

    $logs = Get-ChildItem -Path $logRoot -Filter "*.out.log"

    if ($SelectedRunDir -and (Test-Path $SelectedRunDir)) {
        $runItem = Get-Item $SelectedRunDir
        $windowStart = $runItem.CreationTime.AddMinutes(-5)
        $logs = $logs | Where-Object {
            $_.CreationTime -ge $windowStart -and $_.CreationTime -le (Get-Date).AddMinutes(1)
        }
    }

    $latest = $logs |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latest) { return $latest.FullName }
    return $null
}

function Write-GpuStatus {
    Write-Host ""
    Write-Host "GPU"
    try {
        $gpu = & nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0 -and $gpu) {
            foreach ($line in $gpu) {
                $parts = $line -split ",\s*"
                if ($parts.Count -ge 5) {
                    Write-Host ("  {0}: util {1}%, mem {2}/{3} MiB, temp {4}C" -f $parts[0], $parts[1], $parts[2], $parts[3], $parts[4])
                } else {
                    Write-Host "  $line"
                }
            }
        } else {
            Write-Host "  nvidia-smi output unavailable"
        }
    } catch {
        Write-Host "  nvidia-smi unavailable"
    }
}

function Write-CheckpointStatus {
    param([string]$Dir)

    Write-Host ""
    Write-Host "Checkpoints"
    foreach ($name in @("last.pt", "best.pt")) {
        $path = Join-Path $Dir $name
        if (Test-Path $path) {
            $item = Get-Item $path
            Write-Host ("  {0}: {1}, modified {2} ({3})" -f $name, (Format-BytesMB $item.Length), $item.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), (Format-Age $item.LastWriteTime))
        } else {
            Write-Host ("  {0}: not created yet" -f $name)
        }
    }
}

function Write-RunFiles {
    param([string]$Dir)

    Write-Host ""
    Write-Host "Latest Run Files"
    Get-ChildItem -Path $Dir -Force -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 8 |
        ForEach-Object {
            $size = if ($_.PSIsContainer) { "<dir>" } else { Format-BytesMB $_.Length }
            Write-Host ("  {0,-42} {1,12}  {2}" -f $_.Name, $size, $_.LastWriteTime.ToString("HH:mm:ss"))
        }
}

function Write-LogTail {
    param([string]$LogPath)

    Write-Host ""
    Write-Host "Output Log"
    if (-not $LogPath -or -not (Test-Path $LogPath)) {
        Write-Host "  no run_logs/*.out.log file selected"
        Write-Host "  note: if training was started directly in a terminal, tqdm output stays in that terminal."
        return
    }

    $item = Get-Item $LogPath
    Write-Host ("  {0} ({1}, modified {2})" -f $LogPath, (Format-BytesMB $item.Length), (Format-Age $item.LastWriteTime))
    Write-Host ""

    $lines = Get-Content -Path $LogPath -Tail $TailLines -ErrorAction SilentlyContinue
    $interesting = $lines | Where-Object {
        $_ -match "epoch:" -or
        $_ -match "best_" -or
        $_ -match "loss=" -or
        $_ -match "Traceback" -or
        $_ -match "RuntimeError" -or
        $_ -match "CUDA" -or
        $_ -match "out of memory" -or
        $_ -match "Building " -or
        $_ -match "Samples:"
    }

    if ($interesting) {
        $interesting | Select-Object -Last $TailLines | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  no interesting lines in the latest tail yet"
    }
}

while ($true) {
    $selectedRunDir = Resolve-RunDir
    $selectedOutputLog = Resolve-OutputLog -SelectedRunDir $selectedRunDir

    if (-not $NoClear) {
        Clear-Host
    }

    Write-Host ("Training Watch - {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("Dataset/Model: {0}/{1}" -f $Dataset, $Model)

    if ($selectedRunDir) {
        Write-Host ("RunDir: {0}" -f $selectedRunDir)
        Write-CheckpointStatus -Dir $selectedRunDir
        Write-RunFiles -Dir $selectedRunDir
    } else {
        Write-Host "RunDir: not found yet"
    }

    Write-GpuStatus
    Write-LogTail -LogPath $selectedOutputLog

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $PollSeconds
}
