---
name: rigged-gaussian-splatting
description: "Feasibility, methods, and cost reality of skeleton-rigging Gaussian splats (splat equivalent of AnimaX)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ccb13a99-32a2-4d2b-880e-5c289b6f5a80
---

Can you do the AnimaX idea (skeleton-driven animation) but output a Gaussian splat instead of a mesh? **Yes** — it's an active field called animatable/skinned Gaussian splatting. Relates to [[animax-reimplementation-findings]] and [[project-goal-4dgs]].

**Mechanism:** Linear Blend Skinning (LBS) on Gaussians — canonical splat + skeleton/sparse-control-nodes + skinning weights; each Gaussian's position AND rotation (and rotated SH color coeffs) transform with the bones; optional non-rigid correction field. AnimaX's joint-angle motion output is representation-agnostic, so it can drive a rigged splat directly.

**Key methods:** SC-GS (CVPR 2024, code) = foundational general "sparse control points drive dense Gaussians via LBS"; RigGS (CVPR 2025, articulated objects from video, no template); A³-GS (Oct 2025, auto-estimates skeleton+skinning); Make-It-Animatable (2025, auto-rig+skin mesh OR splat in ~1s); GaussianAvatars/LAM (human heads, FLAME-rigged); RigAnything/UniRig (template-free auto-rig); SV-GS (CVPR 2026).

**Cost reality (the catch):** rigging makes a splat ANIMATABLE but NOT as cheap as a mesh. Per frame an animated splat needs LBS (cheap) + full depth RE-SORT (expensive, can't reuse across frames when geometry moves) + alpha-blend overdraw (expensive). Meshes avoid the sort + overdraw. So animated splat is structurally heavier. Feasible: ONE rigged hero object/avatar (~hundreds-K to ~1M Gaussians) real-time on phone/edge (tight); NOT a full animated splat scene; glasses = tightest budget. Compression/LOD (SOG, sparse control) helps.

**Texture misconception corrected:** browsers DO render realistic textures — WebGL/WebGPU do full PBR; glTF+PBR meshes look great on phones. Splat's real edge over mesh is NOT texture res but: view-dependent appearance (specular via SH), fuzzy/semi-transparent geometry (hair/fur/foliage), and photoreal capture-from-reality with zero material authoring.

**Recommended:** spectrum, not binary — use rigged splats for hero objects/avatars needing captured photorealism, rigged meshes elsewhere / when budget tight; AnimaX-style motion drives both. The high-value open research piece = making rigged-splat animation cheap enough for glasses (compression + LOD + amortized sorting).

**Update (2026-06-24, deep research → PROJECT.md D33):** The WEB-RENDERER path is now concrete, not vaporware. The "dots" look in studio is a renderer gap (THREE.Points) + a position-only skin shader, NOT a hard research problem — `bind_splat.py` already IS the SOTA "per-splat LBS bound to skinned mesh" architecture. Decisive open-source: **Gaussian-VRM** (arXiv 2510.13978, MIT) builds skinned anisotropic splats directly on **mkkellogg/GaussianSplats3D** (the renderer we already use) — and its "**sort on canonical positions, render on skinned positions**" trick directly mitigates the per-frame re-sort cost this memory flagged as the open catch. Strategic Layer-1 engine bet = **Spark** (World Labs, MIT, `SplatMesh extends Object3D`, dual-quaternion `SplatSkinning` that sidesteps the LBS-rotation invalidity). The rotation/SH-must-transform-too point above is confirmed by "On the Skinning of Gaussian Avatars" (2509.11411). Path: gaussian-vrm PoC → Spark → UniMGS (mesh+splat single-pass) only if AR compositing breaks.
