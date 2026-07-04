---
name: humanoid-4dgs-status
description: Current 4DGS-humanoid track status + the goal + the re-focus on building our own dataset (read SESSION_HANDOFF.md)
metadata: 
  node_type: memory
  type: project
  originSessionId: 314a1217-e88e-4382-a153-4ec4f4743bd4
---

**Goal:** train OUR OWN clean 4DGS model → animated Gaussian-splat avatars that the **phone renders ON-DEVICE** (no video streaming; only motion/bone data streamed — §2/D50 arch), **photorealistic STANDALONE** (raw gaussians look good with a plain rasterizer, NO runtime neural renderer). Humanoids first, clean stack = Anny + Anny-One + gsplat.

**Re-focus (D60, 2026-07-04):** we detoured for hours into LHM++ *inference* (Phase-0 phone-playback de-risk) and **never built the actual core = our own training DATASET.** The dataset-creation setup **does not exist yet** (Anny model cloned as a building block, but Anny-One NOT downloaded, zero dataset-gen scripts).

**Key finding:** LHM++ = feed-forward + a **neural renderer** → its exportable *raw* splat is muted/soft; the quality lives in a per-frame neural net (= GPU-per-viewer streaming, not on-device). So **don't retrain LHM++'s arch as-is** — target a standalone-quality arch ([[generation-pipeline-reality-check]] / D55 levers) or per-scene-optimized rigged splat. LHM++ build still valuable (proved the clean Blackwell stack runs; see BLACKWELL_BUILD.md).

**Next:** free disk (99% full) → download Anny-One (~800k synthetic multi-view humans, clean, static poses) → build the **Anny→pose→clean-motion→multi-cam render pipeline** (our 4D generator; clean motion NOT AMASS) → pick arch → rent GPUs to train.

**Read `4dgs/SESSION_HANDOFF.md` first** for concrete state/paths/commands, then PROJECT.md Decision Log D53–D60. Env: conda `lhmpp` (Blackwell). See [[licensing-landmines]] (Anny topology trap, LHM++ NC weights, clean stack), [[rigged-gaussian-splatting]], [[asset-library-architecture]].
