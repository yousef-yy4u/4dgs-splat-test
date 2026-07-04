---
name: generation-texture-method
description: Why our TRELLIS textures are muddy/dark and how the commercial tools actually texture+rig (multi-view PBR diffusion); build-vs-buy
metadata: 
  node_type: memory
  type: reference
  originSessionId: 24579502-6ef7-48d2-b636-2f52b5500f62
---

Deep-research (2026-06-28, D43) on how Meshy/Tripo/Rodin/Hunyuan3D generate textured+rigged 3D, and our clean path. Full report: `research/generation-texture-rigging.md`.

**Why our textures are muddy/dark:** we render TRELLIS's Gaussian splats from many views and bake that → a soft, view-averaged, shadow-contaminated single-colour texture. This is the WRONG method and can't be fixed by tuning the bake (splat inflation, etc.).

**How the commercial tools do it:** mesh-conditioned **multi-view PBR diffusion** — diffusion conditioned on the mesh geometry (normal/coord maps) synthesises view-consistent images (reference-attention + multi-view attention/sync + 3D-aware RoPE), as **decomposed delit PBR** (albedo/metallic/roughness, illumination-invariant), back-projected to UV + super-res + seam-inpaint. (Hunyuan3D-Paint, SyncMVD, MVPaint, MaterialMVP, PBR3DGen.)

**Rigging:** our **UniRig (MIT) is already the right modern learned auto-rigger** — keep it. See [[rigged-gaussian-splatting]].

**Licensing landmine:** best open PBR-texture models (Hunyuan3D-2/2.1/Paint, MaterialMVP) = non-OSI **Tencent Community License** (1M-MAU cap, void in EU/UK/South Korea) → do NOT ship. Only clean MIT/Apache self-host texture upgrade = **TRELLIS.2** (native-3D PBR, unproven quality). See [[licensing-landmines]].

**UPDATE (D44, benchmarked):** built + ran **TRELLIS.2-4B** locally on the 5090 — **EXCELLENT game-ready PBR, decisively beats our gsplat-bake** (matches input quality). Self-hosted, MIT, **$0/asset**, ~80–145s/asset at 512³. Clean-license caveats: DINOv3 encoder (commercial-OK + "Built with DINOv3" attribution; gated) and **briaai/RMBG-2.0 is NON-COMMERCIAL → swap for clean u2net `rembg`** (pipeline skips RMBG when input is RGBA). Blackwell build is a slog: torch 2.11+cu128 + xformers 0.0.35 (torch 2.8/xformers 0.0.32 crashes attention on sm_120), 4 CUDA exts with `9.0+PTX`, transformers-5.x patch (`model.model.layer`). Env: conda `trellis2` + repo `/home/sov2/projects/TRELLIS.2`; bench `generation/bench_trellis2.py`.

**RECOMMENDATION (D44): adopt TRELLIS.2 as geometry+texture backend** (replace v1 TRELLIS + gsplat-bake), keep UniRig + transfer_rig for animation. Tripo "buy" still a fallback (lower ops, per-asset $) — comparison pending Tripo credits. Generation is the authoring BACKEND not the moat. See [[generation-pipeline-reality-check]].
