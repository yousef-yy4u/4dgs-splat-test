# Market & Go-To-Market Research — Marker-Anchored AR Asset Platform

**Product under study:** A no-code platform where any business publishes a 3D asset two ways — (1) an **un-anchored** "view in 3D" web/print widget (works on every phone today), and (2) a **real-world AR anchor** placed via a physical marker (QR or branded image) that points to an owner-seeded, cloud-hosted per-location map. **Beachhead** = local-business storefront signage + e-commerce product viewers. **Endgame** = AR glasses; phone WebAR is the day-one viewer. The company has **no existing AR user base**.

**Report date:** 2026-06-25. Research is web-sourced; every non-obvious claim is cited (URL + access date) in the §Sources section. This space moves fast — figures from vendor blogs and syndicated-report shops are flagged as low-confidence. Where a fact could not be verified, that is stated explicitly rather than guessed.

---

## Executive Summary (the strategic read)

1. **The defensible capability — persistent, world-anchored AR — is real but pre-product, and the market is *withdrawing* from it, not advancing.** When Niantic restructured (sold games to Scopely for $3.5B, May 2025), it **kept** its geospatial/VPS assets but **retired hosted 8th Wall** (access ends Feb 28, 2026) and **did not open-source VPS, Maps, or Hand Tracking** — and redirected its VPS to defense/robotics/enterprise, away from consumer WebAR. Adobe killed Aero (Dec 2025). Meta killed Spark AR (Jan 2025) despite 600k creators. **Hosted, un-anchored WebAR-as-a-standalone-business is, on this evidence, structurally unviable** — which is precisely why owner-seeded per-location anchoring (the thing everyone keeps proprietary or abandons) is the only candidate moat.

