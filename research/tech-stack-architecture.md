# Tech-Stack & Architecture Research Report
## Marker-Anchored AR Asset Platform (per PROJECT.md §0 / D35)

> **Author role:** technical architect. **Scope:** research + design only, no code.
> **Date:** 2026-06-25. **Source of truth:** `/home/sov2/projects/4dgs/PROJECT.md` (§0 product, §0a continuity, §0.6 components, §9c existing pipeline, §2a/D34 mesh-first).
> **Caveat (read first):** AR-platform pricing, 8th Wall's open-source terms, VPS coverage, and WebXR/iOS support are all moving fast in 2024–2026. Every rented dependency below is flagged. Treat numbers as "verified at time of writing," not contractual. This is engineering guidance, not legal advice — counsel must confirm licenses before ship.

---

## 0. The product, restated for architecture purposes

One asset → two publish **surfaces**:

| Surface | What it is | Day-one viewer | Difficulty |
|---|---|---|---|
| **Un-anchored "view in 3D"** | A turntable / "view in your room" widget on a website or print QR. No scan, no marker, no map. | Any phone browser, today | **Easy / solved** — commodity web stack |
| **Anchored marker** | A physical QR/branded-image marker by a storefront → points to an owner-seeded, cloud-hosted, re-localizable per-location map → asset welded to the real place. | Phone WebAR first; glasses = architected endgame | **Hard** — the moat and the risk |

The architectural spine that makes the hard surface tractable (§0.2): **the marker carries a pointer, not a map.** Localization goes global→local: "which of millions of world maps?" becomes "load *this* map ID." That single decision is what lets the anchored product ship shop-by-shop with no planetary mapping effort.

---

# 1. UN-ANCHORED "VIEW IN 3D" SURFACE — the web stack

This is the MVP money-maker (§0.9 step 1) and is essentially a **solved commodity**. The job: render a glTF on a turntable in-page, and on tap launch the OS-native "place in my room" AR flow. The platform fragmentation here is real and unavoidable.

## 1.1 The core viewer — choice: Google `<model-viewer>`

