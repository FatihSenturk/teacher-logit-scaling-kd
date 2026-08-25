import torch
import warnings
from tqdm import tqdm
from utils.visualization import plot_confusion_matrix
from loss_encoder import compute_loss_em
from utils.metrics import Metrics
warnings.simplefilter("ignore")
@torch.no_grad()
def validloop(wandb,args, model,epoch, valid_loader,embeddings):
    torch.cuda.empty_cache()
    #记录每个mini batch的数据，用于计算一个epoch的数据，ids_epoch可以追踪错的最多的ids
    metrics=Metrics(args.num_classes,args.valid_metrics,args.device)
    batchs=len(valid_loader)
    loss_epoch=0

    model.eval()
    valid_pbar = tqdm(
        valid_loader,
        desc=f"----- {epoch},valid",
        disable=None,
        dynamic_ncols=True,
    )
    for batch_id, (idxs, datas, labels,labels_em,image_path) in enumerate(valid_pbar):
        batch_size = labels.size(0)
        labels=labels.to(args.device)
        labels_em=labels_em.to(args.device)
        idxs=idxs.to(args.device)
        """ forward and calculate loss  """
        datas = datas.to(args.device)
       
        out = model(datas)
        preds_em = out[0] if isinstance(out, (tuple, list)) else out
        idxs=idxs.to(args.device)
        if epoch<args.debug_after['valid']:
            idxs=None
        loss_batch,pred_labels=compute_loss_em(
            args.loss_name,
            out,
            embeddings,
            idxs,
            labels,
            datas,
            labels_em,
            kl_beta=getattr(args, "ce_kld_beta", 0.001),
        )
        loss_epoch+=loss_batch.item()
        valid_pbar.set_postfix(loss=loss_batch.item())
        metrics.add_batch(pred_labels.detach(), labels, preds_em.detach(), labels_em=labels_em)
    #logs
    return_metrics=metrics.compute_and_reset()
    loss_epoch=loss_epoch/batchs
    return_metrics['loss_epoch/valid']=loss_epoch
    return_metrics['epoch']=epoch
    wandb.log(return_metrics)
    if getattr(args, "use_swanlab", False):
        import swanlab

        swanlab.log(return_metrics)
    metric_name=f'{args.metric_name}/valid'
    return return_metrics[metric_name]
