# MobileNetV2Plus Öğrenci Modeli - ViCH Head Detaylı Analiz — ⚠️ ÇALIŞMA KAYDI

> **Bu dosya bir çalışma kaydıdır; güncel iddialar makalededir.** Mimari anlatımı geçerli,
> ama içindeki iki doğruluk sayısı bu makaleden gelmiyor: **92.41** Mart 2026'daki farklı
> bir çalışmanın öğretmenidir (bu makalenin öğretmenleri 92.24 / 92.01 / 91.82) ve
> **88.72** o dönemin bir öğrenci ölçümüdür.
>
> Makaledeki her sayının tek kaynağı `diagnostics/paper_tables/RESULTS_TABLES.md`'dir;
> kampanyanın duran bulguları `diagnostics/claims.md` ve
> `diagnostics/PREREGISTRATIONS.md`'de tutulur. Bu belge onların yerine okunmaz.

## 1. GENEL ÖZET

MobileNetV2Plus, öğrenci modeli olarak hafif ve verimli bir mimaride tasarlanmıştır. **ViCH Head** (Variational Inference for Classification Head) ile deterministic sınıflandırma yaparken belirsizlik (uncertainty) tahmin eder. Öğretmen modelinden %2-3 puan daha düşük doğruluk ile çok daha az parametre kullanır.

**Temel Bilgi:**
- **Total Parametreler:** ~2.25M (öğretmen: ~100M)
- **Giriş Çözünürlüğü:** 112, 224 veya 256 piksel
- **Sınıf Sayısı:** 7 (RAF-DB) veya 8 (FERPlus/AffectNet+)
- **ViCH Head:** Class-level probabilistic head
- **LightLE:** True 3-level lightweight layer embedding
- **ECA:** Efficient Channel Attention
- **GeM:** Generalized Mean Pooling

---

## 2. MİMARİ GENEL YAPISI

```
┌─────────────────────────────────────┐
│    MobileNetV2Plus (Lightweight)    │
├─────────────────────────────────────┤
│  Backbone: MobileNetV2              │
│  ├─ 19 Inverted Residual blocks     │
│  ├─ ECA (Efficient Channel Att.)    │
│  ├─ Width Multiplier: 1.0           │
│  └─ Output: (B, 1280, 7, 7)        │
│                                     │
│  Feature Extraction Layer:          │
│  ├─ GeM Pooling                     │
│  └─ Output: (B, 1280)              │
│                                     │
│  LightLE Module (Optional):         │
│  ├─ Level 1: Index 13, 96-dim      │
│  ├─ Level 2: Index 17, 320-dim     │
│  ├─ Level 3: Final, 1280-dim       │
│  ├─ Fusion: Softmax weighted       │
│  └─ Output: (B, 1280)              │
│                                     │
│  Feature Adapter (Optional):        │
│  └─ Linear projection (if needed)  │
│                                     │
│  ViCH Head:                         │
│  ├─ Linear_mu(1280 → num_classes)  │
│  ├─ Linear_logvar(1280 → nc)       │
│  ├─ Logvar clamping: [-10, 10]     │
│  ├─ Sampling (training only)       │
│  └─ Output: logits, mu, logvar     │
└─────────────────────────────────────┘
```

---

## 3. MobileNetV2 BACKBONE DETAYLARI

### 3.1 Genel Yapı

```
MobileNetV2 = 19 Inverted Residual Block

Configuration Table:
┌──────┬─────────┬──────────┬────────────────┐
│ t    │ c       │ n        │ s              │
├──────┼─────────┼──────────┼────────────────┤
│ 1    │ 16      │ 1        │ 1  (1x)        │
│ 6    │ 24      │ 2        │ 2, 1 (2x)      │
│ 6    │ 32      │ 3        │ 2, 1, 1 (2x)   │
│ 6    │ 64      │ 4        │ 2, 1, 1, 1 (2x)│
│ 6    │ 96      │ 3        │ 1, 1, 1        │
│ 6    │ 160     │ 3        │ 2, 1, 1 (2x)   │
│ 6    │ 320     │ 1        │ 1              │
└──────┴─────────┴──────────┴────────────────┘

Açıklama:
- t: Expansion ratio (point-wise expansion factor)
- c: Output channels
- n: Number of blocks
- s: Stride(s) for each block

Total stride = 32 → 224x224 → 7x7 spatial
```

