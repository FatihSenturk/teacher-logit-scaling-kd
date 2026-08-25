@echo off
cd /d "%~dp0"

python train_rafdb_kd.py ^
  --teacher-ckpt "checkpoints\teacher_ce9241_best.pt" ^
  --teacher-input-size 224 ^
  --aligned-dir "data\rafdb_aligned" ^
  --metadata "data\rafdb_aligned\metadata_rafdb_poster_var.csv" ^
  --name RAFDB_ce9241_betaKD_b070_T6_224_feat003_amp_classw ^
  --save-root "results\unified_students" ^
  --epochs 200 ^
  --batch-size 64 ^
  --workers 0 ^
  --img-size 224 ^
  --resize-size 0 ^
  --augment-preset kd ^
  --student-head-type vich ^
  --student-layer-embedding ^
  --student-lightweight-layer-embedding ^
  --student-layer-embedding-layers 3 ^
  --no-vich-sampling ^
  --alpha 0.3 ^
  --temperature 6 ^
  --label-smoothing 0.1 ^
  --mixup 0.1 ^
  --feature-distill-weight 0.03 ^
  --feature-distill-mode mse_cosine ^
  --use-amp ^
  --class-weight-mode effective_number ^
  --class-weight-beta 0.9999 ^
  --scheduler-name cosine_warm_restarts ^
  --min-lr 1e-6 ^
  --gamma 0.98 ^
  --scheduler-t0 10 ^
  --scheduler-t-mult 2 ^
  --swa ^
  --swa-start 90 ^
  --swa-lr 0.0001

pause
