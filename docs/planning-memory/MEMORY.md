# Memory Index

- [Humanoid 4DGS status (CURRENT)](humanoid-4dgs-status.md) — goal + re-focus: build our OWN training dataset (not started); LHM++ = detour; read SESSION_HANDOFF.md
- [Project goal: animated 3D in browser](project-goal-4dgs.md) — animate any 3D thing, render cheaply in browser/glasses; mesh path over splats
- [AnimaX reimplementation findings](animax-reimplementation-findings.md) — AnimaX outputs animated meshes; Wan2.1 Apache base; commercial-licensing constraints
- [Rigged Gaussian splatting](rigged-gaussian-splatting.md) — skeleton-driven splats (SC-GS etc.); feasible but heavier than mesh; texture misconception corrected
- [Stealth agent glasses product](stealth-agent-glasses-product.md) — real product is stealth AI-agent glasses; two separable tracks (agent vs splat-gen); build agent first
- [Generation pipeline reality check](generation-pipeline-reality-check.md) — image→rigged-splat 1.5–2.5s is fantasy; GaussianAvatars is per-subject optimization, not a baker
- [Asset library architecture](asset-library-architecture.md) — generation is offline; runtime is retrieval; static vs animatable split; data-moat
- [Project SSOT log](project-ssot-log.md) — PROJECT.md is the single source of truth; keep it updated every turn a decision changes
- [Licensing landmines](licensing-landmines.md) — Inria 3DGS/SMPL/FLAME/ShapeNet are non-commercial; verified clean commercial stack
- [Generation texture method](generation-texture-method.md) — our gsplat→bake textures are muddy/dark (wrong method); commercial tools use multi-view PBR diffusion; recommend wrapping Meshy/Tripo API (D43)
- [No Claude commit credit](no-claude-commit-credit.md) — never add Co-Authored-By:Claude; git identity = yousef-yy4u GitHub noreply
