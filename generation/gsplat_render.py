"""Commercially-clean gaussian renderer for TRELLIS texture baking.

TRELLIS's `to_glb` bakes a texture by rendering the gaussian from many views via
`diff_gaussian_rasterization` (Inria, NON-COMMERCIAL — PROJECT.md §4a "never ship"
landmine). We monkeypatch `GaussianRenderer.render` to use **gsplat (Apache-2.0)**
instead, so the textured-GLB path is clean for a commercial product.

Matches the interface render_frames expects: returns edict(color=(3,H,W) float [0,1]).
"""
import numpy as np
import torch
import torch.nn.functional as F
import gsplat
from easydict import EasyDict as edict


def _gsplat_render(self, gaussian, extrinsics, intrinsics, colors_overwrite=None):
    opts = self.rendering_options
    res = int(opts["resolution"])
    ssaa = int(opts.get("ssaa", 1) or 1)
    near = opts["near"] if opts.get("near") is not None else 0.01
    far = opts["far"] if opts.get("far") is not None else 100.0
    W = H = res * ssaa

    means = gaussian.get_xyz.contiguous().float()          # (N,3) world
    quats = gaussian.get_rotation.contiguous().float()     # (N,4) wxyz
    scales = gaussian.get_scaling.contiguous().float()     # (N,3) world
    opac = gaussian.get_opacity.contiguous().float().reshape(-1)  # (N,)
    viewmats = extrinsics.to("cuda").float().reshape(1, 4, 4)     # world->cam

    K = intrinsics.to("cuda").float().clone()              # normalized [0,1]
    K[0, :] *= W                                           # -> pixels
    K[1, :] *= H
    Ks = K.reshape(1, 3, 3)

    if colors_overwrite is not None:
        colors = colors_overwrite.to("cuda").float()       # (N,3) direct RGB
        sh_degree = None
    else:
        colors = gaussian.get_features.contiguous().float()  # (N,K,3) SH
        sh_degree = int(gaussian.active_sh_degree)

    # to_glb renders over a BLACK background (render_multiview bg_color=(0,0,0)), which is
    # gsplat's default when backgrounds is omitted — so we skip it (also dodges gsplat's
    # batched-backgrounds shape assertion).
    render_colors, _, _ = gsplat.rasterization(
        means, quats, scales, opac, colors, viewmats, Ks, W, H,
        sh_degree=sh_degree, near_plane=near, far_plane=far,
        render_mode="RGB", rasterize_mode="classic",
    )
    img = render_colors[0].clamp(0, 1).permute(2, 0, 1).contiguous()  # (3,H,W)
    if ssaa > 1:
        img = F.interpolate(img[None], size=(res, res), mode="bilinear",
                            align_corners=False, antialias=True).squeeze(0)
    return edict({"color": img})


_PATCHED = False


def patch():
    """Idempotently swap TRELLIS's Inria GaussianRenderer.render for the gsplat one."""
    global _PATCHED
    if _PATCHED:
        return
    from trellis.renderers import gaussian_render
    gaussian_render.GaussianRenderer.render = _gsplat_render
    _PATCHED = True
