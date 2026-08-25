import torch.nn.functional as F
import torch
from utils.visualization import tensors_show
def am_softmax_loss(logits, labels, s=10.0, m=0.5):
    one_hot = F.one_hot(labels, num_classes=logits.size(1)).float()
    logits_m = logits - one_hot * m  # subtract margin from true class logit
    logits_m = logits_m * s  # optional scaling factor
    return F.cross_entropy(logits_m, labels,reduction='none')
def arcface_loss(cosine_sim, labels, s=30.0, m=0.20):
    one_hot = F.one_hot(labels, num_classes=cosine_sim.size(1)).float()
    theta = torch.acos(torch.clamp(cosine_sim, -1.0 + 1e-7, 1.0 - 1e-7))
    target_logits = torch.cos(theta + m)
    output = cosine_sim * (1 - one_hot) + target_logits * one_hot
    output = output * s
    return F.cross_entropy(output, labels,reduction='none')

def compute_loss_em(loss_name,out,embeddings,idxs,labels,datas,labels_em,kl_beta=0.001):
    '''
    idxs=None,则不做错误分析
    '''
    #计算输出向量和label向量拟合度
    if labels_em.size(1)==0:
        labels_em=embeddings[labels]
    else:
        # FERPlus excludes unknown/non-face votes from the eight emotion columns.
        # Renormalize the remaining emotion mass before distributional CE.
        labels_em = labels_em.float().clamp_min(0.0)
        labels_em = labels_em / labels_em.sum(dim=1, keepdim=True).clamp_min(1e-12)

    preds_em=out[0] if isinstance(out, (tuple, list)) else out
    scores = preds_em.float() @ embeddings.T
    #输出向量和label向量拟合度最高的两个值，第2名认为是难分样本
    topk_values, topk_idxs = torch.topk(scores, k=2, dim=1)
    pred_labels = topk_idxs[:, 0]
    candidate_labels=topk_idxs[:,1]
    candidate_labels_em=embeddings[candidate_labels]
    if loss_name=='cross_entropy':
        loss_batch=F.cross_entropy(preds_em,labels_em,reduction='none',label_smoothing=0.0)
    elif loss_name=='triplet_margin_loss':
        loss_batch=F.triplet_margin_loss(preds_em,labels_em,candidate_labels_em,margin=1.0)
    elif loss_name=='mse_loss':
        loss_batch=F.mse_loss(preds_em,labels_em,reduction='none')
    elif loss_name=='ce_kld_loss':
        if not isinstance(out, (tuple, list)) or len(out) < 3:
            raise ValueError("ce_kld_loss expects model output as (logits, mu, logvar).")
        preds_em_loss = preds_em.float()
        labels_em_loss = labels_em.float()
        mu=out[1].float()
        logvar=out[2].float()
        # 分类损失按样本计算，便于和KL逐样本相加
        loss_ce = F.cross_entropy(preds_em_loss, labels_em_loss, reduction='none')
        loss_kl = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1)
        loss_batch = loss_ce + float(kl_beta) * loss_kl
    elif loss_name=='am_softmax_loss':
        loss_batch=am_softmax_loss(preds_em,labels)
    elif loss_name=='arcface_loss':

        loss_batch=arcface_loss(preds_em,labels)

    else:
        pass

    loss_batch_avg=torch.mean(loss_batch)
    if idxs!=None:
       #错误分类分析
        err_idxs=torch.nonzero(pred_labels!=labels)
        err_idxs=err_idxs.squeeze()
        if len(err_idxs)>0:
            print('error samples')
            print(idxs[err_idxs].detach().cpu().numpy(),labels[err_idxs].detach().cpu().numpy(),'->',pred_labels[err_idxs].detach().cpu().numpy())
        #损失值很大的样本
        ano_idxs=torch.where(loss_batch > 10 * loss_batch_avg)[0]
        if len(err_idxs)>0 and len(ano_idxs)>0:
            print('loss anomalous samples:')
            print(idxs[ano_idxs].detach().cpu().numpy(),\
                labels[ano_idxs].detach().cpu().numpy(),\
                loss_batch[ano_idxs].detach().cpu().numpy())
        tensors_show(datas[err_idxs])

    return loss_batch_avg,pred_labels
