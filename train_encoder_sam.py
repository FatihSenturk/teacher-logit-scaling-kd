import warnings
from tqdm import tqdm
from utils.lr_schedule import cosine_decay, adjust_lr, get_lr
from utils.metrics import Metrics
from loss_encoder import compute_loss_em
import torch
warnings.simplefilter("ignore")
"""
如果labels的向量长度等于args.num_classes,则不对labels做embedding，也就是不转换为onehot编码。
"""
def _forward_loss(args, model, embeddings, idxs, datas, labels, labels_em, amp_context):
    if args.use_amp:
        with amp_context(device_type="cuda"):
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
    return loss_batch, pred_labels, preds_em


def trainloop(wandb,args, epoch, model, scaler, amp_context, optimizer, schedule,train_loader,embeddings):
    batchs=len(train_loader)
    #trainloop只度量主要指标
    metrics=Metrics(args.num_classes,{f'{args.metric_name}/train':0},args.device)
    train_pbar = tqdm(
        train_loader,
        desc=f"epoch {epoch},train",
        disable=None,
        dynamic_ncols=True,
    )
    model.train()
    loss_epoch=0
  
    for batch_id, (idxs, datas,labels,labels_em,image_path) in enumerate(train_pbar):        
        
        labels=labels.to(args.device)
        labels_em=labels_em.to(args.device)
        #如果idxs!=None，可以输出错误样本的热力图等信息
        idxs=idxs.to(args.device)
        if epoch<args.debug_after['train']:
            idxs=None
        datas = datas.to(args.device)
        """-----first step------"""

        loss_batch, pred_labels, preds_em = _forward_loss(
            args, model, embeddings, idxs, datas, labels, labels_em, amp_context
        )
        loss_epoch+=loss_batch.item()
        metrics.add_batch(pred_labels.detach(), labels, preds_em.detach(), labels_em=labels_em)#?
        train_pbar.set_postfix(loss=loss_batch.item())
        # optimizer.zero_grad()
        if scaler is not None:
            scaler.scale(loss_batch).backward()
        else:
            loss_batch.backward()
        optimizer.first_step(zero_grad=True)
        """-----second step------"""
        #out的第一个为preds_em
        loss_batch, pred_labels, preds_em = _forward_loss(
            args, model, embeddings, idxs, datas, labels, labels_em, amp_context
        )
        loss_epoch+=loss_batch.item()
        metrics.add_batch(pred_labels.detach(), labels, preds_em.detach(), labels_em=labels_em)
        train_pbar.set_postfix(loss=loss_batch.item())
        # optimizer.zero_grad()
        if scaler is not None:
            scaler.scale(loss_batch).backward()
            scaler.unscale_(optimizer)
        else:
            loss_batch.backward()
        optimizer.second_step(zero_grad=True)
        if scaler is not None:
            scaler.update()
        adjust_lr(wandb,schedule,epoch,batch_id,batchs)
    #logs
    retrun_metrics=metrics.compute_and_reset()
    loss_epoch=loss_epoch/batchs
    retrun_metrics['epoch']=epoch
    retrun_metrics['loss_epoch/train']=loss_epoch
    wandb.log(retrun_metrics)
    if getattr(args, "use_swanlab", False):
        import swanlab

        swanlab.log(retrun_metrics)

    

