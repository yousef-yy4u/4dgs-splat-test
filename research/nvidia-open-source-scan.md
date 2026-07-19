# NVIDIA Open-Source Scan — clean components for the 4DGS avatar pipeline

> **Date:** 2026-07-13 · **Decision Log:** D61 · **SSOT:** cross-links [PROJECT.md](../PROJECT.md) §0.5/§3, [SESSION_HANDOFF.md](../SESSION_HANDOFF.md), [docs/planning-memory/licensing-landmines.md](../docs/planning-memory/licensing-landmines.md).
>
> **Purpose:** a license-verified sweep of NVIDIA's open-source ecosystem (the 115-project [developer.nvidia.com/open-source](https://developer.nvidia.com/open-source) catalog **plus** the research orgs `NVlabs`, `nv-tlabs`, `NVIDIAGameWorks`, `NVIDIA-RTX`) for components that help build our commercially-clean, on-device, animated Gaussian-splat humanoid-avatar pipeline. All licenses below were verified from primary sources (repo `LICENSE` files, HuggingFace model cards, the NVIDIA license texts) on 2026-07-12/13 by a fan-out of research agents. **Engineering summary, not legal advice** — confirm the flagged items with counsel before commercial ship.

---

## 0. Bottom line

The sweep found three things that matter:

1. **🎯 A near-complete, deliberately-clean pipeline exists — the NVIDIA "SOMA ecosystem."** `GEM-X` (video→pose) + `Kimodo` (text→motion) + `SOMA-X` (topology hub, **Anny is a native backend**) are Apache-code + NVIDIA-Open-Model-License-weights, trained on NVIDIA-owned / **non-AMASS** data. It was engineered specifically to avoid the SMPL/AMASS non-commercial trap — the exact problem our pipeline solves by hand. This hands us most of **Stages 1–2 pre-built**.
2. **⚠️ An urgent warning about code we already run:** `nvdiffrast` — used in [generation/server.py](../generation/server.py)'s texture-bake path — is **NON-COMMERCIAL** (NVIDIA Source Code License, 1-Way Commercial). It must be replaced before any commercial ship.
3. **A clean option exists for every stage**, including a genuinely-commercial feed-forward *image→standalone-Gaussian* model (`Lyra 1.0`) as a Stage-4 reference, and clean shader tooling + a sort-free rendering algorithm for Stage 5.

One load-bearing licensing fact underpins the data-generation options: **the NVIDIA Open Model License explicitly permits using model *outputs* as training data** (NVIDIA claims no ownership of outputs). That turns Cosmos / GEN3C / Lyra from "usable models" into legal synthetic-data generators for Stage 4.

---

## 1. License primer (two NVIDIA licenses, do not confuse them)

