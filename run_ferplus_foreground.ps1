param(
    [string]$WorkDir = "D:\Veriseti\poster-var",
    [string]$Config = "FERPlus_8_ce_kld_200e_lr3e5_sam_f021.yaml",
    [switch]$LogToFile
)

$ErrorActionPreference = "Stop"

$logDir = Join-Path $WorkDir "sweep_logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$ts = Get-Date -Format "yyyy-MM-dd-HH-mm-ss"
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($Config)
$log = Join-Path $logDir "$ts-$baseName.log"

Write-Output "Running config: $Config"
Write-Output "log: $log"
Write-Output "Foreground run active. Press Ctrl+C to stop."
if ($LogToFile) {
    Write-Output "Log mode enabled. tqdm may render as plain lines in terminal."
} else {
    Write-Output "Live tqdm mode enabled (no output piping)."
}

Push-Location $WorkDir
try {
    if ($LogToFile) {
        $oldEap = $ErrorActionPreference
        $oldNativeEap = $null
        if ($PSVersionTable.PSVersion.Major -ge 7) {
            $oldNativeEap = $PSNativeCommandUseErrorActionPreference
            $PSNativeCommandUseErrorActionPreference = $false
        }
        $ErrorActionPreference = "Continue"
        try {
            & python -u main_encoder.py --c $Config 2>&1 | Tee-Object -FilePath $log
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $oldEap
            if ($PSVersionTable.PSVersion.Major -ge 7 -and $null -ne $oldNativeEap) {
                $PSNativeCommandUseErrorActionPreference = $oldNativeEap
            }
        }
    } else {
        & python -u main_encoder.py --c $Config
        $exitCode = $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Error "Run failed with exit code $exitCode. Check: $log"
    exit $exitCode
}

Write-Output "Run completed."
