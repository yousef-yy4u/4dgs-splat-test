# PROJECT.md — Single Source of Truth

> **Status:** Architecture / pre-implementation. No code yet.
> **Last updated:** 2026-06-23 (D24: generation pipeline working — image→splat in ~19s on the 5090)
> **Maintenance rule:** This file is the canonical project log. Update it whenever a decision, plan, feature spec, or idea changes — in conversation OR in files. Append to the **Decision Log** when an idea evolves; edit the relevant section when a spec changes. Keep older decisions visible (strike-through or "superseded by") rather than deleting them, so the reasoning trail survives.

---

## 1. Vision

AI **stealth smart glasses**: look like normal glasses, offer a new experience. Two goals drive everything:
1. **Stealth** — discrete I/O (bone-conduction audio out, wearer-only monocular HUD, discreet good camera). Looks/feels like normal glasses.
2. **Autonomous agent** — full-context AI that manages daily life (scheduling, reminders, shopping, conversations) and can drive phone apps (e.g. open Spotify, pick a song).

Layered on top: **real, physics-enabled 3D objects** rendered into the world via Gaussian splats, and **humanoid telepresence / AI companion** avatars.

### Build order: SOFTWARE FIRST, hardware LAST (committed)
**Strategy A confirmed.** Build software → prototype on the user's iPhone → physical hardware is the LAST step (much later). Hardware constraints are studied now only to derive the requirements the software must respect (see §2a), NOT to build hardware yet. **The phone is both the prototype display AND the real offload-compute device — so phone-prototype work IS the architecture, not a throwaway.**

### Two separable tracks (build independently)
- **Track A — Agent glasses.** Valuable with ZERO splatting: mic + HUD + LLM + phone control. This is the daily-driver value.
- **Track B — 4D splat generation + rendering.** "Summon a photoreal animated object into my room." The flagship demo; the riskiest, least-proven tech.

**Decision:** Tracks are architecturally independent. Track A doesn't depend on Track B. (Originally Track A was "build first"; current focus has shifted to de-risking Track B's rendering core — see §9 Next Steps.)

---

## 2. System Architecture (3-tier compute)

```
[ CLOUD / EDGE SERVER ]  — NVIDIA GPUs. Heavy OFFLINE generation, user mgmt, global library.
        │  (streams: .splatmesh asset ONCE, then tiny live bone matrices)
        ▼
[ PHONE ]  — compute offload. Runs SLAM, physics, lighting estimation, splat RENDERING.
        │  (streams frames / poses to glasses; glasses do late-stage reprojection)
        ▼
[ GLASSES ]  — sensors + discrete I/O. Camera, depth/LiDAR, HUD, bone conduction, IMU.
              Lightweight accessory to the phone. Never does heavy lifting.
```

**Rigid split:** cloud GENERATES (heavy, one-time), the **offload device** RENDERS + ANIMATES + simulates physics (cheap, realtime), glasses DISPLAY + reproject.

### Adaptive offload device (the "render tier" is not fixed)
The offload device varies by context; the system detects capability and scales quality/LOD/splat-budget to match:
- **Out / commuting → phone** (the baseline, mobile-first). MUST work across a range of phones (see below), not just flagships.
- **Home / office → computer** (stronger GPU). Unlocks more: more complex objects, more on-screen at once, heavier workflows.
- (Future) dedicated wearable compute puck = another tier.

**Framerate tiers (D21):** make 45 vs 60 fps TWO quality tiers, not one global choice. **"Rich" = lock 45fps + max splats** (static/slow hero objects; relies on reprojection to keep head-motion smooth). **"Motion" = 60fps + fewer splats** (animated/fast content). Default to 60 as safe; 45-max-splats is a STRETCH tier trusted only once the warp engine (D19) is built — a stable capped rate always beats a fluctuating one.
**Runtime LOD by decimation (NOT regeneration):** to render fewer splats from an existing file, just SELECT a subset — importance-order once by (opacity×size), render top-N. Generate the asset ONCE at high quality; precompute a few discrete LOD levels offline (500k/250k/100k = cheap selection, seconds); switch dynamically at runtime by budget/distance/object-count. Random subsample = holes/popping; importance-order = graceful. (Advanced later: hierarchical merge of dropped splats.) This IS the adaptive runtime LOD the design assumes — never regenerate for performance.
**Benchmarking fairness:** splat render is FILL-RATE-bound → render resolution dominates cross-device comparison AND defines the budget (resolution ↔ splat count trade directly). `Res: 1280x720` toggle = a FAIRNESS BASELINE only (arbitrary, NOT a glasses spec) — use it to settle GPU-vs-GPU + a rough ceiling. **Real glasses res is PER-EYE and TBD** (hardware phase), ~1000–1920 px/eye → dual ~1200×1200 ≈ 2.9M px total vs 720p's 0.92M, so glasses push 2–4× more pixels → the TRUE budget is LOWER than 720p shows. Also: current stereo mode splits the canvas (each eye = half width), so 720p-stereo per-eye is optimistically low. TODO: add a "glasses preset" (dual ~1200×1200/eye) to measure the real product budget. Resolution itself = an adaptive budget knob (render below native + upscale = more splats). Cross-browser (Chrome vs Safari) = minor variable; bigger confounds = resolution/DPR + phone power/thermal throttle. (Note: modern Ryzen iGPU can genuinely beat a thermally-limited phone — trust the data over the earlier A15>iGPU assumption.)
**Per-object count reality:** a single AR object is object-scale, not scene-scale — **~100–300k splats looks high-res for one object** (~100k often plenty; 750k = diminishing returns, hero/close only). Budget = TOTAL on-screen splats (one 300k hero OR three 100k objects). Good news: modest phone budgets support convincing objects.

**Consequence:** the splat budget is a **tiered/adaptive budget**, not one number. Render path must support runtime device-capability detection + per-tier LOD/quality scaling. **Mobile is the from-the-get-go optimization target**; desktop is an *enhanced* mode, never a *required* one.

---

## 2a. Software requirements derived from hardware constraints
Whatever glasses we eventually run on (Snap, Meta, or our own), they share these traits. Software must respect them from day one:
1. **Render for an ADDITIVE display** — never rely on occlusion to look solid. Full opacity, saturated color, contact shadows/AO (biggest "it's really there" cue), avoid bright backdrops. (D12/D13)
2. **Respect a tiered splat budget + per-tier LOD** — ~100–300k splats target; benchmark sets exact per-device numbers. (D9/D10)
3. **Tolerate phone-offload latency** — stream POSES not geometry; on-device reprojection/timewarp for low motion-to-photon. (§2/§3)
4. **Work within narrow FOV (~50°)** — small viewport, no full-peripheral assumptions.
5. **Additive-only scope** — place virtual objects; NO diminished reality. (D11)
6. **Phone = prototype display AND offload compute** — the iPhone AR app built first IS the architecture; what runs on phone now streams to glasses later.