| | **NVIDIA Open Model License** | **NVIDIA Source Code License** (a.k.a. "1-Way Commercial" / per-repo NC variants) |
|---|---|---|
| Commercial use | ✅ Yes — permissive commercial | ❌ **No** — "non-commercially… research or evaluation only" |
| Sell / redistribute the model | ✅ "reproduce, use, create derivative works of, make, have made, **sell, offer for sale, distribute**… and import the Model" | ❌ NVIDIA reserves commercial rights |
| Model **outputs** | ✅ NVIDIA claims **no ownership** → **outputs usable as training data** | n/a (it's a code library) |
| Obligations | attribution notice + license copy on redistribution; don't bypass safety guardrails; no patent/copyright litigation vs NVIDIA (auto-terminates); Trustworthy-AI + export compliance | — |
| OSI open-source? | No (use-restrictions) but behaves like a permissive license for our purposes | No |
| Governs | GEM-X, Kimodo (SOMA/G1), SOMA-X-weights, Lyra-1.0, Cosmos, GEN3C weights | nvdiffrast, kaolin-wisp, nvdiffrec, DiffusionRenderer, GET3D, XCube, LION |

**GPU note:** NVIDIA models run best on NVIDIA GPUs and Omniverse is *licensed* to NVIDIA GPUs — a practical/contractual lock-in, but not a general legal restriction on our own product. Acceptable for now.

**Naming trap — flag loudly:** `NVlabs/GEM-X` (SOMA-based, clean) is **not** `NVlabs/GENMO` (which calls itself "GEM" in its README, is **SMPL-based**, and ships under the **NVIDIA OneWay Noncommercial License**). Use GEM-X. Avoid GENMO.

---

## 2. Findings by pipeline stage

Pipeline recap: **Anny (body) → pose → clean-motion → multi-camera render (Stage 3 dataset) → train image→standalone-gaussian model (Stage 4) → skin+LBS-deform+splat on phone (Stage 5).**

### Stage 1 — clean body model
| Project | Repo | License | Clean? | Role |
|---|---|---|---|---|
| **Anny** | `naver/anny` | Apache-2.0 (assets CC0) | ✅ | Our chosen body model (foundation). |
| **SOMA-X** | `NVlabs/SOMA-X` | Apache-2.0 (weights Apache) | ✅¹ | Canonical topology + retarget hub; **Anny is a native backend** → the SOMA↔Anny glue. |
| *MHR* | `facebookresearch/MHR` (Meta, **not** NVIDIA) | Apache-2.0 | ✅ | Clean fallback body model; redundant given Anny. |

¹ Stay on the SOMA/Anny backends. SOMA-X's `[smpl]`/SMPL-X backends require separately-downloaded SMPL/SMPL-X files under their **non-commercial** license — do **not** use the SMPL/SMPL-X interop.

### Stage 2 — clean motion (the ecosystem's strongest hand)
| Project | Repo | License (code / weights) | Clean? | Role |
|---|---|---|---|---|
| **GEM-X** | `NVlabs/GEM-X` | Apache / NVIDIA Open Model | ✅² | **Video → 77-joint SOMA whole-body motion** (body+hands+face), camera- & world-space. "Trained on NVIDIA-owned data only" — no AMASS/BEDLAM; no SMPL-X at inference. |
| **Kimodo** | `nv-tlabs/kimodo` | Apache / NVIDIA Open Model (SOMA & Unitree-G1 variants) | ✅³ | **Text → 30-joint SOMA motion.** Trained on Bones RigPlay (700h) / BONES-SEED (288h) optical mocap — **explicitly not AMASS**. A clean motion source needing no video at all. |
| **Newton** | `newton-physics/newton` | Apache-2.0 (docs CC-BY-4.0) | ✅ | GPU physics substrate (on Warp+USD) for physically-plausible motion. **Alpha-stage, and needs a controller** — it simulates dynamics, it does not generate a gait. Adopt later. |
| *BONES-SEED* | `bones-studio/seed` (HF dataset) | custom "bones-seed-license" (gated) | ⚠️ | Large clean SOMA-format mocap corpus, but commercial use of the raw BVH needs a separate paid license → **consume it indirectly via Kimodo** (whose weights are commercial). |

² **GEM-X input-video must itself be clean** (self-shot / public-domain / CC-licensed). The tool is clean; motion extracted from arbitrary copyrighted video reintroduces source-copyright + performer-likeness exposure.
³ Use Kimodo's SOMA/G1 variants only. Its **`SMPLX` variant is under the non-commercial NVIDIA R&D Model License** — avoid.

### Stage 3 — the multi-camera render harness (does not exist yet)
| Project | Repo | License | Clean? | Role |
|---|---|---|---|---|
| **Omniverse Replicator** | ships in Omniverse Kit / `isaac-sim/IsaacSim` | NVIDIA AI Product Terms (Apr 2026) | ✅⁴ | **Turnkey synthetic-data generator** — emits multi-cam RGB + depth + segmentation + normals + camera intrinsics/extrinsics out of the box. Could *be* the harness. |
| **Kaolin** | `NVIDIAGameWorks/kaolin` | Apache-2.0 (core) | ✅⁵ | **Differentiable batched camera API + DIB-R rasterizer** → a lighter, dependency-free harness and a clean `nvdiffrast` replacement for mesh GT. |
| **Warp** | `NVIDIA/warp` | Apache-2.0 | ✅ | Write custom **LBS-skinning** + render/depth/mask kernels cleanly; middle ground between Replicator and pure Python. |
| **OpenUSD** | `PixarAnimationStudios/OpenUSD` | Tomorrow OSL 1.0 (≈Apache-2.0) | ✅ | Scene/camera/animation interchange glue if going the Omniverse route; optional for a standalone renderer. |
| **Isaac Sim** | `isaac-sim/IsaacSim` | Apache code + Omniverse Kit terms | ✅⁴ | Superset of Replicator; **overkill** unless you want its robotics surface. |
| *3dgrut* | `nv-tlabs/3dgrut` | Apache-2.0 (deps: tcnn BSD, OptiX EULA) | ✅ | Clean Gaussian ray-trace/rasterize reference; distorted-camera (3DGUT) handling; standalone-gaussian output. Reference, not runtime. |

⁴ **Omniverse is free for production as of May 2026.** Clean for rendering **your own** assets (Anny). Only strings: must run on **NVIDIA GPUs**; do **not** redistribute NVIDIA's bundled SimReady/3D-model assets (irrelevant if you only ship renders of your own body). No "outputs-as-training-data" or "no-competing-model" clause in the Omniverse-governing terms.
⁵ Avoid `kaolin.non_commercial.*` (NC module) and the `kaolin.render.mesh` `nvdiffrast_context` backend (pulls NC nvdiffrast). Use the relocated Apache `kaolin.ops.conversions.FlexiCubes` and Kaolin's own DIB-R.

*Honest read:* for a **first** dataset, a lightweight **Kaolin/gsplat/Blender** harness is faster to stand up than the full Omniverse stack; graduate to Replicator when turnkey ground-truth + RTX photorealism justify the weight.

### Stage 4 — the model (architecture references + data generators)
| Project | Repo | License (code / weights / data) | Usable? | Role |
|---|---|---|---|---|
| **Lyra 1.0** | `nv-tlabs/lyra` | Apache / **NVIDIA Open Model (commercial)** / self-distilled | ✅ **weights usable** | Feed-forward **single-image → explicit standalone 3D Gaussians (`.ply`)**, no runtime neural net — the closest clean, weights-included reference for our exact Stage-4 shape. Scene-level, not rigged → add avatar rigging + LBS. |
| **L4GM** | `nv-tlabs/L4GM-official` | Apache / **CC-BY-NC-SA (NC)** / Objaverse-4D (NC) | code only | Feed-forward **4D**-Gaussian arch — reuse the architecture, **retrain clean**; weights blocked. (Confirms prior D55 finding.) |
| **GAvatar** | NVlabs (paper-only, no code) | — | reference | Best *animatable-avatar representation* idea: Gaussians bound to **pose-driven primitives** + implicit SDF — matches our skin-to-rig plan. Text-input, per-subject, no code → inspiration only. |
| **Cosmos** | `NVIDIA/Cosmos`, `nvidia-cosmos/cosmos-predict2.5` | Apache/OpenMDW / **NVIDIA Open Model** | ✅ data-gen | World-foundation video models (Predict = text/image/video→video; Transfer = conditioned video). Generate photoreal human-motion video for augmentation; **outputs usable as training data**. |
| **GEN3C** | `nv-tlabs/GEN3C` | Apache / **NVIDIA Open Model** | ⚠️ data-gen | Camera-controlled image→consistent multi-view/novel-view via a 3D cache. **Verify its Stable-Video-Diffusion upstream provenance** before deploying weights commercially. |
| *Lyra 2.0* | `nv-tlabs/lyra` (2.0 weights) | Apache / **NVIDIA internal R&D license (NC)** | code only | Higher-quality but **non-commercial weights** — architecture reference only; stay on Lyra-1.0 weights. |

### Stage 5 — on-device render (phone WebGL/WebGPU, mkkellogg/GaussianSplats3D lineage)
| Project | Repo | License | Clean? | Role |
|---|---|---|---|---|
| **Slang** | `shader-slang/slang` | Apache-2.0 (LLVM exc.) | ✅ | Author the **LBS-deform + splat shaders once**, cross-compile to GLSL (mature) / WGSL (experimental) / Metal / SPIR-V. Kills the "3 divergent shader copies" problem. Compile-time tool, nothing shipped to the phone. |
| **vk_gaussian_splatting** | `nvpro-samples/vk_gaussian_splatting` | Apache-2.0 | ✅ (reference) | Reference impl of **sort-free "Weighted Sum Rendering"** + StopThePop — **directly attacks the per-frame depth re-sort cost** of moving splats (the key animated-splat cost). Lift the algorithm into the WebGL/WebGPU shader; don't ship the Vulkan code. |

**No NVIDIA phone/WebGPU splat runtime exists** — every NVIDIA real-time splat effort is desktop CUDA/Vulkan/RTX. Our GaussianSplats3D-lineage viewer stays the runtime; NVIDIA contributes shader tooling (Slang) + algorithms (sort-free), not a runtime.

### Stage 4b — face & lip-sync layer (added D62)
The face is a **separate layer with its own control vocabulary (blendshapes)**, not a sub-part of the body render — and the lip-sync/expression ceiling is the **expression basis**, not the renderer.

| Project | Repo | License | Clean? | Role |
|---|---|---|---|---|
| **LAM** | `aigc3d/LAM` | Apache-2.0 | ✅ | One-shot animatable Gaussian **head**, standalone (no runtime neural net) — the head building block (already on disk). |
| **LAM_Audio2Expression** | `aigc3d/LAM_Audio2Expression` | Apache-2.0 | ✅ | Realtime **audio → ARKit expression** — on-device lip-sync driver. |
| **NVIDIA Audio2Face-3D** | `NVIDIA/Audio2Face-3D` (weights `nvidia/Audio2Face-3D-v3.0`) | NVIDIA Open Model | ✅ | **Audio → ARKit blendshapes / mesh-deform** (SOTA lip-sync). Authoring-time (NVIDIA-GPU); on-device runtime uses LAM_Audio2Expression or pre-baked ARKit tracks. |

**Decisions (D62):** use **ARKit's 52 blendshapes** as the expression vocabulary (proper visemes + eye/brow/gaze; phone-native; unencumbered) over FLAME (speech-agnostic, no tongue); drive lip-sync from **audio**, not audio→FLAME-jaw; give the face a **disproportionate gaussian + resolution budget** (uncanny-valley sensitivity); model **tongue/teeth/eyes** explicitly; for **library hero avatars**, per-subject **dense-capture face optimization** (GaussianAvatars/Codec-Avatars/VHAP) sidesteps the synthetic-FLAME ceiling. Keep FLAME to **FLAME-2023-Open (CC-BY)** only where the canonical topology needs it. Composite avatar = **Anny body + LAM head + MM2 clothing**, puppeted on-device by tiny LLM-authored control signals (joint angles + ARKit coefficients + audio). Full reasoning: [PROJECT.md](../PROJECT.md) D62.

---

## 3. ❌ NC / SKIP list (flagged)

**Non-commercial — do not use (code or weights):**
- **`nvdiffrast`** (NVIDIA Source Code License, 1-Way Commercial) — **currently a dependency; REMOVE.**
- **`kaolin-wisp`** (NVIDIA Source Code License, NC; also dormant + neural-field, off-thesis)
- **`GENMO`** (NVIDIA OneWay Noncommercial + SMPL) — the GEM-X name-trap
- **`nvdiffrec`/3D MoMa, `diffusion-renderer`, `GET3D`, `XCube`, `LION`** (all NVIDIA Source Code License, NC) — architecture *ideas* usable but the NC code must be clean-reimplemented, not copied
- **L4GM weights, Lyra-2.0 weights** (NC) — architectures reusable via clean retrain; weights blocked

**Clean license but wrong platform / overkill (skip for this project):**
- **NVRHI** (MIT), **Falcor** (BSD-3; DLSS/RTXGI/RTXDI/NRD add-ons are proprietary), **RTX Remix** (MIT), **Streamline** (MIT + 1 proprietary file) — all desktop-RTX, no phone/WebGPU path
- **MDL-SDK** (BSD-3) — clean, but authored-PBR is indirect for a *capture-driven* photoreal human; assets (vMaterials) carry separate terms
- **tiny-cuda-nn** (BSD-3) — clean, but neural-field accelerator, off-thesis for a no-neural-renderer, standalone-Gaussian pipeline

---

## 4. Residual license checks before commercial ship
1. **GEN3C** — confirm the Stable-Video-Diffusion-derived backbone's license (SVD started non-commercial; NVIDIA relabeling the composite doesn't auto-clear it).
2. **NVIDIA Open Model License artifacts** (GEM-X, Kimodo, Lyra-1.0, Cosmos) — skim the acceptable-use terms once; permissive-commercial, but it's its own license (attribution + guardrails + no-suing-NVIDIA), not literally Apache.
3. **Omniverse path** — NVIDIA-GPU requirement; don't reship bundled SimReady assets; one-line counsel glance at the parent NVIDIA Software License Agreement's generic "no reverse-engineer to build competing software" clause only if you productize against NVIDIA's own avatar tooling.
4. **GEM-X input video** — provenance discipline (self-shot / public-domain / CC only).
5. **MHR** — confirm no separate model-weights EULA at download (LICENSE file itself is Apache-2.0).

