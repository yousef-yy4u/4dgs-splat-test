# 8th Wall Deep Dive — Technical Due Diligence

**Researcher:** Claude (technical due-diligence, research-only)
**Date:** 2026-06-25
**Purpose:** Verify/correct PROJECT.md §0/§0a claims about 8th Wall's open-sourcing and assess build-vs-adopt for the marker-anchored AR asset platform.

> **TL;DR — the two PROJECT.md claims, verified with corrections:**
> - **(a) "Niantic retired hosted 8th Wall in Feb 2026."** ✅ **CONFIRMED.** Hosted platform (cloud editor / Studio / logins / hosting) retired **Feb 28, 2026**. Already-published experiences keep running until **Feb 28, 2027**, then go dark.
> - **(b) "The 8th Wall ENGINE was open-sourced, but VPS/Maps were NOT."** ⚠️ **PARTIALLY TRUE — needs an important correction.** VPS / Lightship Maps / Geospatial Browser were NOT released (✅ thesis holds). **BUT the most valuable part of "the engine" — the SLAM / world-tracking core — was NOT open-sourced either.** It ships only as a **closed-source binary** under a **restrictive limited-use license** (NOT MIT) that **prohibits using it to build "a substantially similar product or competitive product," and prohibits products whose value "derives substantially from the functionality of the Software."** The MIT-licensed open-source repo deliberately **excludes SLAM**. So "the engine is open-sourced" is too generous: a thin framework is MIT; the AR brains are a take-it-as-is binary with field-of-use restrictions.

---

## 1. TIMELINE & FACTS — what actually happened

| Date | Event | Source |
|---|---|---|
| 2018 | 8th Wall founded (WebAR platform: cloud IDE + CV/SLAM). | [Wikipedia: Niantic Spatial] |
| **Mar 2022** | **Niantic acquires 8th Wall.** | [Wikipedia] |
| **Mar 12, 2025** | Niantic agrees to **sell its games division (incl. Pokémon GO) to Scopely for $3.5B**. | [TechCrunch 2025-03-12] |
| **May 29, 2025** | Scopely deal closes. **Niantic Spatial Inc. spun out** as the remaining geospatial/AR company (CEO John Hanke, CTO Brian McClendon). Capitalized ~$250M ($200M Niantic + $50M Scopely). 8th Wall sits inside **Niantic Spatial**. | [Niantic Labs "Next Chapter"]; [Wikipedia] |
| **Nov 2025** | Niantic Spatial announces 8th Wall will **wind down in 2026** after ~7 years. | [Road to VR]; [8th Wall blog] |
| **Jan 2026** | **Distributed Engine Binary** released — closed-source binary, includes **SLAM**, under a binary-only "limited-use" license for commercial + noncommercial use. | [8th Wall FAQ]; [Road to VR] |
| **Feb 28, 2026** | **Hosted platform RETIRED.** Cloud editor / XR Studio / logins / new-project creation / hosting all go offline. Transition to open source completes. | [Facebook/8th Wall]; [8thwall.org] |
| **~Mar 2, 2026** | **Open-source framework released** (MIT) at **8thwall.org** + **github.com/8thwall**. "Goodbye 8thwall.com. Hello 8thwall.org." | [8th Wall blog 2026-03-02]; [Road to VR 2026-03-10] |
| **Feb 28, 2027** | **Hard cutoff:** existing published experiences hosted on 8th Wall go offline permanently. | [ARLOOPA]; [ar-code] |

**What exactly is being shut down:** the *hosted* business — user logins, the cloud editor (XR Studio / Studio), project dashboard, hosting/CDN, the Geospatial Browser, and (separately, as a service) Lightship VPS + Maps. Not just "hosting": the whole managed SaaS surface. What survives is (i) an MIT open-source repo of the framework and (ii) a separately-licensed binary you self-host.

**Where it lives now:** `https://8thwall.org` (docs/blog), `https://github.com/8thwall/8thwall` (framework, MIT), `https://github.com/8thwall/engine` (the binary + its license). It is described as "community-driven" post-sunset; Niantic Spatial says it will push "further releases … documentation, desktop tools, and runtime components" in following weeks but made **no explicit long-term maintenance or governance commitment** ([Road to VR]).

---

## 2. WHAT IS OPEN SOURCE vs NOT — precise