### 3.2 Inverted Residual Block with ECA

```
class InvertedResidualECA:

Input: (B, in_channels, H, W)

1. Point-Wise Expansion (if expand_ratio ≠ 1):
   ├─ Conv 1x1: in → (in * expand_ratio)
   ├─ BatchNorm
   └─ ReLU6
   Output: (B, hidden_dim, H, W)

2. Depth-Wise Convolution:
   ├─ Conv 3x3 depth-wise: (groups=hidden_dim)
   ├─ BatchNorm
   ├─ ReLU6
   └─ Stride s ∈ {1, 2}
   Output: (B, hidden_dim, H', W')

3. ECA (Efficient Channel Attention):
   ├─ AdaptiveAvgPool2d(1)
   ├─ Conv1d(channel attention)
   ├─ Sigmoid gating
   └─ Broadcast multiply with features
   Output: (B, hidden_dim, H', W')

4. Point-Wise Projection (Linear):
   ├─ Conv 1x1: hidden_dim → out_channels
   ├─ BatchNorm
   └─ NO activation (linear bottleneck)
   Output: (B, out_channels, H', W')

5. Residual Connection (if stride=1 and in_ch=out_ch):
   ├─ Input + Output
   └─ Else: just return output
```

### 3.3 ECA Layer (Efficient Channel Attention)

```
Adaptif Kernel Size Hesaplama:
  gamma = 2 (default)
  b = 1 (default)
  C = channel count
  
  t = |log₂(C) / gamma + b / gamma|
  k = t (if t is odd) else t + 1

Örnek (C=320 için):
  log₂(320) ≈ 8.32
  t = |8.32/2 + 1/2| = 4.91 → 5
  k = 5 (odd, so use as is)

Forward Pass:
  x: (B, C, H, W)
  ├─ AdaptiveAvgPool2d(1) → (B, C, 1, 1)
  ├─ Squeeze: (B, C)
  ├─ Conv1d(kernel_size=k, padding=k//2) → (B, C)
  ├─ Sigmoid → (B, C)
  └─ Expand ve multiply with x
  
Output: (B, C, H, W) * channel weights
```

---

## 4. VICH HEAD (VARIATIONAL INFERENCE FOR CLASSIFICATION HEAD)

### 4.1 Mimarı Yapı

```python
class VICHHead(nn.Module):
    def __init__(
        self,
        in_dim: int = 1280,           # Feature vector dimension
        num_classes: int = 7,         # Number of emotion classes
        use_sampling: bool = True,    # Reparameterization sampling
        logvar_min: float = -10.0,    # Log-variance lower bound
        logvar_max: float = 10.0,     # Log-variance upper bound
        init_logvar_bias: float = -5.0 # Initial logvar bias
    ):
        super().__init__()
        # Two linear layers: mean and log-variance
        self.mu = nn.Linear(in_dim, num_classes)
        self.logvar = nn.Linear(in_dim, num_classes)
        self.in_dim = in_dim
        self.num_classes = num_classes
        self.use_sampling = use_sampling
        self.logvar_min = logvar_min
        self.logvar_max = logvar_max
        self.init_logvar_bias = init_logvar_bias
```

### 4.2 Parameter Count (ViCH Head)

```
7 Sınıf için:
  mu = Linear(1280 → 7):
    Weight: 1280 × 7 = 8,960
    Bias: 7
    Subtotal: 8,967

  logvar = Linear(1280 → 7):
    Weight: 1280 × 7 = 8,960
    Bias: 7
    Subtotal: 8,967

  TOTAL ViCH HEAD: 8,967 + 8,967 = 17,934 parameters

8 Sınıf için:
  mu = Linear(1280 → 8): 10,240 + 8 = 10,248
  logvar = Linear(1280 → 8): 10,240 + 8 = 10,248
  TOTAL: 20,496 parameters
```