2. **The un-anchored "view in 3D" widget is the real business; anchored is the bet.** E-commerce 3D/AR ROI is *partly* real — but the headline numbers (Shopify's "94% higher conversion," Houzz "11x," Rebecca Minkoff "65%") are vendor-published selection-bias artifacts, not causal lift. The credible, mechanism-backed effect is **~20–40% return reduction for high-uncertainty categories (furniture, home, eyewear, footwear, cosmetics)** plus a **modest single-to-low-double-digit conversion lift**. That's enough to sell — willingness-to-pay is proven at the $5–$99/mo QR-SaaS band — but build the business case on returns + a *conservative* lift, not the marketing numbers.

3. **The core hypothesis is directionally right but mis-sequenced on the conversion trigger.** Monetize un-anchored early (sound), give anchored free to seed density (sound — every successful location network seeded with free demand), but **do NOT make a single SMB's scan-analytics dashboard the upsell hook.** Storefront/awareness QR scan rates are low single digits, so the dashboard will too often show a *small* number that argues *against* paying. Convert anchored on **capability gates** (branded image-marker, persistent per-location map, multi-location, watermark removal), with analytics as support.

4. **The 8th Wall migration is a real but crowded, time-boxed pulse — treat it as a launch accelerant, not the franchise.** ~3,000 commercial experiences (50k+ lifetime) need a new home within a ~12-month window. At least 8 vendors (AR Code, ARLOOPA, Blippar, Zappar, HOVARLAY, Kivicube, Glamar, Remix Reality) are already running explicit "8th Wall alternative/migration" campaigns. Use it for SEO/credibility and to seed the un-anchored paid product; the refugees skew enterprise, not your SMB beachhead.

5. **Timing: phone-now is right; glasses-later is load-bearing and slips to ~2028–2032 for world-anchored AR.** Display-*less* AI glasses (Ray-Ban Meta, ~9M cumulative sold) are succeeding but **cannot render anchored AR**. The endgame needs **display + world-tracking** glasses, which are prototype-only (Orion, never for sale) or $2,195 niche (Snap Specs, fall 2026). Underwrite the company on **phone-only economics**; glasses are 4–8-year optionality, not a 2–3-year catalyst.

**Headline pricing recommendation (full detail in §6):** Charge from day one on the **un-anchored** widget (~$19–29 Starter / ~$99–149 Growth, **unlimited views**, card-gated trial — never meter on views); give the **anchored** product a free seeding tier and convert on **capability**, not analytics (~$29–79/location/mo once a branded marker / persistent map / multi-location trigger is hit).

---

## 1. Landscape — Who's Playing, Anchored vs Un-anchored, Pricing, Traction

### Framing: the one scarce capability

The defensible, hard capability is **persistent, world-locked AR** — content pinned to real-world geometry/coordinates via a Visual Positioning System (VPS) or precise geospatial anchoring, persisting across sessions and users. Almost everything else commoditizes: image-target (scan a marker), surface-place / "turntable," face/body/foot try-on. True anchored AR is rare — and even the players who have it mostly **rent it** (Immersal, Google Geospatial, Niantic VPS) rather than own the stack.

**Anchored-AR scorecard:**

- **Genuinely anchored (VPS / area-target / location-locked):** Niantic Lightship/Spatial VPS; Snap (Local Lenses + Niantic VPS partnership); Onirix (Spatial AR VPS); ARLOOPA (via Google Geospatial + Immersal). 8th Wall *had* hosted VPS — now **retired and NOT open-sourced**.
- **Partial / advanced-tracking, not confirmed persistent VPS:** ZapWorks (VPS gated in Mattercraft); MyWebAR ("spatial tracking" top tier).
- **Un-anchored (the vast majority):** HOVARLAY, Adobe Aero (dead), Vectary, Echo3D, Sketchfab, Threekit, Emersya, VNTANA, Google model-viewer/Scene Viewer/Search-3D, Apple Quick Look, Wanna/Wannaby (body/foot), Augment.

**Two headline 2025–2026 signals:** (1) **8th Wall's hosted platform retired Feb 28, 2026** and was open-sourced *without* VPS/Maps; (2) **Adobe killed Aero (Nov–Dec 2025)**. Both giants concluded general-purpose un-anchored consumer WebAR authoring is a thin business; value is migrating to persistent/spatial anchoring (which Niantic itself redirected toward defense/robotics).

### Per-player breakdown

**8th Wall (Niantic Spatial) — the pivotal case.** Leading hosted WebAR platform (founded 2018, acquired by Niantic 2022): cloud editor + XR Studio, SLAM world-tracking, image targets, face/sky effects, hosted **Location AR (VPS)** + Lightship Maps, all to the mobile browser (no app). **Anchored + un-anchored historically.** Pricing (historical): Starter $9.99/mo, Plus $49/mo; **commercial licenses cut $3,000/mo → $700/project/mo (Sept 4, 2024)** — a ~75% reduction widely read as a demand/affordability signal; hosted VPS metered at ~25k calls/mo free then ~$10/1,000 calls (now historical). **Current: no paid plan — all subscriptions ended Feb 28, 2026.** Engine went open-source at 8thwall.org: **MIT** core + Face/Image/Sky effects; **binary-only** SLAM (Jan 2026); **VPS, Maps, Hand Tracking NOT included anywhere** — the hard anchored capability was withdrawn. Self-hosting now required. Existing experiences run until ~Feb 28, 2027 (per press; official blog didn't restate — flag). Deepest brand/agency roster in WebAR (CPG, entertainment, retail, sports). **Market reaction:** framed as "a shutdown dressed as open-sourcing" — good for hobbyists, bad for commercial/anchored users; competitors immediately positioned as "the 8th Wall alternative."

**Niantic Lightship VPS → Niantic Spatial.** The VPS powering cm-scale 6DoF against Niantic's pre-mapped world — the reference standard for real location-anchored AR; works GPS-denied/indoors. **Fully anchored.** Lightship ARDK historically free to develop; VPS metered. **The pivot:** Niantic Spatial's Localize/VPS page now targets **Defense, Robotics & Autonomy, Intelligent Field Operations — not consumer WebAR.** Corporate: sold games to **Scopely for $3.5B** (agreed Mar 2025, closed May 29, 2025); Niantic Spatial spun out with **$250M** capitalization; **VPS at ~1M production locations.** The best consumer location-AR stack walked away from consumer AR.

**Snap — Lens Studio / Local Lenses / Specs (strongest anchored consumer play).** Free Lens Studio authoring, Camera Kit embeds, **Local Lenses** (persistent shared world-anchored AR), and **Specs** (2026 consumer AR glasses). **Genuinely anchored** — plus a **multi-year partnership + $15M investment into Niantic Spatial (June 10, 2025)** bringing VPS/scanning into Lens Studio/Snapchat/Specs (cm-level, city-scale). Monetization = AR advertising (sponsored Lens ads historically ~$500k premium, now as low as ~$10k entry per Digiday). **Specs: $2,195**, $200 deposit, ships fall 2026 (US/UK/France). ~300M daily AR engagers, 4M+ Lenses, ~350–400k AR developers. Reaction: the VPS deal flagged as a potential big moment for persistent city-scale AR; $2,195 widely called dev-grade.

**Zappar / ZapWorks.** UK WebAR pioneer (~2011); ZapWorks/Mattercraft full XR platform. **Mostly un-anchored** (image/surface/face); VPS gated in newer Mattercraft. Pricing (live): Developer ~$12.99/mo; **Pro (commercial) ~$315/mo** (£250), 3 seats, 12k views/yr; Enterprise custom. Deepest brand roster here: Sony, Disney, Marvel, Coca-Cola, Crocs, Nestlé, Unilever, Pfizer, H&M, PepsiCo, Mondelez, LEGOLAND. **Acquired by Infinite Reality for $45M (2024)** — the high-water exit of this cohort (modest).

**ARLOOPA.** Armenia-founded AR studio + no-code Studio + consumer viewer; museums/education/tourism tilt. **Anchored** — marker, markerless, AND location/geospatial via Google Geospatial + Immersal VPS (rented stacks). Pricing: Free + ~$15/$79/$299/mo (aggregator-sourced — flag); White Label $5,999 setup. Long-running indie, no public funding.

**Onirix.** Spanish no-code web-AR; tourism/culture/retail. **Anchored (cleanest pure-play)** — Onirix Spatial AR (VPS) + Area Targets/Wayfinding. Pricing (aggregator, page 403'd — flag): Starter ~€45/mo, Professional ~€299/mo, Enterprise custom. Founded 2017, **~$800k raised** (Seed Feb 2022). Small, capital-light, respected serious VPS vendor.

**HOVARLAY.** Singapore no-code WebAR for **product packaging/print** (QR/marker → interactive AR, remote-updatable). **Un-anchored** (no GPS/VPS). Pricing (live): Free; **Starter $9/mo per SKU; Pro $59/mo per SKU; Enterprise from $2,500/mo** — unusual per-SKU model. ~50 small SE-Asia brands. Sub-scale, no funding found.

**Adobe Aero — DISCONTINUED.** No-code AR authoring (launched ~2019), surface/image-anchored, bundled into Creative Cloud. **Shutdown:** Nov 6, 2025 removed from stores; Dec 3 access ends + .real files stop; Dec 16 server data deleted. Adobe: "the AR landscape has changed since 2020." Strong negative signal for general consumer WebAR authoring.

**MyWebAR (DEVAR).** No-code "Canva for AR" (QR/marker/surface/face), browser-based. **Mostly un-anchored**; top tiers add "3D object + spatial tracking" (closest to anchored, but not a confirmed cross-session VPS). Pricing (live): Free (100 views/yr, no commercial); **Pro $39/mo; Ultimate $399/mo (white-label); Ultimate Plus $999/mo (spatial/object tracking); Phygital $1,199/mo.** Customers: McDonald's, Siemens, Colgate, Nasdaq, PwC, Duke, Yale. **300,000+ users (Dec 2025).** Leading mass-market self-serve, low-ACV/volume play.

**Vectary.** Browser 3D design studio ("Figma for 3D") + WebAR publisher + GenAI 3D (founded 2014). **Un-anchored.** Pricing: Free; Pro AI $25/mo; Business custom. >1M users (self-reported); ~$9.8–14.4M raised. Accessible low-cost on-ramp; small.

**Echo3D.** Cloud 3D/AR/VR **CMS + CDN** for developers (formerly echoAR). **Anchoring N/A** (infra). Pricing (live page JS-only — flag): Free (10 credits/mo); pay-as-you-go ~$0.50/credit; white-label one-time $10,000. **$4M seed (Konvoy) + $5.5M (Qualcomm Ventures, 2022).** Credible niche dev-infra; never mainstream commerce.

**Sketchfab (Epic Games).** Dominant 3D model hosting/viewing + historic marketplace; acquired by Epic July 2021. **Un-anchored** ("View in AR" = USDZ/Scene Viewer). **Store closed**; selling migrated to **Fab** (Epic's unified marketplace) through 2025; free viewer + APIs remain. ~5M users / ~4M models at acquisition. 2024–25 Fab consolidation drew backlash from museums/historians over open-access heritage 3D.

**Threekit.** Enterprise **visual commerce** — 3D configurator, real-time photoreal config, Virtual Photographer, AR, DAM. **Un-anchored.** **No public tiers** (quote-based; secondary "~$500/mo" indicative). Customers: Crate & Barrel, Steelcase, Herman Miller. **~$65.5M raised; $35M Series B (Nov 2021) at ~$300M valuation; no raise/M&A since** — reflecting the 3D-commerce cooldown.

**Emersya.** French all-in-one 3D/AR configurator; furniture-strong. **Un-anchored.** No public pricing (annual, contact sales); touts ~35%+ conversion lift. Customers in furniture/home; fabric partners Kvadrat, BruTextiles. Funding/revenue unknown — lean European.

**VNTANA.** 3D content orchestration + DAM with patented optimization (GLB/USDZ pipeline). **Anchoring N/A** (produces AR-ready assets). Quote-based. Customers (fashion-heavy): Adidas (2,500+ shoes), Diesel, Hugo Boss, Deckers, VF Corp. ~$14–15M raised; **small ~$750k debt raises late 2025** — funding winter, still active.

**Google — model-viewer + Scene Viewer + "View in 3D."** `<model-viewer>` (Apache-2.0, the de-facto "3D on a product page" standard) + Scene Viewer (Android/ARCore) + Search 3D. **Un-anchored** (all session-local). **FREE** (ecosystem strategy). model-viewer v4.3.1 (June 2026), actively maintained. Search "3D animals" library trimmed since ~2024 — Google maintains the plumbing, de-invests the novelty.

**Apple — AR Quick Look (USDZ) + Reality Composer / RC Pro.** Built-in iOS viewer (tap-a-USDZ, no app) + USDZ format + Reality Composer → RC Pro (visionOS/iOS authoring). **Mostly un-anchored** (Quick Look session-local). **FREE** (hardware/ecosystem pull). WWDC 2025 deprecated SceneKit (→ RealityKit); authoring consolidated on RC Pro; classic Reality Composer de-emphasized (no confirmed "discontinued" notice — flag). USDZ+Quick Look is the accepted iOS web-AR standard.

**Wanna / Wannaby.** Fashion virtual try-on (sneakers/watches/jewelry/bags). **Un-anchored** (body/foot, not world). B2B licensing; customers Gucci, Lululemon, Allbirds, Loewe, Valentino, D&G; Farfetch. **Ownership chain (brief was stale):** Farfetch acquired Wannaby (~$24.5M, Apr 2022) → Coupang acquired Farfetch (2024) → **Perfect Corp acquired Wannaby (announced Dec 2024, closed early 2025).** 17.5M try-ons in 2024.

**Augment (augment.com).** AR product-viz for CPG field-sales + e-commerce. **Still alive. Un-anchored** (surface-place). Rare public paid tiers: Essentials €9 / Professional €25 per active device/mo; 3D models ~$170–315 each. Customers: Coca-Cola, Siemens, Nokia, Nestlé, Boeing. **Acquired by StayinFront (CPG field-sales CRM) May 14, 2024** — absorbed into vertical software.

### Cross-cutting conclusions

- **Anchored AR is the moat, and pure-plays are thinning:** 8th Wall *withdrew* hosted VPS; Niantic Spatial *redirected* its VPS to defense/robotics; Snap *rented* Niantic's VPS. That leaves Onirix and ARLOOPA as the main commercial WebAR vendors still selling anchored AR — both partly on rented stacks.
- **Two deaths bracket the un-anchored thesis:** Adobe Aero (Dec 2025) + 8th Wall hosted retirement (Feb 2026).
- **Money is modest:** Zappar's $45M exit is the high-water mark; no venture rocket anywhere in this cohort.
- **Platform-native viewers are free and have eaten the bottom:** Google model-viewer/Scene Viewer + Apple USDZ Quick Look make basic "view in 3D" a $0 commodity — squeezing paid un-anchored SaaS from below.

---

## 2. Why Some Died — Failures, Exits, Pivots, and the Lessons

### The case files

**Blippar — the WebAR unicorn that wasn't (administration Dec 2018).** Raised ~$130–140M; the "$1.5B unicorn" tag is a PR artifact (the last real priced valuation was "over $500M," Series D 2016). Operating loss £34.45M (FY2017) while revenue *fell* £8.5M→£5.7M→£2.3M; went bust with ~£51,525 in the bank. A $5M emergency round needed unanimous shareholder approval; **one shareholder (widely identified as Malaysia's Khazanah) vetoed it.** Root cause: **ARKit/ARCore (2017) commoditized Blippar's core moat**, and revenue was pure **campaign-driven** brand activations (no habitual behavior; ~500k downloads behind inflated "65M registered users"). Afterlife: IP bought ~£500k (Jan 2019), relaunched as small B2B SaaS (Blippbuilder). *No verifiable second collapse — it shrank to a niche survivor.*

**Meta Spark — killing a platform with 600k creators (shut Jan 14, 2025).** Announced Aug 27, 2024; shut Jan 14, 2025. **600,000+ creators, 190+ countries**, effects used "billions of times." **Not a usage failure** — Meta killed the third-party creator layer while keeping first-party effects, reprioritizing to AI + wearables against a Reality Labs division losing **~$17.7B in 2024** ($60B+ cumulative since 2020). The tell: Meta will burn ~$17B/yr on glasses hardware but won't fund a free mobile-AR authoring tool — treating AR filters as a commodity engagement feature, not a platform business. *(AI-as-reason is analyst inference; Meta didn't state it.)*

**Niantic / 8th Wall — category leader, retired (Feb 2026).** Announced Nov 20, 2025; **Feb 28, 2026 = end of platform access; Feb 28, 2027 = final hosting cutoff + data deletion.** The hosted *business* dies; the engine survives (MIT face/image/sky + closed-binary SLAM). **VPS, Maps, Hand Tracking NOT open-sourced — they die with the platform.** ~3,000 commercial experiences (Pizza Hut, Nike, LEGO, AT&T), 50,000+ lifetime, must export and self-host. Why: Niantic sold games to Scopely ($3.5B+$350M, closed May 29, 2025) and spun out Niantic Spatial ($250M) to build a "Large Geospatial Model" for enterprise/robotics — branded marketing WebAR is off-mission. The tell: Niantic **kept location/geospatial, discarded marketing WebAR.** *(Corrections: Niantic was NOT acquired by a Saudi company; Scopely (PIF-backed) bought only the games unit. The ~$50M 8th Wall acquisition price is unconfirmed.)*

**Magic Leap — the $3.5B consumer-AR cautionary tale.** Raised ~$3.5B; peaked ~$6.4–6.7B (2019) then crashed to ~$450M mid-2020 (~93% collapse); in 2021 raised $500M at a flat $2B valuation. Magic Leap One ($2,295) shipped with ~50° FOV, judged "neither magical nor a leap," reportedly sold ~6,000 units vs a 1M-unit target (single-sourced). April 2020: ~1,000 layoffs, founder out, pivot to enterprise. **Saudi PIF rescue ≈ $1.2B total** ($450M 2022 + ~$750M 2023–24) — *NOT the ~$2B in the brief.* By July 2024, exited the headset business to become a Saudi-controlled optics IP supplier. *(Correction: the 2024 partner was **Google** for AR optics/Android XR, **not Microsoft**.)* 14 years, no working business model.

**The graveyard (others):** DAQRI (~$275M, $15k enterprise AR helmet, shut 2019, assets to Snap ~$34M — no validated worker need); Meta Portal (couldn't beat Echo Show; Facebook-camera-in-living-room trust problem; cut 2022); Google Glass ("Glasshole" privacy backlash, $1,500, thin apps; enterprise pivot then fully shut Mar 2023); ODG ($58M Series A, burned it without shipping; IP auctioned Jan 2019); Vuzix (~97% off 2021 peak, only ~$6.3M FY2025 revenue); Meta Company (orig. Meta AR, ~$73M, insolvent 2019); Argon.js (didn't fail — *standardized away into WebXR*).

### Synthesis — what the failures tell us

1. **Is location-anchored AR viable yet? No — still pre-product.** The most revealing data point: Niantic, which *owned* the best WebAR platform *and* the best location-AR assets, **kept the geospatial layer, killed the marketing WebAR, and did not open-source the location features.** Location-anchored *web* AR got *less* accessible in 2026. The smart money believes durable value is persistent world-anchoring for **machines/enterprise** — and even those players treat it as years out.

2. **Is AR demand real or campaign-driven? Overwhelmingly campaign-driven.** Every dead consumer/marketing AR business shared one flaw: **revenue from one-off brand activations, not habitual behavior.** Even Meta Spark's 600k creators / hundreds-of-millions reach weren't enough. The whole authoring category capitulated in ~18 months (Spark AR Jan 2025, Adobe Aero Dec 2025, Wikitude, Vuforia Chalk, 8th Wall Feb 2026). **AR is a feature/campaign cost-center, not a durable platform.**

3. **What business models survive?** (a) picks-and-shovels optics/components to whoever wins the device race (Magic Leap, Avegant, struggling Vuzix); (b) enterprise workflow software that *abandons* hardware (Atheer, enterprise Glass/DAQRI); (c) owning the next device + the AI layer (Meta's revealed preference). **What does NOT survive: hosted/free AR authoring/campaign platforms as standalone businesses.** Every one died, was killed, or shrank. → For this product, defensible value must live in **owning the anchoring/data layer** (the one thing the market keeps proprietary and the incumbent abandoned), not in the (commoditizing) authoring tools.

4. **The "glasses are always 2 years away" risk — real, and the central trap.** The graveyard is full of companies that bet the business on consumer AR glasses arriving on schedule and didn't. Even Meta is still pre-mass-market after $60B+ of losses. **Any plan whose payoff depends on consumer AR glasses at scale should treat that as a 3–7+ year, repeatedly-slipping variable, not an imminent catalyst — and must be viable on phones/web in the meantime.** This product's phone-first structure is the correct hedge.

---

## 3. E-commerce "View in 3D/AR" ROI — Is It Real?

**Bottom line (calibrated):** The claim is **partly real but heavily inflated by vendor self-publication and selection bias.** There is a genuine, repeatable effect — AR/3D raises confidence, engagement, and (modestly) conversion, and reduces returns — but the headline numbers (94%, 11x, 65%) are (a) self-reported by parties who profit from AR, and (b) comparisons of self-selected AR *users* vs non-users (correlation, not causal lift). Strip those out and the credible causal effect is a **single-to-low-double-digit % conversion lift and a ~20–40% return reduction** for high-uncertainty, "visualize-in-my-space / on-me" categories.

### The famous numbers, traced to source

- **"94% higher conversion" — Shopify (corporate X, Sept 18, 2020; Shopify "ROI on AR" blog).** Read literally, it compares conversion on *products that have AR content* (merchant-chosen hero SKUs) among shoppers who *interacted* with AR — **textbook selection bias, not a controlled lift.** No methodology/sample/dates published. The figure is then citation-laundered through Snap/Deloitte, Threekit, and agency blogs. **Treat as marketing, not effect size.**
- **Rebecca Minkoff "44% add-to-cart / 27% order / 65% AR order" — Shopify case study.** No sample, dates, control, or methodology; "after interacting with" = AR-users-vs-non-users selection bias. Most-quoted stat in the space and it's vendor anecdote.
- **Houzz "11x more likely to buy" — Houzz president, reported by CNBC (Jun 8, 2018) and Retail Dive.** Reported independently, but classic selection bias (people who place a 3D sofa are deep-funnel). Directional, not a sitewide lift.
- **Build.com "22% lower return rate" on the *same product* — Mobile Marketing Magazine / AR Insider (Sep 2021).** **The most credible single data point** — the "same product" comparison controls for product mix. Still AR-users-vs-non-users, so likely overstated, but the closest to controlled evidence in the corpus.
- **IKEA Place — widely cited, poorly sourced.** The "189% conversion lift" traces to agency blogs (Single Grain), **not** an IKEA source — treat as fabricated/laundered. IKEA has **not** published rigorous public conversion/return data; academic coverage is a teaching case, not an outcomes study.
- **Apple AR Quick Look — no first-party ROI numbers exist.** Apple provides the tech and a gallery, not data.
- **Wayfair "View in Room 3D" — heavy investment, no public ROI data.** Quoted "20% return reduction" appears only in vendor/agency roundups with no Wayfair primary link.
- **Gucci × Snapchat — +188% PDP views, +25% purchase intent, 18M+ reach (Snap-published).** This is *social-AR advertising* reach/intent, not on-site PDP conversion. "Purchase intent" is a survey proxy.
- **Nike Fit "~28% fewer size returns" — circulates in tech press (Dezeen/Engadget/eMarketer 2019), not clearly Nike-published.** Plausible mechanism, weak provenance.
- **Pure-vendor studies (Threekit 40%/250%, VNTANA 2x/Diesel +70%, Emersya 50%, SeekXR 25%) — treat as advertising.** Selection-biased, recycled, no audits.

### Independent / academic evidence (the part that matters)

- **Snap × Deloitte Digital (May 2021, 15,000 consumers):** 56% say AR boosts confidence in product quality; brands with AR 41% more likely to be considered. Snap-funded; measures **attitudes/confidence**, not sales — but confidence is the most defensible AR effect.
- **Google / Think with Google (2021):** ~66% interested in AR for shopping; 98% of users found it helpful. Google-published, attitudinal.
- **Peer-reviewed (2022–2024):** multiple studies + a meta-analysis (Kumar et al. 2022; 19 studies, ~505k individuals) find AR **positively and significantly affects purchase *intention*,** mediated by interactivity, novelty, reduced perceived risk. **Honest caveat:** almost all measure *intention in lab/survey*, not realized conversion on live storefronts. Consensus supports "AR helps," not "94%."

### What to actually believe

| Claim | Credible? | Best estimate |
|---|---|---|
| "94%" / "65%" / "11x" (Shopify/Minkoff/Houzz) | **No** — vendor, selection-biased | Real but far smaller causal lift; single-to-low-double-digit % |
| Build.com "22% fewer returns" (same-SKU) | **Partly** — best-controlled | Real return reduction; magnitude possibly overstated |
| Returns down ~20–40% (furniture/eyewear/cosmetics/footwear) | **Most credible claim** | Genuine, mechanism-backed |
| Academic: AR raises purchase *intention* | **Yes** (lab/survey) | Robust on intention; weaker on realized revenue |
| IKEA "189%", Wayfair "20%", Apple ROI | **Unverified** | No usable primary source |

**Strongest where:** big-ticket "visualize-in-my-space" goods — **furniture/home first**, then try-on (eyewear, cosmetics, footwear). **Weakest:** small/standardized/commodity goods and apparel where fit isn't the blocker. **No major retailer has published a proper randomized A/B test of on-site view-in-3D conversion lift** — build the business case on **return reduction + a conservative single-to-low-double-digit conversion lift**, and demand a real A/B test before believing any specific number.

---

## 4. Go-To-Market & Pricing — the Central Question

*Convention: **[CITED]** = sourced; **[REASONING]** = inference, flagged.*

### 4.1 Cold-start / chicken-and-egg

The SMB's skepticism about the **anchored** product is *correct on the merits*: nobody wears AR glasses yet, and storefront/awareness QR scan rates are low single digits. Any pitch leaning on "passersby will scan your sign" loses in 2026. Lessons from comparables:

- **Pokémon GO sponsored locations** is the one *proven* location-network model — and it's the opposite of this product: Niantic seeded with a **free consumer game first** (demand), then sold footfall at ≤$0.50/daily-unique-visitor. **[CITED]** **Location AR monetizes only after you own consumer demand** — which this product doesn't and won't (via glasses) for years.
- **Niantic Lightship VPS** reached ~1M locations but produced no consumer hit beyond Niantic's own games — **a persistent world map with no native consumer app is a developer toy, not a business.** The single most important cautionary tale for the anchored product. **[CITED + REASONING]**
- **Snap Local Lenses / Custom Landmarkers** anchor AR to storefronts and have scale (2.5M lenses, 3.5T views) — but only because they ride Snap's existing 400M+ DAU app. **[CITED]**
- **Google Maps Live View** is the rare anchored-AR product with real adoption — because it's bolted onto Maps' billion-user base and solves a *utility* (wayfinding), not a novelty. **[CITED]** **Anchored AR survives as utility on an existing platform; dies as standalone novelty.**
- **Foursquare** is the cleanest "consumer cold-start failed → pivot to data" story (City Guide sunset Dec 2024; survived as a location-data/attribution API business). **[CITED]** Validates the "accumulate analytics" instinct — but points the value at **aggregate B2B data/attribution**, not a single SMB's scan dashboard. **[REASONING]**
- **Nextdoor** is the best *positive* playbook: launched 5 neighborhoods, hand-seeded to 176 pre-launch, gated on a **local champion** (recruit 9 neighbors in 21 days or the neighborhood is cut). **[CITED]** → Seed location density **geographically dense, one walkable cluster at a time, with a local champion** — pick one shopping district/mall/main street, sign every storefront, make that block the demo.

**Did QR behavior stick? Yes — but only at points of intent.** ~75% of US full-service restaurants use QR menus (2025); ~2.9B QR users globally; menus/check-in see 70%+ scan rates. **But awareness signage (posters, storefronts) sits at low-to-mid single-digit scan rates (OOH QR conversions ~0.5–4%).** **[CITED]** → Anchored AR gets real scans when the marker sits at a **point of intent** (menu, product shelf, ticket counter), not as ambient street art. **[REASONING]**

### 4.2 Pricing models in this market — who pays, for what

**WebAR SaaS comps reveal a structural trap — view-metering:**

| Platform | Free | Entry | Top | Meters on views? |
|---|---|---|---|---|
| 8th Wall (historical) | trial | — | $3,000→$700/project/mo | per-project |
| MyWebAR | 5 proj, 100 views/yr, watermark, no commercial | $39/mo (120k views/yr) | $999–$1,199/mo + Enterprise | **yes** |
| Zappar/Zapworks | trial | ~€240–315/mo commercial, 12k views/yr, ~$20/extra 1,000 views | enterprise | **yes (overage)** |
| Hololink | — | tiered, **unlimited-view** positioning | — | **no (differentiator)** |

**Key insight:** incumbents meter on views, which is hostile to seeding density — virality *punishes* you with overage (Zappar's $20/1,000-extra-views). Hololink's deliberate unlimited-view stance is a direct reaction. **[CITED]** **→ For a seed-density strategy, view-metering is the wrong axis. Charge on capabilities/persistence/locations so virality is free advertising, not a bill.** **[REASONING]**

**3D-commerce comps (un-anchored monetization):** Threekit/VNTANA/Emersya are all **enterprise, quote-based, no self-serve**, justified by ROI (Threekit ~40% lift; Emersya ~50% more likely to buy; Shopify 94% / 22–40% returns). **[CITED]** The white space is **self-serve SMB 3D-commerce** at a price an indie Shopify store will swipe a card for. **[REASONING]**

**QR-code SaaS ("boring landing page is a real business"):** Uniqode/Beaconstac **$5/$15/$49/$99/mo**; Flowcode Pro from $5/mo. **[CITED]** Businesses already pay $5–$99/mo for dynamic QR + analytics + an editable hosted page. **The un-anchored "view in 3D" widget is a richer version of exactly that and can be priced in the same band, charge-from-day-one.** **[REASONING]**

**Freemium vs trial vs land-and-expand benchmarks:**
- Freemium free→paid: 3–5% good, 8–12% great; ~5.6% average; ¼ convert below 2.5%. SMB-specifically 3–10%. **[CITED]**
- **Card-gated (opt-out) trials convert ~31% vs ~8.9% opt-in vs ~5.6% pure freemium — ~5–6x better.** **[CITED]**
- SMB SaaS churn is structurally high (3–7%/mo); ~43% of losses in the first 90 days; strong onboarding (<7-day time-to-value) cuts churn ~50%. **[CITED]**

→ Open freemium on the *paid* (un-anchored) product bleeds into the 3–5%/high-churn trap. **Use a card-gated trial on the paid widget; reserve true "free forever" for the *anchored* seeding tier.** **[REASONING]**

### 4.3 Stress-testing the core hypothesis

> *Monetize un-anchored early; give anchored free to seed density + accumulate analytics; convert anchored to paid once you can show owners their numbers.*

**Sound:** monetizing un-anchored early (proven ROI + $5–$99 QR-SaaS band); free anchored as *seeding* (mirrors every successful location network — Niantic's free game, Snap/Google's free features on existing apps, Nextdoor's hand-seeding); "accumulate interaction data as the long-run asset" (the Foursquare survival move — data → B2B/attribution). **[CITED]**

**Failure modes, ranked:**
1. **Analytics too thin to justify a charge (HIGH).** Storefront/awareness scan rates are single-digit-%; a free anchored SMB often sees a *small* number. "47 scans this month" can *kill* the upsell — the same dynamic where a restaurateur's $350/mo Yelp ad brought "<5 trackable customers" and felt like a costly gamble. **[CITED]** **Analytics-as-the-hook only works when the number is big enough to impress — and ambient anchored AR usually won't be.** **[REASONING]**
2. **Free users never convert (HIGH).** Freemium converts 3–5%; "free forever for a thing they're skeptical of" likely converts below that. Need a concrete *trigger* that removes the free version's utility, not a persuasive dashboard. **[CITED]**
3. **Glasses never arrive / arrive late (MEDIUM-HIGH, but hedged).** Orion is non-consumer; endgame is years out. The phone-WebAR hedge is correct — but it means **the anchored product must be justifiable on phone-AR economics alone**, where it competes with a plain QR landing page that's cheaper and already works. **[REASONING]**
4. **Density never reaches "scan the next sign" threshold (MEDIUM).** Lightship's 1M locations with no breakout app shows density alone doesn't create demand; Nextdoor's answer is extreme *local* density + a champion. **[CITED]**

**What comparables say about the conversion lever:** "analytics as upsell" works — but the successful pattern (Amplitude, usage-based SaaS) is **"upgrade when you hit a real usage limit / your usage grew,"** not "pay because we'll show you a vanity metric." **[CITED]** Local-SMB willingness to pay for *foot-traffic analytics* is weak (Yelp/Google Business give analytics free). **→ Don't bet the anchored upsell on analytics. Bet it on capability gates** (persistence, branded markers, multi-location, editing, watermark removal); let analytics be a *supporting* point. **[REASONING]**

### 4.4 The 8th Wall migration wedge

**Real and sizeable, but time-boxed:** access/new-account creation ended Feb 28, 2026; hosted campaigns run to Feb 28, 2027, then offline + data deleted. **[CITED]** ~3,000 commercial experiences (50k+ lifetime) must migrate in a ~12-month window — a genuine refugee pool.

**Crowded:** explicit "8th Wall alternative/migration" campaigns already running from at minimum **AR Code, ARLOOPA (a literal `/8th-wall-migration` page), Blippar (comparison pages), Zappar/Mattercraft, HOVARLAY, Kivicube, Glamar, Remix Reality.** **[CITED]** Saturated — every WebAR vendor is fishing the same pond.

**Durability: low-to-moderate as a standalone strategy.** **[REASONING]** It's a one-time pulse (closes by ~mid-2027); the refugees skew enterprise/agency (feature-parity world-tracking), not the SMB beachhead, and incumbents court them with deeper feature sets. **However** it's a cheap, high-intent awareness/credibility on-ramp: rank for "8th Wall alternative," capture the slice that wants *no-code + simple hosting + good pricing* (where incumbents over-serve/over-price), convert them, and cross-sell the un-anchored commerce widget. **Treat it as a launch accelerant + SEO/credibility play, not the franchise.** The franchise is SMB un-anchored 3D-commerce + locally-seeded anchored.

---

## 5. Market Size & Timing

### 5.1 TAM / SAM

**Top-down AR numbers are hype — use only as context.**

| Metric | Estimate | Source | Caveat |
|---|---|---|---|
| Overall AR market | ~$140–153B (2025) → ~$2.3–3.5T by 2034–35, CAGR ~35–37% | SNS Insider; Fortune Business Insights | **Hype.** Bundles hardware/enterprise/HUDs/gaming; extrapolated CAGR, not bottoms-up. Discount heavily. |
| AR Cloud | $4.18B (2024) → $33.1B (2030), CAGR 41% | Next Move Strategy | Adjacent (spatial-anchoring infra). |
| 3D e-commerce | $3.1B (2024) → $21.5B (2034), CAGR 21.3% | Market.us | The honest adjacent category. |
| AR in e-commerce | $5.88B (2024) → $38.5B (2030), CAGR ~35.6% | Grand View; Market.us | Blends tooling/services/GMV. |

**Bottoms-up SAM (the number to lead with):**

- **Universe:** US small businesses 34.8M (SBA, Nov 2024) — but 27M+ are solo/non-employer; addressable "storefront or sells products" is far smaller. Global SMEs ~358M (Statista 2023). **E-commerce stores — cleanest beachhead:** ~4.8M Shopify stores (Q2 2024), ~2M active merchants, ~90% small; total addressable online stores globally ~20–30M, only a subset selling AR-relevant visualizable goods.
- **ARPU benchmark:** typical SMB SaaS app $10–50/mo → $120–600/yr (grounded in QR-SaaS $5–$99/mo + SMB marketing spend 5–10% of revenue / $10k–$50k/yr). **[CITED]**

| Beachhead segment | Addressable | ARPU/yr | Pool |
|---|---|---|---|
| Shopify stores selling AR-relevant goods | ~0.5–1.0M (10–20% of 4.8M) | $120–600 | ~$300M/yr |
| US local businesses wanting AR signage/marketing | ~2–4M of 34.8M (employer+storefront subset) | $120–600 | ~$400M/yr |
| Global online stores (all platforms) | ~3–5M | $120–600 | (overlaps above) |

**Realistic global SAM ≈ $0.5–1.5B/yr ARR** *before* assuming any single vendor captures it. At 1–5% penetration of the online-store beachhead, a credible **5-year obtainable target is ~$10–50M ARR.** This is 2–3 orders of magnitude below the top-down "$2–3T" — and it's the number that survives scrutiny.

**Skeptic's note:** WTP for "AR" *specifically* is unproven at SMB scale. SMBs pay for **outcomes** (conversion lift, fewer returns, foot traffic), not "AR." The return-reduction thesis is the credible hook; "cool AR signage" is weaker novelty WTP.

### 5.2 AR glasses adoption timing (the endgame dependency)

**Critical distinction: AI glasses (camera+audio, no display) are selling; AR glasses (display + world-anchoring) are barely shipping.** The anchored endgame needs the *second* category.

**Display-LESS AI glasses (succeeding — but cannot render anchored AR):** Ray-Ban Meta / Oakley Meta **~9M cumulative sold** since Oct 2023 (~7M in 2025 alone; EssilorLuxottica, Feb 2026). Meta+EssilorLuxottica ~82% of the smart-glasses market; bringing forward 10M units/yr capacity. IDC: display-less +167% YoY, **13.6M units (2026) → 27.3M (2030).** **No world-anchored display — irrelevant to anchored AR signage.**

**Display / world-anchoring AR glasses (the actual dependency — barely shipping):**
- **Meta Ray-Ban Display ($799, Sept 2025):** monocular *HUD*, US-only at launch — a notification HUD, **not** full world-anchored AR; constrained volumes.
- **Meta Orion (true binocular world-anchored AR):** **prototype only, never for sale** (~1,000 units, ~$10k each, no scale supply chain). Consumer Orion-class ~2027 *at earliest*, likely later; Meta says it "won't be Orion."
- **Snap Specs ($2,195, fall 2026):** real world-anchored AR (51° FOV), US/UK/France — but the price makes it dev/enthusiast niche.
- **Apple:** Vision Pro is a commercial miss (production cuts, development reportedly paused); pivoting to smart glasses, leaks point to a **display-less** first product ~2026; AR-display glasses are a later, undated bet.
- **Google Android XR / Samsung:** Galaxy XR / Project Moohan shipped Oct 2025 at $1,799 — a *headset*, not glasses. Samsung smart glasses (with/without display) expected 2026.

**Analyst installed-base (smart glasses, display + display-less combined):** IDC 2.7M (2024) → 10.6M (2025) → **80M+ installed base by 2030 — but dominated by display-less AI glasses.** Display-equipped AR glasses gain "meaningful traction by 2027." **The display-AR installed base by 2030 is plausibly only single-digit-to-low-tens of millions, heavily skewed to HUD-class, not full world-anchoring.**

### 5.3 Timing verdict

**"Phone now, glasses later" is the right structure — with "later" load-bearing and meaning ~2028–2032 for world-anchored AR, not 2026–2027.**

- **Phone WebAR is the right beachhead today:** works on ~every smartphone, no app; QR-scanning mainstream; SMB WTP at $10–50/mo established; realistic SAM ($0.5–1.5B/yr; ~$10–50M obtainable ARR) reachable **with zero glasses dependency.** Build the business on phone economics alone — glasses are pure upside, never the plan-of-record.
- **HUD-class display glasses:** meaningful traction ~2027–2029; could reach 10M+ installed ~2028–2030 — but a HUD shows notifications, not world-anchored 3D signage.
- **True world-anchored AR (Orion/Specs-class — the actual enabler):** prototype or $2,195 niche today. Mass-market, consumer-priced, world-anchored glasses realistically **~2028–2030 for early adoption (10M+) and ~2031–2034 for mass (50M+)** — price must fall from $800–$2,200 to sub-$500, historically multiple ~2-year hardware generations.

**Risk:** for world-anchored AR *signage*, the endgame is closer to **4–8 years out, not 2–3.** Vision Pro's flop and Orion's unshippability are direct evidence even Apple/Meta are years away. **Mitigation (built in):** because phone WebAR is self-sustaining, glasses-timing is *optionality risk, not survival risk*. Keep the 3D-asset/anchoring layer device-agnostic; underwrite the company on phone-only revenue. **Defensible plan: a phone-first SMB conversion/signage tool that happens to be glasses-ready — not a glasses platform that happens to start on phones.**

---

## 6. Concrete Pricing Recommendation

**Design principles (evidence-backed):** charge on the un-anchored side (proven WTP); use free *only* to seed anchored density; **never meter on views** (it punishes virality — Hololink's wedge, Zappar's pain); prefer a **card-gated trial over open freemium** on paid tiers (~31% vs ~5.6%); gate the anchored upsell on **capability/persistence**, not vanity analytics.

**UN-ANCHORED "View in 3D" widget — charge from day one (this is the business):**
- **Free trial (card-gated, 14-day):** full features, then convert (~5–6x better than open freemium).
- **Starter ~$19–29/mo:** a few 3D products, **unlimited views**, view-in-3D/AR button, basic engagement analytics, light watermark. Priced just above the QR-SaaS band ($5–$99) because you deliver more (3D, not a static page).
- **Growth ~$99–149/mo:** more SKUs, no watermark, conversion/return analytics, Shopify/e-com embed. Anchored to the return-reduction + conservative-lift ROI story — value-based, easily justified for a store with real volume.
- **Enterprise — quote:** unlimited SKUs, SSO, attribution feed. Undercut Threekit/VNTANA/Emersya's quote-gated model with self-serve below it.

**ANCHORED real-world AR — free to seed, convert on capability not analytics:**
- **Anchored Free (forever — the seeding tier):** one location, phone-WebAR via QR marker, **unlimited views**, watermark, generic marker, basic scan counts. The Nextdoor-style density seeder — deploy cluster-by-cluster with a local champion.
- **Conversion triggers (capability gates, priority order):** (1) **branded image-marker** (their logo/sign as the scannable target — removes the "ugly QR on my storefront" objection); (2) **persistent owner-seeded per-location map** (precise persistent anchoring — the moat, the thing free can't do well); (3) **multi-location / chain management**; (4) **watermark removal + editable content + scheduling**; (5) analytics as a *supporting* upsell, not the trigger.
- **Anchored Pro ~$29–79/location/mo** once a trigger is hit; bundle discounts for chains (mirrors multi-location local SaaS + 8th Wall's per-project licensing).

**8th Wall migration:** run it as a **time-boxed acquisition campaign** (dedicated "8th Wall alternative" landing page + free migration help + first-year discount), not a tier. Win on **no-code simplicity + unlimited views + transparent SMB pricing** — the gap incumbents leave. Capture refugees into the *un-anchored paid* product, use their logos for credibility, then cross-sell anchored.

**The data play (Foursquare hedge):** aggregate anchored interaction/map data is a separate, longer-horizon B2B asset (attribution, footfall, location intelligence) — bank it, but do **not** make any single SMB's thin scan dashboard carry the anchored upsell.

---

## Sources

*All accessed 2026-06-25 unless noted. Vendor-published and syndicated-report figures are flagged inline above as low-confidence; treat ARR/revenue/funding totals from GetLatka/Tracxn/Crunchbase as unaudited estimates.*

### Landscape — 8th Wall / Niantic Spatial
- https://info.nianticspatial.com/blog/8th-wall-open-source
- https://www.8thwall.com/blog/post/208587408737/8th-wall-open-source
- https://8thwall.org/ ; https://8thwall.org/docs/migration/faq
- https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/
- https://ar-code.com/blog/8th-wall-is-shutting-down-timeline-impact-and-the-best-8th-wall-alternative-for-webar
- https://www.8thwall.com/pricing ; https://forum.8thwall.com/t/big-news-lower-pricing-for-8th-wall-commercial-licenses/2652
- https://www.8thwall.com/products/location-ar
- https://en.wikipedia.org/wiki/Niantic_Spatial ; https://nianticlabs.com/news/nianticspatial
- https://www.nianticspatial.com/products/localize ; https://lightship.dev/docs/ardk/features/lightship_vps/

### Landscape — Snap
- https://newsroom.snap.com/introducing-specs-augmented-reality-glasses ; https://newsroom.snap.com/launch-specs-2026
- https://www.nianticspatial.com/blog/vps-snap-investment ; https://roadtovr.com/snapchat-niantic-spatial-partnership-vps/
- https://ar.snap.com/lens-studio ; https://ar.snap.com/camera-kit
- https://digiday.com/marketing/500k-snapchats-ar-ads-now-cheap-luring-smaller-advertisers/

### Landscape — other platforms
- Zappar: https://zap.works/pricing/ ; https://www.crunchbase.com/organization/zappar
- ARLOOPA: https://www.arloopa.com/ ; https://studio.arloopa.com/pricing ; https://studio.arloopa.com/learn/how-to-create-location-based-ar
- Onirix: https://www.onirix.com/ ; https://www.onirix.com/pricing/ (403)
- HOVARLAY: https://hovarlay.com/ ; https://hovarlay.com/pricing/
- Adobe Aero: https://helpx.adobe.com/aero/using/whats-new.html ; https://community.adobe.com/questions-82/announcing-adobe-aero-end-of-support-1219182 ; https://www.xrtoday.com/augmented-reality/end-of-an-era-adobe-pulls-the-plug-on-aero-as-ar-industry-reality-bites/
- MyWebAR: https://www.mywebar.com/pricing ; https://mywebar.com/blog/important-changes-to-mywebar-subscription-plans/
- Vectary: https://www.vectary.com/pricing/ ; https://www.trendingtopics.eu/slovak-vectary-closes-7-3m-investment-round/
- Echo3D: https://www.echo3d.com/pricing ; https://www.crowdfundinsider.com/2022/07/193031-echo3d-secures-5-5m-in-funding-from-qualcomm-ventures/
- Sketchfab/Fab: https://techcrunch.com/2021/07/21/epic-games-acquires-sketchfab-a-3d-model-sharing-platform/ ; https://www.fabbaloo.com/news/epic-games-phases-out-sketchfab-in-2025-launches-unified-fab-marketplace ; https://80.lv/articles/historians-are-concerned-about-epic-games-sketchfab-to-fab-migration
- Threekit: https://www.threekit.com/pricing ; https://www.prnewswire.com/news-releases/threekit-raises-35m-to-fuel-growth-of-3d-visual-commerce-platform-301419474.html
- Emersya: https://www.emersya.com/pricing-model/
- VNTANA: https://www.vntana.com/ ; https://en.wikipedia.org/wiki/Vntana
- Google: https://github.com/google/model-viewer ; https://developers.google.com/ar/develop/scene-viewer ; https://9to5google.com/2024/04/30/google-3d-animals-list/
- Apple: https://developer.apple.com/augmented-reality/quick-look/ ; https://developer.apple.com/reality-composer-pro/ ; https://dev.to/arshtechpro/wwdc-2025-scenekit-deprecation-and-realitykit-migration-...
- Wanna/Wannaby: https://www.businesswire.com/news/home/20241223074584/en/Perfect-Corp.-Acquires-Fashion-Tech-Innovator-Wannaby ; https://www.retaildive.com/news/perfect-corp-acquires-wannaby-farfetch-virtual-try-on-tech/736230/
- Augment: https://www.augment.com/pricing/ ; https://www.stayinfront.com/stayinfront-acquires-augmented-reality-software-leader-sas-augment/

### Failures
- Blippar: https://techcrunch.com/2018/12/18/after-130m-in-funding-ar-startup-blippar-collapses/ ; https://techcrunch.com/2018/12/10/ar-startup-blippar-in-danger-...; https://www.engadget.com/2018-12-18-ar-blippar-administration.html ; https://uk.finance.yahoo.com/news/tech-startup-blippar-worth-1bn-went-bust-just-50000-bank-121847102.html ; https://www.campaignlive.com/article/ar-specialist-blippar-ran-losses-34m-administration/1562619 ; https://techcrunch.com/2021/03/23/...-blippar-is-back-with-5m-in-funding-and-a-b2b-model/
- Meta Spark: https://spark.meta.com/blog/meta-spark-announcement/ ; https://techcrunch.com/2024/08/27/creators-are-angered-by-metas-spark-ar-shutdown-...; https://www.shacknews.com/article/142903/facebook-meta-fy-2024-reality-labs ; https://www.meta.com/blog/meta-ray-ban-display-ai-glasses-connect-2025/
- Niantic/8th Wall: https://www.remixreality.com/8th-wall-to-shut-down-after-seven-years-of-advancing-webar/ ; https://techcrunch.com/2025/03/12/pokemon-go-maker-niantic-is-selling-its-games-division-to-scopely-for-3-5b/ ; https://nianticlabs.com/news/niantic-next-chapter ; https://techcrunch.com/2022/03/10/...-niantic-is-acquiring-webar-development-platform-8th-wall/
- Magic Leap: https://en.wikipedia.org/wiki/Magic_Leap ; https://techcrunch.com/2021/10/11/...-magic-leap-raises-500m-at-a-2b-valuation/ ; https://www.bloomberg.com/news/articles/2024-08-06/saudi-arabia-s-pif-provided-750-million-to-depleted-ar-startup-magic-leap ; https://www.engadget.com/2019-12-06-magic-leap-6000-headsets-sold-report.html ; https://9to5google.com/2024/05/30/google-magic-leap/ ; https://moorinsightsstrategy.com/research-notes/magic-leap-exits-headset-market/
- Others: https://techcrunch.com/2019/09/12/another-high-flying-heavily-funded-ar-headset-startup-is-shutting-down/ (DAQRI) ; https://variety.com/2022/digital/news/meta-portal-consumer-video-calling-phased-out-1235289891/ ; https://www.cnbc.com/2023/03/15/google-discontinues-google-glass-enterprise-end-to-early-ar-project.html ; https://techcrunch.com/2019/01/10/an-ar-glasses-pioneer-collapses/ (ODG) ; https://www.investing.com/news/company-news/vuzix-reports-2025-revenue-growth-narrows-annual-loss-93CH-4558433 ; http://argonjs.github.io/

### E-commerce ROI
- https://www.shopify.com/blog/ar-shopping ; https://www.shopify.com/case-studies/rebecca-minkoff ; https://x.com/Shopify/status/1306973590814949376
- https://www.cnbc.com/2018/06/08/houzz-ceo-our-3d-app-makes-users-11-times-more-likely-to-buy-products.html ; https://www.retaildive.com/news/at-houzz-mobile-augmented-reality-is-fueling-sales/525276/
- https://mobilemarketingmagazine.com/case-study-how-buildcom-turned-to-ar-to-increase-customer-engagement-and-sales/ ; https://arinsider.co/2021/09/28/does-ar-really-reduce-ecommerce-returns-2/
- https://developer.apple.com/augmented-reality/quick-look/ ; https://developer.apple.com/videos/play/wwdc2020/10604/
- https://chainstoreage.com/wayfair-dives-deep-ar-3d
- https://forbusiness.snapchat.com/inspiration/gucci-ar-tryon ; https://forbusiness.snapchat.com/blog/the-next-inflection-point-more-than-100-million-consumers-are-shopping-with-ar ; https://www.prnewswire.com/news-releases/deloitte-digital-and-snap-inc-report-...-301290445.html
- https://www.dezeen.com/2019/05/09/nike-fit-app-ar-ai-trainers/ ; https://www.emarketer.com/content/nike-unveils-nike-fit-...
- https://www.threekit.com/3d-and-augmented-reality-stats-and-data ; https://www.vntana.com/case-studies/ ; https://emersya.com/en/articles/interactive-3d-and-ar-for-the-furniture-industry
- https://journals.sagepub.com/doi/10.1177/2043886920947110 (IKEA teaching case) ; https://www.tandfonline.com/doi/full/10.1080/23311975.2023.2208716 ; https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0309468 ; https://www.sciencedirect.com/science/article/pii/S2773067024000219 ; https://link.springer.com/chapter/10.1007/978-981-96-3077-6_58
- https://www.singlegrain.com/digital-marketing/ar-experiences-that-boosted-conversion-rates-by-189/ (agency — flagged unreliable, source of the laundered IKEA 189%)

### GTM, pricing, cold-start
- 8th Wall migration/wedge: https://www.arloopa.com/blog/8th-wall-is-shutting-down-where-to-move-your-webar-projects ; https://studio.arloopa.com/8th-wall-migration ; https://hovarlay.com/augmented-reality-articles/8th-wall-shutting-down/ ; https://www.blippar.com/blippar-vs-8th-wall-which-webar-platform-should-you-choose-in-2026/ ; https://zap.works/mattercraft-for-8th-wall-studio-developers/ ; https://www.kivicube.com/post/augmented-reality-after-8th-wall-shutdown-... ; https://www.glamar.io/alternatives/8thwall
- Pricing comps: https://mywebar.com/pricing/ ; https://www.hololink.io/blog-posts-hololink/choosing-the-right-webar-editor ; https://www.uniqode.com/pricing ; https://www.threekit.com/pricing ; https://www.vntana.com/roundup/best-3d-viewers/
- Freemium/SMB benchmarks: https://firstpagesage.com/seo-blog/saas-freemium-conversion-rates/ ; https://chartmogul.com/reports/saas-conversion-report/ ; https://www.crazyegg.com/blog/free-to-paid-conversion-rate/ ; https://churnkey.co/blog/whats-a-normal-churn-rate-in-saas/ ; https://www.getmonetizely.com/articles/how-to-price-your-data-analytics-and-dashboard-tools-for-small-businesses-... ; https://getlago.com/blog/usage-based-pricing-examples
- Cold-start comps: https://techcrunch.com/2017/05/31/pokemon-go-sponsorship-price/ ; https://www.pymnts.com/news/2017/niantic-charges-pokemon-go-sponsors-up-to-50-cents-per-visitor/ ; https://lightship.dev/products/vps ; https://techcrunch.com/2022/03/16/snapchats-custom-landmarkers-feature-... ; https://blog.google/products/maps/new-sense-direction-live-view/ ; https://www.pymnts.com/connectedeconomy/2022/inside-foursquares-pivot-from-customer-app-location-data-platform/ ; https://www.bu.edu/articles/2011/groupon-bad-for-business/ ; https://www.unusual.vc/how-to-find-the-next-big-business-idea/ (Nextdoor seeding) ; https://about.fb.com/news/2024/09/introducing-orion-our-first-true-augmented-reality-glasses/
- QR adoption/scan rates: https://easymenus.net/blog/qr-code-menu-adoption-statistics-data ; https://www.qrcodechimp.com/qr-code-statistics/ ; https://www.qr-code-generator.com/blog/qr-code-scan-rate-benchmark/ ; https://www.supercode.com/use-case/qr-codes-on-posters
- SMB analytics WTP: https://birdeye.com/blog/state-of-google-business-profiles/

### Market size & glasses timing
- AR market (hype, flagged): https://www.fortunebusinessinsights.com/augmented-reality-ar-market-102553 ; https://www.nextmsc.com/report/augmented-reality-ar-cloud-market
- 3D/AR e-commerce: https://market.us/report/3d-e-commerce-market/ ; https://www.grandviewresearch.com/industry-analysis/augmented-reality-e-commerce-market-report ; https://market.us/report/ar-in-e-commerce-market/
- SMB/e-commerce counts: https://advocacy.sba.gov/2024/11/19/new-advocacy-report-shows-small-business-total-reaches-34-8-million-... ; https://www.statista.com/statistics/1261592/global-smes/ ; https://www.yaguara.co/shopify-statistics/ ; https://seo.ai/blog/how-many-shopify-stores-are-there
- QR/SMB marketing spend: https://www.qrcodechimp.com/qr-code-marketing-guide/ ; https://mercury.com/blog/how-much-should-a-small-business-spend-on-marketing ; https://www.webfx.com/blog/marketing/digital-marketing-budget/
- Glasses sales/timing: https://www.uploadvr.com/meta-essilorluxottica-sold-7-million-smart-glasses-in-2025/ ; https://roadtovr.com/meta-ray-ban-smart-glasses-sales-tripled-2025/ ; https://www.cnbc.com/2026/02/11/ray-ban-maker-essilorluxottica-triples-sales-of-meta-ai-glasses.html (403 on fetch; corroborated by UploadVR/Road to VR) ; https://www.meta.com/blog/meta-ray-ban-display-ai-glasses-connect-2025/ ; https://www.techradar.com/computing/virtual-reality-augmented-reality/meta-orion-ar-glasses-... ; https://roadtovr.com/snap-specs-2026-ar-glasses-release-date-price/ ; https://www.macrumors.com/2025/10/11/vision-pro-future-uncertain/ ; https://roadtovr.com/samsung-galaxy-xr-headset-price-specs-release-date/ ; https://my.idc.com/getdoc.jsp?containerId=prUS53809325 ; https://www.idc.com/resource-center/blog/smart-glasses-surge-the-xr-market-is-rewriting-its-own-rules/

### Verification flags (key uncertainties)
- 8th Wall published-experience cutoff (Feb 28, 2027) from press, not restated on the official open-source blog.
- ARLOOPA/Onirix/Echo3D current pricing is aggregator-sourced or from JS-only pages — verify on live pages.
- IKEA "189%", Wayfair "20%", Apple Quick Look ROI: **no usable primary source** — figures in circulation are unsourced/agency-fabricated. No major retailer has published a randomized A/B test of on-site view-in-3D conversion lift.
- Blippar "$1.5B" = unverified PR; "Khamis" in some briefs = likely confusion with Khazanah. Magic Leap 2024 partner = Google (not Microsoft); Saudi PIF ≈ $1.2B (not ~$2B); 6,000-unit sales single-sourced.
- Top-down trillion-dollar AR TAMs (SNS Insider, Fortune Business Insights) are low-confidence; the bottoms-up SAM (~$0.5–1.5B/yr) is the recommended planning number.
- CNBC EssilorLuxottica article 403'd on fetch; units trajectory corroborated independently.