---

## 5. PLAN OF ACTION

Sequenced, folding these findings into the existing re-focus (SESSION_HANDOFF §7). Phases A–B are the highest-leverage: they clean the current pipeline and hand us most of Stages 1–2 pre-built.

### Phase A — clean the existing pipeline (do first; cheap)
- **A1.** Replace **`nvdiffrast`** in [generation/server.py](../generation/server.py)'s texture-bake path with a clean rasterizer: **Kaolin DIB-R** (Apache) or **gsplat** (Apache) or PyTorch3D (BSD).
- **A2.** Audit the whole `generation/` + `lhmpp` env for other NC deps (the Inria `diff-gaussian-rasterization` is already known → gsplat).

### Phase B — stand up the SOMA ecosystem for Stages 1–2 (the big accelerator)
- **B1.** Clone **SOMA-X** (Apache); install Anny as a native backend (`pip install "py-soma-x[anny]"`); verify the SOMA→Anny topology-transfer + Warp LBS path end-to-end (pose a SOMA skeleton → deform the Anny mesh). Stay off SMPL/SMPL-X backends.
- **B2.** Clone **GEM-X** (Apache + NVIDIA Open Model weights); run video→77-joint SOMA motion on a **self-shot clean** clip; retarget onto Anny via SOMA-X. → clean motion-from-video path.
- **B3.** Clone **Kimodo** (Apache + NVIDIA Open Model, **SOMA/G1 variants only**); run text→motion; retarget onto Anny. → second clean motion source, no video needed.
- **Outcome:** clean, diverse motion driving Anny from both video and text, license-clean end-to-end — largely replacing the hand-built "clean-motion pipeline" of SESSION_HANDOFF §7.3.

