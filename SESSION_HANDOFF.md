# 4DGS Humanoid — Session Handoff (2026-07-04)

> Read this FIRST in a new session, alongside **PROJECT.md** (SSOT, Decision Log D53–D60) and
> **LHM-plusplus/BLACKWELL_BUILD.md** (env recipe). This file = the concrete current state + next steps.

## 1. THE GOAL (do not lose this again)
Train **our own clean-license 4DGS model** that generates **animated Gaussian-splat avatars**, where:
- the **phone renders the splat ON-DEVICE** (no video streaming; only tiny **motion/bone data** streamed — the §2/D50 architecture),
- the splat is **photorealistic STANDALONE** (the raw gaussians look good with a normal splat rasterizer — **NO neural renderer at runtime**),
- **humanoids first** (Anny + Anny-One clean stack), animation via skinning gaussians to a body rig + per-frame LBS deform in the shader (D33/SPIKE already prototyped this).

GS is chosen specifically for photorealism. Mesh-first is the *other* product lane (D34/D46); this track is the splat lane.

## 2. WHERE WE ACTUALLY ARE (honest)
- The last long stretch built **LHM++ inference** (a pretrained model) to de-risk phone playback (Phase 0). It **works** and produced a 160k-gaussian avatar — but that was a DETOUR.
- **The core deliverable — our own training dataset + model — is NOT started.**
- **Dataset-creation setup = DOES NOT EXIST yet.** We have the Anny parametric model cloned (a building block), but Anny-One (the dataset) is NOT downloaded and we've written ZERO dataset-gen scripts.

## 3. KEY FINDING that shapes the model choice (from the LHM++ detour)
- **LHM++ is feed-forward + a NEURAL RENDERER.** Its good looks come from a per-frame neural net that decodes gaussian *features* → image. The exportable **raw splat is muted/soft** (verified: RGB per-gaussian std ~0.09 even on a colorful input).
- A neural renderer at runtime = GPU-per-viewer = server-side streaming = expensive + doesn't scale + not on-device. **Rejected by the user.**
- **Implication:** do NOT retrain the LHM++ architecture as-is (it inherits the muted-standalone problem). Our model must output **good STANDALONE gaussians** — i.e. either (a) a feed-forward arch designed for standalone quality (D55 levers: per-pixel/adaptive budget, high-res supervision, per-primitive textures à la LGTM), or (b) per-scene optimization (minutes/avatar, photoreal standalone; GaussianAvatars/3DGS-Avatar/SC-GS family, rebuilt on gsplat+Anny). **The multi-view animated-human DATASET is needed either way.**

## 4. THE DATASET (what to build next — the real spine)
Two parts (D57):
1. **Anny-One** — ~800k synthetic multi-view humans (camera params, 2D/3D joints, seg masks). Clean/commercial. Covers appearance/shape/pose/multi-view. **STATIC poses.** → just download it (verify its own download license).
2. **Our 4D/motion sequences (WE BUILD THIS)** — drive **Anny** with **CLEAN motion** (self-authored/procedural/Mixamo-audited — **NOT AMASS = NC**) and render **multi-view animated sequences** (M frames × N cameras + camera params). This temporal supervision is what makes it 4D.
→ "Dataset creation setup" = a pipeline that **poses + animates Anny bodies and renders them from N cameras over time.** Anny gives the poseable/skinnable body (`src/anny/`: anthropometry, shape_distribution, skinning, keypoints); we build the motion + multi-cam render harness (Anny is differentiable PyTorch → can render via gsplat/nvdiffrast, or rasterize meshes for supervision).