### 4.3 Forward Pass (Detailed)

```
Input: x ∈ (B, 1280)  # B = batch size

Step 1: Flatten (if not already flat)
  x = x.view(x.size(0), -1)  # Ensure 2D: (B, 1280)

Step 2: Compute Mean Logits
  mu = self.mu(x)           # (B, 7) or (B, 8)
  Shape: (batch, num_classes)

Step 3: Compute Log-Variance
  logvar = self.logvar(x)   # (B, 7) or (B, 8)
  
  # Clamp to prevent numerical instability
  logvar = torch.clamp(logvar, 
                       min=self.logvar_min,   # -10.0
                       max=self.logvar_max)   # +10.0
  Shape: (batch, num_classes)

Step 4: Sampling (Training Mode Only)
  IF self.training AND self.use_sampling:
    ├─ sigma = exp(0.5 * logvar)    # Standard deviation
    ├─ eps ~ N(0, I)                 # Random noise
    ├─ logits = mu + sigma * eps    # Reparameterization
    └─ Purpose: Stochastic gradient descent
  ELSE:
    ├─ logits = mu                  # Deterministic (eval mode)
    └─ Purpose: Stable, reproducible predictions

Step 5: Compute KL Loss
  kl_loss = -0.5 * sum(1 + logvar - mu² - exp(logvar))
  
  Breakdown:
  ├─ 1: Prior variance (N(0,I))
  ├─ logvar: Model-predicted log-variance
  ├─ mu²: Squared mean (distance from prior)
  ├─ exp(logvar): Variance from logvar
  └─ Final: Mean reduction over batch
  
  KL Loss Shape: scalar

Step 6: Return Dictionary
  return {
    "logits": logits,        # (B, 7/8) - classification targets
    "mu": mu,                # (B, 7/8) - mean predictions
    "logvar": logvar,        # (B, 7/8) - log-variance (uncertainty)
    "kl_loss": kl_loss       # scalar - regularization loss
  }
```

### 4.4 Training vs Inference

```
TRAINING MODE (model.train()):
  ├─ use_sampling = True
  ├─ logits = mu + sigma * eps     [Stochastic]
  ├─ Loss = CE(logits, targets) + β*KL_loss
  ├─ Gradients flow through sampling
  └─ Regularization: KL forces q(z|x) ≈ p(z)

INFERENCE MODE (model.eval()):
  ├─ use_sampling = False (or ignored)
  ├─ logits = mu                  [Deterministic]
  ├─ No KL loss computed
  ├─ Stable, reproducible predictions
  └─ Variance estimates still available (mu, logvar)
```

---

## 5. LIGHTWEIGHT LAYER EMBEDDING (LightLE)

### 5.1 3-Level Feature Tap Design

```
MobileNetV2Plus Feature Pyramid:

Layer 0 (Initial):
  Conv 3x3, stride=2: (B, 3, 224, 224) → (B, 32, 112, 112)

Layers 1-19 (Inverted Residual + ECA):
  
  Tap Point 1 (Index 13):  ← First layer embedding
    └─ Channel dimension: 96
    └─ Spatial resolution: 14×14 (after stride-2 ops)
    └─ Purpose: Mid-level features
  
  Tap Point 2 (Index 17):  ← Second layer embedding
    └─ Channel dimension: 320
    └─ Spatial resolution: 7×7 (after stride-2 ops)
    └─ Purpose: High-level features
  
  Tap Point 3 (Final, Index 19):  ← Third layer embedding
    └─ Channel dimension: 1280
    └─ Spatial resolution: 7×7 (no additional stride)
    └─ Purpose: Final semantic features

LightLE combines these THREE taps with learned weights.
```

### 5.2 Feature Extraction Process (LightLE)

