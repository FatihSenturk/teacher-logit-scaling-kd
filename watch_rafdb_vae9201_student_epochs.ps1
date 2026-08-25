param(
    [string]$RunDir = "",
    [int]$PollSeconds = 20,
    [int]$Tail = 12
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not $RunDir) {
    $root = Join-Path $PSScriptRoot "results\unified_students\RAFDB_vae9201_betaKD_b070_T6_224_200e_noSWA"
    $latest = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No run directory found under $root"
    }
    $RunDir = $latest.FullName
}

$csvPath = Join-Path $RunDir "training_log.csv"
Write-Host "Watching run: $RunDir"
Write-Host "CSV: $csvPath"
Write-Host "Poll seconds: $PollSeconds"
Write-Host ""

$lastEpoch = -1

while ($true) {
    if (-not (Test-Path $csvPath)) {
        Write-Host "training_log.csv not found yet. Waiting..."
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $rows = @(Import-Csv -Path $csvPath)
    if ($rows.Count -eq 0) {
        Write-Host "No epoch rows yet. Waiting..."
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $current = $rows[-1]
    $epoch = [int]$current.epoch
    if ($epoch -ne $lastEpoch) {
        Clear-Host
        Write-Host "Watching run: $RunDir"
        Write-Host "Last update: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        Write-Host ""
        Write-Host ("Latest epoch {0}: val_acc={1:N4}% train_acc={2:N4}% val_loss={3:N4} train_loss={4:N4} lr={5}" -f `
            $epoch,
            [double]$current.val_acc,
            [double]$current.train_acc,
            [double]$current.val_loss,
            [double]$current.train_loss,
            $current.lr)
        Write-Host ""
        Write-Host "Recent epochs:"
        $rows | Select-Object -Last $Tail |
            Format-Table `
                @{Label="epoch"; Expression={[int]$_.epoch}; Width=6},
                @{Label="val_acc"; Expression={"{0:N4}" -f [double]$_.val_acc}; Width=10},
                @{Label="train_acc"; Expression={"{0:N4}" -f [double]$_.train_acc}; Width=10},
                @{Label="val_loss"; Expression={"{0:N4}" -f [double]$_.val_loss}; Width=10},
                @{Label="train_loss"; Expression={"{0:N4}" -f [double]$_.train_loss}; Width=11},
                @{Label="lr"; Expression={$_.lr}; Width=14} `
                -AutoSize
        $lastEpoch = $epoch
    }

    Start-Sleep -Seconds $PollSeconds
}
