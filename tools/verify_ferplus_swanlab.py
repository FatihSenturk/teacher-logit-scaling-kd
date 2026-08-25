import argparse
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dataset_utils.image_dataset import build_img_dataloader
from trials.models import create_model
from utils.configs import load_yaml


def main(config_path):
    args = argparse.Namespace()
    load_yaml(args, str(config_path))
    args.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    args.num_workers = 0
    args.cache_img = False

    train_loader, val_loader = build_img_dataloader(args)
    assert len(train_loader.dataset) == 28259, len(train_loader.dataset)
    assert len(val_loader.dataset) == 3153, len(val_loader.dataset)

    model = create_model(args).to(args.device).eval()
    batch = next(iter(val_loader))
    images = batch[1][:2].to(args.device)
    with torch.no_grad():
        output = model(images)
    logits = output[0] if isinstance(output, (tuple, list)) else output
    assert tuple(logits.shape) == (2, 8), tuple(logits.shape)

    print(f"device={args.device}")
    print(f"train_samples={len(train_loader.dataset)}")
    print(f"validation_samples={len(val_loader.dataset)}")
    print(f"logits_shape={tuple(logits.shape)}")
    print("FERPlus SwanLab smoke test: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs" / "FERPlus_8_swanlab_repro.yaml",
    )
    main(parser.parse_args().config)
