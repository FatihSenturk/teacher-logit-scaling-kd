param(
    [Parameter(Mandatory = $true)]
    [string]$RafTeacherCheckpoint,
    [Parameter(Mandatory = $true)]
    [string]$FerTeacherCheckpoint,
    [int]$Epochs = 200,
    [switch]$CloudSwanLab,
    [switch]$SmokeOnly
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$maxTrain = if ($SmokeOnly) { 1 } else { 0 }
$maxVal = if ($SmokeOnly) { 1 } else { 0 }
$runEpochs = if ($SmokeOnly) { 1 } else { $Epochs }
$cloudArg = if ($CloudSwanLab) { @("-CloudSwanLab") } else { @() }

foreach ($resolution in @(224, 112, 256)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run_rafdb_unified_student.ps1 `
        -TeacherCheckpoint $RafTeacherCheckpoint -Resolution $resolution -Epochs $runEpochs `
        -MaxTrainBatches $maxTrain -MaxValBatches $maxVal @cloudArg
    if ($LASTEXITCODE -ne 0) { throw "RAF-DB $resolution run failed." }

    foreach ($classes in @(7, 8)) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File .\run_affectnetplus_unified_student.ps1 `
            -Classes $classes -Resolution $resolution -Epochs $runEpochs `
            -MaxTrainBatches $maxTrain -MaxValBatches $maxVal @cloudArg
        if ($LASTEXITCODE -ne 0) { throw "AffectNet+ $classes-class $resolution run failed." }
    }

    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run_ferplus_unified_student.ps1 `
        -TeacherCheckpoint $FerTeacherCheckpoint -Resolution $resolution -Epochs $runEpochs `
        -MaxTrainBatches $maxTrain -MaxValBatches $maxVal @cloudArg
    if ($LASTEXITCODE -ne 0) { throw "FERPlus $resolution run failed." }
}
