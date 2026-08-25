import argparse
import csv
import os
import sys
import time
from pathlib import Path

import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from thop import profile
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dataset_utils.builder import build_dataloader
from models.mobilenetv2_plus import mobilenetv2_plus
from trials.models import create_model
from utils.configs import load_yaml, seed_everything


DEFAULT_TEACHER_CONFIG = (
    r"C:\Users\mfati\21mar\poster-var\logs\RAFDB\POSTERv2"
    r"\2026-03-30-13-28-13\RAFDB_posterv2_seed1_le1_seed1_le1.yaml"
)
DEFAULT_TEACHER_CKPT = (
    r"C:\Users\mfati\21mar\poster-var\logs\RAFDB\POSTERv2"
    r"\2026-03-30-13-28-13\best.pt"
)
DEFAULT_STUDENT_SWA_CKPT = (
    r"C:\Users\mfati\Desktop\15mar\checkpoints\ablation13\20260403_1250"
    r"\expE_mixup_batch64\swa_student_20260404_0027.pth"
)
DEFAULT_STUDENT_BEST_CKPT = (
    r"C:\Users\mfati\Desktop\15mar\checkpoints\ablation13\20260403_1250"
    r"\expE_mixup_batch64\best_student.pth"
)


def _load_args(config_path, device, batch_size, val_size=None):
    args = argparse.Namespace()
    load_yaml(args, str(config_path))
    args.device = device
    args.use_wandb = False
    args.use_swanlab = False
    args.train_root = None
    args.train_shuffle = False
    args.cache_img = False
    args.num_workers = 0
    args.batch_size = int(batch_size)
    if val_size is not None:
        args.val_size = int(val_size)
        args.train_size = int(val_size)
    return args


def _output_logits(output):
    if isinstance(output, dict):
        return output["logits"]
    return output[0] if isinstance(output, (tuple, list)) else output


def _clean_student_state_dict(state_dict):
    cleaned = {}
    for key, value in state_dict.items():
        if key == "n_averaged":
            continue
        if key.endswith("total_ops") or key.endswith("total_params"):
            continue
        if key.startswith("module."):
            key = key[len("module.") :]
        cleaned[key] = value
    return cleaned


def _load_teacher(config_path, ckpt_path, device):
    args = _load_args(config_path, device, batch_size=16)
    seed_everything(getattr(args, "seed", 0))
    model = create_model(args).to(device)
    ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)
    state_dict = ckpt.get("model", ckpt.get("state_dict", ckpt))
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model, args, ckpt


def _load_student(
    ckpt_path,
    device,
    num_classes=7,
    dropout=0.5,
    width_mult=1.0,
    layer_embedding=False,
    vae_head=False,
    head_type="linear",
    lightweight_layer_embedding=False,
    layer_embedding_layers=3,
    embedding_dim=None,
    use_vich_sampling=False,
):
    model = mobilenetv2_plus(
        num_classes=num_classes,
        width_mult=width_mult,
        dropout_rate=dropout,
        layer_embedding=layer_embedding,
        vae_head=vae_head,
        head_type=head_type,
        lightweight_layer_embedding=lightweight_layer_embedding,
        lightweight_layer_embedding_layers=layer_embedding_layers,
        embedding_dim=embedding_dim,
        use_vich_sampling=use_vich_sampling,
    ).to(device)
    ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)
    state_dict = ckpt.get("state_dict", ckpt.get("model_state_dict", ckpt))
    model.load_state_dict(_clean_student_state_dict(state_dict), strict=True)
    model.eval()
    return model, ckpt


def _evaluate(model, val_loader, device, name):
    y_true = []
    y_pred = []
    model.eval()
    with torch.no_grad():
        for batch in tqdm(val_loader, desc=f"{name} valid", dynamic_ncols=True):
            if len(batch) == 5:
                _idxs, images, labels, _label_em, _paths = batch
            else:
                _idxs, images, labels = batch
            images = images.to(device, non_blocking=True)
            logits = _output_logits(model(images))
            preds = logits.argmax(dim=1).detach().cpu().tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "n": len(y_true),
    }


def _count_params(model):
    return sum(p.numel() for p in model.parameters())


def _measure_flops(model, device, image_size):
    dummy = torch.randn(1, 3, image_size, image_size, device=device)
    model.eval()
    with torch.no_grad():
        macs, _ = profile(model, inputs=(dummy,), verbose=False)
    return macs


def _measure_latency(model, device, image_size, warmup=20, repeats=100):
    dummy = torch.randn(1, 3, image_size, image_size, device=device)
    model.eval()
    with torch.no_grad():
        for _ in range(warmup):
            _output_logits(model(dummy))
        if device.type == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(repeats):
            _output_logits(model(dummy))
        if device.type == "cuda":
            torch.cuda.synchronize()
    latency_ms = (time.perf_counter() - start) * 1000.0 / repeats
    fps = 1000.0 / latency_ms if latency_ms > 0 else 0.0
    return latency_ms, fps


def _row(model_name, model, metrics, ckpt_path, ckpt, device, image_size, skip_latency):
    params = _count_params(model)
    flops = _measure_flops(model, device, image_size)
    if skip_latency:
        latency_ms, fps = None, None
    else:
        latency_ms, fps = _measure_latency(model, device, image_size)

    return {
        "Model": model_name,
        "Accuracy (%)": metrics["accuracy"] * 100.0,
        "Precision (%)": metrics["precision_macro"] * 100.0,
        "Recall (%)": metrics["recall_macro"] * 100.0,
        "Macro-F1 (%)": metrics["macro_f1"] * 100.0,
        "Weighted-F1 (%)": metrics["weighted_f1"] * 100.0,
        "Params (M)": params / 1e6,
        "FLOPs (G)": flops / 1e9,
        "Size (MB)": os.path.getsize(ckpt_path) / (1024 * 1024),
        "Latency (ms)": latency_ms,
        "FPS": fps,
        "Val Samples": metrics["n"],
        "Epoch": ckpt.get("epoch", ""),
        "Checkpoint": str(ckpt_path),
    }


