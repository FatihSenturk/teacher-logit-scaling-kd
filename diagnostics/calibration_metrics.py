"""R3-1'in metrik tanımları — tek yerde, tek kez, ön-kayıt A10'da donmuş spesifikasyonlarla.

NEDEN AYRI DOSYA. Robustluk turunun tüm iddiası "sonuç tek bir ECE spesifikasyonuna
bağlı değil" olduğu için, metriklerin tanımı tablonun kendisinden daha önemlidir. Ayrı
ve test edilebilir bir modülde durursa, hangi formülün kullanıldığı tablodan bağımsız
denetlenebilir.

EŞİT-GENİŞLİK ECE BURADA YENİDEN YAZILMAZ. teacher_temperature_scaling_fit.confidence_ece
zaten kampanyanın yayımlanmış tüm ECE değerlerini üreten fonksiyondur ve n_bins
parametriktir. Yeniden yazmak, 15-kutu sütununun yayımlanmış değerleri yeniden üretip
üretmediği kapısını anlamsız kılardı — iki ayrı uygulama karşılaştırılırdı, oysa kapı
AYNI uygulamanın aynı sayıyı verdiğini doğrulamalı.

TANIMLAR (A10'da beyan edildiği gibi):
  nll            ortalama, doğal log (F.cross_entropy varsayılanı)
  brier          çok-sınıflı: sum_k (p_k - 1[y=k])^2, örnekler üzerinde ortalama
                 (selection_audit'in 'brier' sütunuyla AYNI tanım)
  ece_ew_{b}     eşit-genişlik, b kutu, max-prob üzerinde (confidence_ece)
  ece_em_15      eşit-KÜTLE (adaptif): kutu sınırları güven kuantillerinde, 15 kutu
  ece_classwise  TOP-1 ECE'nin sınıf-başına ortalaması, TAHMİN EDİLEN sınıfa göre
                 gruplanır (aşağıdaki nota bakınız)

CLASSWISE-ECE'DE GRUPLAMA SEÇİMİ — belirsizlik vardı, burada kapatılıyor. "Sınıf-başına
top-1 ECE" iki türlü okunabilir: örnekleri GERÇEK etikete göre gruplamak, ya da TAHMİN
edilen sınıfa göre. Ölçülen büyüklük top-1 güveni olduğu için örneğin ait olduğu grup
tahmin edilen sınıftır: güven o sınıfa aittir, gerçek etikete değil. Gerçek-etikete göre
gruplama, güveni başka bir sınıfın kutusuna yazardı. Seçim tabloda da belirtilir.
Boş kalan sınıflar ortalamaya girmez ve sayıları raporlanır.
"""
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402  (AYNI uygulama)

EQUAL_WIDTH_BINS = (10, 15, 25)
EQUAL_MASS_BINS = 15
CLASSWISE_BINS = 15


def _as_tensors(logits, labels):
    if not torch.is_tensor(logits):
        logits = torch.from_numpy(np.asarray(logits))
    if not torch.is_tensor(labels):
        labels = torch.from_numpy(np.asarray(labels))
    return logits.float(), labels.long()


def nll(logits, labels):
    """Ortalama negatif log olabilirlik, doğal log."""
    logits, labels = _as_tensors(logits, labels)
    return float(F.cross_entropy(logits, labels))


def brier(logits, labels):
    """Çok-sınıflı Brier: tam olasılık vektörü, one-hot hedef."""
    logits, labels = _as_tensors(logits, labels)
    probs = F.softmax(logits, dim=1)
    onehot = F.one_hot(labels, num_classes=probs.shape[1]).float()
    return float(((probs - onehot) ** 2).sum(dim=1).mean())


def ece_equal_mass(logits, labels, n_bins=EQUAL_MASS_BINS):
    """Eşit-kütle (adaptif) ECE: kutu sınırları güvenin kuantilleridir.

    Eşit-genişlik ECE'nin bilinen zaafı, yüksek güven bölgesinde örneklerin tek bir
    kutuya yığılıp sapmayı ortalamada eritmesidir. Eşit-kütle her kutuya yaklaşık aynı
    sayıda örnek koyar. Bağlar (aynı güven değeri) yüzünden kutular tam eşit olmayabilir;
    bu yüzden kutu sayıları da döndürülür ve çağıran taraf raporlayabilir.
    """
    logits, labels = _as_tensors(logits, labels)
    probs = F.softmax(logits, dim=1)
    conf, preds = probs.max(dim=1)
    correct = (preds == labels).float()

    c = conf.numpy()
    # Kuantil sınırları; bağlar yüzünden yinelenen sınırlar teklileştirilir.
    edges = np.unique(np.quantile(c, np.linspace(0.0, 1.0, n_bins + 1)))
    # searchsorted ile atama: ilk kutu solda kapalı, geri kalanlar solda açık/sağda kapalı
    idx = np.clip(np.searchsorted(edges, c, side="left") - 1, 0, len(edges) - 2)

    n = len(c)
    ece, counts = 0.0, []
    for b in range(len(edges) - 1):
        m = idx == b
        cnt = int(m.sum())
        counts.append(cnt)
        if cnt == 0:
            continue
        ece += (cnt / n) * abs(float(correct.numpy()[m].mean()) - float(c[m].mean()))
    return float(ece), counts


def ece_classwise(logits, labels, n_bins=CLASSWISE_BINS):
    """Top-1 ECE'nin sınıf-başına ortalaması; gruplama TAHMİN EDİLEN sınıfa göre.

    Dönüş: (ortalama, sınıf-başına değerler, katkı veren sınıf sayısı).
    """
    logits, labels = _as_tensors(logits, labels)
    preds = logits.argmax(dim=1)
    per_class, n_used = {}, 0
    for k in range(logits.shape[1]):
        m = preds == k
        if int(m.sum()) == 0:
            per_class[k] = None
            continue
        per_class[k] = confidence_ece(logits[m], labels[m], 1.0, n_bins=n_bins)
        n_used += 1
    vals = [v for v in per_class.values() if v is not None]
    return (float(np.mean(vals)) if vals else float("nan"),
            {str(k): v for k, v in per_class.items()}, n_used)


def all_metrics(logits, labels):
    """A10'da beyan edilen sütunların tamamı. Hiçbiri isteğe bağlı değildir."""
    logits, labels = _as_tensors(logits, labels)
    out = {"nll": nll(logits, labels), "brier": brier(logits, labels)}
    for b in EQUAL_WIDTH_BINS:
        out[f"ece_ew_{b}"] = confidence_ece(logits, labels, 1.0, n_bins=b)
    em, em_counts = ece_equal_mass(logits, labels)
    out["ece_em_15"] = em
    cw, cw_per_class, cw_n = ece_classwise(logits, labels)
    out["ece_classwise"] = cw
    out["_aux"] = {"equal_mass_bin_counts": em_counts,
                   "classwise_per_class": cw_per_class,
                   "classwise_classes_used": cw_n,
                   "acc": float((logits.argmax(1) == labels).float().mean() * 100.0),
                   "n": int(labels.shape[0])}
    return out


# Rapor sütun sırası -- tabloların hepsi bu sırayı kullanır.
METRIC_ORDER = ["nll", "brier", "ece_ew_10", "ece_ew_15", "ece_ew_25",
                "ece_em_15", "ece_classwise"]
METRIC_LABEL = {"nll": "NLL", "brier": "Brier",
                "ece_ew_10": "ECE ew-10", "ece_ew_15": "ECE ew-15", "ece_ew_25": "ECE ew-25",
                "ece_em_15": "ECE em-15", "ece_classwise": "classwise-ECE"}