## 3. The Two Latencies (do not conflate)

| | **A: Time-to-first-render** | **B: Steady-state render + animate** |
|---|---|---|
| When | Once per *new* object | Every frame, forever |
| Requirement | Tolerable load wait | **Realtime 60–90 fps** |
| Where | Cloud GPU | Phone SoC + glasses reproject |
| Realistic today | **~15–40s** (optimizable to ~5–15s) | **Feasible at ~100–300k splats** |

The realtime/cheap requirement applies ONLY to B. A is a load screen, not a realtime budget.
**The original "1.5–2.5s for the whole pipeline" claim was a fantasy** — see Decision Log D1.

### Generation pipeline (Latency A, one-time, cloud)
| Stage | Realistic | Notes |
|---|---|---|
| Text → image (skip if image input) | 1–3s | Flux / SDXL-turbo |
| Image → 3D gaussians+mesh | 10–30s | **TRELLIS / TripoSR / LGM** (all MIT). AVOID InstantMesh (Zero123++ = NC) & Hunyuan3D-2 (geo/MAU-restricted). Output splats directly. See §4a. |
| Auto-rig (animatable only) | ~0.5s | **UniRig (MIT)** — AVOID RigAnything (Adobe NC); Make-It-Animatable = Mixamo-data taint. Arbitrary topology = open problem. |
| Bind splats → mesh triangles | <1s | Geometric nearest-triangle, NO per-asset training |

**Key lever:** use a feed-forward generator that emits Gaussians directly + bind geometrically. This avoids GaussianAvatars-style per-asset photometric optimization (minutes–hours), which is NOT a realtime baker.

### Runtime (Latency B, per-frame, phone)
`joint angles → LBS deform mesh + bound splats → rasterize → display`
- Deform + binding: negligible cost.
- **Gaussian rasterization is the real bottleneck.** Budget **~100–300k splats** for stereo 60–72 fps on phone-class SoC. "Millions of splats" breaks it. Use LOD + culling + foveation.
- **Motion-to-photon:** phone renders, glasses do **late-stage reprojection (timewarp)** to keep latency < ~20ms.

### Animation source (separate one-time cost)
AI-generated motion (AnimaX-style) = seconds–minutes per clip, then playback is free. Mocap/physics/pre-canned = instant.

---

## 4. Asset Library Architecture (the economic core & data moat)

**Principle:** generation is NOT a runtime step. Build a growing, deduplicated library; at runtime do RETRIEVAL with generation as the rare miss path. Library compounds with usage → marginal cost → ~0. This is the network-effect **moat**.

### Data model: Category → Class → Instance
- **Category** — semantic, for browse/search ("chair"). Contains many classes.
- **Class** — shared **mesh + rig + physics/collision params** ("wooden 4-leg dining chair"). The geometry unit.
- **Instance** — an **appearance splat** on a class + optional metadata (brand/price/SKU) + owner.

> A couch and a rocking chair are SEPARATE CLASSES under the "chair" category — different geometry & physics, can't share a mesh. "Versions of a chair" = separate classes, not instances.

**Class match ≠ appearance shared:** when a scan matches a shared class, reuse the class (mesh/rig/physics) but the captured splat stays a **private instance** pointing at that class. *Shared geometry, private appearance.*

> **Critical constraint:** splats are bound to mesh triangles, so "same mesh, different splat" only works when variation is APPEARANCE-ONLY (Doritos flavors, book covers, colorways). For variable geometry (furniture, organic) it breaks. For STATIC props (most everyday objects), skip the shared mesh entirely — store per-instance splats + a cheap collision proxy; "class" is then just a retrieval/dedup grouping. Mesh-sharing's real payoff is ANIMATABLE classes (rig genuinely reused).

### Scopes = ONE pool, two metadata flags (NOT three databases)
- **Visibility:** `global` | `marketplace` | `private`
- **Curation:** `hand-curated` | `provider-verified` | `user-generated`

| Scope | = | Contents |
|---|---|---|
| Global | (global, hand-curated) + auto-grown generics | generic everyday objects |
| Marketplace | (marketplace, provider-verified) | buyable products, providers self-upload, commerce metadata (price/SKU/checkout) |
| Private | (private, user-generated) | user scans/creations + ALL humanoids; premium-tier feature |

### Write-time ROUTER (replaces naive "discard/keep")
On every scan, one classifier (you already need a humanoid detector — extend it) routes:
- **Person/face →** private humanoid profile
- **Branded / copyrighted / IP →** block, or keep private-only (never shared)
- **Buyable product →** marketplace scope
- **Generic non-branded object →** flat shared pool, **dedup-on-write** (similar → reuse existing, different → keep)

> Dedup-on-write IS the flywheel. But "no search" is an illusion — the similarity check IS the retrieval layer, moved to write-time where it needs HIGHER precision (a wrong discard deletes user data). Still needs embeddings + ANN index.

### Other library decisions
- **Cold-start:** seed offline from **Objaverse-XL (~10M) / ShapeNet** converted to our format. Don't launch empty.
- **Multi-view capture:** on a miss, exploit that glasses see a VIDEO stream — capture multiple frames as the user looks around the object. Far better than single-snapshot→3D (which hallucinates unseen sides).
- **Library janitor:** dedup + quality-scoring + curation, or retrieval DEGRADES with growth. Self-improving requires self-pruning.
- **Cross-scope retrieval ranking policy** (business decision): private (personalization) vs marketplace (revenue) vs global (fallback).
- **Predictive device cache:** glasses cache assets predictively via agent context (location/time) — the context engine is the prefetcher.
- **Progressive enhancement on the FOCAL object:** show retrieved proxy immediately → hot-swap accurate generated asset when ready. Silent substitution ONLY for ambient/background props.
- **"Costs nothing" caveat:** marginal cost → 0, but standing CDN/storage/index + long-tail gen remain. Reality = "cheap, dominated by serving," not "free."

---

## 4a. Software stack licensing (commercial-use audit — VERIFIED)
For a COMMERCIAL product. Several popular models/datasets are non-commercial landmines; the clean stack below avoids all of them. (Engineering summary, not legal advice — counsel to confirm before ship.)