**Build-vs-rent:** RENT (adopt OSS). **License:** Apache-2.0 (Google). **Why:** it is the single component that already solves the three-platform AR-launch problem with one HTML tag, is built *on* three.js, and is maintained by Google. ([model-viewer docs](https://modelviewer.dev/), [Google AR developer guide](https://developers.google.com/ar/develop/webxr/model-viewer))

`<model-viewer>` dispatches to **three different AR back-ends** depending on the device — this is the load-bearing fact of the whole un-anchored surface:

| Platform | AR back-end `<model-viewer>` uses | Format consumed | How "place in room" works |
|---|---|---|---|
| **Android (Chrome)** | **WebXR** (default) *or* **Google Scene Viewer** (intent) | glTF/GLB | WebXR Hit-Test API finds a real-world plane (floor=horizontal, wall=vertical); model placed on it, stays in browser, keeps DOM/annotations. Faster (no re-download). ([Google AR guide](https://developers.google.com/ar/develop/webxr/model-viewer)) |
| **iOS (Safari)** | **Apple AR Quick Look** (`rel="ar"` link hand-off) | **USDZ** | Safari hands the USDZ to the OS AR Quick Look viewer; ARKit does the plane detection + placement. **No WebXR involved** (see §1.4). |
| **Desktop / unsupported** | In-page three.js turntable only | glTF/GLB | Orbit controls, no AR. |

**The glTF-vs-USDZ dual-format problem (real, must design for):** Android/Web want **glTF/GLB**; iOS AR Quick Look wants **USDZ**. ([Fab/Sketchfab on glTF/GLB/USDZ](https://support.fab.com/s/article/glTF-GLB-and-USDZ)) `<model-viewer>` can **auto-generate USDZ on the fly** from your GLB for Quick Look, which removes the need to author twice — but the auto-USDZ is lossy (USDZ supports **only one animation track**, fewer material extensions than glTF). ([model-viewer FAQ](https://modelviewer.dev/docs/faq.html), [model-viewer AR Quick Look notes](https://www.netguru.com/blog/ar-quick-look-and-usdz)) **Architecture decision:** for anything with animation or non-trivial materials, **pre-bake a curated USDZ per asset at publish time** (via `gltf-transform` / Apple's `usdzconvert` / RealityKit tooling) and store it as a quality-tier sibling of the GLB, rather than trusting the on-the-fly conversion. Treat auto-USDZ as the fallback only.

## 1.2 Why `<model-viewer>` over the alternatives (each evaluated)

- **Raw three.js** — RENT, MIT. Use it *under* `<model-viewer>` (which is three.js) and for the **authoring editor's** custom canvas, but **not** as the embedded viewer: you'd reimplement Scene-Viewer/Quick-Look hand-off and USDZ generation by hand. ([three.js](https://threejs.org))
- **WebXR Hit-Test API** — the W3C standard `<model-viewer>` already uses internally on Android for surface placement. We consume it *through* model-viewer, not directly, for the un-anchored surface. Direct use is reserved for the anchored surface (§2).
- **Google Scene Viewer (Android) + Apple AR Quick Look (iOS)** — the OS-native AR viewers. We don't build on them directly; `<model-viewer>` brokers both. They are *why* the dual glTF/USDZ format exists. ([Scene Viewer + iOS discussion](https://github.com/google/model-viewer/discussions/2042))
- **8th Wall WebAR (surface/world tracking)** — RENT engine, now **hosted service retired Feb 2026** (see §2.2). For the *un-anchored* surface its world-tracking is overkill: AR Quick Look + WebXR Hit-Test give "place on surface" for free, on more devices, with no SDK. Reserve 8th Wall's engine for the anchored surface where we need continuous SLAM in-browser.
- **AR.js** — RENT, MIT. Lightweight, marker/location-based; tracking quality is weak (it's a 2017-era library). Fine as a zero-cost fallback, not the primary. ([AR frameworks comparison](https://thespatialstudio.de/en/blog/ar-frameworks-in-comparison))
- **MindAR** — RENT, MIT, free, self-hosted JS. Strong for **image-target** tracking (relevant to §2a), rated ~5/10 vs 8th Wall's 8/10 for tracking robustness. Good zero-cost option for the *marker-image* tracking layer. ([MindAR target guide](https://www.mindar.org/how-to-choose-a-good-target-image-for-tracking-in-ar-part-1/), [comparison](https://overlyapp.com/blog/best-web-based-augmented-reality-platforms-to-try-in-2025/))
- **Zappar / Zapworks** — RENT, commercial SaaS, no-code, image/world/face tracking ~7/10, has an embed tool. A competitor more than a dependency; relevant as a feature-bar benchmark for our authoring UX. ([Zapworks comparison](https://www.hololink.io/blog-posts-hololink/choosing-the-right-webar-editor))

## 1.3 Delivery — embed / iframe / shareable link / print QR

All four delivery modes are trivial once the asset is a `<model-viewer>` on a CDN-hosted page:
- **Embed/iframe:** a hosted viewer page per asset (`viewer.ourapp.com/a/{assetId}`); customers paste an `<iframe>` or a `<script>` web-component snippet.
- **Shareable link:** the same URL, opened directly → full-screen viewer with an "AR" button.
- **Print QR:** a QR encoding that same URL → un-anchored placement on phone. (Note: this QR is just a link to the viewer, **not** the anchored marker of §2 — different role, same primitive.)

## 1.4 The iOS WebXR gap (affects everything web-AR)

**Critical, verified, fast-moving:** **Safari on iPhone/iPad does NOT support the WebXR Device API** (through at least iOS 17, still true in 2025–2026). visionOS 2 Safari supports `immersive-vr` only — **not** `immersive-ar`. ([Variant Launch: state of WebXR on iOS](https://launch.variant3d.com/blog/23-06-state-webxr-on-ios-beyond), [MDN WebXR](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API)) Consequence:
- **Un-anchored on iOS works anyway** because it uses **AR Quick Look (native ARKit), not WebXR.** This is why the un-anchored surface is safe on day one.
- **Anchored on iOS is the problem** — there's no native browser API for continuous SLAM + custom map relocalization. Workarounds: **8th Wall engine / Variant Launch / Zappar** ship their **own SLAM in WASM** to fake WebXR on iOS. This is the crux of the web-vs-native decision (§6).

## 1.5 Hosting / CDN / compression

| Concern | Choice | Build/Rent | License | Why |
|---|---|---|---|---|
| Mesh geometry compression | **Draco** | RENT | Apache-2.0 | 60–90% vertex reduction; native in glTF + model-viewer. ([compression overview](https://www.axl-devhub.me/en/blog/optimizing-3d-models)) |
| Mesh compression (alt) | **meshoptimizer / EXT_meshopt** | RENT | MIT | Similar ratio, **much faster decode**; better for many small assets. ([three.js forum](https://discourse.threejs.org/t/compression-draco-ktx2-example/31382)) |
| Texture compression | **KTX2 / Basis Universal** | RENT | Apache-2.0 | GPU-native, 4–8× less GPU memory than PNG/JPEG; essential on weak phones (§0.6 quality tiers). |
| Asset pipeline tooling | **gltf-transform** | RENT | MIT | One tool to Draco/meshopt/KTX2-optimize, generate LOD tiers, and convert to USDZ at publish. |
| Decoder hosting | model-viewer's lazy decoder modules (jsDelivr/unpkg) or self-host | — | — | Decoders load by URL from CDN; self-host for reliability/SLA. |
| Asset CDN | **Cloudflare R2 + CDN** (or CloudFront over S3) | RENT | commercial | R2 has **zero egress fees** — decisive for serving many MB of 3D to many viewers (§4). |

> Mesh-first (D34): all of the above is tuned for **glTF meshes**, the baseline render path. Static splats are a hero tier handled separately (§3.3 / §4).

---

# 2. ANCHORED MARKER SURFACE — the hard path

This is the differentiator and the primary technical risk (§0.7). Break it into six sub-problems.

## 2.1 (a) Marker tech — QR vs image-target tracking

Two distinct jobs the marker can do (PROJECT.md §0.3 separates **Identity** from **Pose**):

| Marker type | Gives Identity? | Gives initial Pose? | Library | License | Notes |
|---|---|---|---|---|---|
| **QR code** | ✅ (encodes URL/ID) | ⚠️ weak — a QR *can* give a rough pose from its 4 corners + known physical size, but it's small, so pose is noisy at distance | `jsQR` / `zxing-js` (decode) | Apache-2.0 / MIT | Cheapest, universal, printable anywhere. Best at **identity**, mediocre at durable pose. |
| **Branded image target** (logo/sign as trackable) | ✅ (target ID → record) | ✅ better — larger, textured, continuous 6DoF tracking while in view | **MindAR** (free), **8th Wall Image Targets** (MIT, open-sourced Feb 2026), **Zappar** | MIT / commercial | Prettier (doubles as branding, §0.5), better continuous pose, but needs a feature-rich image; tracking ~5–8/10. ([8th Wall image targets](https://www.8thwall.com/docs/guides/image-targets/), [comparison](https://overlyapp.com/blog/best-web-based-augmented-reality-platforms-to-try-in-2025/)) |

**Recommendation:** support **both**, but architect around **QR-for-identity + map-for-pose**. The marker's job is to reliably answer "which map + which asset"; durable pose past the marker is the **map's** job (§0.3), not the marker's. Branded image targets are an upsell aesthetic + a *better* initial pose lock, not the pose system of record. **8th Wall Image Targets is now MIT-licensed open source** — adopt it as the image-target engine where image markers are used. ([8thwall.org open-source](https://8thwall.org/docs/open-source))

## 2.2 (b) Marker → cloud-pointer resolution

Pure application logic, fully BUILD:
```
marker (QR text / image-target ID)  →  GET /resolve/{markerId}
                                    →  { mapId, assetId, anchorPose, gps, permissionScope }
```
This is the **Marker Service** (§4). The marker holds only a short opaque ID/URL; the multi-MB map and asset live in the cloud, fetched on demand. This indirection is the entire reason the product scales shop-by-shop (§0.2).

## 2.3 (c) The per-location re-localizable MAP service — **the key build-vs-rent decision**

This is where the product lives or dies. Options:

### RENT options (third-party VPS)
| Service | Status (2026) | Accuracy | Pricing (verified) | License/terms | Verdict |
|---|---|---|---|---|---|
| **Niantic Spatial VPS** (post-spinoff) | ⚠️ **Niantic sold gaming to Scopley for $3.85B; "Niantic Spatial" is now an independent spin-off.** 8th Wall hosted VPS **goes offline Feb 2027.** New VPS lives under Niantic Spatial / Scaniverse. | cm-level, ~1M locations | Free tier ~20k credits/mo; **VPS = 12 credits/query**; top-ups ~$1/1,800 credits; Pro $50/mo adds commercial rights. ([Niantic Spatial pricing](https://www.nianticspatial.com/pricing), [VPS product](https://www.nianticspatial.com/products/visual-positioning-system)) | Commercial tier required; **owner-seeded mapping not the core model** (their maps are their asset) | **Risky dependency** — org just restructured, the product we'd lean on (8th Wall VPS) is being killed. Avoid as the spine. |
| **Google ARCore Geospatial API** | Stable, Google-backed | Geospatial (lat/lng/alt + heading) via Google's VPS, anchored to **Street View** coverage | **Free** to use the API; quota 100k req/min. ([Geospatial API](https://developers.google.com/ar/develop/geospatial), [quota](https://developers.google.com/ar/develop/c/geospatial/api-usage-quota)) | Free, but **coverage = where Google has Street View** (great in cities, absent indoors / many storefronts) and **ARCore = Android-native, no iOS-Safari path** | **Best free RENT where coverage exists**; not owner-seedable; weak indoors. Good MVP shortcut in dense districts. |
| **ARCore Cloud Anchors** | Stable (persistent anchors 1–365 days) | Local shared-anchor, not city-scale | Per-anchor resolve; modest. ([Cloud Anchors](https://developers.google.com/ar/develop/cloud-anchors)) | Android-native + cross-platform SDK; **anchors expire (max 365d)** | Owner-seeds a small local anchor → closest off-the-shelf match to our model, **but expiry + Android-native + no occlusion mesh** limit it. |
| **Immersal** | Active commercial VPS | cm-level | Free = non-commercial + watermark, ≤100 imgs/map; Pro = 500 imgs/map; Enterprise = unlimited + **on-prem deployment + REST API for web**. ([Immersal pricing](https://immersal.com/pricing), [docs](https://developers.immersal.com/docs/immersal-sdk/pricing/)) | Commercial license needed; **owner-seeded mapping IS their model** (you map your own space) | **Closest commercial fit to owner-seeded** — REST API + private/on-prem is exactly our shape. Strong RENT candidate for MVP. |
| **Azure Spatial Anchors** | ❌ **RETIRED 20 Nov 2024.** | — | — | — | **Dead. Do not use.** Microsoft named no official replacement. ([ASA retirement](https://azure.microsoft.com/en-us/updates?id=azure-spatial-anchors-retirement), [Q&A](https://learn.microsoft.com/en-us/answers/questions/1433376/)) |
| **MultiSet AI** | Active (markets itself as the ASA replacement) | ~6 cm median indoors, private deploy, scan-agnostic | Contact sales | Commercial; private deployment | Emerging RENT alt worth piloting; less proven. ([MultiSet](https://www.multiset.ai/post/azure-spatial-anchors-alternative)) |

### BUILD option (own the map = the moat)
The defensible piece PROJECT.md §0.9 explicitly wants to own. Pipeline:
- **Capture:** guided phone scan (LiDAR on Pro iPhones strengthens it; plain camera works but lighting-sensitive, §0.4).
- **Mapping:** **COLMAP** (SfM/bundle adjustment, BSD-licensed) → sparse/dense reconstruction in a stable, GPS-tagged coordinate frame.
- **Relocalization:** **hloc (Hierarchical-Localization, cvg)** — image retrieval (NetVLAD/MegaLoc) for coarse place recognition → local feature matching (**SuperPoint + LightGlue/SuperGlue**) → PnP for cm-accurate 6DoF query pose against the stored map. ([hloc](https://github.com/cvg/Hierarchical-Localization)) **License caution:** hloc itself is permissive, but **SuperPoint + SuperGlue weights are Magic Leap research/NON-COMMERCIAL** — must swap to commercially-clean matchers (DISK, R2D2, LightGlue with permissive weights, or train own) before ship. This is a §4a-style landmine.
- **What "build" entails (honest):** a GPU mapping cluster (the RTX 5090 §8c serves the *generation* pipeline; mapping needs its own scaled compute), a robust server-side BA pipeline, a relocalization service exposed via REST, **and** the §0.7 robustness work (multi-condition capture, ongoing re-capture from every marker scan as a fresh mapping sample). This is months of real engineering, but **bounded** (per-location, not planetary).

### **Recommendation on the map (the headline build-vs-rent call):**
- **MVP:** **RENT Immersal** (REST API + owner-seeded mapping + private deploy matches our model best of the rented options) **OR** ship the **marker-pointer + minimal own-map** path in dense districts. Use **ARCore Geospatial (free)** only as an Android-where-Street-View-exists accelerator.
- **Strategic:** **BUILD the owner-seeded per-location map** (COLMAP + hloc with commercially-clean matchers) as the moat — this is the one component that should NOT stay rented, because it *is* the defensible product (§0.9). Rent to ship, build to own. Sequence the build behind un-anchored revenue.

## 2.4 (d) On-device SLAM / persistence — and the WebXR gap

Persistence past the marker (§0.3 "Pose") needs continuous on-device tracking:
- **Android:** ARCore (native) or WebXR (Chrome) — both expose plane detection, anchors, **depth API**.
- **iOS:** **ARKit (native)** — full SLAM, LiDAR depth, world anchors. **Safari/WebXR cannot reach any of it** (§1.4).
- **WebXR reality:** the **anchors module, depth-sensing module, and hit-test** exist in the spec and work on Android Chrome + Quest Browser, but are **inconsistently supported and absent on iOS Safari.** ([WebXR depth-sensing](https://www.w3.org/TR/webxr-depth-sensing-1/), [WebXR browser support 2026](https://www.testmuai.com/learning-hub/webxr-compatible-browsers/)) **WebXR does NOT expose enough for custom-map relocalization** on its own — it gives you tracking and anchors *within a session*, not "localize my camera against a multi-MB cloud map I uploaded." That logic must run in your own WASM SLAM (8th Wall engine) or a native app.
- **Gap verdict:** marker + map relocalization + durable persistence **forces either (a) a WASM SLAM engine (8th Wall's now-MIT engine binary)** running custom relocalization in-page, **or (b) a native app** (ARKit/ARCore). Vanilla WebXR alone is insufficient for the anchored surface, especially on iOS. → §6.

## 2.5 (e) Coordinate-frame sharing between owner & viewer

The map defines **one shared coordinate frame**. Owner places the asset → pose stored **in map frame** (§0.4 anchor record). Viewer localizes camera into the *same* map frame → renders the asset at the stored pose. Both sides agree because both reference the same bundle-adjusted map origin. This is exactly what a VPS/relocalization service provides; it's the reason the map is stored **once per location, shared by every asset and viewer** there (§0.4). Coarse GPS is stored for indexing/pre-fetch only, not for pose.

## 2.6 (f) Occlusion / depth

For an asset to be hidden by a real wall (§0.8), the renderer needs real-world depth:
- **Runtime depth:** WebXR Depth API / ARKit/ARCore Depth (LiDAR where present) → per-frame depth buffer → occlude virtual fragments behind real geometry. Available natively; in WebXR only on supported Android.
- **Map-baked depth:** the per-location map should carry a **depth/occluder mesh** (from COLMAP dense reconstruction or LiDAR scan) so occlusion is correct even where runtime depth is weak. PROJECT.md §0.8 makes this a **day-one data-model requirement** — the map stores enough 3D geometry to occlude.
- **LiDAR vs photogrammetry:** LiDAR (Pro iPhones) = instant, metric, robust depth → best occluder mesh + scale. Photogrammetry (COLMAP) = works on any camera but lighting-sensitive and scale-ambiguous without a reference. **Guided capture should prefer LiDAR when available, fall back to photogrammetry** (§0.4).

---

# 3. AUTHORING WEB APP — no-code editor + the existing TRELLIS/UniRig backend

## 3.1 The existing pipeline (PROJECT.md §9c) — verified, real, repurposed

Confirmed in `/home/sov2/projects/4dgs/generation/`:
- **`server.py`** — Flask app; **TRELLIS loaded once resident (~40s)** then fast per-gen; routes `/generate`, `/status/<job>`, `/out/<path>`, `/library*`, `/studio*`.
- **Pipeline (`pipeline()` in server.py):** `image(s) → TRELLIS (mesh + splat) → clean_mesh → UniRig skeleton → UniRig skin`. TRELLIS runs in its own env; **UniRig stages run as subprocesses in `unirig-venv` (Python 3.11 for `bpy`)** while TRELLIS needs its own env — a multi-venv subprocess architecture already solved.
- **`bind_splat.py`** — transfers nearest-vertex skin weights into the mesh frame so splats animate with the skeleton (D28/D29); ICP/Umeyama refine for splat↔mesh alignment.
- **`studio.html` / `library.html`** — browser studio (mesh-first defaults, splat hero layer) + CLIP-embedding library/dedup/search (D32).
- **Hardware:** runs locally on **RTX 5090, 32GB VRAM** (§8c) — no cloud GPU needed to start.

**This is the authoring image-to-3D backend.** Under D35 it stops serving "glasses summoning" and starts serving "a business uploads a product photo → gets a riggable glTF asset." Zero re-architecture needed; it already emits mesh + optional splat + rig + library record.

## 3.2 How it plugs into the no-code editor

```
[No-code Authoring Web App]
  ├─ 2D canvas / drawing tool  ──┐
  ├─ Product-image upload      ──┤→ POST /generate (existing Flask) → job → TRELLIS→UniRig→bind
  ├─ Template picker           ──┘                                   → glTF + (optional static splat) + rig
  ├─ Animation builder (keyframe/timeline, no JS)  → animation tracks baked into glTF
  ├─ Interaction triggers (tap/proximity) → metadata on asset record
  └─ Marker designer (style QR / register branded image target)
```
- **2D canvas / product-image pipelines (§0.5):** the canvas tool produces a flat graphic → presented as a 3D card/extrusion (no generation needed, cheapest path) **or** routed through TRELLIS for true image-to-3D. The product-image path is the TRELLIS path directly. These two are the MVP pipelines (§0.10).
- **Animation builder:** a timeline UI emits standard glTF animation tracks (driving the UniRig skeleton) — no per-asset training, plays back free at runtime (§3 Latency reality: generation is offline, playback is cheap).
- **Editor canvas tech:** **three.js** (MIT) for the in-browser 3D editing canvas; `<model-viewer>` for preview-as-published. React/Next.js front end.
- **Quality tiers (§0.6):** at publish, `gltf-transform` auto-produces Draco/meshopt/KTX2 LOD tiers + the curated USDZ, so weak devices keep frame rate.

## 3.3 Splat handling (mesh-first, D34)

Per D34/§0.5: **mesh-first is the baseline; static splats are a premium hero layer.** The existing pipeline already emits both; the authoring tool defaults to mesh, offers static-splat capture as an upsell. **Animated splats stay deferred** (D33 demoted to "static splatting for hero assets" — expensive/fragile). Render guidance (additive-display-safe, central-FOV-safe layout, ≥2 LOD tiers) is baked into the authoring defaults (§0.6).

---

# 4. BACKEND SERVICES

| Service | Responsibility | Concrete tech | Build/Rent | Why |
|---|---|---|---|---|
| **Asset store** | Versioned assets, quality tiers (GLB + USDZ + optional static splat + animations + interactions) | **Object storage: Cloudflare R2** (or S3); metadata in Postgres | RENT infra / BUILD logic | R2 = **zero egress** (serving MB-scale 3D to many viewers); versioning + tier variants as object keys. |
| **Anchor registry** | Lightweight records: `{anchor pose in map frame, asset ref, map ID, coarse GPS, owner, permission scope, spatial claim}` (§0.4, §0.8) | **PostgreSQL + PostGIS** | BUILD | PostGIS gives GPS spatial indexing ("anchors near me", spatial-claim overlap detection for governance/anti-spam §0.8) in one DB. |
| **Map service** | Ingest owner scans → re-localizable per-location maps; serve relocalization queries; store occluder mesh | **COLMAP + hloc** (build) **or Immersal REST** (rent), maps in R2/S3, indexed by GPS + marker ID | RENT→BUILD | The moat (§2.3). Rent to ship, build to own. |
| **Marker service** | Mint/style markers (QR via `qrcode`/`zxing`; image targets via MindAR/8th Wall compiler); resolve marker → {mapId, assetId} | Stateless API + a marker-asset store | BUILD | Pure app logic (§2.2); cheap. |
| **Viewer runtime** | On phone/glasses: read marker → fetch map+asset → localize → render → SLAM persistence → device projection | `<model-viewer>` (un-anchored) + 8th Wall MIT engine / WASM SLAM (anchored web) + native ARKit/ARCore (anchored app, later) | RENT+BUILD | Surface-specific (see §6). |
| **API layer** | Auth, asset CRUD, generation jobs, anchor CRUD, billing, moderation/permission model (§0.8) | **Node/TypeScript (NestJS) or Python (FastAPI)** REST; existing **Flask** generation backend behind it as an internal job service | BUILD | FastAPI keeps language-parity with the Python generation stack; Flask `/generate` becomes an internal worker. |
| **Job queue / GPU workers** | TRELLIS/UniRig generation jobs; COLMAP/hloc mapping jobs | **Celery/RQ + Redis**, GPU workers (RTX 5090 now → scale to cloud GPU) | BUILD | Generation + mapping are offline/async (Latency A, §3); never on the request path. |
| **Delivery / CDN** | Compress + stream assets & maps | **Cloudflare R2 + CDN**, Draco/meshopt/KTX2, model-viewer lazy decoders | RENT | §1.5. |
| **Auth / billing** | Per-seat / per-asset (un-anchored) + per-location subscription (anchored) (§0.9 pricing) | **Auth0/Clerk + Stripe** | RENT | Standard SaaS; don't build. |

---

# 5. THE VR / GLASSES QUESTION ("how do we connect it to VR / how does VR render it?")

This is the architected endgame (§0.9 step 4), not the launch surface. The answer is a **discipline**, not a port.

## 5.1 WebXR vs OpenXR
- **WebXR** = the browser API (Android Chrome, Quest Browser, **not iOS Safari**). It's how the *phone web* surface reaches AR today.
- **OpenXR** = the native cross-vendor runtime standard (Khronos) that AR/VR glasses (Quest, future see-through glasses, Snap/Meta-class) expose to native apps. ([WebXR standards/future](https://daggerinteractive.co.uk/blog/2025-12-05/webxr-standards-future-proofing-your-ar-vr-investment))
- **Bridge:** WebXR is essentially "OpenXR for the web." An asset described correctly for one is described correctly for the other, **because we describe assets in world units, not pixels** (next).

## 5.2 Describe assets in world units (meters) — the key idea
PROJECT.md §0.6 / §2a is explicit and correct: **don't render to a display size — describe the asset in meters and let each device's WebXR/OpenXR runtime handle FOV / resolution / lens / IPD / reprojection.** A 1.5 m sign is 1.5 m on a phone screen, on a Quest, and on future see-through glasses. The runtime owns the projection math. Our job is **budget/design discipline**, not per-device rendering code. This is what makes "build for phone now, run on glasses later" a real architectural path rather than a rewrite.

## 5.3 What runs where (carries §2 3-tier split / D15 / D19)
```
[ CLOUD ]   offline generation (TRELLIS/UniRig) + map building (COLMAP/hloc).  One-time (Latency A).
[ PHONE ]   SLAM, relocalization-against-map, asset render, physics, lighting.  Per-frame (Latency B).
[ GLASSES ] DISPLAY + late-stage reprojection / timewarp ONLY.  <10ms motion-to-photon, must stay local.
```
- **Reprojection/timewarp stays on glasses (D15/D19):** warping the last rendered frame to the freshest head pose must happen at the very end of the chain, on-device; if the phone did it, the result re-incurs the link latency the warp exists to hide (§7/§2a). A dropped/late AR frame reads as **nausea** — non-negotiable.
- **Phone-as-offload-compute:** the heavy render runs on the phone (the §8c device today; a paired phone for glasses tomorrow). Glasses stay a thin display+warp accessory. This is the same Snapdragon-AR2-class split PROJECT.md §7 already commits to.

## 5.4 Cross-device LOD / quality tiers
Same `≥2 quality tiers` from §0.6/§0.10: weak HW (or narrow-FOV glasses) picks the cheaper LOD tier (mesh-only, fewer splats) and **never drops a frame**; strong HW unlocks the hero static-splat tier. Tiers are precomputed offline (decimation, not regeneration — D9/D10) and selected at runtime by device capability.

## 5.5 Additive-display constraints (§2a)
See-through glasses **add light, can't subtract** → can't render black, can't truly occlude with the display. Design rule baked into authoring: **bright, saturated, high-contrast assets; contact shadows/AO for "it's really there"; central-FOV-safe layout for narrow (~50°) FOV.** These constraints are encoded in the authoring tool's defaults now so today's phone assets are *already* glasses-safe.

## 5.6 Concrete path: phone WebAR → glasses viewer
1. **Today:** un-anchored via `<model-viewer>` (WebXR/Quick Look); anchored via WASM-SLAM web or native app. World-units + tiers + additive-safe design already applied.
2. **Bridge:** same asset records, same map service, same world-unit poses; swap the *viewer runtime* from phone-web to a phone-paired-glasses native app speaking **OpenXR**, reusing the same backend untouched.
3. **Endgame:** glasses do display+warp, phone does render+SLAM+relocalize against our map. No asset re-authoring — the meters-not-pixels discipline pays off here.

---

# 6. THE BIG DECISION — web app vs native phone app (per surface)

## 6.1 Un-anchored surface → **WEB. Unambiguous.**
`<model-viewer>` + AR Quick Look (iOS) + Scene Viewer/WebXR (Android) deliver "view in 3D" and "place in my room" on **billions of phones with no app install** (§0.9). iOS works *because* it uses native AR Quick Look, sidestepping the iOS-WebXR gap entirely (§1.4). **No native app. Ship web.**

## 6.2 Anchored surface → **the hard call**
Can WebAR (WebXR) deliver marker + map relocalization + persistence + occlusion?
- **Vanilla WebXR: NO.** It gives in-session tracking/anchors/hit-test on Android, **nothing on iOS Safari**, and **no path to localize against a custom multi-MB cloud map** (§2.4). Depth/occlusion modules are inconsistent and iOS-absent (§2.6).
- **WASM-SLAM web (8th Wall MIT engine / Variant Launch): PARTIALLY YES.** These ship their own SLAM + image-target tracking in-browser, working on **both** iOS and Android with no install. The newly **MIT-open-sourced 8th Wall engine + image targets** (Feb 2026) make this viable and license-clean for commercial use; **the engine binary (SLAM) is binary-only but permits commercial use**, while VPS/Maps were NOT open-sourced (which is exactly why we build the map ourselves). ([8thwall.org open source](https://8thwall.org/docs/open-source), [Road to VR](https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/)) This can do marker-tracking + our own relocalization-against-map (via REST to our map service) + decent persistence — **but occlusion quality and durable multi-user persistence are weaker than native.**
- **Native (ARKit/ARCore): FULL YES.** Best SLAM, LiDAR depth/occlusion, durable world anchors — but costs the install, kills the "scan-and-go" funnel, and doubles platform work.

## 6.3 Recommendation + phased path
- **MVP (web-first, glasses-architected):**
  - Un-anchored: **`<model-viewer>` web** (ships now).
  - Anchored: **WebAR on the MIT-licensed 8th Wall engine** (image-target / QR marker → resolve pointer → fetch our map+asset → relocalize via our map-service REST → render), accepting weaker occlusion/persistence as a known v1 limit. Marker-only local pose is the graceful fallback when the map can't lock (§0.7). This keeps the **no-install funnel** intact on both iOS and Android.
- **Phase two (native where it pays):** a **native ARKit/ARCore app** for premium anchored experiences needing LiDAR occlusion + durable multi-user persistence (and as the bridge toward the OpenXR glasses viewer, §5.6). Offer it as an upsell, not a gate.
- **Verdict in one line:** **Un-anchored = web, forever. Anchored = web (WASM-SLAM) for MVP to preserve the no-install funnel; native is a phase-two premium tier and the glasses on-ramp — not an MVP requirement.**

---

# 7. TEXT ARCHITECTURE DIAGRAMS

## 7.1 Un-anchored "view in 3D" surface
```
                         ┌──────────────────────── AUTHORING (offline) ────────────────────────┐
                         │  Product photo / 2D canvas / template                                │
                         │        │                                                             │
                         │        ▼                                                             │
                         │  Flask /generate ─► TRELLIS (mesh+splat) ─► clean_mesh ─► UniRig rig │
                         │        │                                                             │
                         │        ▼   gltf-transform: Draco/meshopt/KTX2 LOD tiers + USDZ bake  │
                         │  Asset store (R2) ◄── versioned GLB + USDZ + static-splat tier        │
                         └──────────────────────────────────────────────────────────────────────┘
                                          │  (publish: embed / link / print-QR)
                                          ▼
   ┌───────────────────────────── VIEWER PAGE (CDN) ─────────────────────────────┐
   │   <model-viewer src=GLB  ios-src=USDZ>   (Apache-2.0, three.js under it)     │
   └───────────────┬───────────────────────────┬──────────────────┬─────────────┘
                   │ Android                    │ iOS              │ Desktop
                   ▼                            ▼                  ▼
         WebXR Hit-Test / Scene Viewer    AR Quick Look      three.js turntable
         (place on floor/wall, GLB)       (ARKit, USDZ)       (orbit, no AR)
```

## 7.2 Anchored marker surface
```
  ┌──────────────────────── OWNER (publish, offline) ─────────────────────────┐
  │ guided phone scan (LiDAR>camera) ─► MAP SERVICE                            │
  │     COLMAP (SfM/BA)  +  hloc relocalization  [BUILD = moat]                │
  │     (or RENT Immersal REST)  ─► per-location map (GPS-indexed) + occluder  │
  │ place asset in map frame ─► ANCHOR REGISTRY (Postgres+PostGIS):            │
  │     {pose@mapframe, assetRef, mapId, gps, owner, permission, spatialClaim} │
  │ MARKER SERVICE mints QR / branded image-target ──► print & hang            │
  └───────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼   (passerby scans marker)
  ┌──────────────────────────── VIEWER (phone, MVP) ──────────────────────────┐
  │ read marker ─► /resolve/{id} ─► {mapId, assetId, pose}                     │
  │      │                                                                     │
  │      ▼  fetch map + asset (R2/CDN)                                         │
  │ WASM-SLAM (8th Wall MIT engine)  ─► localize camera vs map  (shared frame) │
  │      │  cm-accurate pose          (vanilla WebXR CANNOT do this; iOS=no XR)│
  │      ▼                                                                     │
  │ render asset @ stored pose, welded to storefront                          │
  │  + occlude via map occluder mesh / depth   + marker-leaves-view ► SLAM     │
  │    carries anchor ► re-acquire ► map re-locks   (fallback: marker-only)    │
  └───────────────────────────────────────────────────────────────────────────┘
                                   │  (phase two / endgame)
                                   ▼
  ┌──────────────────────── GLASSES VIEWER (OpenXR, later) ───────────────────┐
  │ PHONE: render + SLAM + relocalize-vs-map (world units, meters)            │
  │ GLASSES: display + late-stage reprojection/timewarp ONLY (<10ms, local)   │
  │ assets additive-safe, central-FOV-safe, ≥2 LOD tiers — already authored   │
  └───────────────────────────────────────────────────────────────────────────┘
```

---

# 8. CONSOLIDATED BILL OF COMPONENTS — "tech stack = X + Y + Z"

**Tech stack =**
**Authoring** (React/Next + three.js [MIT] editor + existing **Flask + TRELLIS [MIT] + UniRig [MIT] + bind_splat** generation backend on RTX 5090; `gltf-transform` [MIT] tiering/USDZ bake)
**+ Un-anchored viewer** (Google **`<model-viewer>`** [Apache-2.0] → WebXR Hit-Test / Scene Viewer on Android, **AR Quick Look** on iOS via baked **USDZ**; three.js fallback)
**+ Anchored viewer** (MVP: **8th Wall MIT open-source engine** [MIT + binary-only SLAM, commercial-OK] for WASM SLAM + **Image Targets**; **QR** [zxing/jsQR] for identity; phase-two **native ARKit/ARCore**)
**+ Map / relocalization** (MVP RENT **Immersal** REST [commercial] or **ARCore Geospatial** [free, Street-View coverage]; STRATEGIC BUILD **COLMAP** [BSD] + **hloc** [permissive — but swap SuperPoint/SuperGlue NC weights for clean matchers] = the moat)
**+ Compression/CDN** (**Draco** [Apache] + **meshoptimizer** [MIT] + **KTX2/Basis** [Apache] over **Cloudflare R2 + CDN** [zero-egress])
**+ Backend** (**PostgreSQL + PostGIS** anchor registry/spatial claims; **FastAPI** API; **Celery/Redis** GPU job queue; **Auth0/Clerk + Stripe** [commercial])
**+ Glasses endgame** (**OpenXR** native viewer; world-units-in-meters discipline; phone renders, glasses reproject — no asset re-authoring).

**Explicitly DEAD / AVOID:** Azure Spatial Anchors (retired Nov 2024); Niantic/8th Wall **hosted VPS** (offline Feb 2027 — engine open-sourced but VPS/Maps/Hand-tracking were not); SuperPoint/SuperGlue NC weights in any shipped map pipeline; original Inria 3DGS rasterizer (NC, per §4a) for any splat tier.

**Biggest technical risk (carries §0.7):** **relocalization robustness across lighting/season/occlusion/device** — a one-pass owner scan often won't re-lock. Mitigations are architectural: guided multi-condition capture, **every marker scan = a fresh ground-truthed re-mapping sample**, map-baked occluder mesh, and graceful marker-only-local-pose fallback. This is the one place to invest deep engineering, and the reason the **map should be built, not rented**, long-term.

---

## Sources
- model-viewer: https://modelviewer.dev/ · https://modelviewer.dev/docs/faq.html · https://developers.google.com/ar/develop/webxr/model-viewer
- glTF/USDZ dual format: https://support.fab.com/s/article/glTF-GLB-and-USDZ · https://www.netguru.com/blog/ar-quick-look-and-usdz · https://github.com/google/model-viewer/discussions/2042
- Compression/CDN: https://www.axl-devhub.me/en/blog/optimizing-3d-models · https://discourse.threejs.org/t/compression-draco-ktx2-example/31382
- WebXR support / iOS gap: https://launch.variant3d.com/blog/23-06-state-webxr-on-ios-beyond · https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API · https://www.w3.org/TR/webxr-depth-sensing-1/ · https://www.testmuai.com/learning-hub/webxr-compatible-browsers/
- 8th Wall open source: https://8thwall.org/docs/open-source · https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/ · https://www.8thwall.com/docs/guides/image-targets/
- Niantic Spatial VPS: https://www.nianticspatial.com/pricing · https://www.nianticspatial.com/products/visual-positioning-system
- ARCore Geospatial / Cloud Anchors: https://developers.google.com/ar/develop/geospatial · https://developers.google.com/ar/develop/cloud-anchors · https://developers.google.com/ar/develop/c/geospatial/api-usage-quota
- Immersal: https://immersal.com/pricing · https://developers.immersal.com/docs/immersal-sdk/pricing/
- Azure Spatial Anchors retirement: https://azure.microsoft.com/en-us/updates?id=azure-spatial-anchors-retirement · https://learn.microsoft.com/en-us/answers/questions/1433376/
- MultiSet (ASA alternative): https://www.multiset.ai/post/azure-spatial-anchors-alternative
- hloc / COLMAP: https://github.com/cvg/Hierarchical-Localization
- WebAR platform comparison: https://overlyapp.com/blog/best-web-based-augmented-reality-platforms-to-try-in-2025/ · https://www.hololink.io/blog-posts-hololink/choosing-the-right-webar-editor · https://thespatialstudio.de/en/blog/ar-frameworks-in-comparison
- MindAR: https://www.mindar.org/how-to-choose-a-good-target-image-for-tracking-in-ar-part-1/
- WebXR/OpenXR future: https://daggerinteractive.co.uk/blog/2025-12-05/webxr-standards-future-proofing-your-ar-vr-investment