```
Input: x (B, 3, 224, 224)

Loop through self.features (19 blocks):
  for feature_idx, layer in enumerate(self.features):
    x = layer(x)
    
    if feature_idx in [13, 17, 19]:  # Tap indices
      ├─ Adaptive Global Average Pooling
      │  └─ (B, C, 7, 7) → (B, C, 1, 1) → (B, C)
      │
      ├─ Channel Alignment (Parameter-Free):
      │  if C ≠ 1280:
      │    ├─ Unsqueeze: (B, C) → (B, 1, C)
      │    ├─ Linear interpolation: resize to 1280
      │    └─ Squeeze: (B, 1, 1280) → (B, 1280)
      │  else:
      │    └─ Keep as is
      │
      └─ Append to tokens list

tokens = [(B, 1280), (B, 1280), (B, 1280)]  # 3 tokens
```

### 5.3 Fusion Mechanism

```
Stacked Tokens: (3, B, 1280)

Step 1: Add Level Embeddings
  self.level_embeds = nn.Parameter(torch.zeros(3, 1280))
  
  tokens = tokens + level_embeds.unsqueeze(0)
  # Broadcast: (3, B, 1280) + (1, 3, 1280)
  
  Output: (3, B, 1280)

Step 2: LayerNorm Fusion
  self.fusion_norm = nn.LayerNorm(1280)
  
  tokens = fusion_norm(tokens)  # (3, B, 1280)
  
  Purpose: Normalize across feature dimension

Step 3: Softmax-Weighted Fusion
  self.level_weights = nn.Parameter(torch.zeros(3))
  
  weights = softmax(level_weights)  # (3,)
  # Example: [0.33, 0.33, 0.34]
  
  weights = weights.view(1, -1, 1)  # (1, 3, 1)
  
  Step 4: Weighted Sum
  fused = (tokens * weights).sum(dim=1)  # (B, 1280)
  
  Output: (B, 1280) - single fused feature vector
```

### 5.4 Parameter Count (LightLE)

```
For 7 or 8 classes (same structure):

Level Embeddings:
  Shape: (3, 1280)
  Parameters: 3 × 1280 = 3,840

Fusion Norm (LayerNorm(1280)):
  Weight: 1280
  Bias: 1280
  Parameters: 2,560

Fusion Weights (Learnable scalar):
  Shape: (3,)
  Parameters: 3

TOTAL LIGHTLE: 3,840 + 2,560 + 3 = 6,403 parameters
```

---

## 6. GEM POOLING (GENERALIZED MEAN POOLING)

### 6.1 Konsept

```
Traditional Pooling:
  - MaxPool: Extracts maximum value
  - AvgPool: Computes average
  
GeM Pooling (Generalized Mean):
  - Learnable power parameter p
  - p=1 → AvgPool behavior
  - p→∞ → MaxPool behavior
  - p=3 (default) → Interpolate between

Formula:
  GeM(x) = (1/N * Σ(x_i^p))^(1/p)
  
  where:
    - N = number of spatial elements
    - p = learnable power parameter
    - Can be initialized and tuned during training
```

### 6.2 Implementation

```python
class GeM(nn.Module):
    def __init__(self, p=3.0, eps=1e-6):
        super(GeM, self).__init__()
        self.p = nn.Parameter(torch.ones(1) * p)
        self.eps = eps

    def forward(self, x):
        # x: [B, C, H, W]
        
        # Clamp to avoid NaN (very small values safe from log)
        x = torch.clamp(x, min=self.eps)
        
        # Raise to power p
        x = x.pow(self.p)
        
        # Average pool over spatial (H, W) dimensions
        x = F.avg_pool2d(x, (x.size(-2), x.size(-1)))
        # Output: (B, C, 1, 1)
        
        # Take root (1/p power)
        x = x.pow(1.0 / self.p)
        
        return x
        # Output: (B, C, 1, 1)
```

### 6.3 Usage in MobileNetV2Plus