There are **TWO separate license regimes**. This split is the single most important fact in this report.

### A) `github.com/8thwall/8thwall` — the framework — **MIT License** ✅ truly open, commercial-friendly
Verified against the raw LICENSE: standard MIT ("deal in the Software without restriction," attribution-only, no warranty). Contains:
- **ECS** — the entity-component-system game engine that powered 8th Wall Studio.
- **Engine package** wrappers / AR module glue: **Face Effects, Image Targets, Sky Effects** integration code.
- **XRExtras** — XR/3D helper code.
- **Desktop app** (3D dev tooling), **image-target-cli** (compiles image targets), landing-page fallback, example projects.

**Crucially, this MIT repo does NOT contain SLAM / world tracking.** The README and docs state SLAM "is distributed separately under a binary-only license" and is "available via the distributed engine binary." So the *open* part is the scene graph, the effects glue, and tooling — not the spatial-tracking brain.

### B) `github.com/8thwall/engine` — the Distributed Engine Binary — **closed source, restrictive license** ⚠️
This is the actual AR engine: a compiled, hyper-optimized WebAR runtime. **Includes:**
- **SLAM / World Tracking** (the best-in-class piece)
- **Image Targets** (marker tracking)
- **Face Effects**, **Sky Segmentation**
- **Absolute Scale**
- Integrations for A-Frame, three.js, PlayCanvas, Babylon.js

**Does NOT include (proprietary / dead / Niantic-Spatial-services-only):**
- **Lightship VPS** (Visual Positioning Service)
- **Niantic Lightship Maps**
- **Geospatial Browser**
- **Hand Tracking**
- Source code, ability to modify, the cloud editor, hosting/CDN, analytics, project dashboard

#### The license verdict (the load-bearing finding)
The engine binary's LICENSE ("XR Engine License Agreement") is **NOT permissive.** Verbatim terms (from raw LICENSE):

- **Grant (1.1):** "limited, non-exclusive, non-transferable, non-sublicensable, **revocable** license … to install, execute, and distribute the Software."
- **Commercial restriction (1.2):** you may not use it "in connection with any product or service: (1) **which is offered for a fee or other consideration**, and (2) **whose value derives, entirely or substantially, from the functionality of the Software.**" (Both prongs must be met to be prohibited.)
- **Prohibited uses:** "(i) reverse engineer, decompile or disassemble; (ii) modify or create derivative works of, distribute sell, sublicense or otherwise transfer the Software; (iii) copy … except as strictly necessary; or **(iv) use the Software or any documentation to create, improve (directly or indirectly) or offer a substantially similar product or service, or build a competitive product.**"
- **Termination:** either party may terminate on **5 days' written notice**.
- **Attribution required:** must credit "Niantic Spatial as the creator," retain copyright + a link to the Agreement (in source for web, or in an about/legal screen for packaged apps).
- **AS IS**, all warranties disclaimed, licensee indemnifies Niantic Spatial.

**Can a commercial product freely use it?** — **Qualified yes, with real risk.** The official "Permitted Use FAQ" / engine-distribution docs clarify the intent: ✅ permitted to "install, execute, and distribute the engine binary in its original form **as part of your own application, product, or service**" — branded AR campaigns, experiential marketing, agencies building experiences for clients. The stated principle: **"if you're selling the *experience*, not the *engine*, your use is permitted."** ❌ Prohibited: selling the engine itself, an engine-based toolkit, or a "substantially similar / competitive product."

**The gray zone that matters for US (§0):** our product is a **no-code platform that lets businesses build AR experiences** — i.e., we resell AR-building capability, and a non-trivial share of that capability's value would "derive substantially from" 8th Wall's SLAM. That is *exactly* the shape of "an engine-based toolkit" / "competitive product" the license names. The docs explicitly flag the SaaS-AR-builder case as **not clearly addressed / a gray area**. Combined with a **revocable, 5-day-termination, can't-modify, can't-fix-bugs** binary from a company that just exited the business, this is a material licensing and continuity risk — not a clean foundation. **PROJECT.md §0.6's phrasing "open-sourced 8th Wall engine + WebXR/three.js for world-tracking/SLAM" overstates what is actually free-to-build-on:** the SLAM is the binary, not the MIT code, and the binary's terms are hostile to exactly our SaaS shape.

---

## 3. FEATURE INVENTORY vs PRODUCT NEED (§0)

