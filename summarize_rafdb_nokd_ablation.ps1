param(
    [string]$ResultsRoot = "results"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$items = Get-ChildItem -Path $ResultsRoot -Recurse -Filter metrics_best.json -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "rafdb_nokd" } |
    ForEach-Object {
        $m = Get-Content -Raw $_.FullName | ConvertFrom-Json
        [pscustomobject]@{
            Run = Split-Path (Split-Path $_.DirectoryName -Parent) -Leaf
            Stamp = Split-Path $_.DirectoryName -Leaf
            Accuracy = [math]::Round([double]$m.accuracy, 4)
            MacroF1 = [math]::Round([double]$m.macro_f1, 4)
            WeightedF1 = [math]::Round([double]$m.weighted_f1, 4)
            ParamsM = [math]::Round([double]$m.params_m, 6)
            Head = $m.head
            BetaVich = $m.beta_vich
            FeatureDim = $m.feature_dim
            BestEpoch = $m.best_epoch
            Checkpoint = $m.checkpoint
        }
    } | Sort-Object Accuracy -Descending

$items | Format-Table -AutoSize