```
After features extraction (7×7 spatial resolution):
  feature_maps: (B, 1280, 7, 7)

GeM Pooling:
  ├─ Clamp: avoid numerical issues
  ├─ Power: (B, 1280, 7, 7) ^ p
  ├─ AvgPool2d: (B, 1280, 7, 7) → (B, 1280, 1, 1)
  ├─ Root: (B, 1280, 1, 1) ^ (1/p)
  └─ Flatten: (B, 1280)

Benefits:
  ├─ Learnable pooling strategy
  ├─ Better feature aggregation
  ├─ Soft attention without explicit attention
  └─ Improves generalization
```

---

## 7. FEATURE ADAPTER

### 7.1 Purpose & Configuration

```
Optional linear projection layer between features and classifier.

Usage:
  ├─ Adaptive dimensionality reduction
  ├─ Additional non-linearity
  └─ Feature space adaptation

Example:
  feature_adapter_dim = 512  # Project to 512-dim
  
  Adapter = Linear(1280, 512)
  
  With adapter flow:
    x_features: (B, 1280)
    ├─ adapter(x): (B, 512)
    ├─ dropout(x): (B, 512)
    └─ classifier(x): (B, 7)
```

### 7.2 Parameter Counting

```
NO ADAPTER (feature_adapter_dim = 0 or None):
  ├─ Adapter parameters: 0
  ├─ Classifier input: 1280
  └─ Total added: 0 params

WITH ADAPTER (feature_adapter_dim = 512):
  ├─ Linear(1280 → 512):
  │  ├─ Weight: 1280 × 512 = 655,360
  │  └─ Bias: 512
  │  Subtotal: 655,872
  └─ Total added: 655,872 params

Recommendation: Usually disabled (feature_adapter_dim=0) to keep
the model lightweight for student models.
```

---

## 8. FORWARD PASS - COMPLETE EXAMPLE

### 8.1 Input to Output Flow

```
Input: RGB Image (1, 3, 224, 224) [single sample]

┌─────────────────────────────────┐
│ STAGE 1: FEATURE EXTRACTION     │
└─────────────────────────────────┘

Step 1: MobileNetV2 Backbone
  ├─ Conv 3x3, stride=2: 3 → 32 channels
  │  Output: (1, 32, 112, 112)
  │
  ├─ 19 × Inverted Residual Blocks (with ECA)
  │  ├─ Multiple stride-2 operations
  │  ├─ Channel progression: 32→16→24→32→64→96→160→320
  │  └─ Final output: (1, 1280, 7, 7)
  │
  ├─ ECA attention applied in each block
  │  └─ Adaptive channel gating
  │
  └─ Output: (1, 1280, 7, 7)

┌─────────────────────────────────┐
│ STAGE 2: LAYER EMBEDDING (LightLE)
└─────────────────────────────────┘

IF lightweight_layer_embedding=True:
  
  Tap Index 13:
    ├─ Extract: features[13](x) → (1, 96, H, W)
    ├─ AdaptiveAvgPool2d(1) → (1, 96)
    ├─ Linear interpolate 96→1280 → (1, 1280)
    └─ Add level_embeds[0] → (1, 1280)
  
  Tap Index 17:
    ├─ Extract: features[17](x) → (1, 320, H, W)
    ├─ AdaptiveAvgPool2d(1) → (1, 320)
    ├─ Linear interpolate 320→1280 → (1, 1280)
    └─ Add level_embeds[1] → (1, 1280)
  
  Tap Index 19 (Final):
    ├─ Extract: features[19](x) → (1, 1280, 7, 7)
    ├─ GeM pooling → (1, 1280, 1, 1)
    ├─ Flatten → (1, 1280)
    └─ Add level_embeds[2] → (1, 1280)
  
  Stack: (3, 1, 1280)
  LayerNorm: (3, 1, 1280)
  Softmax-weighted fusion: (1, 1280)

ELSE (no LightLE):
  ├─ GeM pooling: (1, 1280, 7, 7) → (1, 1280, 1, 1)
  ├─ Flatten: (1, 1280)
  └─ Output: (1, 1280)

┌─────────────────────────────────┐
│ STAGE 3: FEATURE ADAPTATION     │
└─────────────────────────────────┘

IF feature_adapter is not Identity:
  ├─ Linear projection: (1, 1280) → (1, adapter_dim)
  └─ Output: (1, adapter_dim)
ELSE:
  └─ No change: (1, 1280)

┌─────────────────────────────────┐
│ STAGE 4: DROPOUT                │
└─────────────────────────────────┘

Dropout: (1, 1280) [random drop during training]
Output: (1, 1280)

┌─────────────────────────────────┐
│ STAGE 5: ViCH CLASSIFIER HEAD   │
└─────────────────────────────────┘

Input: (1, 1280)

TRAINING MODE:
  ├─ mu = Linear(1280→7): (1, 7)
  ├─ logvar = Linear(1280→7): (1, 7)
  ├─ logvar = clamp(logvar, -10, 10): (1, 7)
  ├─ sigma = exp(0.5 * logvar): (1, 7)
  ├─ eps ~ N(0,1): (1, 7)
  ├─ logits = mu + sigma * eps: (1, 7)
  ├─ kl_loss = -0.5*sum(1+logvar-mu²-exp(logvar)): scalar
  └─ return {logits, mu, logvar, kl_loss}

INFERENCE MODE:
  ├─ mu = Linear(1280→7): (1, 7)
  ├─ logvar = Linear(1280→7): (1, 7)
  ├─ logits = mu (deterministic): (1, 7)
  └─ return {logits, mu, logvar, 0}

FINAL OUTPUT:
  ├─ logits: (1, 7) - raw predictions
  ├─ mu: (1, 7) - mean predictions (same as logits at inference)
  ├─ logvar: (1, 7) - log-variance (uncertainty per class)
  └─ kl_loss: scalar - regularization term
```