**🟢 CLEAN COMMERCIAL STACK (use these):**
- **Generation:** TRELLIS (MIT), TripoSR (MIT), LGM (MIT)
- **Auto-rig:** UniRig (MIT) — the safe rigging choice
- **Motion:** Wan2.1 (Apache-2.0) — safest base; AnimaX unreleased, re-audit at release
- **Render:** mkkellogg/GaussianSplats3D (MIT), PlayCanvas + SuperSplat (MIT)
- **Compress:** Draco (Apache), meshoptimizer (MIT), KTX2/Basis (Apache); splat = PlayCanvas **sogs / splat-transform / PLAS** (Apache/MIT)
- **Retrieval:** CLIP (MIT code), DINOv2 **current Apache-2.0 weights** + vector DB
- **Seed data:** Objaverse **filtered to CC0/CC-BY only** (persist per-asset license + attribution)
- **Parametric (humanoid, future):** FLAME **2023 Open (CC-BY-4.0)** or Meshcapade-licensed

**🔴 LANDMINES (do NOT ship):**
- **Original 3DGS (Inria) + diff-gaussian-rasterization** — explicit NON-COMMERCIAL. Never ship this code or derivatives; use permissive renderers + clean-room optimization.
- **SOG research repo (Fraunhofer)** — inherits Inria NC → use PlayCanvas sogs/PLAS instead.
- **InstantMesh** — Apache code but Zero123++ weights = CC-BY-NC → blocked; swap multi-view stage.
- **Hunyuan3D-2** — NO rights in EU/UK/South Korea; >1M MAU needs a Tencent license.
- **RigAnything** — Adobe non-commercial → hard blocker; use UniRig.
- **ShapeNet** — non-commercial, no path → exclude; use filtered Objaverse.
- **SMPL (+ SMPL-X/AMASS/most body rigs)** — non-commercial AND taints models trained on it → Meshcapade commercial license or avoid.
- **FLAME (non-2023 variants)** — non-commercial → use FLAME 2023 Open or license.
- **DINOv2 pre-Aug-2023 weights** — were CC-BY-NC; pin to current Apache weights; avoid biology variants.
- **Make-It-Animatable** — MIT code but Mixamo/Adobe skeleton data → retarget to owned skeleton or diligence.
- **Tripo platform/API** — free tier = non-commercial output; need paid tier for commercial rights.

## 5. Physics (EASY TIER ONLY — current scope)

**Mental model:** physics runs on a hidden **collision proxy** (box/convex hull/compound), NOT the splats. Splats are drawn wherever the proxy lands. Engine = Bullet/Jolt/PhysX on the phone, realtime.

**In scope (all feasible, realtime today):**
- Move / rotate anywhere ✅
- Float midair (mark body **kinematic**, gravity off) ✅
- Drag around midair ✅
- Drop / fall (mark **dynamic**, gravity on) ✅
- Bounce, settle, rest (restitution + friction) ✅
- Throw, knock over, stack, collide with other virtual objects ✅

**Caveat — collide with the REAL world:** needs the environment inside the physics sim.
- Floor/table **plane detection** → easy, no special HW.
- Arbitrary furniture/edges → needs real-time room mesh from **depth/LiDAR**.

**Physics params live on the CLASS** (mass, restitution, friction, collision proxy).

**OUT OF SCOPE for now (hard tier — deferred):** breaking/fracturing, cutting, soft-body squish/bend. Reason: splats are a **hollow shell** — breaking exposes interior never captured (no appearance data); also requires pre-authored fracture pieces. Revisit later as a per-object authored "hero" effect only.

---

## 6. Humanoid / Telepresence (the emotional core)

- Each user has a **private humanoid avatar profile**.
- Add **family/friends** as AR avatars.
- **Shared visual sessions** on a call → "feel like you're in the same room."
- **AI companion avatar** that walks/sits with the user and converses naturally.

**Clear-eyed cost note:** humanoids are kept PRIVATE (correct for privacy) but are ALSO the most expensive to produce (GaussianAvatars-style per-subject optimization + live face/body tracking to drive them) and the LEAST dedup-able (every person unique → no flywheel, full cost per user). **The real cost center is the humanoid pipeline, not the object library.**

**Build order within this track:** AI companion avatar first (single asset, optimized offline once) → then live human↔human telepresence (real-time capture + drive on both ends = hardest).

---

## 6b. Input / Interaction (HOW the user drives the HUD)
**Was a gap — now spec'd.** Output/content was fully designed; input wasn't. Camera hand-gestures are feasible (outward camera + phone CV) BUT as PRIMARY HUD navigation they fight the stealth core: air-waving is the most conspicuous possible interaction, causes gorilla-arm fatigue, and draws power. Wrong default for a stealth device.

**Key distinction — two different jobs, different inputs:**
- **HUD/menu/agent navigation** (all-day, in-public) → must be DISCREET.
- **3D object manipulation** (grab/move/rotate a splat object) → hand gestures genuinely shine here; conspicuousness justified by deliberate engagement.

**DECIDED — dual-mode (two contexts):**
- **Stealth mode = SILENT SPEECH.** Discreet, all-day/public. Command grammar ("open Spotify", "next", "summon X"). Limited expressiveness, invisible to bystanders.
- **Power mode = FULL HAND MOTION.** Spatial/direct manipulation — point midair & interact, grab/move/rotate objects. Fast & comfortable, conspicuous → used in private (home/office). Covers BOTH 3D object manipulation AND general HUD control.
- They complement (different contexts), not overlap. User accepts the tradeoff (stealth=limited, power=visible).

**RISK + mitigation:** silent-speech IN (subvocal/EMG) is the LEAST-proven tech in the project (AlterEgo = lab; Meta neural = wrist not throat) — highest-risk input bet. **Mitigation: prototype stealth mode with ORDINARY VOICE as stand-in** — identical command grammar/agent intent, only capture differs (mic now → EMG sensors at HW phase). Entire stealth UX buildable today; risk lives in production HW, not current software. **Optional cheap backstop: keep temple touch** as a discreet fallback if silent speech underdelivers.

**Open sub-decision (non-blocking):** mode switching = auto-by-context (private/public via location) vs manual toggle. Settle during HUD UX design.

**HW implications (all production-phase):** hand-tracking = existing camera + phone CV (CV runs on phone; activate contextually, not always-on); silent-speech = +EMG/subvocal sensors (immature); temple-touch backstop = cheap.

**Where hand tracking is processed = PHONE, not glasses.** Principle: TWO kinds of real-time. Head-pose reprojection = HARD real-time (<10ms → must be on glasses, wireless round-trip blows it). Hand interaction = SOFT real-time (~50ms tolerance, usable to ~100ms → phone round-trip fits). So hand-pose CV + gesture + interaction run on the phone alongside SLAM (cameras already stream there); glasses stay minimal (camera + display + warp). The two budgets LAYER: phone sets object world-position at hand-latency, glasses reprojection keeps it head-locked at <10ms → no swim even with phone-latency hand updates. Failure mode: bad link → grabbed object trails hand (rubber-band); mitigate with fast link + optional on-glasses prediction for the actively-held object. Optional later optimization: on-glasses hand-keypoint detection to stream keypoints not frames (bandwidth+privacy). Prototype = all phone anyway (iPhone camera + ARKit).

