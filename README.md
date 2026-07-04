# 4dgs — project archive (planning-first)

Private archive of the **4DGS project**: planning, decisions, research, and findings — so it's
accessible from anywhere. Code is included but **the planning docs are the point.**

## Two products (both kept)
- **Marker-Anchored AR Asset Platform** (B2B no-code AR publishing) → **[PROJECT.md](PROJECT.md)** (SSOT).
- **AR Productivity Glasses** (wearer-facing AR cockpit) → **[GLASSES.md](GLASSES.md)** (SSOT).

The **active technical workstream** right now is **4DGS humanoid avatar generation** (train our own
clean model → on-device photorealistic animated Gaussian-splat avatars). Its state is in
[SESSION_HANDOFF.md](SESSION_HANDOFF.md).

## Read in this order
1. **[SESSION_HANDOFF.md](SESSION_HANDOFF.md)** — CURRENT state, the goal, what's built vs. not, next steps. Start here.
2. **[PROJECT.md](PROJECT.md)** — the single source of truth. Product spec + the full **Decision Log (D1–D60)** — every idea, why it evolved, what was rejected. This is the core planning artifact.
3. **[GLASSES.md](GLASSES.md)** — the glasses product SSOT (separate product, shared foundations).
4. **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** — build plan for the platform MVP.
5. **[docs/planning-memory/](docs/planning-memory/)** — distilled cross-session findings (the "memory"): licensing landmines, rigged-gaussian-splatting reality, generation-pipeline reality check, humanoid-4dgs status, asset-library architecture, etc.
6. **[research/](research/)** — deep-research reports: market & GTM, tech-stack/architecture, 8th Wall dive, generation texture/rigging.
7. **[docs/BLACKWELL_BUILD.md](docs/BLACKWELL_BUILD.md)** — reproducible recipe for running the LHM++ humanoid stack on an RTX 5090 (sm_120).

## The current goal in one paragraph
Train **our own clean-license 4DGS model** producing **animated Gaussian-splat avatars** that the
**phone renders on-device** (only motion/bone data streamed — no video streaming, no runtime neural
renderer), **photorealistic standalone**. Humanoids first, on a commercially-clean stack (**Anny**
parametric body + **Anny-One** synthetic dataset + **gsplat** rasterizer). The dataset-creation
pipeline is the next thing to build (see SESSION_HANDOFF §7). See Decision Log **D53–D60** for how we
got here (incl. the LHM++ detour and the neural-renderer finding that shaped the model choice).

## Repo layout
- `PROJECT.md`, `GLASSES.md`, `SESSION_HANDOFF.md`, `IMPLEMENTATION_PLAN.md`, `CLAUDE.md` — planning/spec.
- `docs/` — pulled-in findings + build recipe.
- `research/` — deep-research reports (+ `research/salvage/` = reusable SV4D Blackwell attention patch).
- `platform/` — the B2B platform web app (Next.js). Generated model blobs are gitignored.
- `generation/` — the generation/authoring pipeline (image→3D, rig, splat PoCs). Large outputs gitignored.
- `benchmark/` — the on-device splat render benchmark (WebGL) + test assets.

> Generated model files (`.glb/.usdz/.ply/.pth/.safetensors`, `platform/storage/`, `generation/out*`,
> `node_modules/`) are **gitignored** — this archive is for planning + source, not multi-GB binaries.
