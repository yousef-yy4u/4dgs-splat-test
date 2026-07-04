# Generation: texture & rigging — how the commercial tools do it, and our clean path

> Deep-research report (2026-06-28). Triggered by a critical product problem: our self-hosted
> TRELLIS+UniRig pipeline produces **muddy/dark textures** (a colorful dwarf / a head bake out
> near-black). Question: how do Meshy / Tripo / Rodin / Hunyuan3D actually texture & rig, and how
> do we replicate it in a **commercially-license-clean** stack? Method: 5-angle fan-out, 23 sources
> fetched, 25 claims adversarially verified (24 confirmed, 1 killed). Sources cited inline.

## TL;DR
Our texture stage uses the **wrong method**. We render TRELLIS's Gaussian splats from many views and
bake that into a texture — a soft, view-averaged blur by construction. The commercial tools do
**mesh-conditioned multi-view PBR diffusion** instead, and that gap can't be closed by tuning our
bake. Our **rigging** (UniRig, MIT) is already the right modern approach. **Recommendation:** since
generation is our authoring backend, *not* our moat, the fastest path to the quality bar is to
**wrap a commercial generation API (Meshy or Tripo) behind our existing async job interface**, while
keeping self-hosted TRELLIS+UniRig as a fallback. The only unambiguously MIT/Apache *self-hosted*
texture upgrade is **TRELLIS.2** (native-3D PBR), but its quality is so far only an authors' claim.

---

## 1. How they get bright, crisp textures (the texture method)

