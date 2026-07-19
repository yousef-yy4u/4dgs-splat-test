# Avatar Architecture — how the puppet is composed & controlled

> **One-page spec** (2026-07-13, D62/D63). The avatar is a **video-game puppet whose skin is photoreal Gaussian splats.** It lives **on the phone** (pre-built). The server/LLM sends only small **"puppet-string" packets** telling it how to move, express, and what to wear. This is the §2/D50 motion-data-only streaming — and it's *why* we require standalone + on-device gaussians (you can stream puppet-strings cheaply; you can't stream a live-rendered photoreal human cheaply).

## 1. Anatomy — what the puppet is made of
| Part | What it is | Source (clean) |
|---|---|---|
| **Base: body** | photoreal gaussian skin on a **skeleton** | Anny (Apache) |
| **Base: face identity** | animatable gaussian head | LAM (Apache) |
| **Rig** | body = skeleton bones; face = **expression sliders** (ARKit blendshapes) | SOMA skeleton / ARKit convention |
| **Skin** | gaussians attached to the rig; deform via **LBS** (bones) + **blendshapes** (face) | gsplat (Apache) |
| **Layers on top** | hair, clothing, accessories — **separate attachable gaussian assets** | MM2 clothing; hair module (build/source clean) |

The **base (body shape + face identity) is FIXED per avatar** — it's "who the avatar is." Everything else is a layer.

## 2. Control signals — the "data packets"
Per frame the server streams only:
- **Body:** skeleton **joint angles** (from a motion library / GEM-X video→motion / Kimodo text→motion)
- **Face:** **ARKit blendshape coefficients** (+ audio → **Audio2Face-3D** for lip-sync)
- **Composition (once, not per frame):** which base, which hair/clothing parts, what colors

Tiny — a few hundred numbers per frame. The phone does the rendering. The **LLM is the puppeteer**: it decides "walk over, smile, say this line, wearing the red jacket" → emits the control + composition packets.

