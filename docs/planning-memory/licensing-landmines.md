---
name: licensing-landmines
description: Commercial-use licensing landmines in the 4dgs model/dataset stack + the verified clean stack
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7fa889b7-cdf5-419f-9a65-e527b3ffcb4b
---

Verified commercial-use licensing audit for the 4dgs splat pipeline (full table in PROJECT.md §4a). The project is COMMERCIAL, so non-commercial licenses are blockers.

**🔴 DO-NOT-SHIP landmines:**
- **Original 3D Gaussian Splatting (Inria/GraphDeco) + `diff-gaussian-rasterization` = NON-COMMERCIAL.** The single most important one for a splat product — never ship this code or derivatives. Use permissive renderers (mkkellogg, PlayCanvas — MIT) + clean-room optimization.
- **SMPL / FLAME (non-2023) = non-commercial AND taint models trained on them** (infects SMPL-X, AMASS, GaussianAvatars, most human-avatar rigs). Path: Meshcapade license, or use **FLAME 2023 Open (CC-BY-4.0)**.
- **ShapeNet = non-commercial, no path** → exclude; seed from Objaverse filtered to CC0/CC-BY only.
- **Hunyuan3D-2** = no rights in EU/UK/South Korea + 1M-MAU cap (Tencent license).
- **InstantMesh** = blocked by CC-BY-NC Zero123++ stage despite Apache code.
- **RigAnything** = Adobe non-commercial → use UniRig instead.
- **SOG research repo (Fraunhofer)** = inherits Inria NC → use PlayCanvas sogs/PLAS.
- **DINOv2 pre-Aug-2023 weights** were CC-BY-NC (relicensed Apache later) → pin current weights.
- **L4GM (NVIDIA 4D recon) WEIGHTS = CC-BY-NC-SA-4.0 ("research only")** + trained on non-commercial Objaverse-4D → weights unusable commercially. Code is Apache-2.0, so the ARCHITECTURE is copyable but must be retrained clean (verified via deep-research 2026-07-01, D55). Same "copy the model not the weights" story as clean-room 3DGS.
- **SMPL/SMPL-X/STAR = free for ACADEMIC only, commercial via Meshcapade sublicense; MANO/AMASS non-commercial** — the whole standard humanoid-parametric toolkit is a landmine.

**🟢 CLEAN STACK:** TRELLIS/TripoSR/LGM (MIT gen) · UniRig (MIT rig) · Wan2.1 (Apache motion; AnimaX unreleased) · mkkellogg+PlayCanvas (MIT render) · **gsplat (Apache) = the clean differentiable rasterizer** (replaces Inria NC) · Draco/meshopt/KTX2/sogs/splat-transform/PLAS (compress) · CLIP+DINOv2-current (retrieval) · Objaverse CC0/CC-BY (seed) · FLAME-2023-Open (humanoid face).
**Clean parametric HUMAN body model = Anny (NAVER Labs Europe, `naver/anny`, Apache-2.0)** — commercially-usable SMPL/SMPL-X replacement; scan-free (built from MakeHuman/MPFB2 CC0 + WHO anthropometric calibration, so it escapes the Max-Planck NC scan chain). Verified 2026-07-01 (D55/D56, arXiv 2511.03589).
**⚠️ Anny TOPOLOGY TRAP (D56, a D41-class hidden-NC landmine):** headline license is clean BUT the **`smplx` interoperability topology is download-for-NON-COMMERCIAL-use-only** — its convenience path (dropping Anny into existing SMPL-X benchmark codebases) silently re-introduces NC. **Ship rule: use only Anny's DEFAULT (13,380-vert/163-bone) or `soma` topology (Apache-2.0, from NVlabs SOMA-X); NEVER enable the `smplx` flag in any code path touching a shippable artifact** (training-data gen, tracking, or released model). Verify per-download notices + SOMA-X's own NVlabs terms at integration.
**Anny-One dataset (D57, web-verified 2026-07-01):** ~800k PHOTOREALISTIC SYNTHETIC humans (full-body poses + hands + faces, multi-env) w/ 2D/3D joints, pose params, seg masks, camera intrinsics/extrinsics, hand/face keypoints — positioned privacy/license-unconstrained for COMMERCIAL use (HMR trained on it matches scan-based models). → the clean humanoid TRAINING SET largely exists (skip building it). Verify: (a) the dataset's OWN license notice at download (may differ from Anny code's Apache); (b) it's HMR/STATIC-pose — for 4D you still generate MOTION sequences by driving Anny, with a CLEAN motion source (self-authored/procedural/Mixamo-audited, NOT AMASS=NC).
**LHM / LHM++ (`aigc3d/LHM`, `aigc3d/LHM-plusplus`, Alibaba Tongyi, ICCV 2025) — use LHM++ (newer).** LHM++ = 700M, input res 1024, 1/4/8/16-view + video, **160,000 gaussians**, ~8GB VRAM, 0.79s, exports standard `.ply` (`scripts/inference/to_gs_ply.py`). **LICENSE (two-layer trap, verified in cloned repo 2026-07-01 D58):** (a) **code = Apache-2.0**; (b) **weights = CC-BY-NC-4.0 (`LICENSE_WEIGHT`, NON-COMMERCIAL) → reference/eval only, MUST retrain clean**; (c) **`LICENSE_NVIDIA` = NVIDIA EG3D Source Code License (NON-COMMERCIAL) → an EG3D-derived CODE module is NC at the code level, not just weights → clean build must AUDIT+REPLACE it, not only retrain** (also check the `arcface` face-ID dep). **LHM++ dep landmine (D59):** its install pulls `diff-gaussian-rasterization` (Inria, NON-COMMERCIAL, D41 trap) + `simple-knn` alongside `gsplat==1.4.0` (Apache). Clean build must render via gsplat only; fine for Phase-0 eval. Also pins torch 2.3/cu121 (won't run on Blackwell sm_120 → use trellis2's torch 2.11/cu128 combo).
**GIFT: LHM++ ships an `SMPLX-FREE` variant** (`LHMPP-700M-SMPLX-FREE`; default `PixelShuffle` is also SMPLX-free) → the SMPL-X architectural dependency may already be removed → **start the clean retrain from the SMPLX-FREE variant** (swap remaining SMPL-X→Anny default/SOMA, train on Anny-One). Anny is fully differentiable → clean end-to-end single-photo avatar generator.
**Privacy (D57):** Anny+Anny-One sever the biometric↔mesh link (synthetic + WHO averages, zero real scans) so the GDPR sensitive-biometric problem doesn't hit the FOUNDATION. Residual app-layer rules only: (1) don't hoard user uploads (process in-memory, delete; no silent retrain w/o consent); (2) train on synthetic (Anny-One) not scraped real people; (3) no re-ID/surveillance use. See [[rigged-gaussian-splatting]].

Engineering summary, not legal advice — counsel to confirm Inria + Meshcapade + Tencent terms before ship. See [[asset-library-architecture]], [[animax-reimplementation-findings]].