**Confirmed (3-0): SOTA texture = mesh-conditioned MULTIVIEW DIFFUSION → unwrap/back-project to UV — explicitly NOT baking a single shaded render or a Gaussian-splat render.**
- A diffusion model, **conditioned on the generated mesh's geometry** (rendered normal + position/coordinate maps), synthesizes view-consistent multi-view images, which are then **unwrapped/back-projected into the UV texture**. This is the dominant class across Hunyuan3D-Paint, SyncMVD, MVPaint, PBR3DGen, MaterialMVP, Make-A-Texture — and by technique-membership, Meshy/Tripo.
- Sources: Hunyuan3D 2.0/2.1 ([2501.12202](https://arxiv.org/pdf/2501.12202), [2506.15442](https://arxiv.org/pdf/2506.15442)), SyncMVD ([2311.12891](https://arxiv.org/pdf/2311.12891)), MVPaint ([2411.02336](https://arxiv.org/html/2411.02336v1)), MaterialMVP ([2503.10289](https://arxiv.org/pdf/2503.10289)), PBR3DGen ([2503.11368](https://arxiv.org/html/2503.11368)), [Make-A-Texture (WACV 2025)](https://openaccess.thecvf.com/content/WACV2025/papers/Gorelik_Make-A-Texture_Fast_Shape-Aware_3D_Texture_Generation_in_3_Seconds_WACV_2025_paper.pdf).

**Confirmed (3-0): cross-view consistency (what makes it crisp not blurry) = reference attention + multi-view attention/sync + 3D-aware RoPE.** Reference attention pulls fidelity from the input image; multi-view attention / latent-or-image-domain synchronization keeps views agreeing. SyncMVD blends latents in UV space each denoising step; MVPaint syncs in the *decoded image* domain weighted by cos(view-dir, normal) because 32×32 latents map to UV poorly.

**Confirmed (3-0): the fix for the muddy/dark look = TRUE DECOMPOSED PBR + ILLUMINATION-INVARIANT training.** They output separate **albedo / metallic / roughness** (Disney Principled BRDF), trained so albedo is **delit** (no baked-in shadows/highlights) and relightable — not one shaded color texture. Hunyuan3D 2.1 uses a dual-branch UNet + illumination-invariant loss across the same object under different lighting; MaterialMVP does dual-channel + consistency-regularized training; PBR3DGen uses a VLM (GPT-4V) to infer metalness unobservable in RGB.

**Confirmed (3-0): finishing passes matter** — per-view single-image **super-resolution**, **UV inpainting** of unobserved patches (KNN/vertex color propagation), and **seam-smoothing**. Standard in Hunyuan3D-Paint and MVPaint stage 3.

**Confirmed (3-0): emerging alternative = NATIVE 3D PBR generation.** **TRELLIS.2** (Microsoft, MIT, [2512.14692](https://arxiv.org/html/2512.14692v1)) predicts PBR material latents (base color, metallic, roughness, opacity) **directly in its sparse-voxel 3D latent domain** jointly with geometry — no multi-view render/bake/align step, which it argues removes exactly the appearance inconsistencies our gsplat+bake suffers. ⚠️ Single Dec-2025 preprint; quality is the authors' own un-benchmarked assertion.

> **Why ours is dark/muddy (confirmed by contrast):** a Gaussian-splat render is soft and view-averaged; baking it gives a blurry, shadow-contaminated single color texture with no PBR decomposition. It is the failure mode these papers explicitly designed against.

## 2. Rigging & animation

**Confirmed (3-0): UniRig (what we already self-host, MIT) IS the modern learned auto-rigger** — not Mixamo humanoid-template fitting. A GPT-like autoregressive transformer with **Skeleton Tree Tokenization** predicts topologically valid skeletons across **humans, animals, AND objects**; **Bone-Point Cross Attention** predicts skin weights ([UniRig repo](https://github.com/VAST-AI-Research/UniRig), SIGGRAPH 2025 [2504.12451](https://arxiv.org/html/2504.12451v1)). So our rig stage is already "how they do it."
- Caveats: weights trained on Articulation-XL2.0 (derived from Objaverse-XL, ODC-By + per-object licenses) — a training-data *provenance* note, not a software-license problem (LICENSE is verbatim MIT). Per-creature rig *quality* on unusual topologies varies.
- Commercial UX (Meshy rigging API, Tripo, Anything World): one-click humanoid rig + a library of preset idle/walk/run animations — same shape as our motion-preset picker, just more motions.

## 3. Build vs buy

### Self-host (license-clean options)
- **Geometry + rig core: KEEP.** TRELLIS (MIT) + UniRig (MIT) are both clean for resale.
- **Texture: the weak link.** The technically-best open PBR-texture models — **Hunyuan3D-2 / 2.1 / Hunyuan3D-Paint** and **MaterialMVP** — ship under a **non-OSI Tencent "Community License"**: commercial use barred above **1M MAU** without a separate Tencent grant, and the license **"DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"** ([2.1 LICENSE](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE), [2.0 LICENSE](https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE)). **A real landmine for a global B2B SaaS reselling generated assets — treat as do-not-ship.**
- **Only unambiguously MIT/Apache texture upgrade today = TRELLIS.2** (native-3D PBR). Best clean self-host path, but unproven quality and need to confirm weights/availability + RTX 5090 latency.

### Buy (wrap a commercial API) — pricing/ToS *(lower-confidence: blog/aggregator + vendor help-docs, mid-2026; verify before shipping)*
| Tool | ~per-asset | Commercial/resale rights | Notes |
|---|---|---|---|
| **Stability SF3D** | ~$0.07–0.10 | — | cheapest; weaker quality |
| **TRELLIS.2 (via 3D AI Studio)** | ~$0.08–0.15 | — | hosted TRELLIS.2 |
| **Tripo** | ~$0.10–0.25 (~$0.21 at 3k credits/$15.90) | paid tiers grant commercial rights | strong quality + rigging |
| **Meshy** | ~$0.10–0.40 (Pro: ~20 credits = ~$0.40/textured model) | **Premium = full rights, sell w/ NO attribution**; **Free = CC BY 4.0 (attribution req'd)** | rigging+animation API; PBR |
| **Rodin / Hyper3D** | ~$0.50–1.50+ ($120/mo min) | **all tiers (incl. free) grant full commercial rights** | priciest; high quality |

- **Input-copyright is the user's responsibility** across all vendors (don't feed copyrighted images) — already in our governance model.
- Generated-asset copyright is **contractually licensed** by the vendor, not inherent IP — fine for our use, but it means we depend on their ToS staying favorable.

## Recommended workflow (synthesis — not a verified claim)
1. **Wrap a commercial generation API (Meshy or Tripo) behind our existing async job interface** (`submitGeneration → poll → finalize`). The platform already doesn't care where the GLB comes from; this is a contained worker-backend swap. It instantly fixes texture quality, is snappy, does rigging+animation too, and outputs PBR GLB + USDZ — the formats we already serve. Use a **PAID tier** (Meshy Premium / Tripo paid) for clean resale rights; never the CC-BY free tier.
2. **Keep self-hosted TRELLIS+UniRig as a fallback / cost lever** for later scale (it's free per-asset once the GPU is paid for).
3. If/when we want to return to self-host for quality, **swap the gsplat-bake for TRELLIS.2 native-PBR (MIT)** — the only clean-license texture upgrade — after benchmarking its quality + latency on the 5090.
4. Regardless of generator: always run **super-resolution + UV inpainting + seam-smoothing** finishing passes (cheap, standard).
5. **Do NOT ship Hunyuan3D-2/2.1/Paint or MaterialMVP** in the product — Tencent Community License (1M-MAU cap, void in EU/UK/SK).

## Open questions / gaps
- TRELLIS.2 real quality vs Meshy/Hunyuan in independent benchmarks (only authors' claim so far) + 5090 latency.
- Exact current Meshy/Tripo/Rodin per-asset pricing + reselling ToS (verify against live pricing pages before committing).
- TRELLIS v1 / TripoSG / TripoSR specific texture limits + license terms (TripoSG license unconfirmed here).