§0 needs: (i) WebAR **surface/world tracking** for the un-anchored "view in your room" widget; (ii) **image-target / marker** tracking for the anchored marker. We do NOT need face filters, etc.

| 8th Wall feature | In OSS (MIT)? | In binary? | Do WE need it (§0)? |
|---|---|---|---|
| **SLAM / World Tracking** (surface placement) | ❌ | ✅ (binary) | **YES — core** (un-anchored "view in your room") |
| **Image Targets** (marker tracking) | glue ✅ / target-cli ✅ | ✅ (binary runtime) | **YES — core** (anchored marker-pointer) |
| **Absolute Scale** | ❌ | ✅ | Nice-to-have (correct real-world sizing) |
| Face Effects / Face Tracking | ✅ (MIT glue) | ✅ | **NO** |
| Sky Segmentation / Sky Effects | ✅ (MIT glue) | ✅ | **NO** |
| Hand Tracking | ❌ (not released) | ❌ | NO |
| Lighting estimation | partial (engine) | bundled | Minor (asset realism); not required v1 |
| ECS / Studio scene engine | ✅ (MIT) | — | Maybe (could inform our authoring tool; we likely build our own on three.js) |
| Lightship **VPS** | ❌ | ❌ | **NO — and this is the point: we build our own** owner-seeded maps (§0.2) |
| Lightship **Maps** | ❌ | ❌ | NO |
| Geospatial Browser | ❌ | ❌ | NO |
| Cloud editor / hosting / dashboard / analytics | ❌ (dead) | — | NO — we build our own SaaS surface anyway |

**Net:** we need exactly the two features that **live only in the restrictively-licensed binary** (SLAM, image-target runtime). The MIT release gives us almost nothing we'd actually depend on for the core tracking.

---

## 4. BUILD-IT-YOURSELF / ALTERNATIVES

We need two capabilities: **(W) markerless surface/world tracking** (un-anchored) and **(M) image-target/marker tracking** (anchored).

### Browser-substrate reality check (2026)
- **WebXR** has a good `immersive-ar` + **Hit Test** story on **Android Chrome / Samsung Internet / Quest** — usable for surface placement. **WebXR Image Tracking remains experimental/flagged**, not broadly shipped.
- **iOS Safari STILL does not implement WebXR** (macOS/iOS/iPadOS) as of 2026 — only visionOS Safari has partial (immersive-VR) support, and not the AR module. **This is the entire reason 8th Wall mattered:** it ran a self-contained CV/SLAM stack in plain WebGL/`getUserMedia`, giving robust markerless WebAR **on iOS** where WebXR can't. Any alternative must clear the same iOS bar.

| Option | Covers | License / cost | Quality vs 8th Wall | Verdict for us |
|---|---|---|---|---|
| **AR.js** | M (marker), basic surface | OSS (MIT-ish) | Marker tracking OK but jittery; markerless weak. Runs on iOS. | Free fallback for the marker path; not flagship quality. |
| **MindAR** | M (image + face) | OSS (MIT) | Decent image tracking, easy; widely flagged as **not commercial-grade** robustness. iOS-capable. | Good for cheap image-target MVP; expect tracking gap. |
| **Zappar Universal AR SDK / Mattercraft** | W + M + face | **Commercial, paid** (Pro ~€240/mo, view-metered) | Tracking ~7/10; closest no-code+SDK peer; iOS via WebXR/App Clip + own CV. Strong docs. | Strong commercial alt; but it's a paid dependency on another vendor (and a potential *competitor* to us). |
| **Blippar WebAR SDK** | W + M + face | Commercial | **GPU SLAM, 30fps**, explicitly markets **8th-Wall-compatible migration**. | Closest drop-in to 8th Wall's quality; paid vendor dependency. |
| **Google model-viewer + Scene Viewer** | "View in your space" (ARCore) | OSS (Apache-2.0) | **Excellent for the un-anchored widget** on Android; one `<model-viewer>` tag. No custom SLAM, no markers. | **Use for un-anchored Android.** |
| **Apple AR Quick Look (USDZ)** | "View in your space" (ARKit) | Native, free | **Excellent un-anchored on iOS**; no markers, no in-page control. | **Use for un-anchored iOS.** Pair with model-viewer = covers billions of phones, zero SLAM code. |
| **WebXR Hit Test (three.js)** | W (Android) | OSS | Native-quality surface tracking **on Android only** (no iOS). | Use where available; can't carry iOS alone. |
| **WebXR Image Tracking** | M | OSS, **experimental/flagged** | Not production-ready, not on iOS. | Watch, don't depend. |
| **MediaPipe** | building block (CV/tracking primitives) | OSS (Apache-2.0) | Not a SLAM stack; image/face/hand detection. | Could feed a custom marker detector. |
| **Niantic Lightship ARDK** | W + **VPS** | Native (Unity), Niantic SDK | Strong, but **native app**, ties us back to Niantic Spatial — the dependency we're trying to avoid; not WebAR. | Avoid; contradicts §0.2 thesis. |
| **Immersal** | **VPS/relocalization** (maps) | Commercial SDK | A real VPS alternative for the *anchored map* piece — relevant to §0.7. | **Watch for the map/relocalization layer**, not the widget. |
| **Plain three.js + custom CV** | W + M (DIY) | OSS | You'd be rebuilding SLAM — months/years to approach 8th Wall. | Don't build SLAM from scratch. |

