---
name: animax-reimplementation-findings
description: "AnimaX architecture, output type, and commercial-licensing findings for reimplementation"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ccb13a99-32a2-4d2b-880e-5c289b6f5a80
---

AnimaX (SIGGRAPH Asia 2025, arXiv 2506.19851) — the chosen method for [[project-goal-4dgs]]. Code/weights NOT released (repo github.com/anima-x/anima-x is a placeholder; LICENSE is Apache-2.0 but no code yet), so it must be reimplemented.

**What AnimaX outputs:** an **animated/rigged MESH (skeletal animation)**, NOT a Gaussian splat and NOT a video. Input = static 3D mesh + text motion prompt. It generates multi-view RGB video + multi-view pose maps as *intermediate scaffolding*, then does 2D joint localization → triangulation → inverse kinematics → joint angles applied to animate the input mesh. Output exports cleanly to glTF/GLB → renders trivially/cheaply in Three.js/Babylon/PlayCanvas on phones and edge devices; animation streams as KB/frame (just joint angles). AnimaX is the ANIMATION layer only — visual quality = quality of the input mesh.

**Base model:** Wan2.1 1.3B text-to-video (Apache-2.0, NO commercial restrictions, runs in ~8GB VRAM) — commercially clean and cheap. Architecture: concat RGB+pose tokens over time → joint 3D self-attention + modality embedding + shared RoPE positional encoding + Plücker-ray camera conditioning + multi-view attention. Two-stage training: (1) LoRA fine-tune single-view joint video-pose diffusion, (2) freeze, train camera embeddings + multi-view attention. ~161,023 clips.

**Commercial-licensing reality (gate = data, not code):**
- AnimaX's own training data = Objaverse + **Mixamo** + **VRoid**. AVOID Mixamo (Adobe ML-training/redistribution terms) and VRoid (mixed per-model terms) for a commercial model.
- MV-Video dataset (Animate3D's data, HF: yanqinJiang/MV-Video) = ODC-BY database; underlying assets ~50k CC-BY, ~100 CC0 (commercial OK w/ attribution), ~400 CC-BY-SA (share-alike risk), ~1,500 CC-BY-NC + ~400 CC-BY-NC-SA (NON-commercial — filter out). Per-object license in uid_info_dict.json. BUT MV-Video has NO pose/skeleton data (Animate3D is skeleton-free), so it only covers AnimaX's RGB half — pose maps must be re-rendered from rigged source meshes.
- Recommended clean path: reimplement AnimaX arch on Wan2.1 + self-render a dataset (RGB + pose) from CC-BY/CC0 rigged assets. Don't ship anyone's released weights (provenance risk: AnimateDiff→WebVid, MVDream→SD2.1, MV-Video→mixed/NC).

**Animate3D (NeurIPS 2024, github.com/yanqinJiang/Animate3D):** code IS released under Apache-2.0 (code only — weights unlicensed, risky provenance). Skeleton-FREE, neural-deformation + 4D-SDS, slower (per-asset optimization), lower motion quality than AnimaX. Usable as Apache reference code, not for its weights.
