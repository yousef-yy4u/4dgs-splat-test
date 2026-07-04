# IMPLEMENTATION_PLAN.md — Marker-Anchored AR Asset Platform

> **Companion to [PROJECT.md](PROJECT.md) §0 (the SSOT).** This is the phased build plan for the D35 platform. Sequencing follows the GTM bet (PROJECT.md §0.9) and the corrected stack (D38/D39). Keep it current under the same maintenance rule.
> **Last updated:** 2026-06-27 (D42 — Phase 1 reprioritized to deepen the no-code authoring/generation studio first; revenue/delivery plumbing recorded + deferred). Initial plan: 2026-06-25 (D40).
> **Assumptions (state-and-correct):** small/solo team; **revenue-first** (ship the surface that pays NOW); phone is the day-one viewer; glasses are deferred. If the team/resourcing or the "ship-fastest-to-revenue" priority is wrong, the phase ordering changes — flag it.

---

## 0. Guiding principles (decide ties with these)
1. **Un-anchored ships first and pays first.** It works on every phone today and has real e-commerce ROI independent of any AR user base (PROJECT.md §0.9, D37). It funds everything else.
2. **Don't build the moat before the wedge.** The owner-seeded map is the long-term defensibility, but it's Phase 3–4 — rent localization to get there (D39).
3. **Reuse what already works.** `generation/server.py` (TRELLIS-resident + UniRig + `bind_splat`, RTX 5090) becomes the authoring image→3D backend essentially unchanged (D39, PROJECT.md §9c).
4. **Mesh-first; static splats are a hero tier; animated splats stay deferred** (D34).
5. **Governance is a data-model decision, not a feature** — owner / permission scope / spatial claim exist in the schema from the first anchored row (PROJECT.md §0.8).
6. **Licensing hygiene is a release gate** — every model/library/weight cleared before ship (§4a + the new D38/D39 traps).
7. **No 8th Wall binary at the core** (D38: revocable, anti-compete clause aimed at our shape). Keep any AR-SLAM dependency abstracted behind our own interface so it's swappable.

---

## 1. Two surfaces, one asset (architecture at a glance)
Full component design + diagrams: [research/tech-stack-architecture.md](research/tech-stack-architecture.md).

- **One asset, two delivery paths.** Author once → store a **glTF/GLB** (canonical) **+ a pre-baked USDZ** (iOS). 
  - **Un-anchored viewer:** `<model-viewer>` (Apache-2.0) → **WebXR/Scene Viewer on Android**, **AR Quick Look + USDZ on iOS** (no WebXR needed — see the iOS note below). Delivered as an embeddable web component / iframe + shareable link + print QR.
  - **Anchored viewer:** marker (QR or branded image) → resolves to `{mapId, assetId, pose}` → device localizes against our map → renders welded to the place. Web (WASM-SLAM) for MVP; native ARKit/ARCore as the premium/occlusion tier.
- **iOS reality (why USDZ):** all iOS browsers run on WebKit, which has **no WebXR** — so iPhone un-anchored AR goes through Apple's native **AR Quick Look (USDZ)**, not WebXR. Android uses the WebXR/Scene Viewer path. This is a coverage requirement, not a preference (iPhone ≈ half of US viewers).

---

## 2. Phase map

| Phase | Theme | Ships | Monetizes? | Gated by |
|---|---|---|---|---|
| **0** | Foundations | internal | no | — |
| **1** | Un-anchored "View in 3D" MVP | **public, paid** | **yes (day one)** | Phase 0 |
| **2** | 8th Wall migration capture | acquisition campaign | indirectly | Phase 1 |
| **3** | Anchored MVP (marker + rented map) | public, free-to-seed | capability-gated | Phase 1 |
| **4** | Anchored moat (own map + occlusion + native) | premium tier | yes | Phase 3 |
| **5** | Glasses-ready | deferred | — | hardware era (~2028–2032) |

---

## 3. Phase 0 — Foundations *(enabling work, keep thin)*
**Goal:** the smallest backbone Phase 1 needs — no speculative platform-building.
**Build:** account/auth, multi-tenant data model, asset store + CDN, the authoring backend wired to the existing pipeline, billing skeleton.
**Stack:** Next.js/React web app · Postgres · object storage + CDN (Cloudflare R2 or S3+CloudFront) · Auth (Clerk/Auth0) · Stripe · an async **job queue** (e.g. Redis/RQ or a managed queue) fronting `generation/server.py` on the 5090.
**Reuse:** `generation/server.py` becomes the image→3D worker behind the queue (TRELLIS/UniRig/bind_splat untouched).
**Asset format decision (do now):** canonical **GLB** (mesh-first, Draco/meshopt/KTX2 compressed) + a **baked USDZ per asset at publish** (curated, not lossy auto-convert — one animation track survives the conversion, so author within that limit for AR). Quality tiers (LOD) baked at publish.
**Exit criteria:** an authenticated user can upload an image, the backend produces a GLB+USDZ, it lands in the store + CDN, and a stub viewer renders it.