### Phase C — build the Stage-3 multi-camera render harness
- **C1.** Decide **Omniverse Replicator** (turnkey GT writers, free-for-production, NVIDIA-GPU-only, heavyweight) **vs** lightweight **Kaolin** (Apache DIB-R + differentiable camera API) / **Warp** kernels. *Recommendation:* prototype the lightweight Kaolin/gsplat harness first; benchmark Replicator head-to-head when GT-completeness/photorealism justify the Omniverse weight.
- **C2.** Wire: animate Anny (Phase B motion) → place N cameras over M frames → emit multi-view RGB + depth + segmentation + normals + camera intrinsics/extrinsics. Use **OpenUSD** as the scene interchange if Omniverse; skip if lightweight.

### Phase D — pick + prototype the Stage-4 model
- **D1.** Study **Lyra 1.0** (Apache code + commercial weights; feed-forward image→standalone `.ply` gaussians) as the clean reference arch + output representation; **L4GM** (Apache code, retrain-clean) for the 4D temporal head; **GAvatar** (paper) for the animatable-gaussians-on-pose-driven-primitives representation.
- **D2.** Optionally synthesize extra multi-view/video training data with **Cosmos**/**GEN3C** (outputs usable as training data under NVIDIA Open Model License; clear the GEN3C SVD-provenance flag first).
- **D3.** Decide feed-forward-standalone vs per-scene-optimized (D55/D60) — this sets what the Stage-3 harness must emit.

### Phase E — Stage-5 on-device render
- **E1.** Adopt **Slang** to author the LBS-deform + splat shaders once → cross-compile to GLSL (now) / WGSL (as it matures) / Metal. Keep the mkkellogg/GaussianSplats3D-lineage viewer as the runtime.
- **E2.** Port the **sort-free weighted-sum rendering** technique from **vk_gaussian_splatting** (Apache) into the phone splat shader to kill the per-frame depth re-sort cost (the animated-splat cost flagged in [[rigged-gaussian-splatting]] + the D50 Tier-2 gate).

### Cross-cutting discipline
- **Clean input video only** for GEM-X (self-shot / public-domain / CC).
- **Stay off the NC traps:** nvdiffrast, GENMO, Kimodo-SMPLX, SOMA-X SMPL backends, `kaolin.non_commercial.*`, kaolin `nvdiffrast_context`, nvdiffrec/DiffusionRenderer/GET3D/XCube/LION, L4GM/Lyra-2.0 weights.
- Clear the **residual license checks (§4)** before commercial ship.

---

## 6. Repos referenced
GEM-X `NVlabs/GEM-X` · Kimodo `nv-tlabs/kimodo` · SOMA-X `NVlabs/SOMA-X` · Anny `naver/anny` · Lyra `nv-tlabs/lyra` · L4GM `nv-tlabs/L4GM-official` · Cosmos `NVIDIA/Cosmos` · GEN3C `nv-tlabs/GEN3C` · Kaolin `NVIDIAGameWorks/kaolin` · Warp `NVIDIA/warp` · Newton `newton-physics/newton` · OpenUSD `PixarAnimationStudios/OpenUSD` · Isaac Sim `isaac-sim/IsaacSim` · 3dgrut `nv-tlabs/3dgrut` · Slang `shader-slang/slang` · vk_gaussian_splatting `nvpro-samples/vk_gaussian_splatting` · MDL-SDK `NVIDIA/MDL-SDK` · Falcor/NVRHI/RTX-Remix/Streamline (RTX). **NC/skip:** nvdiffrast `NVlabs/nvdiffrast` · kaolin-wisp · GENMO `NVlabs/GENMO` · nvdiffrec `NVlabs/nvdiffrec` · diffusion-renderer · GET3D · XCube · LION (all `nv-tlabs`).
