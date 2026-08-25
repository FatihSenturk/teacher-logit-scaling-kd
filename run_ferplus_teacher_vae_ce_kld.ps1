param(
    [switch]$SmokeOnly,
    [switch]$CpuSmoke
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$config = "FERPlus_8_teacher_vae_ce_kld.yaml"
$smokeArgs = @(
    "tools\smoke_unified_protocol.py",
    "--config", "configs\$config",
    "--expected-train-samples", "28259",
    "--expected-val-samples", "3153"
)
if ($CpuSmoke) { $smokeArgs += "--cpu" }
python -u @smokeArgs
if ($LASTEXITCODE -ne 0) { throw "FERPlus smoke test failed." }
if ($SmokeOnly) { return }

python -u main_encoder.py --c $config
if ($LASTEXITCODE -ne 0) { throw "FERPlus teacher training failed." }
