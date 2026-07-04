---
name: generation-pipeline-reality-check
description: "Reality check on the image→rigged-splat pipeline — GaussianAvatars is per-subject optimization, not a sub-second baker"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7fa889b7-cdf5-419f-9a65-e527b3ffcb4b
---

The proposed pipeline (single image → 3D mesh → auto-rig → bake splats → stream bone angles) is architecturally correct, but the claimed **1.5–2.5s total is fantasy**. Corrected understanding of the three cited papers:

- **GaussianAvatars** (arxiv 2312.02069) — splats-bound-to-FLAME-mesh-triangles. NOT a feed-forward baker: requires **~600k iterations of per-subject training on 16-cam video**, i.e. minutes–hours per asset. The binding *concept* is reusable; the training cost is not magic-able away. This was the biggest misconception.
- **Make-It-Animatable** (arxiv 2411.18197) — genuinely feed-forward auto-rig (~0.5s) BUT trained on **humanoids**. Arbitrary topology (quadruped/chair/mechanism) is unsolved feed-forward.
- **A³-GS** (OpenReview EEA5IwSUXU) — animates articulated objects via mesh–Gaussian hybrid, but from **multi-view images via per-object optimization**, not feed-forward.

Realistic envelope: feed-forward + lower-quality + humanoid-biased (~15–40s), OR high-quality per-asset optimization (minutes+). Not 2s for "any 3D thing."

**What genuinely works:** streaming joint angles (not geometry) at runtime + local LBS on device — trivial bandwidth, correct design. **Rendering caveat:** "millions of splats" stereo on a phone SoC is at the edge; budget ~100k–500k splats with LOD, not millions. Relightable Gaussians make generation heavier. See [[stealth-agent-glasses-product]], [[rigged-gaussian-splatting]].