## 7. Hardware (Track A / glasses)

Target: looks like normal glasses; discrete I/O; comfortable; ~8h battery; no heat issues.
Components: bone-conduction audio out, wearer-only monocular HUD (waveguide), discreet camera, depth/LiDAR (for physics + occlusion), IMU.

### Glasses-side compute = split/distributed AR (thin glasses, heavy phone)
Our model independently = Qualcomm Snapdragon AR2 design philosophy. Glasses do only: (1) receive phone stream, (2) drive microdisplay + electrochromic dimming (the D12 work), (3) **reprojection/timewarp** (warp last frame to current head pose via onboard IMU so world-locked objects don't swim). That reprojection is the "one hard job" — display-adjacent, NOT full rendering. Heavy splat render stays on the phone.

**Component spectrum:**
- **Dumb tethered display (Xreal/Rokid class):** display driver + USB-C only, no compute/reprojection. World-lock weak (floating screens OK, anchored objects swim). **~$300–500 whole glasses, off-the-shelf TODAY.**
- **Thin AR + co-processor (Snapdragon AR2 class):** + sensor hub + onboard reprojection; solid 6DoF; offloads render to phone. = our target tier. NOT a hobby part — reference-design/ODM/NDA/volume, a months-long hardware program. Belongs in the LAST phase.
- **Standalone (Snap dual-SoC):** everything onboard, $$$ — what we avoid.

**Prototyping decision:** phone-only now; defer glasses board to production. Cheap "feel it in-glasses" shortcut = drive an off-the-shelf Xreal/Rokid USB-C display (~$300–500) from the phone, zero HW engineering (imperfect world-lock, feel-prototype only). Real co-processor = final hardware phase via ODM.

**Can the phone do ALL the display compute? Almost — reprojection is the irreducible glasses-side sliver.** Split the "display" into: (1) physical optics/panel/dimming = always on glasses (hardware, not compute); (2) heavy compute (render, SLAM, apps) = 100% phone ✅; (3) **reprojection/timewarp = MUST stay on glasses** to match Specs' world-lock (7ms motion-to-photon). Physics: warp must happen at the very END of the chain using the freshest pose — if the phone does it, the result travels back over the link and re-adds the latency the warp exists to hide. Zero glasses compute (dumb USB-C display) still works but drops to floating-screen tier (objects swim). KEY WIN: Specs uses dual Snapdragons because it does EVERYTHING onboard (standalone, no phone); we keep ONLY the warp local → **Specs-grade display quality with a tiny fraction of Specs' chip** (cheap FPGA/warp ASIC, not a GPU/SoC). Irrelevant to the phone prototype; production-phase part.

**CHIP-AGNOSTIC — NOT locked to Snapdragon (either end).** The glasses never do heavy render (phone does), so they only need a modest display+warp+sensors engine. Options, cheapest→turnkey: small **FPGA / display-warp ASIC** (Lattice/AMD — best fit, glasses' job is fundamentally an image-warp, lowest latency, no NDA) → general **ARM SoC** (MediaTek/Rockchip RK3588/NXP i.MX — cheap/open, more DIY pipeline) → **dumb USB-C display, no SoC** (Xreal/Rokid, weak world-lock) → **Snapdragon AR2** (turnkey but pricey + NDA + lock-in). Phone side also not Snapdragon (prototype = iPhone/Apple silicon; production = any phone). Silicon choice = production-phase decision, changes nothing about phone software now.

### Display capability ceiling: ADDITIVE-ONLY (decides what's renderable)
The stealth HUD is **optical see-through** = it ADDS light, cannot SUBTRACT. Consequences:
- ✅ Can do: place/add virtual objects, labels, HUD, *brighter* overlays.
- ❌ Cannot do: hide/remove real objects, darken or repaint real surfaces, full occlusion. Virtual objects look slightly ghostly over bright backgrounds.
- **Environment manipulation ("change wall color / hide my bed / replace real objects") = Diminished/Mediated Reality, which REQUIRES video passthrough (opaque goggles, editable per-pixel) — the OPPOSITE of stealth.** You can't have full redecoration AND stealth optical glasses.
- DR is also a research-grade lift even on passthrough (real-time segmentation + background inpainting + temporally-stable relighting).
- Exotic middle ground: segmented dimming (Magic Leap 2 style) = partial darkening/occlusion, but bulky/anti-stealth, not arbitrary removal.
- **Verdict:** stealth track is ADDITIVE-ONLY. Full environment manipulation = a separate **video-passthrough product (v-future fork)**, not a feature on this track.

### Making objects look SOLID (not ghostly) in a stealth form factor
Problem: additive optics make virtual objects translucent/faded. Goal: objects look solid/opaque, but small & discrete.
- **True per-pixel occlusion (opaque) in a small form factor = UNSOLVED frontier.** It's physics, not sourcing: a near-eye occlusion mask is heavily defocused; making it sharp needs relay optics → bulk. That's WHY segmented dimming (Magic Leap 2) is bulky. No compact off-the-shelf version exists; compact occlusion (holographic/phase-SLM, soft-occlusion) is years-out research.
- **Shippable compact recipe = CONTRAST-based solidity (not true occlusion):** (1) dynamic **global electrochromic dimming** (small LC tint, no relay optics, darken whole view a bit so content pops), (2) **high-brightness microLED / laser-beam-scanning** light engine (tiny, high nits), (3) **rendering tricks** — full opacity, saturated color, contact shadows/AO, avoid thin edges & bright backdrops.
- **Result:** convincingly solid INDOORS; weaker over bright windows / sunlight (real light overwhelms additive).
- **Trade:** dimming = tinted lenses = "sunglasses indoors" look → fights stealth. Mitigate with DYNAMIC dimming (only where/when content shown, only as much as needed).
- **Decision:** design around contrast-based solidity; treat true compact occlusion as a research line to MONITOR, not a dependency.

**Known contradictions to resolve BEFORE industrial design:**
- Wearer-only HUD = waveguide display = bulky, narrow-FOV, hard to hide. **Display vs stealth is the core contradiction.**
- Display + LiDAR + good camera + 8h battery + "looks normal" are **mutually exclusive today**. Must drop/trade something.
- Heat on a face-worn device with camera+display+LiDAR+radio is a hard limiter; 8h is optimistic.
- "Silent speech by bone conduction" conflates two techs: bone conduction = audio OUT; silent-speech IN = subvocalization/EMG (separate, less mature). Don't assume one component does both.

---

## 7b. DEFERRED — Hardware Industrial Design (develop LATER, placeholder)
Not designing hardware now (software-first). These are captured as TODO topics to flesh out in the hardware phase:
- [ ] **Bill of Materials (BOM)** — full component list: waveguide + light engine (microLED/LBS), electrochromic layer, warp chip (FPGA/ASIC), connectivity radio, IMU, camera(s), depth/LiDAR, mics, bone-conduction transducers, EMG/silent-speech sensors, battery, PCB/SoM, housing. With cost estimates per component.
- [ ] **Frame/industrial design** — form factor, geometry, single-lens integration, hinge/temple layout to hide electronics, weight distribution.
- [ ] **Material** — TR90 polymer (per Snap) vs alternatives; durability, weight, skin contact, RF transparency.
- [ ] **Thermal** — heat dissipation on a face-worn device (camera+display+radio); passive vs active; duty-cycling; comfort limits.
- [ ] **Battery** — capacity vs weight vs ~8h target; in-frame vs temple vs charging-case top-up; safety.
- [ ] **Connections** — glasses↔phone link (wireless 60GHz/Wi-Fi6E vs wired USB-C), bandwidth/latency budget for stream + reprojection, charging/data port.
- [ ] **Sensor placement & ergonomics** — camera FOV vs hand-tracking zone, eye-relief, fit range, comfort, all-day wear.

## 8. Open Questions / Decisions To Make
- [x] ~~Primary input modality~~ DECIDED (D18): dual-mode = silent speech (stealth) + full hand motion (power). See §6b.
- [ ] **Mode-switching mechanism** (§6b): auto-by-context vs manual toggle — settle during HUD UX design.
- [ ] **Growth fork** (recommended: consent-gated promotion). Manual-only global = no moat. Auto-promote generic classes via dedup-on-write + IP/privacy filter + curation. Personal splats NEVER promoted. → leaning toward the router model in §4.
- [ ] **Retrieval layer spec:** embedding choice (CLIP-on-renders vs DINO vs 3D-native), vector DB, two-tier thresholds (geometry for class, appearance for instance), cross-scope ranking policy.
- [ ] **Splat-count / fps budget** on real target hardware (the load-bearing unknown for Track B).
- [ ] **Hardware contradiction resolution** (display vs stealth).
- [ ] **Asset format spec** (`.splatmesh` container: mesh + skeleton + skin weights + splat coefficients + physics params + metadata).
- [ ] **Provenance / licensing** for commercial library (Wan2.1 / CC-BY / CC0 base where possible).
- [ ] Compression: Draco+meshopt+KTX2 (mesh), SOG + LOD (splat).

---

## 8c. Dev resources
- **Server (`shnri`):** NVIDIA **RTX 5090, 32GB VRAM** (Blackwell — needs recent PyTorch + CUDA 12.8), 36 cores, 94GB RAM, Docker, Python 3.12, Node 18. → generation (TRELLIS etc.) runs LOCALLY, no cloud GPU needed to start.
- Test devices: iPhone 14 (60Hz), Windows laptop (AMD Radeon iGPU). Render budget validated ~200k splats/object (D22).
- `.ply` test fixtures preserved in `benchmark/assets/` (Shu2 splat, Hammer point cloud).

## 9. Next Steps (proposed roadmap)
See conversation recommendation. Highest-leverage first:
1. **De-risk the rendering core (Track B foundation).** Vertical slice: take/generate ONE rigged splat asset, render it with rigid-body physics (drop/bounce/move) and measure the **splat-count vs fps** curve in stereo. **Mobile-first**, benchmarked across a **device matrix spanning ~last 3 years of phones** (low/mid/flagship — must not be flagship-only), to produce a **per-tier splat budget**, plus a desktop run as the *enhanced* upper tier. This validates the load-bearing assumption ("realtime animated splats on cheap hardware") AND establishes the adaptive-quality tiers.
2. **Spec + prototype the retrieval layer** (embeddings + ANN + write-time router + dedup-on-write).
3. **Offline generation pipeline** (image/text → splats+mesh → geometric bind), seeded from Objaverse.
4. In parallel, **Track A agent loop** (mic + HUD + LLM + phone control) — independent of B.

---

## 8b. Competitive landmark: Snap Specs ($2,200, 2026)

Snap Inc.'s consumer AR glasses. **Validates our reasoning, doesn't kill us.**
- Specs: see-through waveguide, 51° FOV, 132g, **electrochromic lenses** (clear→tinted 10s), 7ms motion-to-photon, **~4h battery** (20h w/ case), onboard/standalone compute, $2,200.
- **They did NOT solve occlusion.** Waveguide + electrochromic = additive optics + global dimming = EXACTLY the D12 contrast-based-solidity recipe. No true per-pixel opaque occlusion exists; D12 confirmed by a billion-dollar competitor. No magic display to "adopt."
- **Local rendering cost them battery (4h vs our 8h goal)** — confirms our phone-offload bet is a legit different design point (lighter/cooler/longer), not a deficiency.
- **What Snap actually solved = INTEGRATION/miniaturization, not new optics** — single clean integrated lens (not chunky multi-element), self-contained/wireless (not tethered). The dual Snapdragons enable untethered operation AND cause the 4h battery AND drive the cost. Their cleverness and their weakness share one root cause.
- **COST CORRECTION (earlier "$2,200 me-too" was wrong):** the $2,200 is mostly the dual flagship SoCs + sensors, NOT the display. Our phone-offload architecture DELETES the onboard compute → meaningfully cheaper than Snap. Display optics (waveguide+light engine+electrochromic) are the big remaining single cost. Evidence: Meta display glasses = $800 by leaning on an external device. So a phone-offloaded device plausibly targets the **~$800 class, not $2,200** — same display category, lower price, lighter, longer battery. (Hardware is later anyway.)
- **Strategic conclusion: do NOT compete on hardware.** Matching their display/price = a $2,200 me-too vs Snap/Meta/Apple (platforms, ecosystems, scale we can't beat) AND loses stealth. Our moat = SOFTWARE: the agent + the asset-library content flywheel.
  - **Strategy A (preferred): be the software/content LAYER**, platform-agnostic — run the agent + asset library ON Snap/Meta/whoever wins. Sell shovels. A $2,200 competitor arriving = hardware commoditizing = good for this play.
  - **Strategy B: build a DELIBERATELY DIFFERENT device** — stealth, agent-first, longer-battery (phone-offloaded), cheaper, less flashy-AR. Different segment than Snap's dev-flashy showpiece.
  - **Avoid the middle:** a $2,200 stealth-ish device competing on AR rendering loses on every axis.

## 9a. Rendering Benchmark Slice — spec (Next Step #1, detailed)
> **BUILT (compare viewer):** `benchmark/viewer.html` — toggles Splat / Mesh / Bones, Combined vs Side-by-side. Mesh+bones from `assets/crab_rigged.glb` (decimated 50k-face GLB w/ armature, via `generation/prep_viewer.py`/bpy); splat as colored points (crisp splat stays on splat.html). Makes the 1-bone skeleton bug visible. Three.js (esm.sh), no mkkellogg (avoids two-three-instances conflict).
> **BUILT (real assets):** `benchmark/real.html` — loads real `.ply`s with per-asset toggles. `Shu2Edited.ply` = real 3DGS splat (~66k); `Hammer_point_cloud.ply` = plain colored point cloud (665k pts, NOT a splat). Still uses the approximate additive/no-sort renderer (loader+toggle+rough perf, not pixel-accurate). Faithful sorted-3DGS render (mkkellogg) = next step for exact sort-cost. Assets in repo (~24MB; move to LFS/external if it grows).
> **BUILT:** `benchmark/index.html` (self-contained WebGL2 page, no deps) + `benchmark/README.md`. v1 uses synthetic gaussians + additive/no-sort blending = render-throughput budget (slightly optimistic); refine later with real renderer (mkkellogg) on a real asset. Untested by author — user runs it. Awaiting first results to fill the per-device budget table.
> **HOSTING:** repo = github.com/yousef-yy4u/AI-SG; deployed on **Railway** via `Dockerfile` (caddy:2-alpine serves `benchmark/` on `$PORT` per `Caddyfile`). Open the Railway `*.up.railway.app` domain on the phone. (Cloudflare quick-tunnel abandoned — QUIC instability on the server, error 1033.)
>
> **✅ RESULTS (first real data, 2026-06-22; size 1.2, stereo, sustained):**
> | Device | Res | 60fps budget | ~45–50fps | Throttle |
> |---|---|---|---|---|
> | iPhone 14 (Apple GPU) | 720p (0.9M px) | ~200–250k | 350k→47 | stable |
> | **iPhone 14** | **glasses 2400×1200 (2.88M px)** | **~200k** | ~250–300k est | 350k→35→27 🔴 |
> | Laptop (AMD Radeon iGPU, RDNA3-class) | 720p | ~750k | 1M→55 | stable |
> | Laptop | glasses (2.88M px) | ~350k | 500k→50 | stable |
>
> **HEADLINE: iPhone 14 holds ~200k splats stereo @ locked 60fps @ glasses res, thermally stable → a single photoreal object (D21 ~100–300k range) runs realtime on a mid-2022 phone. Core assumption VALIDATED.** Insight: ≤200k is splat-COUNT-bound (res barely matters); fill-rate only bites at 350k. CAVEATS: benchmark is optimistic (additive, NO per-frame sort) → real 3DGS budget somewhat LOWER; iPhone 14 is 60Hz so true edge is between 200k–350k (test 250k/300k); newer/Pro phones do more. Laptop AMD iGPU beats the phone (~1.75× at glasses res) — confirms D13/fairness note.

**Goal:** produce a per-device splat-budget table that validates "realtime splats on cheap hardware" and seeds the adaptive tiers (D9).

**Devices available now:** iPhone 14 (A15, **mid anchor**) + Windows laptop w/ integrated graphics, no dGPU, Ryzen 3/5, 16GB RAM (**low anchor — likely WEAKER than the iPhone for splats**). True desktop dGPU tier = TODO (no hardware yet).

**Stack decision:** **Web, WebGL2 first** (one build runs Safari/iOS + Chrome/Edge + any phone). Renderer = existing **Three.js + mkkellogg/GaussianSplats3D** (don't write a rasterizer). WebGPU = later upside test. Web perf is a **conservative floor** — native will be ≥ web.

**Scope (tight):** static splat cloud + **rigid-body** transform + physics proxy only. NO per-splat skeletal skinning (rigid object = ONE transform matrix; skinning only needed for animated characters = later slice). NO full AR/SLAM yet (render fullscreen + single ground plane).
> Insight: every easy-tier physics interaction (move/drop/bounce/float/throw/stack) is rigid-body → whole cloud transforms by one matrix. Cheap.

**Asset:** one object splat `.ply`, decimated into a sweep (content irrelevant, COUNT is the variable). Decimate via SuperSplat "reduce" or top-K-by-(opacity×scale). Sweep: **25k, 50k, 100k, 200k, 350k, 500k, 750k, 1M**.

**Methodology gotchas:** (1) **Sustained not peak** — median fps over a 5-min run + record fps-after-5min (thermal throttle is the mobile killer, esp. face-worn). (2) **Stereo ≈ 2× cost** — test mono for the clean curve, then a render-twice stereo pass (the real AR target).

**Table columns:** Device | GPU/SoC | Browser/API | Splat count | Resolution | Mode (mono/stereo) | FPS sustained (p50, 5min) | Frame time p95 (ms) | Mem (MB) | FPS after 5min | Verdict.
**Verdict (mono):** 🟢 ≥60 (≥72 ideal AR) · 🟡 30–60 · 🔴 <30. Largest 🟢 per device = that tier's budget; halve-ish for stereo.

## 9c. Generation pipeline — WORKING (image → splat, on the 5090)
**Status: end-to-end working.** image → TRELLIS → gaussian `.ply` → importance-decimate to budget → render.
- **Env:** venv `/home/sov2/projects/gen-venv` (Python 3.12), torch **2.11.0+cu128** (Blackwell sm_120), TRELLIS clone at `/home/sov2/projects/TRELLIS`.
- **Deps that worked on Blackwell:** `xformers 0.0.35` (from pytorch cu128 index — sm_120 flash-attn-2 op works but ONLY fp16/bf16, not fp32), `spconv 2.3.8` (spconv-cu126 wheel), `utils3d`, `plyfile`. **kaolin STUBBED** (`gen-venv/.../site-packages/kaolin/utils/testing.py` → no-op `check_tensor`) since it's only imported for the mesh path, which gaussian-only never runs.
- **Required env vars at run:** `PYTHONPATH=/home/sov2/projects/TRELLIS XFORMERS_DISABLED=1 ATTN_BACKEND=xformers SPARSE_BACKEND=spconv SPCONV_ALGO=native`. `XFORMERS_DISABLED=1` forces **DINOv2** (image encoder) to native attention (it ran fp32 → xformers fa2 rejected it); TRELLIS's own sparse attn still uses xformers (runs fp16 → works).
- **Scripts (in repo `generation/`):** `run_trellis.py` (image→`out/output.ply`, formats=['gaussian'] only), `decimate_ply.py` (top-N by opacity×volume → LOD).
- **First result:** robot-crab sample image → **859,328 splats in ~19s** (pipeline load ~43s first time), decimated → `benchmark/assets/robot_crab_200k.ply` (200k, 13MB), wired into `real.html` (3rd toggle "Generated crab").
- **MESH output also WORKS** (formats=['mesh']) with the kaolin stub — flexicubes extracts fine without real kaolin. Crab → 464,708 verts / 929,372 faces. So pipeline gives aligned mesh+gaussians (needed for rig→bind). GLB *texture* export still needs nvdiffrast (deferred — raw mesh geometry is enough for rigging).
- **UniRig setup (in progress):** venv `/home/sov2/projects/unirig-venv` (**Python 3.11.15** via uv — bpy needs 3.11), torch 2.11+cu128, bpy 4.2, spconv 2.3.8, all bulk deps ✅. Clone at `/home/sov2/projects/UniRig`. Crab mesh exported → `generation/out/crab_mesh.obj` (464k verts).
  - **✅ SKELETON WORKS** — `crab_skeleton.fbx` generated, NO compilation. How (reproducibility): (1) set `_attn_implementation: sdpa` in `configs/model/unirig_ar_350m_1024_81920_float32.yaml` (was flash_attention_2); (2) pure-Python STUBS in unirig-venv site-packages: `torch_cluster` (real fps), `torch_scatter` (real segment_csr/scatter), `flash_attn[.modules.mha.MHA]` (raises if called). Skeleton uses michelangelo encoder (only fps runs); PTv3/skin imports are satisfied by stubs but not executed.
  - **✅ SKIN model RUNS too — no flash_attn compile.** How: (1) native sdpa-backed `MHA` in the flash_attn stub matching flash-attn's exact params (Wq/Wkv/out_proj) so the skin ckpt loads; (2) set `enable_flash: False` on the PTv3 mesh_encoder in `configs/model/unirig_skin.yaml` → PTv3 uses its built-in manual-attention path (no flash_attn_varlen); (3) `torch_scatter.segment_csr` stub (real impl); (4) `sitecustomize.py` forces `torch.load(weights_only=False)` (ckpt has python-box objects). Skin inference produced `predict_skin.npz`.
  - **🐞 OPEN BUG: skeleton is DEGENERATE (1 bone).** `crab_skeleton.fbx` armature has a single `bone_11`; skin npz shows `joints (1,3)`, so the export indexes out of bounds. The skin *machinery* is fine — the AR *skeleton* came out as 1 bone. Suspect: my `torch_cluster.fps` stub feeding the michelangelo encoder (most likely), or an AR-sampling subtlety with sdpa. Giraffe example test hit an unrelated npz_dir path bug (`tmp/examples/giraffe/raw_data.npz` not found) — clean A/B still needed.
  - **NEXT DEBUG:** validate the fps stub correctness; get a known-good example skeleton (fix npz_dir path); confirm sdpa vs flash AR output. THEN: bind splats→rig + skinning + animate + ElevenLabs.
- **DEMO TARGET (user pick): splat-quality animated** (not mesh) → needs faithful renderer (done, splat.html) + rig + splat-to-rig binding + skinning. Hardest path.
- **NEXT:** decision on the flash_attn/scatter/cluster compilation (skin weights). Skeleton-only achievable now. Note: ElevenLabs = audio only; movement is a SEPARATE source (procedural/motion model). First MVP demo likely = rigged MESH animated in Three.js + ElevenLabs audio (splat-binding fidelity is a later upgrade). Render fidelity caveat: real.html's isotropic-additive viewer makes splats look sparse — validate true quality via superspl.at or integrate mkkellogg.

## 10. Decision Log (idea evolution — newest last)

- **D1 — "1.5–2.5s whole pipeline" rejected.** GaussianAvatars is per-subject optimization (600k iters), NOT a sub-second baker. Make-It-Animatable's 0.5s is humanoid-only. A³-GS is multi-view optimization, not feed-forward. → Reframed into the **two-latency model** (§3): one-time generation ~15–40s, steady-state render realtime.
- **D2 — Architecture = retrieval, not runtime generation.** Adopted the library/cache + generation-fallback model as the economic core and data moat (§4).
- **D3 — Library refinements.** Ambient-vs-focal substitution; static-vs-animatable tiers; seed from Objaverse; multi-view capture; janitor; privacy/brand caveats.
- **D4 — Data model: class (geometry) vs instance (appearance).** Same model unifies everyday objects AND commerce SKUs. Splat-binding constraint surfaced (appearance-only variation).
- **D5 — Three scopes = one pool + flags.** global/marketplace/private as visibility×curation, not 3 DBs. Added **category → class → instance** (fixed "chair is a class" bug). Surfaced growth fork.
- **D6 — Simplification debate.** User proposed flat "everything-shared + dedup-on-write, only humanoids private." Verdict: drop the deep nesting (good), but DON'T flatten scopes — everything-shared = IP-takedown firehose + deletes commerce. **Synthesis: keep dedup-on-write, replace binary keep/discard with a write-time ROUTER** (§4). Humanoid telepresence vision added (§6).
- **D7 — Physics scoped to EASY TIER only** (§5). Hard tier (break/cut/soft-body) deferred — splats are hollow shells.
- **D8 — This file created** as single source of truth.
- **D9 — Adaptive offload tiers + mobile-first benchmark.** Offload device is context-dependent: phone when out (baseline), computer when home/office (enhanced — more complex objects/workflows). Splat budget is therefore TIERED, with runtime device-detection + per-tier LOD. Benchmark across a phone matrix spanning ~last 3 years (not flagship-only); desktop = enhanced upper tier, never required. Mobile optimized from the get-go. (§2, §9)
- **D20 — Licensing audit done; stack swapped to commercially-clean (§4a).** Verified landmines: Inria 3DGS code + diff-gaussian-rasterization (NON-COMMERCIAL — never ship), SOG research repo, InstantMesh/Zero123++ (NC), Hunyuan3D-2 (no EU/UK/SK, 1M-MAU cap), RigAnything (Adobe NC), ShapeNet (NC), SMPL/FLAME-non-2023 (NC + training-taint). Clean stack: TRELLIS/TripoSR/LGM + UniRig + Wan2.1 + mkkellogg/PlayCanvas + Draco/meshopt/KTX2/sogs/PLAS + CLIP/DINOv2-Apache + Objaverse(CC0/CC-BY) + FLAME-2023-Open. (§4a, §3) + §7b deferred hardware-ID placeholder added.
- **D24 — Generation pipeline WORKING end-to-end on the 5090.** image → TRELLIS → 859k-splat `.ply` in ~19s → importance-decimate to 200k budget → rendered in real.html. Blackwell deps solved (xformers cu128 + spconv-cu126 + kaolin stub + DINOv2 native attn). Full reproducibility in §9c. Keystone achieved — next: rigging (UniRig), text→image front-end, then retrieval/library. (§9c)
- **D23 — Moving to PRODUCT; first build = GENERATION PIPELINE (TRELLIS on local RTX 5090).** Keystone: produces the assets retrieval/library/agent all depend on. Target loop: image/text → TRELLIS → 3D gaussian splat → decimate to ~200k budget → render in real.html. Setup wrinkle: 5090 is Blackwell → needs recent PyTorch + CUDA 12.8. TRELLIS = MIT, outputs gaussians natively (clean per §4a). (§8c, §9)
- **D22 — Benchmark FIRST RESULTS: core assumption validated.** iPhone 14 = ~200k splats stereo @ locked 60fps @ glasses res (2400×1200), thermally stable → one photoreal object (D21 range) runs realtime on phone-class HW. Laptop AMD iGPU ~350k @ glasses 60fps (beats phone). ≤200k is count-bound not fill-bound. Caveats: benchmark optimistic (no per-frame sort → real budget lower); 60Hz cap hides true edge (test 250k/300k); validate later with real renderer. (§9a)
- **D21 — Framerate = two tiers (45 rich / 60 motion); per-object counts are modest.** Stable capped framerate beats fluctuating. 45fps+max-splats (static heroes, reprojection-dependent) = stretch tier; 60fps = safe default until warp engine proven. Single AR object looks high-res at ~100–300k splats (not millions — that's scene-scale); budget = total on-screen splats. Splat size: hold fixed for count sweep (correct), do ONE size-sensitivity pass at budget count to bound fill-rate vs count-bound. (§2)
- **D19 — Hand tracking processed on PHONE, not glasses.** Two kinds of real-time: head reprojection = hard (<10ms, local/glasses); hand interaction = soft (~50ms, phone round-trip fits). Hand CV runs on phone w/ SLAM; glasses stay minimal. Budgets layer (phone = object world-pos, glasses reprojection = head-lock → no swim). Failure: bad link → object trails hand; mitigate fast link + optional on-glasses prediction. (§6b)
- **D18 — Input DECIDED: dual-mode = silent speech (stealth) + full hand motion (power).** Silent speech = discreet all-day command grammar; hand motion = spatial direct-manipulation for private use, covers objects AND general HUD. Complementary by context. RISK: silent-speech IN is least-proven tech → mitigate by prototyping stealth mode with ordinary VOICE (identical grammar, swap to EMG at HW phase); optional temple-touch backstop. Mode-switching = open sub-decision. (§6b)
- **D17 — Input/interaction was a gap; now spec'd (§6b).** Camera hand-gestures feasible but fight stealth as PRIMARY nav (conspicuous + gorilla-arm + power). Split: HUD nav = DISCREET vs hand-gestures for 3D OBJECT manipulation. *(Primary modality resolved in D18.)*
- **D16 — Architecture is CHIP-AGNOSTIC (not locked to Snapdragon).** Glasses never render (phone does) → only need display+warp+sensors. Options cheapest→turnkey: FPGA/warp-ASIC (best fit) → general ARM SoC (MediaTek/Rockchip/NXP) → dumb USB-C display (no SoC) → Snapdragon AR2 (turnkey, pricey, NDA). Phone side also any-chip (iPhone prototype, any phone production). Silicon = production-phase decision, irrelevant to current phone software. (§7)
- **D15 — Glasses-side compute scoped = split/distributed AR (= Snapdragon AR2 philosophy).** Glasses do only stream-receive + display-drive + reprojection (the "one hard job"); phone does heavy render. Target = thin-AR-co-processor tier, but it's reference-design/ODM/NDA = a months-long HW program → LAST phase. Prototype phone-only now; optional cheap feel-prototype = drive off-the-shelf Xreal/Rokid USB-C display (~$300–500) from phone. Don't spend on the glasses chip yet. (§7)
- **D14 — Software-first committed + cost claim corrected.** Path: software → iPhone prototype → hardware LAST. Phone = prototype display AND real offload compute (not throwaway). Snap's win = integration/miniaturization (single integrated lens, untethered via dual SoCs), not new optics. CORRECTION to D13: $2,200 is mostly the onboard dual SoCs, not the display; phone-offload deletes that compute → our target is the ~$800 display-glasses class, not $2,200. Derived §2a software requirements from hardware constraints. (§1, §2a, §8b)
- **D13 — Snap Specs ($2,200) = validation, not kill shot; compete on SOFTWARE not hardware.** Their "advanced display" is waveguide + electrochromic = the D12 contrast recipe (no occlusion miracle). Local rendering → 4h battery (our phone-offload = legit differentiator). ~~Adopting their display = $2,200 me-too~~ *(cost claim superseded by D14)*. Moat = agent + asset library. Strategy A (preferred): be the platform-agnostic software/content layer; Strategy B: deliberately-different stealth/agent-first/longer-battery device. (§8b)
- **D12 — Solid-looking objects via contrast, not occlusion.** True compact per-pixel occlusion is unsolved frontier optics (defocus + relay-optics bulk = why segmented dimming is bulky). Compact path = contrast-based solidity: dynamic global electrochromic dimming + high-brightness microLED/LBS + rendering tricks (shadows/opacity). Solid indoors, weaker vs bright backgrounds. Dimming mildly fights stealth → use dynamic dimming. True occlusion = research to monitor, not a dependency. (§7)
- **D11 — Environment manipulation is display-incompatible with stealth.** "Recolor walls / hide bed / replace real objects" = Diminished/Mediated Reality, needs VIDEO PASSTHROUGH (per-pixel editable). Stealth HUD is optical see-through = ADDITIVE-ONLY (adds light, can't subtract/remove/darken). So the stealth track is additive-only (add virtual objects ✅, remove/repaint real ones ❌); full redecoration = separate passthrough product (v-future fork). (§7)
- **D10 — Benchmark slice spec'd.** Stack = WEB / WebGL2 / Three.js (mkkellogg renderer), not native — one build everywhere, conservative perf floor. Scope = static cloud + rigid-body only (rigid object = one transform matrix; skeletal skinning & full AR deferred). Devices: iPhone 14 (mid) + integrated-GPU laptop (low anchor, likely weaker than the phone). Measure sustained (5min) fps vs splat-count sweep, mono then stereo → per-tier budget table. (§9a)
