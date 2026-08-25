# B4 — τ×T tasarımı: dört kol, kurucu (τ, T) değerleriyle

Üretici: `diagnostics/tau_t_factorial.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · kol tanımları `p6_1_early_reading.PAIRS`'ten **ithal**

> Üç bağımsız hakem bu bölümü *confounded* diye okudu ve **üçü de yanıldı**. Tasarımda τ ile T ayrı ayrı oynuyor. Sorun sergilemede: makalede yalnız **çarpım** (T·τ) görünüyor, kurucu değerler hiçbir yerde yok. Bu tablo onları basıyor ve üç **marjinal** kontrastı ekliyor — her biri tek bir faktörü oynatıyor, yani confound olmadığının doğrudan kanıtı.

## 1 · Dört kol

| τ | T | n | ECE (ort ± sd) | doğruluk (ort ± sd) | tohumlar |
|---|---|---|---|---|---|
| **3** | **1.70** | 3 | 0.0405 ± 0.0020 | 89.635 ± 0.181 | [42, 1, 43] |
| **6** | **0.85** | 3 | 0.0797 ± 0.0016 | 89.646 ± 0.180 | [42, 1, 43] |
| **6** | **1.70** | 3 | 0.0447 ± 0.0029 | 89.429 ± 0.196 | [42, 1, 43] |
| **12** | **0.85** | 3 | 0.0771 ± 0.0031 | 89.983 ± 0.415 | [42, 1, 43] |

### Tohum tohum

| τ | T | ECE s42 | ECE s1 | ECE s43 | acc s42 | acc s1 | acc s43 |
|---|---|---|---|---|---|---|---|
| 3 | 1.70 | 0.0427 | 0.0402 | 0.0387 | 89.831 | 89.602 | 89.472 |
| 6 | 0.85 | 0.0781 | 0.0814 | 0.0795 | 89.831 | 89.472 | 89.635 |
| 6 | 1.70 | 0.0472 | 0.0415 | 0.0455 | 89.244 | 89.407 | 89.635 |
| 12 | 0.85 | 0.0806 | 0.0762 | 0.0746 | 89.505 | 90.189 | 90.254 |

## 2 · Eşleşmiş çiftler — aynı T·τ çarpımı (P6.1'in çökme testi)

| çift | değişen | n | ΔECE (ort ± sd) | işaret | Δacc (pp, ort ± sd) | işaret |
|---|---|---|---|---|---|---|
| **T·τ = 5.10** | τ 3→6, T 1.70→0.85 | 3 | -0.0391 ± 0.0032 | `---` | -0.011 ± 0.147 | `-+-` |
| **T·τ = 10.20** | τ 6→12, T 1.70→0.85 | 3 | -0.0324 ± 0.0029 | `---` | -0.554 ± 0.267 | `---` |

## 3 · Marjinal kontrastlar — **tek faktör oynuyor**

Bu üç satır hakem itirazının doğrudan cevabı. Her birinde bir faktör sabit tutuluyor, diğeri oynatılıyor; iki kol da defterde mevcut, yani kontrast türetilmiş değil **ölçülmüş**.

| kontrast | sabit | değişen | n | ΔECE (ort ± sd) | işaret | Δacc (pp, ort ± sd) | işaret |
|---|---|---|---|---|---|---|---|
| **τ etkisi @ T=1.70** | T = 1.70 | τ 3 → 6 | 3 | +0.0042 ± 0.0028 | `+++` | -0.206 ± 0.375 | `--+` |
| **T etkisi @ τ=6** | τ = 6 | T 0.85 → 1.70 | 3 | -0.0349 ± 0.0045 | `---` | -0.217 ± 0.322 | `---` |
| **τ etkisi @ T=0.85** | T = 0.85 | τ 6 → 12 | 3 | -0.0025 ± 0.0044 | `+--` | +0.337 ± 0.576 | `-++` |

> Tasarımın confound olmadığı buradan okunur: τ'nun etkisi **iki ayrı T değerinde ayrı ayrı** ölçülebiliyor ve T'nin etkisi **sabit τ'da** ölçülebiliyor. Üç kontrastın üçü de tek değişkenli.

---

Kaynak: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa · kol tanımı: `diagnostics/p6_1_early_reading.py::PAIRS`

