import argparse
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_utils.builder import build_dataloader
from kd_common import extract_logits, unpack_image_batch
from models.mobilenetv2_plus import mobilenetv2_plus
from trials.models import create_model
from utils.configs import load_yaml


EXPECTED_STUDENT_PARAMS = {
    7: 2_248_291,
    8: 2_250_853,
}


def main(args):
    config = argparse.Namespace()
    load_yaml(config, str(args.config))
    config.num_workers = 0
    config.batch_size = min(int(config.batch_size), 2)
    config.cache_img = False
    config.device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda:0")

    teacher = create_model(config).to(config.device).eval()
    train_loader, val_loader = build_dataloader(config)
    if train_loader is None or val_loader is None:
        raise RuntimeError("Teacher smoke test requires train and validation loaders.")
    if args.expected_train_samples and len(train_loader.dataset) != args.expected_train_samples:
        raise RuntimeError(
            f"Train sample mismatch: expected {args.expected_train_samples}, got {len(train_loader.dataset)}."
        )
    if args.expected_val_samples and len(val_loader.dataset) != args.expected_val_samples:
        raise RuntimeError(
            f"Validation sample mismatch: expected {args.expected_val_samples}, got {len(val_loader.dataset)}."
        )

    images, _labels = unpack_image_batch(next(iter(val_loader)))
    images = images[:2].to(config.device)
    with torch.no_grad():
        teacher_logits_a = extract_logits(teacher(images))
        teacher_logits_b = extract_logits(teacher(images))
    expected_shape = (images.size(0), int(config.num_classes))
    if tuple(teacher_logits_a.shape) != expected_shape:
        raise RuntimeError(f"Teacher logits shape mismatch: expected {expected_shape}, got {teacher_logits_a.shape}.")
    if not torch.allclose(teacher_logits_a, teacher_logits_b, atol=0.0, rtol=0.0):
        raise RuntimeError("Teacher evaluation is not deterministic.")

    student = mobilenetv2_plus(
        num_classes=int(config.num_classes),
        width_mult=1.0,
        dropout_rate=0.3,
        layer_embedding=True,
        head_type="vich",
        lightweight_layer_embedding=True,
        lightweight_layer_embedding_layers=3,
        use_vich_sampling=False,
    ).to(config.device).eval()
    with torch.no_grad():
        student_output_a = student(images)
        student_output_b = student(images)
        student_logits_a = extract_logits(student_output_a)
        student_logits_b = extract_logits(student_output_b)
    if tuple(student_logits_a.shape) != expected_shape:
        raise RuntimeError(f"Student logits shape mismatch: expected {expected_shape}, got {student_logits_a.shape}.")
    if not torch.allclose(student_logits_a, student_logits_b, atol=0.0, rtol=0.0):
        raise RuntimeError("VICH no-sampling evaluation is not deterministic.")

    expected_head = 2 * (1280 * int(config.num_classes) + int(config.num_classes))
    expected_level_embeddings = 3 * 1280
    expected_le = expected_level_embeddings + 2 * 1280 + 3
    actual_head = student.head_parameter_count()
    actual_le = student.layer_embedding_parameter_count()
    actual_level_embeddings = student.level_embedding_parameter_count()
    total_params = sum(parameter.numel() for parameter in student.parameters())
    if student.layer_embedding_indices != (13, 17, 18):
        raise RuntimeError(f"Unexpected LightLE taps: {student.layer_embedding_indices}.")
    heavy_projections = [
        name
        for name, module in student.named_modules()
        if isinstance(module, torch.nn.Linear)
        and module.in_features == 1280
        and module.out_features == 1280
    ]
    if heavy_projections:
        raise RuntimeError(f"Forbidden heavy LightLE projections found: {heavy_projections}.")
    if actual_head != expected_head:
        raise RuntimeError(f"VICH head mismatch: expected {expected_head}, got {actual_head}.")
    if actual_le != expected_le:
        raise RuntimeError(f"LightLE mismatch: expected {expected_le}, got {actual_le}.")
    if actual_level_embeddings != expected_level_embeddings:
        raise RuntimeError(
            f"Level embedding mismatch: expected {expected_level_embeddings}, got {actual_level_embeddings}."
        )
    expected_total = EXPECTED_STUDENT_PARAMS[int(config.num_classes)]
    if total_params != expected_total:
        raise RuntimeError(f"Student total parameter mismatch: expected {expected_total}, got {total_params}.")

    print(f"dataset={config.dataset_name}")
    print(f"classes={config.num_classes}")
    print(f"train_samples={len(train_loader.dataset)}")
    print(f"validation_samples={len(val_loader.dataset)}")
    print(f"teacher_logits_shape={tuple(teacher_logits_a.shape)}")
    print(f"student_logits_shape={tuple(student_logits_a.shape)}")
    print(f"student_total_params={total_params}")
    print(f"vich_head_params={actual_head}")
    print(f"lightle_params={actual_le}")
    print(f"level_embedding_params={actual_level_embeddings}")
    print("Unified protocol smoke test: OK")


def parse_args():
    parser = argparse.ArgumentParser("Smoke test unified teacher/student protocol")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--expected-train-samples", type=int, default=0)
    parser.add_argument("--expected-val-samples", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