**The quality gap, honestly:** 8th Wall's markerless SLAM **was** best-in-class for *web* AR, principally because it delivered robust markerless tracking **on iOS** where the browser gives you nothing. That moat is now half-eroded: **Blippar (GPU SLAM, 8th-Wall-compatible) and Zappar Mattercraft are credible commercial peers**, and for the **un-anchored "view in your room"** use case specifically, **native AR Quick Look (iOS) + Scene Viewer/model-viewer (Android) are arguably better than custom WebAR** — they hand off to the OS's own ARKit/ARCore, which beats any in-browser SLAM and needs no engine license at all. The remaining genuine gap is **in-browser markerless world tracking with full in-page control on iOS** (no OS hand-off) — that is where 8th Wall / Blippar / Zappar still beat the free stack.

---

## 5. RECOMMENDATION

**Recommended: HYBRID, leaning build-from-alternatives — do NOT make the 8th Wall binary the load-bearing core.**

1. **Un-anchored "view in 3D" (§0.9 step 1, the FIRST surface):** build on **`<model-viewer>` (Scene Viewer/ARCore) + AR Quick Look (USDZ/ARKit)**. Apache-2.0 / native, free, no engine license, OS-quality tracking, covers iOS + Android today. **This removes any 8th Wall dependency from the surface we ship first.** This is a correction to §0.6's lean on the 8th Wall engine for the un-anchored path — the OS-native viewers are a cleaner, license-free, higher-quality fit for exactly that turntable/"place on surface" use case.
2. **Anchored marker path (§0 step 3):** the **identity/marker** read is trivial (QR/URL) and needs no engine. For **in-browser image-target + short-range SLAM persistence on iOS**, evaluate **MindAR/AR.js (free, lower quality) vs Blippar/Zappar (paid, near-8th-Wall quality)** before reaching for the 8th Wall binary. If you do use the 8th Wall binary, treat it as **a replaceable component "as part of a broader experience"** (FAQ-permitted shape), keep it behind an abstraction, and **get the SaaS-platform question in writing** — because the "competitive product / value-derives-substantially" clauses plausibly bite a no-code AR-builder, and the license is **revocable on 5 days' notice** and **cannot be modified or bug-fixed**.
3. **The map / relocalization layer (§0.7, the actual moat):** build owner-seeded per-location maps ourselves; benchmark against **Immersal** and **ARCore Geospatial** as rent-vs-build references. Niantic open-sourced **nothing** here.

**Risk of building on a project Niantic just walked away from:**
- **Abandonment / governance:** "community-driven," **no stated long-term maintenance commitment** from Niantic Spatial. A core dependency owned by no committed maintainer.
- **Security/maintenance:** the SLAM binary is **unmodifiable** — you cannot patch a bug or a vulnerability in it, ever. MIT framework you can fork, but the framework isn't the valuable part.
- **License revocability:** the binary license is **revocable, 5-day termination, restrictive on competitive/SaaS use** — fragile to anchor a business on.
- **Continuity for migrating 8th Wall customers (§0.9 step 2):** still a valid GTM wedge (thousands of orphaned brands), but you serve them with **your** stack + the OS-native viewers, **not** by re-hosting their dependence on a sunset binary.