**PROGRESS (2026-06-25, committed on branch `platform-scaffold`):** `platform/` scaffolded + verified (builds, boots, serves; `/api/health` reaches the live GPU worker — `genWorker: ok`). Done:
- **Next.js 16 (App Router, TS, Tailwind 3) on Node 20, React 19, Clerk 7 — 0 npm vulnerabilities.** Security note: the initial Next **14** scaffold was abandoned — Next 14 is EOL and carries 4 high-severity advisories (RSC DoS, cache-poisoning, SSRF, middleware-bypass class) whose fixes exist only in 16.x. Honoring the "no vulnerable deps" requirement forced **Node 20** (installed as the official binary at `~/.local/node20`, referenced by path — nvm's pipe-to-bash installer was sandbox-blocked; no shell-profile edits) → Next 16. A transitive postcss advisory is pinned out via an npm `overrides`. **To use Node 20 in this repo: prefix commands with `PATH=~/.local/node20/bin:$PATH`.** Tailwind kept at 3 (skip the v4 migration churn).
- **Prisma data model** ([platform/prisma/schema.prisma](platform/prisma/schema.prisma)) — multi-tenant + one-asset-two-surfaces + **governance baked into `Anchor` from day one**.
- **Clerk auth** — ClerkProvider + `clerkMiddleware` (protects `/dashboard`, `/api/assets`) + DB user/org sync on first sign-in ([platform/lib/auth.ts](platform/lib/auth.ts)) + protected dashboard.
- **GPU-worker client** ([platform/lib/gen-worker.ts](platform/lib/gen-worker.ts)) wired to `generation/server.py`; `.env.example`, README.

**DB + auth LIVE + verified (2026-06-26):** `DATABASE_URL` (Railway Postgres) + Clerk keys wired; **first migration applied** (`prisma/migrations/..._init`, committed) and schema in sync. End-to-end verified against the real services: `/api/health` → `{db: ok, genWorker: ok}` (200); `/dashboard` → 307 redirect to Clerk sign-in (protected route works). Gotcha recorded: managed Postgres needs `?sslmode=require&connect_timeout=30` or Prisma throws a false `P1001` (now in `.env.example`). **Still manual:** an actual browser sign-in → auto-org-creation (`ensureUserOrg`) — code is wired + the redirect proves Clerk is live, but the create path runs only on a real authenticated request.
**Asset pipeline + "view in 3D" publish — BUILT (2026-06-26, committed):** image → `POST /api/assets` → GPU worker (`generation/server.py`) → poll `GET /api/assets/:id` → finalize (download GLB + **bake USDZ** via `generation/glb_to_usdz.py`, Blender headless, no nvdiffrast) → `POST /api/assets/:id/publish` → public `/v/[slug]` `<model-viewer>` (Android Scene Viewer/WebXR via `src`, iOS AR Quick Look via `ios-src`) + dashboard upload/progress/preview/QR. Local storage behind `lib/storage.ts` + `/files/[...]` with correct content-types (USDZ = `model/vnd.usdz+zip`). **Verified:** build green (0 vulns); seeded asset renders at `/v/demo` with both formats + correct content-types; USDZ bake produces a valid package.
**Remaining for Phase 1 quality:**
- ✅ **Textured GLB — DONE (D41).** Worker `/generate_static` now bakes a real 1024² texture via gsplat (Apache-2.0) + nvdiffrast, dodging TRELLIS's hidden Inria-rasterizer dependency. Verified colored (crate → wood/metal texture) at `/v/crate`. (Follow-up: GLB compression/LOD; texture-size/quality tuning.)
- ✅ **Full image→generate→view chain verified end-to-end (2026-06-26)** via `platform/scripts/dryrun.ts` (drives the real `submitGeneration`→worker→`finalizeAsset`→publish; skips only the Clerk/HTTP wrapper). Crab image → READY with **both GLB + USDZ** → `/v/<slug>` serves both. Caught + fixed two glue bugs: upload FormData needed a filename (Flask dropped it), and USDZ was wrongly marked failed on Blender's segfault-on-exit (judge by output file). Remaining: a literal on-device AR-tap on a real iPhone + Android.
- Storage → R2/CDN; GLB compression (Draco/meshopt/KTX2) + LOD tiers.
- (Minor: drop legacy `.eslintrc.json` for ESLint-9 flat config; silence the `process.cwd()` Turbopack warning in `lib/storage.ts`.)

---

## 4. Phase 1 — Un-anchored "View in 3D" MVP *(the revenue wedge — top priority)*
**Goal:** a local business / SMB brand can, unaided, create a 3D asset and publish a "view in 3D / view in your space" widget to their site or a print QR — and pay for it.
**Build:**
- **Authoring (1–2 pipelines only, the cheapest/highest-demand):** (a) **product-image → 3D** (existing pipeline), (b) **2D canvas / drawing → 3D-presented sign**. Simple keyframe/timeline animation builder (no code). Mesh-first defaults.
- **Viewer + delivery:** `<model-viewer>` web component; **Android → Scene Viewer/WebXR**, **iOS → AR Quick Look/USDZ**; embed snippet (iframe/web-component), shareable link, auto-generated **print QR**.
- **Billing + analytics:** Stripe plans; **view/interaction analytics but NEVER meter on views** (D37 — views are free advertising). Card-gated trial.
- **Compression/CDN delivery** with LOD tiers.
**Stack:** model-viewer (Apache-2.0) · three.js · Scene Viewer (Android) · AR Quick Look/USDZ (iOS) · Draco/meshopt/KTX2 · PostHog or self-host for analytics.
**Pricing to wire (per D37, pending user ratification — §6):** Starter ~$19–29/mo (unlimited views, light watermark) · Growth ~$99–149/mo (no watermark, conversion/return analytics, e-com embed) · Enterprise quote.
**Exit criteria:** a non-technical user signs up, makes an asset from a product photo, embeds it on a test Shopify/web page, sees it in their room on both an iPhone (USDZ) and an Android (WebXR), and pays via Stripe.

**REPRIORITIZED (D42, 2026-06-27).** The user chose to deepen the **no-code authoring/generation suite** (the surface customers touch) before the revenue/delivery plumbing. Within Phase 1 the active workstream is now §0.5's expanded studio; the plumbing is recorded and deferred.
- **Active now — authoring studio (PROJECT.md §0.5, D42):**
  1. ✅ **Productize the rigged/animation pipeline — BUILT + verified (2026-06-27).** Dashboard has a **Static / Animated** toggle; "Animated" routes to the worker's `/generate` (TRELLIS→UniRig→`bind_splat`). Worker now bakes a generic **idle skeletal animation** + **vertex colour** (sampled from the gaussian splat) into the rigged GLB ([generation/prep_viewer.py](generation/prep_viewer.py)); the public viewer auto-plays it (`autoplay`) and the USDZ bake carries the single skeletal track into AR Quick Look ([generation/glb_to_usdz.py](generation/glb_to_usdz.py) `--animation`). Schema: `Asset.genMode` + `Asset.animated`. **Verified end-to-end + in-browser** on a human image: GLB has skin + 1 animation; USDZ contains `SkelAnimation`; `finalizeAsset` sets `animated=true`, bakes the animated USDZ, publishes a widget; headless-Chromium render of `/v/<slug>` showed the colored figure with 74.5% inter-frame pixel motion (auto-rotate off → the idle clip is playing). Rig-failed→static fallback is surfaced in the dashboard.
  1a. ✅ **High-fidelity texture on rigged assets — BUILT + verified (2026-06-27).** Replaces low-res vertex colour with the static product's proven 1024² texture. **First approach failed + was abandoned:** baking the gaussian onto the *rigged* mesh's auto-UVs wrapped badly — UniRig's mesh + Blender `smart_project` gives heavily fragmented UV islands (confirmed with a UV-grid render → chaotic patches), plus a 2× rescale and sub-pixel splats. **Working approach ([transfer_rig.py](generation/transfer_rig.py)):** generate TRELLIS's `to_glb` textured mesh (good xatlas UVs + clean gsplat+nvdiffrast bake — identical to the static product, [server.py](generation/server.py) `pipeline()`), then in Blender **transfer the UniRig skeleton + skin weights onto that mesh** (align by bbox, Data-Transfer vertex groups by nearest face, re-parent to the armature, carry the baked animation). Wired with **vertex-colour fallback**. Verified in the product model-viewer: correctly-wrapped textured character (face/skin + clothing coherent front/side/back), 28-joint skin, `baseColorTexture` set, and 30% inter-frame motion (animation deforms via the transferred weights). Bonus: the displayed mesh is now `to_glb`'s cleaner geometry, not the heavily-cleaned rigging mesh.
  1b. ✅ **Dark/black-texture fix (2026-06-27).** Colorful inputs (e.g. a dwarf) were baking to near-black textures (median [6,5,5]). Root cause: TRELLIS gaussians are many *tiny* splats (median scale ~9e-4) → sub-pixel at 1024² → gsplat renders them with black gaps that the texture optimiser averages in (the muted crate masked this; saturated objects exposed it). Fix: **adaptive splat-scale inflation before the bake render** ([gsplat_render.py](generation/gsplat_render.py) `inflate_scales` — grows splats to ~1.2% of object extent, so sparse gaussians inflate ~12-16× for ~95% coverage while already-dense ones barely change). Applied in both `pipeline()` and `pipeline_static()`. Result: non-empty texel brightness [58,45,37]→[108,82,64], coverage 14%→93%; the dwarf renders fully coloured in model-viewer. Tradeoff: bigger splats soften the texture (painterly, not crisp) — acceptable for v1; a sharper path would need to match the Inria rasterizer's dense small-splat handling.
  2. **No-code animation editor** — keyframe/timeline + interaction triggers, built on that skinning.
  3. **Drag-and-drop motion library** — reusable clips retargeted onto an asset's rig (low-risk, high-value). *(v0 BUILT 2026-06-27: a **motion picker** at creation time — `idle`/`sway`/`bob`/`spin`/`float`, all **rig-agnostic** presets baked by [generation/prep_viewer.py](generation/prep_viewer.py); threaded image→`/generate`(motion)→GLB. Verified the presets produce distinct animations. Next: semantic motions — wave/walk — need bone labels + retargeting, and a true drag-drop/timeline UI.)*
  4. **AR scene/page editor + templates/themes** — compose what the viewer sees; backgrounds/themes for use cases like restaurant menus (pure web app, no GPU-research risk — parallelizable).
  5. **Video → 3D object / 3D animation + AI-assist** — video upload; replicate motion from a video (monocular mocap→retarget); describe-the-scene/motion in text. *Research-grade; humanoid/simple rigs first.*
  6. **Splatting made easy** — static-first authoring UX; finish the D33/SPIKE animated-splat POC (GPU/browser validation in [generation/SPIKE_animated_splat.md](generation/SPIKE_animated_splat.md)) before exposing animated splats.
- **Deferred (recorded, D42) — revenue/delivery plumbing, still required to actually ship+pay:** Stripe billing + card-gated trial · R2/CDN + GLB compression (Draco/meshopt/KTX2) + LOD tiers · analytics (PostHog/self-host, never meter views) · 2D-canvas authoring · real-device AR tap (iPhone USDZ + Android WebXR).

---

## 5. Phase 2 — 8th Wall migration capture *(time-boxed acquisition, runs alongside Phase 1 launch)*
**Goal:** convert the post-Feb-2026 8th Wall refugees into Phase 1 paying customers before fast-followers do.
**Build:** a migration landing page + SEO content; a **free import path** for common 8th Wall assets (GLB/USDZ already portable; the AR *logic* is not — scope to asset + simple-interaction import, not full project port); first-year discount funnel into the un-anchored paid tier.
**Note (D37):** ≥8 vendors are already campaigning; treat this as a launch accelerant + credibility play, **not the franchise**. Time-box it.
**Exit criteria:** N migrated brands live on the paid un-anchored tier (set N as the campaign target).

---

## 6. Phase 3 — Anchored MVP (marker + rented map) *(the upsell; starts once Phase 1 is generating revenue)*
**Goal:** an existing un-anchored customer can anchor their asset outside their real shop with a printed marker, viewable on a passerby's phone.
**Build:**
- **Marker service:** mint/resolve QR + branded image-target markers → `{mapId, assetId, pose}`.
- **Map service (RENT first):** **Immersal** (REST + owner-seeded mapping + private deploy = closest fit) or ARCore Geospatial. Abstract behind our own `MapService` interface so Phase 4 can swap in our own map.
- **Anchor registry (governance from day one):** `{anchor pose in map frame, asset ref, map ID, coarse GPS, owner, permission scope, spatial claim}` + a moderation queue.
- **Guided capture flow:** coaches multi-angle / multi-distance / good-lighting scans with quality checks (this is the front line against the relocalization risk).
- **Anchored viewer:** web WASM-SLAM for the no-install funnel — **abstracted SLAM provider** (candidates: Blippar / Zappar; MindAR/AR.js as free lower-quality fallback; explicitly NOT the 8th Wall binary). Marker-only local-pose fallback when the map can't lock.
**Hard constraint (D39):** vanilla WebXR cannot localize against a custom cloud map on any browser, and iOS has no WebXR → anchored is WASM-SLAM (web) or native; plan native as Phase 4.
**Pricing (D37):** free seed tier (one location, generic QR, watermark) → **Anchored Pro ~$29–79/location/mo**, converted on **capability gates** (branded marker → persistent map → multi-location → watermark removal), **not** on a scan-count dashboard (D37: storefront scan rates are low single digits → analytics is support, not the trigger).
**Exit criteria:** an owner scans their storefront, places an asset, prints a marker; a second phone reads the marker and shows the asset welded to the storefront across two different lighting conditions.

---

## 7. Phase 4 — Anchored moat (own map + occlusion + native)
**Goal:** own the defensible layer + close the quality gaps that rented maps and web SLAM can't.
**Build:**
- **Owner-seeded map pipeline (the moat):** **COLMAP + hloc** relocalization. **Licensing gate:** hloc's default SuperPoint/SuperGlue weights are non-commercial → **ship LightGlue/DISK/R2D2** instead (§4a-class trap, D39).
- **Occlusion/depth:** map-baked occluder mesh so assets hide behind real walls.
- **Native viewer (premium tier):** ARKit/ARCore for LiDAR occlusion + durable multi-user persistence; this is also the **OpenXR/glasses on-ramp**.
- **Ongoing re-capture:** every marker scan becomes a fresh ground-truthed mapping sample that improves the map (turns the primary risk into a flywheel).
**Exit criteria:** a self-built map relocalizes a returning viewer across season/lighting/occlusion changes as well as or better than the rented service it replaces; occlusion is correct; the native app persists an anchor for multiple users.

---

## 8. Phase 5 — Glasses-ready *(deferred to the hardware era, ~2028–2032 per D37)*
No build now. Keep the viewer runtime described in **world units (meters)** behind an OpenXR/WebXR abstraction so the same anchored asset renders on glasses when display+world-tracking glasses arrive at scale. Underwrite the whole business on **phone-only economics** until then.

---

## 9. Cross-cutting workstreams (run continuously, not as a phase)
- **Governance / moderation / privacy:** owner+permission+spatial-claim in the schema from the first anchored row; moderation review model; process scans on-device + discard raw frames where possible (PROJECT.md §0.8).
- **Licensing gate (release checklist):** TRELLIS/UniRig clean (§4a); model-viewer Apache; **no 8th Wall binary at core (D38)**; **no NC SuperPoint/SuperGlue in the map pipeline (D39)**; Immersal/ARCore terms confirmed; any SLAM SDK's commercial terms confirmed. Nothing ships unaudited.
- **Cross-device LOD / additive-display discipline** (PROJECT.md §0.6 / §2a).
- **Analytics** that informs the customer (returns, engagement) without metering views.

---

## 10. Immediate next actions (first sprint — concrete)
1. **Stand up Phase 0 backbone:** Next.js app + Postgres + R2/CDN + Stripe skeleton + the job queue in front of `generation/server.py`.
2. **Ship the asset pipeline end-to-end headless:** image in → GLB (compressed, LOD) + baked USDZ out → CDN URL. (Reuses the 5090 pipeline; add the USDZ bake + compression steps.)
3. **Drop in `<model-viewer>`** with the Android(WebXR/Scene Viewer)/iOS(AR Quick Look) split and verify "view in your room" on a real iPhone + a real Android.
4. **Pick the authoring pipeline to lead with** (product-image vs 2D-canvas) and build that one no-code flow.
5. **Decide hosting/region + the licensing checklist owner.**

---

## 11. Open decisions for the user (don't let these block the first sprint)
- **Ratify Phase-1 pricing** (Starter/Growth/Enterprise numbers + capability-gated anchored) into PROJECT.md §0.9/§0.10, or adjust.
- **Lead authoring pipeline:** product-image first, or 2D-canvas/drawing first?
- **Team/resourcing** — confirms or reshuffles the phase tempo.
- **Rent target for Phase 3 map:** Immersal vs ARCore Geospatial (pick when Phase 3 starts; benchmark both).
