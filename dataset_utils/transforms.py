from torchvision import transforms


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def _train_augs(name):
    name = str(name).lower()
    # Keep this conservative so it works across AffectNet/RAFDB/FER+ configs.
    if "qcs" in name:
        return [
            transforms.RandomHorizontalFlip(),
            transforms.RandomApply(
                [transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05)],
                p=0.5,
            ),
        ]
    if "poster" in name:
        return [
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
        ]
    return [transforms.RandomHorizontalFlip()]


def get_data_transforms(args):
    train_size = int(getattr(args, "train_size", 224))
    val_size = int(getattr(args, "val_size", train_size))
    transforms_name = getattr(args, "transforms_name", "default")
    transforms_name_l = str(transforms_name).lower()

    if bool(getattr(args, "unified_resolution_crop", False)):
        resize_size = int(getattr(args, "train_resize_size", train_size))
        dataset_name = str(getattr(args, "dataset_name", "")).lower()
        rotation = 12.0 if "affect" in dataset_name else 10.0
        color_jitter = float(getattr(args, "aug_color_jitter", 0.2))
        random_erasing_p = float(getattr(args, "aug_random_erasing_p", 0.5))
        train_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(rotation),
            transforms.RandomCrop((train_size, train_size)),
            transforms.ColorJitter(
                brightness=color_jitter,
                contrast=color_jitter,
                saturation=color_jitter,
            ),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(p=random_erasing_p),
        ]
        valid_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.CenterCrop((val_size, val_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        return {
            "train": transforms.Compose(train_tfms),
            "valid": transforms.Compose(valid_tfms),
        }

    # AffectNet custom policy:
    # Resize(236) -> HFlip -> Rotation(12) -> RandomCrop(224) -> ColorJitter(0.2) -> Normalize -> RandomErasing
    if transforms_name_l in {"affectnet-custom", "affectnet_custom", "affectnet-strong", "affectnet_strong"}:
        resize_size = int(getattr(args, "train_resize_size", 236))
        train_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(12),
            transforms.RandomCrop((train_size, train_size)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(),
        ]
        valid_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.CenterCrop((val_size, val_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        return {
            "train": transforms.Compose(train_tfms),
            "valid": transforms.Compose(valid_tfms),
        }

    # RAF-DB POSTER-Var paper policy:
    # Resize(224) -> HFlip -> Rotation(12) -> RandomCrop(224)
    # -> ColorJitter(0.2) -> Normalize -> RandomErasing
    if transforms_name_l in {"rafdb-paper", "rafdb_paper", "postervar-rafdb", "postervar_rafdb"}:
        resize_size = int(getattr(args, "train_resize_size", train_size))
        random_erasing_p = float(getattr(args, "aug_random_erasing_p", 0.5))
        train_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(12),
            transforms.RandomCrop((train_size, train_size)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(p=random_erasing_p),
        ]
        valid_tfms = [
            transforms.Resize((val_size, val_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        return {
            "train": transforms.Compose(train_tfms),
            "valid": transforms.Compose(valid_tfms),
        }

    # RAF-DB published-recipe policy (Table 1, no rotation/crop):
    # Resize(224) -> HFlip -> ColorJitter(0.2) -> Normalize -> RandomErasing
    if transforms_name_l in {"rafdb-recipe", "rafdb_recipe"}:
        resize_size = int(getattr(args, "train_resize_size", train_size))
        random_erasing_p = float(getattr(args, "aug_random_erasing_p", 0.5))
        train_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(p=random_erasing_p),
        ]
        valid_tfms = [
            transforms.Resize((val_size, val_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        return {
            "train": transforms.Compose(train_tfms),
            "valid": transforms.Compose(valid_tfms),
        }

    # FER+ custom policy:
    # Resize(232) -> HFlip -> Rotation(10) -> RandomCrop(224) -> ColorJitter(0.2) -> Normalize -> RandomErasing
    if transforms_name_l in {"ferplus-custom", "ferplus_custom", "ferplus-strong", "ferplus_strong"}:
        resize_size = int(getattr(args, "train_resize_size", 232))
        train_tfms = [
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.RandomCrop((train_size, train_size)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(),
        ]
        valid_tfms = [
            transforms.Resize((val_size, val_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        return {
            "train": transforms.Compose(train_tfms),
            "valid": transforms.Compose(valid_tfms),
        }

    train_tfms = [
        transforms.Resize((train_size, train_size)),
        *_train_augs(transforms_name),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
    valid_tfms = [
        transforms.Resize((val_size, val_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]

    return {
        "train": transforms.Compose(train_tfms),
        "valid": transforms.Compose(valid_tfms),
    }