**Verdict on PROJECT.md's strategic thesis** ("8th Wall's open-sourced engine is usable BUT VPS/Maps were NOT open-sourced, which is why owner-seeded per-location maps are the defensible piece we build"):
- ✅ **The defensibility half is CONFIRMED and actually STRONGER than stated.** Niantic released **no VPS, no Maps, no Geospatial Browser, no relocalization** — the persistent-anchoring layer is wholly unserved by the open release. Owner-seeded per-location maps remain a genuine, un-handed-out moat. Good thesis.
- ⚠️ **The "engine is usable" half needs correction.** The *valuable* engine (SLAM/world tracking) is **NOT open source** — it's a **restrictively-licensed, unmodifiable, revocable binary** whose terms are **hostile to a no-code AR-builder SaaS** (the exact §0 shape). Lean on **OS-native viewers (model-viewer + AR Quick Look)** and **commercial peers (Blippar/Zappar) where in-browser SLAM is truly needed**, and treat the 8th Wall binary as an optional, abstracted, legally-vetted component — not the foundation. **Update §0.6 accordingly.**

---

## Sources (primary first)

- 8th Wall blog, "Goodbye 8thwall.com. Hello 8thwall.org." (2026-03-02) — https://www.8thwall.com/blog/post/208587408737/8th-wall-open-source (redirects to 8thwall.org)
- 8th Wall blog, "Transition Update: Engine Distribution and Open Source Plans" — https://www.8thwall.com/blog/post/202888018234/8th-wall-update-engine-distribution-and-open-source-plans
- 8th Wall Open Source docs — https://8thwall.org/docs/open-source
- 8th Wall Migration FAQ (Distributed Engine Binary license & permitted use) — https://8thwall.org/docs/migration/faq
- 8th Wall Engine Distribution docs — https://www.8thwall.com/docs/migration/engine-distribution/
- GitHub framework (MIT) — https://github.com/8thwall/8thwall ; LICENSE: https://raw.githubusercontent.com/8thwall/8thwall/main/LICENSE
- GitHub engine binary + LICENSE (XR Engine License Agreement) — https://github.com/8thwall/engine ; https://raw.githubusercontent.com/8thwall/engine/main/LICENSE
- Facebook/8th Wall — "Platform access ends February 28, 2026." — https://www.facebook.com/the8thwall/photos/1527342312143360/
- Road to VR, "Niantic's WebAR Platform 8th Wall Goes Open Source as Hosted Services Go Offline" (2026-03-10) — https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/
- Niantic Labs, "Niantic's Next Chapter" (Niantic Spatial spin-out) — https://nianticlabs.com/news/niantic-next-chapter
- TechCrunch, "Niantic selling games division to Scopely for $3.5B" (2025-03-12) — https://techcrunch.com/2025/03/12/pokemon-go-maker-niantic-is-selling-its-games-division-to-scopely-for-3-5b/
- Wikipedia, Niantic Spatial — https://en.wikipedia.org/wiki/Niantic_Spatial
- WebXR browser support (2026), iOS gap — https://www.testmuai.com/learning-hub/webxr-compatible-browsers/ ; https://launch.variant3d.com/blog/23-06-state-webxr-on-ios-beyond
- WebXR Image Tracking status — https://chromestatus.com/feature/6548327782940672
- Alternatives comparisons — Kivicube https://www.kivicube.com/post/augmented-reality-after-8th-wall-shutdown-your-2026-guide-to-the-right-webar-platform/ ; Blippar https://www.blippar.com/best-webar-platforms-for-agencies-2026/ ; Zappar/Mattercraft https://zap.works/mattercraft-for-8th-wall-studio-developers/ ; ARLOOPA https://www.arloopa.com/blog/8th-wall-is-shutting-down-where-to-move-your-webar-projects

> **Note on a source conflict:** the 8thwall.org *open-source* doc page summarizes the binary as "Commercial and noncommercial use permitted," while the raw **LICENSE** text prohibits products that are both for-a-fee and value-derives-substantially-from-the-Software, and prohibits "competitive products." These are reconciled by the Permitted-Use FAQ: commercial use is OK *when the engine is one component of a broader experience you sell*, NOT when you resell engine/AR-building capability itself. For a no-code AR-builder SaaS this is a genuine gray area — **get written clarification before depending on it.**
