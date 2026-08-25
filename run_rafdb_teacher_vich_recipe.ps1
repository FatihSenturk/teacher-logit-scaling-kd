$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
python -u main_encoder.py --c RAFDB_posterv2_vich_recipe.yaml
if ($LASTEXITCODE -ne 0) { throw "RAF-DB VICH (published-recipe) teacher training failed." }