### 8.2 Loss Computation (Training)

```
Total Loss = CE Loss + KLD Loss

CE Loss:
  y_pred = softmax(logits)       # (B, 7)
  y_true = one_hot(labels)       # (B, 7)
  
  loss_ce = CrossEntropy(logits, labels)  # Scalar
  
  Weighted: loss_ce (dominant, ~1.0)

KLD Loss (from ViCH head):
  kl_loss = -0.5 * sum(1 + logvar - mu² - exp(logvar))
  
  Weighted: β * kl_loss
  where β = 1e-4 (from config)
  
  Purpose: Regularization, KL annealing

Total:
  L_total = loss_ce + (1e-4) * kl_loss
  
  Example numbers:
    loss_ce = 0.5
    kl_loss = 100.0
    L_total = 0.5 + 1e-4*100 = 0.5 + 0.01 = 0.51
```

---

## 9. TRAINING CONFIGURATION

### 9.1 RAF-DB Student Training

```yaml
Model Configuration:
  ├─ num_classes: 7
  ├─ width_mult: 1.0
  ├─ dropout_rate: 0.3
  ├─ layer_embedding: true
  ├─ lightweight_layer_embedding: true
  ├─ embedding_dim: 1280
  ├─ feature_adapter_dim: 0
  ├─ use_vich_sampling: true
  ├─ vich_logvar_min: -10.0
  ├─ vich_logvar_max: 10.0
  └─ vich_init_logvar_bias: -5.0

Training Hyperparameters:
  ├─ Epochs: 200
  ├─ Batch Size: 48
  ├─ Learning Rate: 3e-4
  ├─ Weight Decay: 1e-4
  ├─ Optimizer: AdamW
  ├─ LR Scheduler: CosineAnnealingLR
  └─ EMA Decay: 0.999

Data Augmentation:
  ├─ Input resolution: 224×224
  ├─ Train: Resize 256, RandomCrop 224
  ├─ Val: Resize 256, CenterCrop 224
  ├─ RandomHorizontalFlip: 50%
  ├─ Rotation: ±12 degrees
  ├─ ColorJitter: 0.2 (brightness/contrast/saturation)
  └─ Random Erasing: 10%

Loss Weights:
  ├─ α (CE): 0.3 (hard label CE)
  ├─ β (KD): 0.7 (teacher soft target KD)
  ├─ γ (VICH KL): 1e-4 (regularization)
  └─ Temperature (KD): 4.0

Mixup Configuration:
  ├─ Alpha: 0.1
  ├─ Teacher: Never sees mixed images
  ├─ Student: Gets mixed images + mixed targets
  └─ Purpose: Regularization + KD
```

