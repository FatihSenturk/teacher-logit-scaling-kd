param(
    [string]$WorkDir = "D:\Veriseti\poster-var"
)

$ErrorActionPreference = "Stop"

$configs = @(
    "FERPlus_8_ce_kld_10e_lr3e5_sam_pretrain_f01v2.yaml",
    "FERPlus_8_ce_kld_10e_lr3e5_sam_pretrain_f12v0.yaml"
)

$logDir = Join-Path $WorkDir "sweep_logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Write-Output "Starting FER+ other-splits 10-epoch pretrain runs..."
foreach ($cfg in $configs) {
    $ts = Get-Date -Format "yyyy-MM-dd-HH-mm-ss"
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($cfg)
    $log = Join-Path $logDir "$ts-$baseName.log"

    Write-Output "Running config: $cfg"
    Write-Output "  log: $log"
    Write-Output "  (Foreground run, Ctrl+C stops training)"

    Push-Location $WorkDir
    try {
        $oldEap = $ErrorActionPreference
        $oldNativeEap = $null
        if ($PSVersionTable.PSVersion.Major -ge 7) {
            $oldNativeEap = $PSNativeCommandUseErrorActionPreference
            $PSNativeCommandUseErrorActionPreference = $false
        }
        $ErrorActionPreference = "Continue"
        try {
            & python -u main_encoder.py --c $cfg 2>&1 | Tee-Object -FilePath $log
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $oldEap
            if ($PSVersionTable.PSVersion.Major -ge 7 -and $null -ne $oldNativeEap) {
                $PSNativeCommandUseErrorActionPreference = $oldNativeEap
            }
        }
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        Write-Error "Run failed for $cfg with exit code $exitCode. Check: $log"
        exit $exitCode
    }
}

Write-Output "All runs completed."
