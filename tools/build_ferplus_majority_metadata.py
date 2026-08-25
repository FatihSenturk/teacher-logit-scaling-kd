import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


EMOTIONS = [
    "neutral",
    "happiness",
    "surprise",
    "sadness",
    "anger",
    "disgust",
    "fear",
    "contempt",
]
VOTE_COLUMNS = [*EMOTIONS, "unknown", "NF"]
USAGE_TO_FOLD = {"Training": 0, "PublicTest": 1, "PrivateTest": 2}
USAGE_TO_DIR = {
    "Training": "FER2013Train",
    "PublicTest": "FER2013Valid",
    "PrivateTest": "FER2013Test",
}


def majority_label(votes):
    cleaned = votes.astype(np.float64, copy=True)
    cleaned[cleaned < 1.0 + sys.float_info.epsilon] = 0.0
    vote_sum = cleaned.sum()
    label = int(cleaned.argmax())
    if cleaned[label] <= 0.5 * vote_sum or label >= len(EMOTIONS):
        return None
    return label


def build_metadata(annotation_csv, image_root, output_csv):
    annotations = pd.read_csv(annotation_csv)
    rows = []
    rejected = Counter()

    for source_row, row in annotations.iterrows():
        votes = row[VOTE_COLUMNS].to_numpy(dtype=np.float64)
        label = majority_label(votes)
        if label is None:
            rejected[row["Usage"]] += 1
            continue

        image_name = row["Image name"]
        if not isinstance(image_name, str) or not image_name:
            raise ValueError(f"Accepted row {source_row} has no image name.")

        relative_path = Path(USAGE_TO_DIR[row["Usage"]]) / image_name
        image_path = image_root / relative_path
        if not image_path.exists():
            raise FileNotFoundError(f"Accepted FER+ image is missing: {image_path}")

        output_row = {
            "path": relative_path.as_posix(),
            "label": label,
            "fold": USAGE_TO_FOLD[row["Usage"]],
        }
        # Preserve the original ten-rater vote counts. ImageDataset normalizes
        # the eight expression columns with votes_sum=10 at load time.
        output_row.update({emotion: int(row[emotion]) for emotion in EMOTIONS})
        output_row["source_row"] = int(source_row)
        rows.append(output_row)

    metadata = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(output_csv, index=False)

    split_counts = metadata.groupby("fold").size().to_dict()
    class_counts = {
        int(fold): {
            int(label): int(count)
            for label, count in group["label"].value_counts().sort_index().items()
        }
        for fold, group in metadata.groupby("fold")
    }

    expected = {0: 25060, 1: 3199, 2: 3153}
    if split_counts != expected:
        raise RuntimeError(f"Unexpected FER+ majority counts: {split_counts}, expected {expected}")

    print(f"Saved: {output_csv}")
    print(f"Accepted samples: {len(metadata)}")
    print(f"Split counts: {split_counts}")
    print(f"Train + PublicTest: {split_counts[0] + split_counts[1]}")
    print(f"PrivateTest: {split_counts[2]}")
    print(f"Class counts: {class_counts}")
    print(f"Rejected counts: {dict(rejected)}")


def parse_args():
    parser = argparse.ArgumentParser("Build official FER+ majority metadata")
    parser.add_argument(
        "--annotation-csv",
        type=Path,
        default=Path(r"C:\Users\mfati\Downloads\fer2013new.csv"),
    )
    parser.add_argument(
        "--image-root",
        type=Path,
        default=Path(r"C:\datasets\processed"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("configs/FERPlus_majority_metadata.csv"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    build_metadata(
        annotation_csv=cli_args.annotation_csv,
        image_root=cli_args.image_root,
        output_csv=cli_args.output,
    )
