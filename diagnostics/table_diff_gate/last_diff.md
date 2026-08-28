# Table diff gate — last comparison

Baseline: **2026-08-28T14:19:03** — R8 (28 Agu 2026): §5.7 TOST marjinin PAYDASI beyanla hizalandi. Metin marji 'twice the SCALED CONTROL arm's seed deviation' diye beyan ediyor; equivalence_tests.py ise T* kolunu referans aliyordu. Iki tanim ayni degil (2x0.0031764 vs 2x0.0034800) ve basili p_TOST eski paydadan geliyordu. Uretici beyanla hizalandi, ayni kural JSD ekseninde de uygulandi ('the same margin'). SONUC: p_tost 0.2535 -> 0.2164 (makalede 0.25 -> 0.22), sinif DEGISMEDI (inconclusive); JSD ekseni 0.9967 -> 0.9965, sinif ayni (difference beyond margin). Yeni hucre derived/s57.tost_margin: basili delta=0.0034, 2 x ferplus_scaled_ece_axis.arms[1.0].ts_ece[1], yuvarlama 4dp_floor (marj yukari yuvarlanamaz). CHANGED 1 (beyan hizalamasi), VANISHED 0.  
Cells compared: 1660 (1660 in the baseline)

✅ No deviation — every cell is at its baseline value.
