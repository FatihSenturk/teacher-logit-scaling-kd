param(
    [switch]$SmokeOnly,
    [switch]$CpuSmoke
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$config = "RAFDB_teacher_vae_ce_kld.yaml"
$smokeArgs = @("tools\smoke_unified_protocol.py", "--config", "configs\$config")
if ($CpuSmoke) { $smokeArgs += "--cpu" }
python -u @smokeArgs
if ($LASTEXITCODE -ne 0) { throw "RAF-DB smoke test failed." }
if ($SmokeOnly) { return }

python -u main_encoder.py --c $config
if ($LASTEXITCODE -ne 0) { throw "RAF-DB teacher training failed." }
