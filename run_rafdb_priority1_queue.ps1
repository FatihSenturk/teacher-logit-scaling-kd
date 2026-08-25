param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [ValidateSet("noswa_seed1", "swa200_seed1", "swa200_seed43")]
    [string]$StartAt = "noswa_seed1"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Priority 1 queue (see user plan, 2026-07-17): fill out the VAE9182+224px+VICH
# student line to 3 seeds per recipe. train_rafdb_kd.py has NO --resume flag
# (unlike main_encoder.py's teacher trainer), so a crash mid-run cannot resume
# from a checkpoint -- retry here means a full restart from epoch 0. Each
# attempt gets a fresh timestamped run dir (train_rafdb_kd.py's own
# --name/save-root convention), so retries never collide with a crashed
# attempt's partial output.
#
#   noswa_seed1   : RAFDB_vae9182_betaKD_b070_T6_224_200e_noSWA, seed=1
#                   (seed42=89.928%, seed43=89.342% already exist; this
#                   completes the 3-seed set for that recipe)
#   swa200_seed1  : RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200, seed=1
#   swa200_seed43 : same recipe, seed=43
#                   (only the default-seed run, 90.059% best/89.635% SWA,
#                   exists for this recipe; these two test whether that
#                   single-seed peak is reproducible or SWA/scheduler luck)
$stages = @(
    @{ Bat = "run_rafdb_vae9182_224_vich_200e_noSWA_seed1.bat";        Name = "noswa_seed1";   EstHours = 3.5 },
    @{ Bat = "run_rafdb_vae9182_224_vich_best_400e_swa200_seed1.bat";  Name = "swa200_seed1";  EstHours = 6.9 },
    @{ Bat = "run_rafdb_vae9182_224_vich_best_400e_swa200_seed43.bat"; Name = "swa200_seed43"; EstHours = 6.9 }
)

function Invoke-Priority1Stage {
    param([string]$BatFile, [string]$StageName)

    Write-Host ""
    Write-Host "########## STAGE: $StageName ($BatFile) : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host "=== [$StageName] Attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
        # .bat ends in `pause`; redirect its stdin from NUL so the queue
        # doesn't block waiting for a keypress that will never arrive.
        # Use a full, quoted path (not a bare filename) -- relying on cmd.exe's
        # own CWD across this bash -> powershell.exe -File -> cmd /c chain is
        # fragile and was observed to fail with "not recognized as an internal
        # or external command".
        $fullBatPath = Join-Path $PSScriptRoot $BatFile
        cmd /c "`"$fullBatPath`" < NUL" | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageName] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        if ($exitCode -eq 0) {
            Write-Host "=== [$StageName] Completed successfully. ==="
            return $true
        }

        Write-Host "[$StageName] Exited non-zero. No --resume support in train_rafdb_kd.py -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }

    Write-Host "=== [$StageName] Exhausted $MaxRetries attempts without completing. ==="
    return $false
}

$stageNames = $stages | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $ok = Invoke-Priority1Stage -BatFile $stage.Bat -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping queue: stage $($stage.Name) did not complete. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Priority 1 queue completed successfully (all 3 seed runs done). ==="
exit 0
