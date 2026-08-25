"""FERPlus entry point for the shared config-based MobileNetV2Plus KD pipeline."""

from train_affectnetplus_kd import main, parse_args


if __name__ == "__main__":
    args = parse_args()
    args.dataset_name = "FERPlus"
    if args.num_classes not in (None, 8):
        raise ValueError("FERPlus unified protocol requires 8 classes.")
    args.num_classes = 8
    args.supervision = "soft"
    args.label_smoothing = 0.0
    if not args.expected_train_samples:
        args.expected_train_samples = 28259
    if not args.expected_val_samples:
        args.expected_val_samples = 3153
    main(args)
