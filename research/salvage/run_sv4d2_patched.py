"""SV4D2 runner with a Blackwell (sm_120) attention fix.

xformers has no memory_efficient_attention kernel for head_dim>256 on compute
capability 12.0 (flash needs <=256, cutlass needs <=sm9.0). SV4D2 uses head_dim
512 in its spatio-temporal attention, so we monkeypatch xformers'
memory_efficient_attention to route through torch's native scaled_dot_product_
attention, which falls back to the MATH backend for large head dims and works on
any GPU. (Same monkeypatch strategy as the D41 gsplat renderer swap.)
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # repo root: relative assets/, checkpoints/, outputs/

import torch
import xformers.ops


def _sdpa_meff(query, key, value, attn_bias=None, p=0.0, scale=None, op=None):
    # xformers accepts either 4D (B, M, H, K) [spacetime attn] or 3D (B, M, K)
    # [sgm CrossAttention passes (B*heads, M, dim_head)]. torch SDPA wants (B, H, M, K).
    nd = query.dim()
    if nd == 4:                                   # (B, M, H, K) -> (B, H, M, K)
        q, k, v = query.transpose(1, 2), key.transpose(1, 2), value.transpose(1, 2)
    else:                                         # (B, M, K)    -> (B, 1, M, K)
        q, k, v = query.unsqueeze(1), key.unsqueeze(1), value.unsqueeze(1)
    mask = attn_bias if isinstance(attn_bias, torch.Tensor) else None
    out = torch.nn.functional.scaled_dot_product_attention(
        q, k, v, attn_mask=mask, dropout_p=p, scale=scale
    )
    return out.transpose(1, 2) if nd == 4 else out.squeeze(1)


xformers.ops.memory_efficient_attention = _sdpa_meff
print("[patch] xformers.memory_efficient_attention -> torch SDPA (Blackwell head_dim>256 fix)")

from fire import Fire
from scripts.sampling.simple_video_sample_4d2 import sample

if __name__ == "__main__":
    Fire(sample)