### 9.2 Optimizer Details

```
AdamW (Adam with Weight Decay):
  ├─ Default β₁: 0.9
  ├─ Default β₂: 0.999
  ├─ Default ε: 1e-8
  ├─ Weight decay (decoupled): 1e-4
  └─ Learning rate: 3e-4

Cosine Annealing LR Schedule:
  LR(t) = LR_min + (LR_max - LR_min) * (1 + cos(π*t/T)) / 2
  
  Parameters:
    ├─ LR_max: 3e-4
    ├─ LR_min: ~0 (typically 1e-6)
    ├─ T: 200 (max epochs)
    └─ t: current epoch
  
  Behavior:
    ├─ Epoch 0: LR = 3e-4
    ├─ Epoch 100: LR ≈ 1.5e-4
    ├─ Epoch 199: LR ≈ 0
```

---

## 10. INFERENCE & DEPLOYMENT

### 10.1 Model Loading

```python
import torch
from models.mobilenetv2_plus import mobilenetv2_plus

# Initialize model
model = mobilenetv2_plus(
    num_classes=7,
    width_mult=1.0,
    dropout_rate=0.3,
    layer_embedding=True,
    lightweight_layer_embedding=True,
    use_vich_sampling=True,
    vich_logvar_min=-10.0,
    vich_logvar_max=10.0,
    vich_init_logvar_bias=-5.0,
)

# Load checkpoint
checkpoint = torch.load('best_checkpoint.pth', 
                        map_location='cpu')
model.load_state_dict(checkpoint['model_state_dict'])

# Set to eval mode
model.eval()
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)
```

### 10.2 Inference Code

```python
def predict_emotion(image_path, model, device):
    # Load and preprocess image
    from PIL import Image
    import torchvision.transforms as transforms
    
    # Preprocessing
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    image = Image.open(image_path).convert('RGB')
    image = transform(image).unsqueeze(0)  # (1, 3, 224, 224)
    image = image.to(device)
    
    # Forward pass
    with torch.no_grad():
        output = model(image)
    
    # Extract predictions
    logits = output['logits']          # (1, 7)
    mu = output['mu']                  # (1, 7)
    logvar = output['logvar']          # (1, 7)
    
    # Get confidence
    probabilities = torch.softmax(logits, dim=1)  # (1, 7)
    predicted_class = torch.argmax(probabilities, dim=1)  # (1,)
    confidence = probabilities.max().item()
    
    # Uncertainty from logvar
    uncertainty = torch.exp(0.5 * logvar)  # Standard deviation
    
    emotion_labels = [
        'Neutral', 'Happiness', 'Sadness', 'Anger',
        'Surprise', 'Disgust', 'Fear'
    ]
    
    return {
        'emotion': emotion_labels[predicted_class.item()],
        'confidence': confidence,
        'logits': logits[0].cpu().numpy(),
        'uncertainty': uncertainty[0].cpu().numpy()
    }
```

### 10.3 Inference Speed

```
Throughput (Batch=1):
  ├─ GPU (RTX 3080): ~200-300 samples/sec
  ├─ Latency: ~3-5 ms per image
  └─ Memory: ~100 MB

Memory Footprint:
  ├─ Model size: ~9 MB (state_dict)
  ├─ Runtime memory: ~150 MB
  └─ Suitable for edge devices (if quantized)

Optimization Tips:
  ├─ Use TorchScript JIT compilation
  ├─ ONNX export for CPU inference
  ├─ Quantization (8-bit or 4-bit)
  ├─ Pruning (remove small weights)
  └─ Distillation (compress further)
```

---

## 11. PARAMETER SUMMARY

### 11.1 Total Parameter Count (7 Classes)

