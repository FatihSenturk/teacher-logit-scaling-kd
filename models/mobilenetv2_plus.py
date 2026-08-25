import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from pathlib import Path

# ------------------------------------------------------------------------------
# 1. ECA Layer (Efficient Channel Attention)
# ------------------------------------------------------------------------------
class ECALayer(nn.Module):
    """
    Efficient Channel Attention (ECA) Layer.
    Paper: https://arxiv.org/abs/1910.03151
    """
    def __init__(self, channels, gamma=2, b=1):
        super(ECALayer, self).__init__()
        # Adaptive kernel size k
        # k = | (log2(C) / gamma) + (b / gamma) |_odd
        t = int(abs((math.log(channels, 2) + b) / gamma))
        k = t if t % 2 else t + 1
        
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.conv = nn.Conv1d(1, 1, kernel_size=k, padding=k//2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x: [B, C, H, W]
        y = self.avg_pool(x)       # [B, C, 1, 1]
        y = y.squeeze(-1).permute(0, 2, 1) # [B, 1, C]
        y = self.conv(y)           # [B, 1, C]
        y = self.sigmoid(y)        # [B, 1, C]
        y = y.permute(0, 2, 1).unsqueeze(-1) # [B, C, 1, 1]
        return x * y.expand_as(x)

# ------------------------------------------------------------------------------
# 2. GeM (Generalized Mean Pooling)
# ------------------------------------------------------------------------------
class GeM(nn.Module):
    """
    Generalized Mean Pooling.
    p=1 -> AvgPool
    p=inf -> MaxPool
    """
    def __init__(self, p=3.0, eps=1e-6):
        super(GeM, self).__init__()
        self.p = nn.Parameter(torch.ones(1) * p)
        self.eps = eps

    def forward(self, x):
        # x: [B, C, H, W]
        # clamp to avoid NaN with power
        x = torch.clamp(x, min=self.eps).pow(self.p) 
        x = F.avg_pool2d(x, (x.size(-2), x.size(-1)))
        x = x.pow(1.0 / self.p)
        return x


class VAEClassifier(nn.Module):
    """
    Lightweight VAE-style classifier head inspired by POSTER-Var.

    The head predicts class-space mean/log-variance vectors and samples logits
    during training. At evaluation time it returns the mean logits for stable
    deterministic inference.
    """
    def __init__(self, in_features, out_features):
        super(VAEClassifier, self).__init__()
        self.fc_mu = nn.Linear(in_features, out_features)
        self.fc_logvar = nn.Linear(in_features, out_features)

    def reparameterize(self, mu, logvar):
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(self, x):
        x = x.view(x.size(0), -1)
        mu = self.fc_mu(x)
        logvar = self.fc_logvar(x)
        logits = self.reparameterize(mu, logvar)
        return logits, mu, logvar


class VICHHead(nn.Module):
    """
    Lightweight class-level probabilistic classifier head.

    Unlike a heavy VAE-style head, VICH predicts mean and log-variance directly
    in class space: Linear(feature_dim, num_classes) for both branches.
    """
    def __init__(
        self,
        in_dim: int,
        num_classes: int,
        use_sampling: bool = True,
        logvar_min: float = -10.0,
        logvar_max: float = 10.0,
        init_logvar_bias: float = -5.0,
    ):
        super().__init__()
        self.in_dim = int(in_dim)
        self.num_classes = int(num_classes)
        self.use_sampling = bool(use_sampling)
        self.logvar_min = float(logvar_min)
        self.logvar_max = float(logvar_max)

        self.mu = nn.Linear(self.in_dim, self.num_classes)
        self.logvar = nn.Linear(self.in_dim, self.num_classes)
        self.init_logvar_bias = float(init_logvar_bias)

        self.reset_parameters()

    def reset_parameters(self):
        nn.init.normal_(self.mu.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.mu.bias)
        nn.init.normal_(self.logvar.weight, mean=0.0, std=0.01)
        nn.init.constant_(self.logvar.bias, self.init_logvar_bias)

    @property
    def expected_param_count(self):
        return 2 * (self.in_dim * self.num_classes + self.num_classes)

    def forward(self, x, return_aux: bool = True):
        x = x.view(x.size(0), -1)
        mu = self.mu(x)
        logvar = self.logvar(x)
        logvar = torch.clamp(logvar, min=self.logvar_min, max=self.logvar_max)

        if self.training and self.use_sampling:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            logits = mu + eps * std
        else:
            logits = mu

        kl_loss = -0.5 * torch.sum(
            1.0 + logvar - mu.pow(2) - logvar.exp(),
            dim=1,
        ).mean()

        if return_aux:
            return {
                "logits": logits,
                "mu": mu,
                "logvar": logvar,
                "kl_loss": kl_loss,
            }
        return logits

# ------------------------------------------------------------------------------
# 3. MobileNetV2 Components (Inverted Residual with ECA)
# ------------------------------------------------------------------------------
class ConvBNReLU(nn.Sequential):
    def __init__(self, in_planes, out_planes, kernel_size=3, stride=1, groups=1, act_layer=nn.ReLU6):
        padding = (kernel_size - 1) // 2
        super(ConvBNReLU, self).__init__(
            nn.Conv2d(in_planes, out_planes, kernel_size, stride, padding, groups=groups, bias=False),
            nn.BatchNorm2d(out_planes),
            act_layer(inplace=True) if act_layer is not None else nn.Identity()
        )

class InvertedResidualECA(nn.Module):
    def __init__(self, inp, oup, stride, expand_ratio, use_eca=True, act_layer=nn.ReLU6):
        super(InvertedResidualECA, self).__init__()
        self.stride = stride
        assert stride in [1, 2]

        hidden_dim = int(round(inp * expand_ratio))
        self.use_res_connect = self.stride == 1 and inp == oup

        layers = []
        if expand_ratio != 1:
            # pw
            layers.append(ConvBNReLU(inp, hidden_dim, kernel_size=1, act_layer=act_layer))
        
        # dw
        layers.extend([
            ConvBNReLU(hidden_dim, hidden_dim, stride=stride, groups=hidden_dim, act_layer=act_layer),
        ])
        
        # ECA Injection (After depthwise, before projection)
        if use_eca:
            layers.append(ECALayer(hidden_dim))

        # pw-linear
        layers.extend([
            nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
            nn.BatchNorm2d(oup),
        ])
        
        self.conv = nn.Sequential(*layers)

    def forward(self, x):
        if self.use_res_connect:
            return x + self.conv(x)
        else:
            return self.conv(x)

# ------------------------------------------------------------------------------
# 4. MobileNetV2++ Main Model
# ------------------------------------------------------------------------------
def _make_divisible(v, divisor, min_value=None):
    if min_value is None:
        min_value = divisor
    new_v = max(min_value, int(v + divisor / 2) // divisor * divisor)
    # Make sure that round down does not go down by more than 10%.
    if new_v < 0.9 * v:
        new_v += divisor
    return new_v

class MobileNetV2Plus(nn.Module):
    def __init__(
        self,
        num_classes=7,
        width_mult=1.0,
        dropout_rate=0.2,
        act_layer=nn.ReLU6,
        layer_embedding=False,
        vae_head=False,
        head_type=None,
        lightweight_layer_embedding=False,
        lightweight_layer_embedding_layers=3,
        embedding_dim=None,
        feature_adapter_dim=None,
        layer_embedding_indices=None,
        use_vich_sampling=True,
        vich_logvar_min=-10.0,
        vich_logvar_max=10.0,
        vich_init_logvar_bias=-5.0,
    ):
        super(MobileNetV2Plus, self).__init__()
        if head_type is None:
            head_type = "vae" if vae_head else "linear"
        head_type = str(head_type).lower()
        if head_type == "le_vae":
            head_type = "vae"
        if head_type not in {"linear", "vae", "vich"}:
            raise ValueError(f"Unsupported MobileNetV2Plus head_type: {head_type}")
        
        block = InvertedResidualECA
        input_channel = 32
        last_channel = 1280
        
        # Setting of inverted residual blocks
        # t, c, n, s
        inverted_residual_setting = [
            # t, c, n, s
            [1, 16, 1, 1],
            [6, 24, 2, 2],
            [6, 32, 3, 2],
            [6, 64, 4, 2],
            [6, 96, 3, 1],
            [6, 160, 3, 2],
            [6, 320, 1, 1],
        ]

        # Building first layer
        input_channel = _make_divisible(input_channel * width_mult, 8)
        self.last_channel = _make_divisible(last_channel * width_mult, 8) if width_mult > 1.0 else last_channel
        
        features = [ConvBNReLU(3, input_channel, stride=2, act_layer=act_layer)]
        feature_channels = [input_channel]
        
        # Building inverted residual blocks
        for t, c, n, s in inverted_residual_setting:
            output_channel = _make_divisible(c * width_mult, 8)
            for i in range(n):
                stride = s if i == 0 else 1
                features.append(block(input_channel, output_channel, stride, t, use_eca=True, act_layer=act_layer))
                feature_channels.append(output_channel)
                input_channel = output_channel
                
        # Building last several layers
        features.append(ConvBNReLU(input_channel, self.last_channel, kernel_size=1, act_layer=act_layer))
        feature_channels.append(self.last_channel)
        
        self.features = nn.Sequential(*features)
        self.layer_embedding = bool(layer_embedding)
        self.vae_head = bool(vae_head)
        self.head_type = head_type
        self.lightweight_layer_embedding = bool(lightweight_layer_embedding)
        self.lightweight_layer_embedding_layers = int(lightweight_layer_embedding_layers)
        self.embedding_dim = int(embedding_dim) if embedding_dim is not None else self.last_channel

        # Better Head: GeM + FC/VAE
        self.pool = GeM() 
        self.dropout = nn.Dropout(p=dropout_rate)

        if self.layer_embedding and not self.lightweight_layer_embedding:
            if layer_embedding_indices is None:
                # Multi-scale taps: early semantic, mid semantic, final semantic.
                layer_embedding_indices = (6, 13, len(features) - 1)
            self.layer_embedding_indices = tuple(int(i) for i in layer_embedding_indices)
            invalid = [i for i in self.layer_embedding_indices if i < 0 or i >= len(features)]
            if invalid:
                raise ValueError(f"Invalid layer embedding feature indices: {invalid}")
            self.layer_projections = nn.ModuleList([
                nn.Sequential(
                    nn.Conv2d(feature_channels[i], self.embedding_dim, kernel_size=1, bias=False),
                    nn.BatchNorm2d(self.embedding_dim),
                    nn.GELU(),
                )
                for i in self.layer_embedding_indices
            ])
            self.level_embeds = nn.Parameter(torch.zeros(1, len(self.layer_embedding_indices), self.embedding_dim))
            self.fusion_norm = nn.LayerNorm(self.embedding_dim)
            self.level_weights = None
            classifier_in_features = self.embedding_dim
        elif self.layer_embedding and self.lightweight_layer_embedding:
            if layer_embedding_indices is None:
                layer_embedding_indices = (13, 17, len(features) - 1)
            self.layer_embedding_indices = tuple(int(i) for i in layer_embedding_indices)
            if len(self.layer_embedding_indices) != self.lightweight_layer_embedding_layers:
                raise ValueError(
                    "LightLE tap count must match lightweight_layer_embedding_layers: "
                    f"{len(self.layer_embedding_indices)} != {self.lightweight_layer_embedding_layers}"
                )
            invalid = [i for i in self.layer_embedding_indices if i < 0 or i >= len(features)]
            if invalid:
                raise ValueError(f"Invalid lightweight layer embedding feature indices: {invalid}")
            self.layer_projections = nn.ModuleList()
            self.level_embeds = nn.Parameter(torch.zeros(self.lightweight_layer_embedding_layers, self.last_channel))
            self.fusion_norm = nn.LayerNorm(self.last_channel)
            self.level_weights = nn.Parameter(torch.zeros(self.lightweight_layer_embedding_layers))
            classifier_in_features = self.last_channel
        else:
            self.layer_embedding_indices = tuple()
            self.layer_projections = nn.ModuleList()
            self.level_embeds = None
            self.fusion_norm = nn.Identity()
            self.level_weights = None
            classifier_in_features = self.last_channel
        self.pre_adapter_features = int(classifier_in_features)
        adapter_dim = int(feature_adapter_dim) if feature_adapter_dim is not None and int(feature_adapter_dim) > 0 else 0
        if adapter_dim and adapter_dim != self.pre_adapter_features:
            self.feature_adapter = nn.Linear(self.pre_adapter_features, adapter_dim)
            classifier_in_features = adapter_dim
        else:
            self.feature_adapter = nn.Identity()
        self.classifier_in_features = int(classifier_in_features)

        # Projection/Classifier. VICH returns a dictionary, VAE returns tuple.
        if self.head_type == "vich":
            self.classifier = VICHHead(
                classifier_in_features,
                num_classes,
                use_sampling=use_vich_sampling,
                logvar_min=vich_logvar_min,
                logvar_max=vich_logvar_max,
                init_logvar_bias=vich_init_logvar_bias,
            )
        elif self.head_type == "vae":
            self.classifier = VAEClassifier(classifier_in_features, num_classes)
        else:
            self.classifier = nn.Linear(classifier_in_features, num_classes)

        # Weight initialization
        self._initialize_weights()
        if isinstance(self.classifier, VICHHead):
            # _initialize_weights visits all Linear modules; restore VICH-specific
            # log-variance bias after the generic initialization pass.
            self.classifier.reset_parameters()

    def forward_features(self, x):
        if not self.layer_embedding:
            x = self.features(x)       # [B, 1280, H/32, W/32]
            x = self.pool(x)           # [B, 1280, 1, 1]
            x = torch.flatten(x, 1)     # [B, 1280]
            return x

        if self.lightweight_layer_embedding:
            tokens = []
            target_indices = set(self.layer_embedding_indices)
            for feature_idx, layer in enumerate(self.features):
                x = layer(x)
                if feature_idx in target_indices:
                    pooled = F.adaptive_avg_pool2d(x, output_size=1).flatten(1)
                    if pooled.shape[1] != self.last_channel:
                        # Parameter-free channel alignment keeps LightLE genuinely lightweight.
                        pooled = F.interpolate(
                            pooled.unsqueeze(1),
                            size=self.last_channel,
                            mode="linear",
                            align_corners=False,
                        ).squeeze(1)
                    tokens.append(pooled)

            if len(tokens) != len(self.layer_embedding_indices):
                raise RuntimeError(
                    f"Expected {len(self.layer_embedding_indices)} LightLE tokens, got {len(tokens)}."
                )

            tokens = torch.stack(tokens, dim=1)
            tokens = self.fusion_norm(tokens + self.level_embeds.unsqueeze(0))
            weights = torch.softmax(self.level_weights, dim=0).view(1, -1, 1)
            return torch.sum(tokens * weights, dim=1)

        tokens = []
        projection_idx = 0
        target_indices = set(self.layer_embedding_indices)
        for feature_idx, layer in enumerate(self.features):
            x = layer(x)
            if feature_idx in target_indices:
                projected = self.layer_projections[projection_idx](x)
                pooled = self.pool(projected).flatten(1)
                tokens.append(pooled)
                projection_idx += 1

        if len(tokens) != len(self.layer_embedding_indices):
            raise RuntimeError(
                f"Expected {len(self.layer_embedding_indices)} layer tokens, got {len(tokens)}."
            )

        x = torch.stack(tokens, dim=1)
        x = self.fusion_norm(x + self.level_embeds)
        return x.mean(dim=1)

    def forward(self, x):
        x = self.forward_features(x)
        x = self.feature_adapter(x)
        x = self.dropout(x)
        x = self.classifier(x)
        return x

    def adapter_parameter_count(self):
        return sum(p.numel() for p in self.feature_adapter.parameters())

    def head_parameter_count(self):
        return sum(p.numel() for p in self.classifier.parameters())

    def layer_embedding_parameter_count(self):
        if self.level_embeds is None:
            return 0
        return (
            self.level_embeds.numel()
            + sum(p.numel() for p in self.fusion_norm.parameters())
            + (self.level_weights.numel() if self.level_weights is not None else 0)
        )

    def level_embedding_parameter_count(self):
        return 0 if self.level_embeds is None else self.level_embeds.numel()

    def fusion_norm_parameter_count(self):
        return sum(p.numel() for p in self.fusion_norm.parameters())

    def fusion_weight_parameter_count(self):
        return 0 if self.level_weights is None else self.level_weights.numel()

    def expected_vich_head_parameter_count(self):
        if isinstance(self.classifier, VICHHead):
            return self.classifier.expected_param_count
        return None

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def load_pretrained_weights(self, progress=True):
        """
        Load weights from torchvision (ImageNet pretrained MobileNetV2).
        Only works seamlessly for width_mult=1.0.
        """
        from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
        print("Loading ImageNet pretrained weights...")
        try:
            local_checkpoint = (
                Path(__file__).resolve().parents[1]
                / "pretrained"
                / "hub"
                / "checkpoints"
                / "mobilenet_v2-b0353104.pth"
            )
            if local_checkpoint.exists():
                pretrained_model = mobilenet_v2(weights=None)
                state_dict = torch.load(local_checkpoint, map_location="cpu", weights_only=False)
                pretrained_model.load_state_dict(state_dict, strict=True)
                print(f"Using packaged ImageNet weights: {local_checkpoint}")
            else:
                weights = MobileNet_V2_Weights.IMAGENET1K_V1
                pretrained_model = mobilenet_v2(weights=weights)
            pretrained_dict = pretrained_model.state_dict()
            model_dict = self.state_dict()
            
            # Map weights
            # The structure is very similar (features.X.conv.Y...)
            # We iterate over our model's keys and try to find matches in pretrained
            
            # Key mapping:
            # features.0.0.weight -> features.0.0.weight
            # features.1.conv.0.0.weight -> features.1.conv.0.0.weight (for IR blocks without ECA)
            # features.X.conv.0... (for IR blocks with ECA)
            # The block structure in torchvision is:
            # InvertedResidual -> conv (Sequential) -> [ConvBNReLU, ConvBNReLU, ...]
            
            # Our structure:
            # InvertedResidualECA -> conv (Sequential) -> [ConvBNReLU, ConvBNReLU, ECALayer, Conv2d, BatchNorm2d]
            
            # So the indices within 'conv' might differ due to ECA insertion?
            # Let's look at InvertedResidualECA again.
            # layers.extend([ConvBNReLU, ...])
            # layers.append(ECALayer)
            # layers.extend([Conv2d, BatchNorm2d])
            # self.conv = Sequential(*layers)
            
            # Torchvision InvertedResidual:
            # layers.extend([ConvBNReLU, ...]) (expansion)
            # layers.extend([ConvBNReLU, ...]) (depthwise)
            # layers.append(Conv2d) (projection)
            # layers.append(BatchNorm2d)
            # self.conv = Sequential(*layers)
            
            # So for expansion=1 blocks:
            # TV: [dw, proj, bn] -> 0, 1, 2
            # Ours: [dw, eca, proj, bn] -> 0, 1, 2, 3 (if eca inserted at idx 1)
            # Wait, InvertedResidualECA:
            # layers.append(ConvBNReLU) (pw) -> idx 0
            # layers.extend([ConvBNReLU]) (dw) -> idx 1
            # layers.append(ECALayer) -> idx 2
            # layers.extend([Conv2d, BatchNorm2d]) -> idx 3, 4
            
            # TV InvertedResidual:
            # layers.extend([ConvBNReLU]) (pw) -> idx 0
            # layers.extend([ConvBNReLU]) (dw) -> idx 1
            # layers.append(Conv2d) -> idx 2
            # layers.append(BatchNorm2d) -> idx 3
            
            # So:
            # 0 (pw) -> 0 (pw) [Match]
            # 1 (dw) -> 1 (dw) [Match]
            # 2 (eca) -> Missing in TV [Skip]
            # 3 (proj) -> 2 (proj) [Mismatch index]
            # 4 (bn) -> 3 (bn) [Mismatch index]
            
            # We need smart loading.
            
            new_state_dict = {}
            unused_pretrained_keys = set(pretrained_dict.keys())
            
            for key in model_dict:
                # Basic check: if key exists directly
                if key in pretrained_dict and pretrained_dict[key].shape == model_dict[key].shape:
                    new_state_dict[key] = pretrained_dict[key]
                    unused_pretrained_keys.discard(key)
                    continue
                
                # Handle shifted indices due to ECA
                # Pattern: features.X.conv.Y...
                parts = key.split('.')
                if len(parts) > 3 and parts[0] == 'features' and parts[2] == 'conv':
                    block_idx = parts[1]
                    layer_idx = int(parts[3])
                    param_name = ".".join(parts[4:])
                    
                    # Mapping logic
                    # If expansion != 1:
                    #   0 -> 0 (pw)
                    #   1 -> 1 (dw)
                    #   2 -> ECA (Skip)
                    #   3 -> 2 (proj)
                    #   4 -> 3 (bn)
                    
                    # If expansion == 1 (first block):
                    #   TV: [dw, proj, bn] -> 0, 1, 2
                    #   Ours: [dw, eca, proj, bn] -> 0, 1, 2, 3
                    #   0 -> 0
                    #   1 -> ECA
                    #   2 -> 1
                    #   3 -> 2
                    
                    # BUT wait, specific blocks have expansion=1.
                    # Block 0 (features.1) in MobileNetV2 has expansion=1.
                    
                    # Let's try to infer from shape match
                    # Iterate over unused pretrained keys in the same block 'features.X'
                    # and try to match shape and type (weight/bias/running_mean/etc)
                    
                    found = False
                    prefix = f"features.{block_idx}.conv"
                    
                    # Potential candidate keys in pretrained dict
                    candidates = [k for k in unused_pretrained_keys if k.startswith(prefix) and k.endswith(param_name)]
                    
                    for cand in candidates:
                         if pretrained_dict[cand].shape == model_dict[key].shape:
                             new_state_dict[key] = pretrained_dict[cand]
                             unused_pretrained_keys.discard(cand)
                             found = True
                             break
                    
                    if found:
                        continue

            model_dict.update(new_state_dict)
            self.load_state_dict(model_dict)
            print(f"Loaded {len(new_state_dict)}/{len(model_dict)} keys from ImageNet pretrained MobileNetV2.")
            
        except Exception as e:
            print(f"Failed to load pretrained weights: {e}")

                
def mobilenetv2_plus(
    num_classes=7,
    width_mult=0.7,
    dropout_rate=0.2,
    act_layer=nn.ReLU6,
    layer_embedding=False,
    vae_head=False,
    head_type=None,
    lightweight_layer_embedding=False,
    lightweight_layer_embedding_layers=3,
    embedding_dim=None,
    feature_adapter_dim=None,
    layer_embedding_indices=None,
    use_vich_sampling=True,
    vich_logvar_min=-10.0,
    vich_logvar_max=10.0,
    vich_init_logvar_bias=-5.0,
):
    return MobileNetV2Plus(
        num_classes=num_classes,
        width_mult=width_mult,
        dropout_rate=dropout_rate,
        act_layer=act_layer,
        layer_embedding=layer_embedding,
        vae_head=vae_head,
        head_type=head_type,
        lightweight_layer_embedding=lightweight_layer_embedding,
        lightweight_layer_embedding_layers=lightweight_layer_embedding_layers,
        embedding_dim=embedding_dim,
        feature_adapter_dim=feature_adapter_dim,
        layer_embedding_indices=layer_embedding_indices,
        use_vich_sampling=use_vich_sampling,
        vich_logvar_min=vich_logvar_min,
        vich_logvar_max=vich_logvar_max,
        vich_init_logvar_bias=vich_init_logvar_bias,
    )

if __name__ == '__main__':
    # Initial verification
    model = mobilenetv2_plus(width_mult=0.7)
    params = sum(p.numel() for p in model.parameters())
    print(f"MobileNetV2++ (w=0.7, ECA, GeM) Parameters: {params/1e6:.2f}M")
    
    x = torch.randn(2, 3, 224, 224)
    y = model(x)
    print(f"Output scale: {y.shape}")