## 5. WHAT'S BUILT / ON DISK
- **conda env `lhmpp`** (Blackwell: torch 2.11+cu128, xformers 0.0.35, sm_120). Cloned from `trellis2`. Full recipe: `LHM-plusplus/BLACKWELL_BUILD.md`.
- **`/home/sov2/projects/LHM-plusplus`** — LHM++ repo (architecture reference for retrain). Weights `checkpoints/LHMPP-700M` (4.3GB, HF `3DAIGC/LHMPP-700M`, **CC-BY-NC — eval only**). Priors `pretrained_models/huggingface/...LHMPP-Prior` (7.7GB, incl. SMPL-X/FLAME/voxel_grid). Patched: `core/utils/model_download_utils.py` (disabled the hf_hub self-downgrade). Shim: `_compat/sitecustomize.py` (numpy-alias + xformers→SDPA Blackwell fix).
- **`/home/sov2/projects/anny`** — Anny parametric body (Apache-2.0). Use **default or `soma` topology ONLY** (the `smplx` topology is NC — D56 trap). Native `mixamo`/`game_engine` rigs.
- **Avatar assets** (feed-forward, muted — expected): `/tmp/lhmpp_test.ply`, `/tmp/lhmpp_avatar2_upright.ply` (160k gaussians, standard 3DGS PLY: xyz/opacity/scale/rot/SH-deg0).
- **`~/4dgs-splat-test`** — GitHub Pages phone-test repo (mkkellogg WebGL viewer, auto-orbit + FPS HUD). Avatar staged as `assets/lhmpp_avatar_160k.ply`, viewer defaults to it. **User must `git push` (no creds in headless env).** Live: https://yousef-yy4u.github.io/4dgs-splat-test/
- **`research/salvage/`** — SV4D Blackwell attention patch (reusable).
- Prior clean-stack tooling still present: `generation/bind_splat.py`, `split_by_bone.py`, `poc_splat_smooth.html` (skinned-splat rig+LBS-deform-in-shader PoC — the on-device animation prototype), `TRELLIS.2`, `UniRig`, `gsplat`.

## 6. ENVIRONMENT GOTCHAS
- **Shared box.** shnri's `qwen`/ollama (~20–26GB VRAM) + a birthd-asr service run on the single 5090. **Do NOT evict.** GPU windows open when qwen idle-unloads (watch `nvidia-smi`; LHM++ inference needs ~20GB peak). ollama is a persistent server (not a finite batch), so "free" = idle gaps.
- **Blackwell (sm_120):** compile ALL CUDA exts with `TORCH_CUDA_ARCH_LIST="9.0+PTX"` (NOT 12.0 — CUDA-12.5 nvcc can't target compute_120), `CUDA_HOME=/usr/local/cuda-12.5`. spconv must be **`spconv-cu126`** (cu120's cumm SIGFPEs on sm_120).
- **DISK: 99% full (7.9GB free).** MUST clean before downloading Anny-One (tens of GB). Fat: LHM++ priors/weights (~12GB), env caches. Other users'/projects' envs (gof 15G, spike_lam 10G) and MM2 (8.4G, user's clothing work — KEEP), LAM (11G, KEEP) — do NOT delete without asking. `conda clean -a`, `pip cache purge`, `/tmp/pip-*` are safe reclaims.
- **HF token** in `generation/.env` (`HF_TOKEN`, user yyousef4u).
- **No GitHub push creds** in this headless env — user pushes `~/4dgs-splat-test` manually.

## 7. NEXT STEPS (the re-focus)
1. **Free disk** (safe reclaims + ask about big envs).
2. **Download Anny-One** (verify its download license).
3. **Build the Anny → pose → clean-motion → multi-camera render pipeline** (our 4D dataset generator). Clean motion source only (not AMASS).
4. **Decide the target architecture** for standalone-quality gaussians (D55 feed-forward levers vs per-scene-optimized rigged splat). This determines what supervision the dataset must emit (multi-view render loss; deformable/rigged target).
5. **Wire training** (rent multi-GPU per D53; the 5090 is prototyping only).

## 8. OPEN QUESTIONS / DON'T FORGET
- Anny-One's exact download license (verify before commercial reliance).
- LHM++/DGS-LRM own weight licenses (LHM++ weights = CC-BY-NC confirmed; treat as eval-only).
- The diff_gaussian_rasterization in the lhmpp env is Inria **NC** (eval only) — clean build renders via **gsplat**.
- MM2 (clothing/drape) + LAM (headless human + FLAME lipsync) are existing user projects that feed the D57 compositional layers (clothing / face) — revisit when building attribute control.
- Runtime playback: D50 proved 600k static splats @ 45–60fps on iPhone; the **animated-deformation** (Tier-2) on-device test is still the real gate (poc_splat_smooth.html is the tool).
