import warnings

import torch
from tqdm import tqdm

from loss_encoder import compute_loss_em
from utils.lr_schedule import adjust_lr, cosine_decay, get_lr
from utils.metrics import Metrics

warnings.simplefilter("ignore")


def trainloop(wandb, args, epoch, model, scaler, amp_context, optimizer, schedule, train_loader, embeddings):
    batchs = len(train_loader)
    metrics = Metrics(args.num_classes, {f"{args.metric_name}/train": 0}, args.device)
    train_pbar = tqdm(
        train_loader,
        desc=f"epoch {epoch},train",
        disable=None,
        dynamic_ncols=True,
    )
    model.train()
    loss_epoch = 0

    for batch_id, batch in enumerate(train_pbar):
        if len(batch) == 5:
            idxs, datas, labels, labels_em, _image_path = batch
            labels_em = labels_em.to(args.device)
        else:
            idxs, datas, labels = batch
            labels_em = None

        labels = labels.to(args.device)
        if labels_em is None or labels_em.size(1) == 0:
            labels_em = embeddings[labels]

        idxs = idxs.to(args.device)
        if epoch < args.debug_after["train"]:
            idxs = None

        datas = datas.to(args.device)

        if args.use_amp:
            with amp_context(device_type="cuda"):
                try:
                    out = model(datas, labels)
                except TypeError:
                    out = model(datas)
                preds_em = out[0] if isinstance(out, (tuple, list)) else out
                loss_batch, pred_labels = compute_loss_em(
                    args.loss_name,
                    out,
                    embeddings,
                    idxs,
                    labels,
                    datas,
                    labels_em=labels_em,
                    kl_beta=getattr(args, "ce_kld_beta", 0.001),
                )
        else:
            try:
                out = model(datas, labels)
            except TypeError:
                out = model(datas)
            preds_em = out[0] if isinstance(out, (tuple, list)) else out
            loss_batch, pred_labels = compute_loss_em(
                args.loss_name,
                out,
                embeddings,
                idxs,
                labels,
                datas,
                labels_em=labels_em,
                kl_beta=getattr(args, "ce_kld_beta", 0.001),
            )

        loss_epoch += loss_batch.item()
        metrics.add_batch(pred_labels.detach(), labels, preds_em.detach(), labels_em=labels_em)
        train_pbar.set_postfix(loss=loss_batch.item())

        if scaler is not None:
            scaler.scale(loss_batch).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss_batch.backward()
            optimizer.step()

        optimizer.zero_grad()
        adjust_lr(wandb, schedule, epoch, batch_id, batchs)

    retrun_metrics = metrics.compute_and_reset()
    loss_epoch = loss_epoch / batchs
    retrun_metrics["epoch"] = epoch
    retrun_metrics["loss_epoch/train"] = loss_epoch
    wandb.log(retrun_metrics)
    if getattr(args, "use_swanlab", False):
        import swanlab

        swanlab.log(retrun_metrics)