```
MobileNetV2 Backbone:
  ├─ Conv3x3 (3→32): ~800
  ├─ 19 Inverted Residuals: ~2,140,000
  └─ Final Conv (320→1280): ~400,000
  Subtotal: ~2,541,000

Lightweight Layer Embedding:
  ├─ Level embeddings: 3,840
  ├─ LayerNorm weights: 2,560
  ├─ LayerNorm bias: 2,560
  ├─ Fusion weights: 3
  └─ Subtotal: 8,963

ViCH Head:
  ├─ Linear_mu (1280→7): 8,967
  ├─ Linear_logvar (1280→7): 8,967
  └─ Subtotal: 17,934

GeM Pooling:
  ├─ Power parameter p: 1
  └─ Subtotal: 1

Dropout:
  └─ No parameters

TOTAL (7 Classes): ~2,568,698 ≈ 2.57M

Reported in README: 2,248,291 (model config différent?)
Discrepancy: Possible width_mult or configuration variation
```

### 11.2 Parameter vs Teacher Model

```
MobileNetV2Plus (Student) vs POSTERv2 (Teacher):

                    Student         Teacher     Ratio
─────────────────────────────────────────────────────
Total Params:       2.25M           ~100M       1:44
FLOPs (224×224):    0.33G           ~15G        1:45
Model Size:         ~9 MB           ~400 MB     1:44
Inference Speed:    200 img/s       20 img/s    10x faster
Accuracy (RAF-DB):  88.72%          92.41%      -3.7%
─────────────────────────────────────────────────────

Student Efficiency:
  ├─ 45x smaller in parameters
  ├─ 45x fewer FLOPs
  ├─ 10x faster inference
  ├─ Accurate within 3.7% of teacher
  └─ Ideal for knowledge distillation
```

---

## 12. ViCH HEAD vs VAE HEAD KARŞILAŞTIRMASI

```
                    ViCH Head       VAE Head
─────────────────────────────────────────────
Class Space:        Direct          Latent + linear
Dimensionality:     num_classes     num_classes
Parameters:         ~18K (7-cls)    ~256K+ (768→nc)
Complexity:         Light           Heavy
Sampling:           Optional        Always (training)
Uncertainty:        Per-class       Latent space
Use Case:           Classification  Reconstruction
Training Speed:     Fast            Slower
─────────────────────────────────────────────

Why ViCH for Student?
  ├─ Lightweight: ~18K params vs ~256K
  ├─ Efficient: Direct class-space prediction
  ├─ Practical: Per-class uncertainty
  └─ Fast: No latent reconstruction needed
```

---

## 13. ÖZET & KÖŞELİ NOKTALAR

### 13.1 Temel Özellikler

✅ **Hafif Mimari:** 2.25M parametreler, 0.33G FLOPs  
✅ **ViCH Head:** Class-level probabilistic predictions  
✅ **LightLE:** True 3-level lightweight layer embedding  
✅ **ECA:** Efficient channel attention bütün blokta  
✅ **GeM Pooling:** Learnable mean pooling  
✅ **Multi-Resolution:** 112, 224, 256 piksel destekler  
✅ **Uncertainty:** LogVar ile per-class belirsizlik  
✅ **Fast Inference:** ~200 samples/sec (GPU)  

### 13.2 Sınırlamalar

⚠️ **Doğruluk:** Öğretmenden ~3.7% düşük  
⚠️ **Transfer:** RAF-DB specific training  
⚠️ **Mobile:** Quantization gerekli edge deployment için  
⚠️ **Stability:** Logvar clamping sayısal kararlılık için  

### 13.3 Optimization Potansiyeli

🔧 **Quantization:** FP32 → INT8 (4x küçülme)  
🔧 **Pruning:** Unimportant weights kaldırma  
🔧 **Distillation:** Daha küçük model  
🔧 **Layer Fusion:** Conv+BN fusion  

---

**Document Version:** 1.0  
**Model Status:** Production-ready student model  
**Last Updated:** 2026-06-14
