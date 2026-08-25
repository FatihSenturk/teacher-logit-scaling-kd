import timm


def create_model(args):
    """
    Build local models used by this project.
    """
    name = str(args.model_name).lower()

    if name == "posterv2":
        from trails.posterv2.PosterV2_7cls import pyramid_trans_expr2

        return pyramid_trans_expr2(
            img_size=getattr(args, "train_size", 224),
            num_classes=args.num_classes,
            vae=getattr(args, "vae_head", False),
            layer_embedding=getattr(args, "layer_embedding", False),
            votes_sum=getattr(args, "votes_sum", 0),
            vich=getattr(args, "vich_head", False),
            vich_use_sampling=getattr(args, "vich_use_sampling", True),
            vich_logvar_min=getattr(args, "vich_logvar_min", -10.0),
            vich_logvar_max=getattr(args, "vich_logvar_max", 10.0),
            vich_init_logvar_bias=getattr(args, "vich_init_logvar_bias", -5.0),
        )

    # Fallback to timm for any other model name.
    # Prefer direct timm model id; if it fails, try hf_hub prefix.
    try:
        return timm.create_model(args.model_name, pretrained=args.pretrained_timm, num_classes=args.num_classes)
    except Exception:
        return timm.create_model(
            f"hf_hub:{args.model_name}",
            pretrained=args.pretrained_timm,
            num_classes=args.num_classes,
        )