**Concrete runtime stack (D68 — this is the mainstream "two-clock" pattern of NVIDIA ACE / Inworld / Convai):**
- **Director clock = the LLM, per TURN** (not per frame): streams reply text + one emotion label + sparse gesture/clip-ID **tags**. Never joint angles/blendshapes.
- **Animator clock = on-device @30–60fps:** the **FACE is driven by the AUDIO** (audio→ARKit via **LAM_Audio2Expression**, Apache/CPU; or Audio2Face-3D) — it stays lip-synced even while the LLM is slow; the **BODY is driven by the tags** → a curated clean-mocap library (D67) blended by a state machine, kept non-robotic by **inertialization** (transitions) + **motion matching** (locomotion) + always-on additive breathing/gaze.
- **The LLM never emits joint angles** — no shipping system does. Generative body motion (EMAGE/DiffSHEG/Kimodo) is authoring-time only; Kimodo-SOMA-SEED is the one commercially-clean generator.
- **Latency:** win response-start with **endpointing** (smart-turn VAD, the #1 lever) + warm connection; use **speculative decoding / DeepSeek-MTP** on the cloud LLM to keep TTS fed on long turns (language layer only — not motion).
- **Bandwidth:** 52 blendshapes + 163 joint angles/frame ≈ **~25–30 KB/s** — 3 orders below video, the quantitative case for on-device standalone gaussians. See [PROJECT.md](../PROJECT.md) D68.

## 3. Composition & customization — TWO kinds (this is the key idea)
Each part is a **labeled/separate group of gaussians** — which you get for free from the layered design (hair is its own asset, iris is its own group, etc.). That labeling is what makes both operations below possible.

- **RECOLOR — instant, on-device, unlimited.** Color is a per-gaussian attribute; changing it is just math on that part's gaussians. → **hair color, eye color, skin tone, clothing color.** Real-time, no re-generation.
- **SWAP — a parts library ("wardrobe").** Attach a *different pre-made part* rigged to the same body. → **hairstyle, garment, accessories.** You build a library of hair/garment assets; the user picks one. (Generating a *brand-new arbitrary* hairstyle from a prompt is a separate, harder generative problem — not needed for a curated library.)

**Why fix the base:** because body shape + face stay constant, hair and clothing are **fitted once** to that body and never need re-fitting. If body shape varied, every garment/hairstyle would need auto-refitting (hard). Fixing the base is the simplification that makes customization tractable.

## 4. Who does what
- **Offline (authoring):** optimize each base avatar → photoreal standalone gaussians; build the parts library (hair/garments); fit layers to the base.
- **Runtime (phone):** assemble base + chosen parts + colors; apply motion + expression; render on-device.
- **LLM (puppeteer):** chooses actions + composition → control/composition packets.

## 5. Bonus — this also shrinks the dataset
Because attributes are disentangled layers, you do **not** train "every avatar × every outfit × every hairstyle." You train **bodies + faces**, and build **hair/clothing as a separate library.** Disentangling kills the combinatorial explosion — the whole reason layers beat one baked avatar (D57).

## 6. What's easy vs hard (honest)
- **Easy:** recolor anything; body motion (skeleton + LBS); on-device playback of standalone gaussians.
- **Medium:** hairstyle/garment **swap** (needs a parts library); face **lip-sync** (audio→ARKit via Audio2Face/LAM_Audio2Expression).
- **Hard:** clothing that **drapes/moves** with the body under motion (the MM2 work); **hair as gaussians** (fine, translucent, moving); **seams** (hairline, collar, neck) blending within the phone gaussian budget; **generating new arbitrary parts** from scratch (separate generative track).

## 7. Clean-license mapping
Body **Anny** (Apache) · Face **LAM** (Apache) · lip-sync **Audio2Face-3D** (NVIDIA Open Model) / **LAM_Audio2Expression** (Apache) · motion **GEM-X/Kimodo/SOMA-X** (Apache + NVIDIA Open Model) · clothing **MM2** · expression vocabulary **ARKit** (unencumbered) · render **gsplat** (Apache). Recolor is math on gaussian attributes (clean). See [licensing-landmines](planning-memory/licensing-landmines.md), [PROJECT.md](../PROJECT.md) D57/D60/D61/D62/D63.

## 8. Where photorealism comes from + what it costs (D65/D66)
**The one rule: `output realism = training-image realism`.** The per-gaussian color (degree-3 SH) is fit by a photometric loss = a *reproduction* mechanism, so the avatar looks exactly as photoreal as the images it's optimized against. Two ways to get photoreal images:
- **(b) SYNTHETIC render — the adopted path (D66):** render the base body + each garment/hairstyle **photoreal** (Omniverse/Cycles/MetaHuman-class: skin scans, strand hair, path-traced light, cloth sim), **multi-view + multi-pose**, then optimize gaussians on those renders. Realism ceiling = *asset quality*. Fully automated, privacy-clean. **Appearance + motion come together in the same render — NOT separate.**
- **(a) REAL CAPTURE — the max-realism alternative:** multi-view photos/video of a real person → real skin baked into the gaussians. Higher ceiling, but needs a capture rig + privacy handling.
- **Do NOT render gray for this path.** Gray (pyrender) was a cost shortcut *specific to the real-capture branch* (appearance sourced elsewhere → render motion cheap). On the synthetic-photoreal path we render photoreal-and-moving.
- **Layers keep it affordable (D63):** render a handful of base bodies + a wardrobe of parts *each once* (NOT body×outfit×hair combos); swap needs each part as its own gaussian group → optimize parts separately, compose + recolor at runtime.
- **Not one feed-forward model:** each avatar/part is built by its own **per-subject optimization** run → library (feed-forward → muted gaussians needing a runtime neural renderer, D60).
- **Cost:** per-subject optimization = ONE 24GB GPU (RTX 4090 ~$0.30/hr spot); photoreal-render + fit ≈ **~$7–30/subject** (Cycles render dominates); a curated hero+wardrobe library = a few hundred to ~$1k. No A100/H100 unless building the dropped feed-forward model.
- **Anny-One (static Cycles renders)** = geometry/rig/coverage supervision + pretraining; **Audio2Face/LAM/ElevenLabs = face/voice DRIVERS**, not appearance sources.

See [PROJECT.md](../PROJECT.md) D65/D66, [[generation-texture-method]], [[asset-library-architecture]].