def _write_outputs(rows, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {out_path}")
    headers = [
        "Model",
        "Accuracy (%)",
        "Precision (%)",
        "Recall (%)",
        "Macro-F1 (%)",
        "Weighted-F1 (%)",
        "Params (M)",
        "FLOPs (G)",
        "Size (MB)",
        "Latency (ms)",
        "FPS",
    ]
    print("\nMarkdown:")
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            if value is None:
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                values.append(str(value))
        print("| " + " | ".join(values) + " |")


def parse_args():
    parser = argparse.ArgumentParser("Evaluate RAF-DB teacher/student table")
    parser.add_argument("--teacher-config", type=Path, default=Path(DEFAULT_TEACHER_CONFIG))
    parser.add_argument("--teacher-ckpt", type=Path, default=Path(DEFAULT_TEACHER_CKPT))
    parser.add_argument("--student-swa-ckpt", type=Path, default=Path(DEFAULT_STUDENT_SWA_CKPT))
    parser.add_argument("--student-best-ckpt", type=Path, default=Path(DEFAULT_STUDENT_BEST_CKPT))
    parser.add_argument("--out", type=Path, default=Path("rafdb_teacher_student_metrics_table.csv"))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--teacher-image-size", type=int, default=224)
    parser.add_argument("--student-image-size", type=int, default=256)
    parser.add_argument("--student-layer-embedding", action="store_true")
    parser.add_argument("--student-lightweight-layer-embedding", action="store_true")
    parser.add_argument("--student-layer-embedding-layers", type=int, default=3)
    parser.add_argument("--student-vae-head", action="store_true")
    parser.add_argument("--student-head-type", choices=["linear", "vich", "vae", "le_vae"], default="linear")
    parser.add_argument("--student-embedding-dim", type=int, default=None)
    parser.add_argument("--student-use-vich-sampling", action="store_true")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--skip-latency", action="store_true")
    parser.add_argument("--include-best-student", action="store_true")
    parser.add_argument("--skip-swa-student", action="store_true")
    return parser.parse_args()


def main():
    parsed = parse_args()
    if parsed.device == "auto":
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(parsed.device)
    print(f"Device: {device}")

    teacher, teacher_args, teacher_ckpt = _load_teacher(parsed.teacher_config, parsed.teacher_ckpt, device)
    teacher_data_args = _load_args(
        parsed.teacher_config,
        device,
        parsed.batch_size,
        val_size=parsed.teacher_image_size,
    )
    _train_loader, teacher_val_loader = build_dataloader(teacher_data_args)
    if teacher_val_loader is None:
        raise RuntimeError("Validation loader could not be built.")

    rows = []
    teacher_metrics = _evaluate(teacher, teacher_val_loader, device, "POSTER-Var Teacher")
    rows.append(
        _row(
            "POSTER-Var Teacher",
            teacher,
            teacher_metrics,
            parsed.teacher_ckpt,
            teacher_ckpt,
            device,
            parsed.teacher_image_size,
            parsed.skip_latency,
        )
    )
    del teacher
    if device.type == "cuda":
        torch.cuda.empty_cache()

    student_data_args = _load_args(
        parsed.teacher_config,
        device,
        parsed.batch_size,
        val_size=parsed.student_image_size,
    )
    _train_loader, student_val_loader = build_dataloader(student_data_args)
    if student_val_loader is None:
        raise RuntimeError("Student validation loader could not be built.")

    if not parsed.skip_swa_student:
        student, student_ckpt = _load_student(
            parsed.student_swa_ckpt,
            device,
            layer_embedding=parsed.student_layer_embedding,
            vae_head=parsed.student_vae_head,
            head_type=parsed.student_head_type,
            lightweight_layer_embedding=parsed.student_lightweight_layer_embedding,
            layer_embedding_layers=parsed.student_layer_embedding_layers,
            embedding_dim=parsed.student_embedding_dim,
            use_vich_sampling=parsed.student_use_vich_sampling,
        )
        student_metrics = _evaluate(student, student_val_loader, device, "MobileNetV2Plus KD + SWA")
        rows.append(
            _row(
                "MobileNetV2Plus KD + SWA",
                student,
                student_metrics,
                parsed.student_swa_ckpt,
                student_ckpt,
                device,
                parsed.student_image_size,
                parsed.skip_latency,
            )
        )
        del student
        if device.type == "cuda":
            torch.cuda.empty_cache()

    if parsed.include_best_student:
        best_student, best_ckpt = _load_student(
            parsed.student_best_ckpt,
            device,
            layer_embedding=parsed.student_layer_embedding,
            vae_head=parsed.student_vae_head,
            head_type=parsed.student_head_type,
            lightweight_layer_embedding=parsed.student_lightweight_layer_embedding,
            layer_embedding_layers=parsed.student_layer_embedding_layers,
            embedding_dim=parsed.student_embedding_dim,
            use_vich_sampling=parsed.student_use_vich_sampling,
        )
        best_metrics = _evaluate(best_student, student_val_loader, device, "MobileNetV2Plus KD")
        rows.append(
            _row(
                "MobileNetV2Plus KD",
                best_student,
                best_metrics,
                parsed.student_best_ckpt,
                best_ckpt,
                device,
                parsed.student_image_size,
                parsed.skip_latency,
            )
        )

    _write_outputs(rows, parsed.out)


if __name__ == "__main__":
    main()
