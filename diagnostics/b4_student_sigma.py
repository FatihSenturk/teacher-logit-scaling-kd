"""Throwaway diagnostic: student-side VICH sigma^2 collapse check (B4, second half).
Loads the completed baseline run's best_checkpoint.pth
(kd_logs_rafdb_newrecipe_lightle_swa/rafdb_newrecipe_baseline_lightle_swa_150e/2026-07-16-01-50-24)
and runs it over the val split to report student logvar percentiles.
Read-only, no training code modified.
"""
import json
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_mu_logvar, clean_state_dict  # noqa: E402
from train_rafdb_kd import build_loaders, build_student  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def percentile(t, q):
    return torch.quantile(t.float(), q).item()


def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    data_args = SimpleNamespace(
        aligned_dir=Path("data/rafdb_aligned"),
        metadata=Path("data/rafdb_aligned/metadata_rafdb_poster_var.csv"),
        train_folds=[2], val_folds=[3], train_frac=1.0, val_frac=1.0,
        batch_size=64, workers=0, img_size=224, resize_size=0,
        augment_preset="kd", rotation_degrees=12.0, color_jitter=0.2,
        random_erasing_p=0.1, ra_mag=7, balanced_sampler=False,
        class_weight_mode="none", class_weight_beta=0.9999,
        no_train_augment=False, teacher_cache=None,
    )
    _train_loader, val_loader = build_loaders(data_args)

    student_args = SimpleNamespace(
        student_head_type="vich", width_mult=1.0, dropout=0.5,
        student_layer_embedding=True, student_vae_head=False,
        student_lightweight_layer_embedding=True, student_layer_embedding_layers=3,
        student_embedding_dim=768, student_feature_adapter_dim=0,
        use_vich_sampling=False, vich_logvar_min=-10.0, vich_logvar_max=10.0,
        vich_init_logvar_bias=-5.0, student_pretrained=False,
    )
    student = build_student(student_args, device)
    ckpt_path = PROJECT_ROOT / "kd_logs_rafdb_newrecipe_lightle_swa" / "rafdb_newrecipe_baseline_lightle_swa_150e" / "2026-07-16-01-50-24" / "best_checkpoint.pth"
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    student.load_state_dict(clean_state_dict(ckpt["model_state_dict"]), strict=True)
    student.eval()

    all_logvar = []
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device, non_blocking=True)
            output = student(images)
            _mu, logvar = extract_mu_logvar(output)
            if logvar is not None:
                all_logvar.append(logvar.mean(dim=1).cpu())

    result = {"student_ckpt": str(ckpt_path), "best_epoch": ckpt.get("epoch")}
    if all_logvar:
        lv = torch.cat(all_logvar)
        result.update({
            "student_mean_logvar_min": percentile(lv, 0.0),
            "student_mean_logvar_p25": percentile(lv, 0.25),
            "student_mean_logvar_median": percentile(lv, 0.50),
            "student_mean_logvar_p75": percentile(lv, 0.75),
            "student_mean_logvar_max": percentile(lv, 1.0),
        })
    else:
        result["error"] = "student did not expose mu/logvar"
    print(json.dumps(result, indent=2))
    (PROJECT_ROOT / "diagnostics" / "b4_student_sigma_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
