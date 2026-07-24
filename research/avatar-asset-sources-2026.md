# Realistic avatar asset sourcing — licensing research (2026-07-23)

> **Scope:** find commercially-clean, affordable sources to raise realism (esp. **skin/texture**) beyond
> the current MakeHuman/MPFB2 + PolyHaven + AmbientCG baseline, for a pipeline that (1) fits Gaussian
> splats to source imagery/scans, (2) may attach corrective MLPs, and (3) **ships the resulting asset to
> end-user browsers**. Every candidate below is graded against all four gates: **commercial / redistribute
> (ship-to-browser) / no-AI-clause / affordable**. Quotes are verbatim from primary sources where a fetch
> succeeded; anywhere a primary fetch failed or a secondary summary had to stand in, it's flagged
> **[UNVERIFIED]** — treat those as leads to re-check by hand, not cleared findings. This is engineering
> research, not legal advice; confirm anything load-bearing with counsel before shipping.

## Acquired / Buy list (2026-07-23) — acquisition pass

Moved from research → acquisition. Everything below was license-verified **verbatim from the actual bundled
license file** (not the marketplace label) before pulling. Staged under the durable gitignored asset area
`dataset/motion_out/assets_src/` with a `PROVENANCE.md` beside each download.

### ✅ DOWNLOADED & STAGED (all free, all license-verified verbatim)

| Asset | License (verified) | Where | Size |
|---|---|---|---|
| **Lee Perry-Smith "Infinite" head** — `.glb` + COL/SPEC/4K-displacement/tangent maps + license file | **CC-BY 3.0**, from the bundled `LeePerrySmith_License.txt` | `assets_src/heads/lee_perry_smith_infinite/` | 2.1 MB |
| **SMOKEWORKS Skins Vol.0** — Hannah + Mike, BaseColor/Normal/ORM PNG @ 4096² | **CC BY 4.0**, from the bundled `licenseagreement.docx` | `assets_src/skins/smokeworks_vol0/` | ~66 MB (PNG) |
| **SMOKEWORKS Skins Vol.1** — Dave + Tinasia + Hwang, BaseColor/Normal/ORM PNG @ 4096² | **CC BY 4.0**, from the bundled `licenseagreement.docx` | `assets_src/skins/smokeworks_vol1/` | ~95 MB (PNG) |

- **Infinite head** pulled from the three.js official example mirror
  (`github.com/mrdoob/three.js/.../examples/models/gltf/LeePerrySmith`) — the canonical clean redistribution
  that ships the license file with the asset. Verbatim grant: *"Infinite, 3D Head Scan by Lee Perry-Smith is
  licensed under a Creative Commons Attribution 3.0 Unported License... Do what you want with the files, but
  always mention where you got them from."* **Attribution required** (Lee Perry-Smith / Infinite-Realities).
- **SMOKEWORKS packs** pulled from itch.io (name-your-own-price, $0 minimum). The itch download is
  JS-gated — the flow that works: request the game page with a **browser User-Agent** (curl's default UA gets
  the shell without the `data-upload_id` download button), grab csrf → POST `/download_url` → GET the
  download-page HTML → read `data-upload_id` → POST `/<game>/file/<upload_id>` for a 60-second signed R2 URL.
  Both packs' bundled `licenseagreement.docx` is **plain CC BY 4.0** (verbatim: credit "Rashad Patterson
  (ZSTUDIOS)", link `https://rpatterson-zstudios.itch.io/`, indicate derivation). itch tags include **no-ai**;
  Vol.1 page: *"No generative AI was used."*
- **5 full PBR skin identities** now staged (sex / age / ethnicity spread), all on the MakeHuman UV → **drop-in**
  for `blender_render_skin.py`'s `build_skin()` (BaseColor→Base Color, Normal→Normal Map, ORM→Occlusion/
  Roughness/Metallic). Directly closes **Immediate-Next §5** (real skin UV vs the current procedural stand-in).

### 🔎 License nuances found on close reading (both cleared, worth recording)
- **Infinite head:** its CC license carries *"Based on a work at www.triplegangers.com"* — this is the CC
  **attribution field** for the scan's origin, **not** a Triplegangers ToS. The governing grant is Lee
  Perry-Smith's CC-BY 3.0; the Triplegangers block (item 13) does **not** apply to this asset. **Clean.**
- **SMOKEWORKS:** the itch page note says *"do not resell the texture files,"* but the **formal bundled
  license is plain CC BY 4.0 and does not contain that restriction.** Embedding a baked skin in a shipped
  avatar was always fine under CC BY; the note only discourages bare resale of the raw pack. **Clean.**
- **No asset in this pass turned out NOT clean on close reading** — the two above are the only nuances, and
  both resolve clean.

### 💰 BUY LIST (for the user — I can't purchase)
Honest result: **the clean, good-looking assets in the D97 shortlist are all free**, so the buy list is thin.
- **Optionally tip the SMOKEWORKS creator** at https://rpatterson-smokeworks.itch.io/skins-vol0 and
  `/skins-vol1` — name-your-own-price; a few dollars supports continued CC-BY skin releases. **Not required**
  (we took them free, license-permitted).
- **No verified paid pack under $100 beats the free haul.** The high-realism paid scan vendors (3DScanStore,
  Renderpeople, Triplegangers, 3d.sk) remain **BLOCKED / CONDITIONAL on the AI-training clause** (see items
  6–9, 13) — do **not** buy these on their standard licenses for this pipeline. The only "spend money" route
  that actually clears the AI gate is the **commission with rights assigned** (~$300–1.5k head / ~$1.5–6k
  body — over the $100/pack budget but the only clean paid path; see "The commission route" below).

### ⏸️ FETCH-LATER (free & clean, not pulled — disk / value)
- **SMOKEWORKS TGA versions** — each pack also ships uncompressed **50 MB TGAs** (~300 MB/pack). Skipped as
  redundant with the staged PNGs; re-download the full `.zip` from itch if ever needed. URL as above.
- **Morgan McGuire Computer Graphics Archive — Infinite-head full SSS map set** (cavity / thickness /
  translucency / curvature / occlusion / derivatives — the channels the three.js version omits). Free,
  CC-BY (McGuire archive). Grab if the extra subsurface channels are wanted for a hero-grade skin bake.
- **AmbientCG / cc0-textures.com "Human Skin 1–6"** (CC0, ~1K–4K tiles, AO/Diffuse/Normal/Height/Rough).
  Free, zero-clause CC0, tiny — **detail/pore overlay only**, not an identity source (item 3). Pull on demand
  when a detail layer is needed; not worth the disk to stage speculatively.

---

## Cross-cutting finding (read this first)

Gate (2) "redistribution" turns out to be the *easier* gate in practice — almost every professional scan
vendor (3DScanStore/Ten24, Renderpeople, AXYZ, Fab/Megascans) sells a "**single for-sale commercial
project**" license that is written to permit exactly what we do: bake/integrate the asset into one shipped
product. Gate (3) — **no-AI/ML-training clause** — is the one now closing off almost the entire
professional human-scan market, and it closed specifically **because of pipelines like ours**. Since
~2023, 3DScanStore, Texturing.xyz, AXYZ, and Renderpeople have all added explicit bans on using their
scans/textures to train "digital humans," "character generators," or run "computer vision research" —
and Gaussian-splat optimization (even per-subject/overfit) plus a corrective MLP is defensibly *exactly*
the kind of "neural network / data train" use these clauses were drafted to stop. Triplegangers went
further and got a public news story out of fighting off an AI-scraping bot. **Don't assume a "single
commercial project" license clears us — check the AI clause specifically, every time**, and prefer
sources where there's no AI-training clause to trip *at all* (true CC0/CC-BY, or content we own outright).

---

## Findings by candidate

### CLEAN

**1. Lee Perry-Smith / "Infinite" head scan (Infinite-Realities / ir-ltd.net)** — ★ best find of this pass
- **License:** Creative Commons **Attribution 3.0 Unported**. Verbatim (MIT-hosted three.js example
  license file, and independently confirmed via the Sketchfab mirror, Blend Swap, and Clara.io mirrors):
  > "licensed under a Creative Commons Attribution 3.0 Unported License... Permissions beyond the scope
  > of this license may be available at http://www.ir-ltd.net/"
  Creator's own plain-language framing on the release page: *"Do what you want with the files, but
  always mention where you got them from."*
- **Gates:** Commercial ✅ (CC-BY has no field-of-use restriction) · Redistribution ✅ (CC-BY explicitly
  permits distribution and derivative works) · AI/ML clause: **none** — this is a bona fide CC license
  issued directly by the rights-holder in 2010, not a marketplace ToS that could carry a bolted-on 2023-25
  AI ban. Attribution ✅ required (credit Lee Perry-Smith / Infinite-Realities). Price: **free**.
- **Realism:** Genuinely scan-grade — this is the asset Pixar used in its public RenderMan
  photorealistic-skin-shading tutorial. Ships lambert/high-res-bump/normal/cavity/thickness/derivatives/
  occlusion/proximity/translucency/curvature maps — a full subsurface-scattering-ready skin map set, not
  just a diffuse color. **Head only**, ~15-year-old topology (will need retopo/retarget to fit our rig,
  and the "used by 100,000+ downloads" ubiquity means it's visually recognizable in CG circles — fine as
  a texture/detail source, less fine as a hero identity to ship verbatim).
- **Verdict: CLEAN.** Best available raise-the-skin-realism-ceiling asset with zero clause risk found in
  this pass. Use as a detail/normal/SSS reference layered onto our own topology, not shipped as-is.

**2. "Skins Vol.0" / "Skins Vol.1" — MakeHuman-compatible skin texture packs (SMOKEWORKS ENT, itch.io)**
- **License:** Creative Commons **Attribution 4.0 International**, confirmed on both product pages.
  Verbatim (Vol.0 creator statement): *"All I ask [is] to credit me and to not resell the texture files.
  Other than that, feel free to modify and use them as you please for any of your personal and commercial
  projects."*
- **Gates:** Commercial ✅ · Redistribution/embedding ✅ (only bare resale of the raw texture files is
  barred — embedding in a shipped avatar is fine) · AI/ML clause: **none** (plain CC-BY 4.0, no
  marketplace ToS layer); pack description explicitly states *"No generative AI was used"* in production
  (photo-based). Attribution ✅ required. Price: **name-your-own-price, free minimum** (donation-based).
- **Realism:** 4K, PBR-workflow, purpose-built for the MakeHuman UV layout we already use — directly
  drop-in with our existing pipeline, higher realism than the CC0 packs currently in use.
- **Verdict: CLEAN.** Immediately actionable — slot into the existing MakeHuman/MPFB2 asset pipeline.

**3. CC0 human-skin texture tiles (cc0-textures.com, "Human Skin 1–6")**
- **License:** CC0 (public domain dedication), no restriction of any kind.
- **Gates:** all four trivially clear — CC0 has no clauses to trip.
- **Realism:** **Low-to-moderate** — these are tileable skin-surface patches (pore/wrinkle detail
  material), not full face/body identity maps. Useful as a **detail/roughness overlay** layered onto a
  base texture (e.g. blended over a MakeHuman diffuse or the Skins Vol.0/1 packs above) rather than a
  standalone identity source.
- **Verdict: CLEAN**, but treat as a detail-layer supplement, not a realism-ceiling raiser on its own.

**4. Stable Diffusion 1.5 / SDXL (self-hosted or via most API providers) for synthesized skin/pore detail**
- **License:** **CreativeML Open RAIL-M**. Verbatim on use scope: *"Use may include creating any content
  with, finetuning, updating, running, training, evaluating and/or reparametrizing the Model."* The
  license's only restrictions are the Attachment A **use-based** bans (illegal use, exploiting minors,
  disinformation, doxxing, harassment, automated high-stakes decisions) — **no clause barring use of
  outputs as texture/training input for a downstream, non-foundational-model pipeline** was found.
  You own the outputs.
- **Gates:** Commercial ✅ · Redistribution (ship baked-in output) ✅ · AI/ML clause: **does not apply to
  our downstream use** — the license restricts what you do *to the model*, not what you do *with a
  generated image* once you own it (using it as a texture, or as a supervision image for our own
  per-subject gaussian fit, is not "training a new foundational model"). Price: **free** (self-host) or
  cheap per-image API credits.
- **Newer models caution:** SD3.5+ ships under the **Stability AI Community License** instead, which adds
  one specific restriction: outputs may not be used *"to train new foundational models"* (LoRAs/finetunes
  of *your own* stuff are fine) — again doesn't touch our per-subject avatar pipeline, but note it, and
  note the **Community License requires an Enterprise agreement above $1M annual revenue** (not a
  near-term concern).
- **Realism:** Depends entirely on the pipeline you build around it — raw prompted output is not
  automatically a usable UV-mapped, multi-channel (albedo/normal/roughness) skin texture set. Best used
  as an **img2img/ControlNet-normal detail synthesizer** applied to an existing MakeHuman/scan base, not
  a one-shot texture generator.
- **Verdict: CLEAN** for the license; realism payoff requires real pipeline engineering, not just a prompt.

**5. Meshy AI, paid tier only (cross-reference: already validated elsewhere in this project)**
- Per `/root/4dgs/research/generation-texture-rigging.md`: **Premium = full rights, sell w/ NO
  attribution; Free = CC BY 4.0 (attribution required) — never the CC-BY free tier** for asset generation.
  Same rule applies here: paid-tier Meshy output for skin/texture generation is commercially clean; the
  free tier reintroduces an attribution obligation we'd rather avoid at scale.
- **Realism:** Mesh-conditioned diffusion texture, not light-stage capture — good for clothing/props/hair
  cards, not yet scan-grade for facial skin pore detail.
- **Verdict: CLEAN (paid tier only)**, already in the project's known-good column; noted here for
  skin/texture-specific use as an extension of the existing decision.

---

### CONDITIONAL (real license text found, but the AI-clause or a technical requirement makes it risky for *our specific pipeline* — don't use without written vendor confirmation)

**6. 3DScanStore / Ten24** (same company — Ten24 is the scanning studio that operates the 3DScanStore shop)
- **Verbatim, paid "Business Commercial Single Project License":** *"Integration of scans into a SINGLE
  for sale commercial project such as video games / movies / virtual reality experiences"* — this text
  would seem to clear gate 2 for us (one shipped product).
- **But, verbatim, all tiers:** *"Sell or freely distribute character generators or digital humans created
  using AI training data derived from 3d scan store models, scans or texture maps"* and *"Resell or
  freely distributing AI training data sets derived either from the 3D models on this site"* are both
  explicitly barred. Also barred: *"Do not sell or distribute any of these 3D models or scans (modified
  or not) by itself... or material/texture packs derived from scans on this site."*
- **Read against our pipeline:** a Gaussian-splat-fit + corrective-MLP avatar built from a 3DScanStore
  scan is arguably exactly the prohibited "digital human created using AI training data derived from
  [their] models." **Do not rely on the standard single-project license for this pipeline.**
- **The one looser thread:** their free sample scans carry a separate, plainer grant — verbatim: *"Feel
  free to use this scan as you wish for both commercial and personal projects. All we ask is that you
  provide us with a credit wherever it's used"* — silent on AI/ML rather than explicitly barring it. Lower
  risk than the paid catalog, but silence isn't permission; get it in writing before relying on it.
- **Realism:** Industry-standard photogrammetry, AAA-game-grade — the highest realism ceiling found in
  this pass, *if* the license risk can be closed.
- **Verdict: CONDITIONAL.** Worth a direct email to Ten24/3DScanStore asking explicitly: "does your
  commercial license permit Gaussian-splat optimization and a corrective neural net trained per-subject
  on your scan, where the *output avatar* (not the scan itself) ships to end users?" Do not proceed
  without that answer in writing.

**7. Renderpeople** (free and paid 3D people — same terms apply to both per their ToS)
- **Verbatim, commercial use:** *"Rendering of still images and animations for commercial or private
  use..."* and *"Real-time rendering for commercial or private use, such as for AR, VR, and XR
  applications as well as computer and video games"* — permitted.
- **Verbatim, redistribution:** *"Any kind of transfer, especially renting, reselling, lending, or
  sublicensing the 3D data as well as the license from the Licensee to third parties"* is barred; SaaS
  deployment where third parties access the underlying 3D data is forbidden **except for computer games**
  (ambiguous whether a browser-delivered AR/avatar app counts — needs a direct ask).
- **Verbatim, AI/ML:** *"Use of the 3D data for Computer Vision Research"* — explicitly defined to include
  dataset creation, neural network training, and ML model development — **requires express written
  consent** via a separate agreement.
- **Verdict: CONDITIONAL, leaning BLOCKED as-is.** The CV-research clause almost certainly captures our
  Gaussian-fit + MLP pipeline. The license does carve out a path (written consent) — email them — but
  don't proceed on the standard license.

**8. AXYZ Design** [secondary-summary based — primary licensing-info page is JS-rendered and could not be
fetched directly; **flag for manual re-verification** before relying on this]
- **Reported clause (from a fetched summary page, not primary text):** *"No Stock Media may be used to
  Resell or freely distribute AI training data sets derived either from the Stock Media or as pack of
  images or renders created using Stock Media products themselves."*
- **Reported technical redistribution requirement:** when redistributing an integration, *"the 3D model's
  database/geometry must be password-protected, encrypted, or reside in an executable file and cannot be
  imported by third parties."* If accurate, this alone is disqualifying for us — we ship glTF/gaussian
  assets to browsers, which are inherently client-inspectable; DRM-locking geometry is not compatible
  with our delivery model.
- **Verdict: CONDITIONAL, leaning BLOCKED**, pending direct verification of the primary license text.

**9. 3d.sk (human photo references and scans, subscription model)** [**UNVERIFIED** — the terms page
returned HTTP 403 on two separate fetch attempts; everything below is from search-engine summaries only]
- **Reported:** commercial subscription *"lets you use their photos and scans in commercial work, texture
  packs, models, games, cinematics, etc., and sell the resulting assets to clients or third parties"* —
  if accurate, this is a **more redistribution-permissive stance than any other scan vendor found** in
  this pass (explicitly allows selling the resulting assets, not just "one project").
- **Reported carve-out:** bars use in *"design template applications intended for resale... including
  website templates, Flash templates, and business card templates"* — narrow, doesn't touch our use case.
- **No AI/ML clause was surfaced** in search summaries, but given the 2023-25 industry-wide sweep, assume
  one may exist until the primary ToS can actually be read.
- **Reported price:** ~€490/yr (freelancer tier) to ~€1,290/yr (studio tier) per a third-party review site
  — **stale/unverified, may not reflect current pricing.**
- **Verdict: CONDITIONAL / genuinely promising but UNVERIFIED.** This is the single highest-priority item
  to manually re-check (create a trial account, read the live Content License Agreement) — if the
  redistribution language holds up and there's no AI clause, this could be the best paid option found.

---

### BLOCKED

**10. Texturing.xyz** (confirms and sharpens the existing project blocklist entry)
- **Verbatim:** prohibits use of *"any product purchased (including geos, textures, photos) to work with
  Artificial intelligence tools and software (deep learning, neural network, data train..)"*, and bars
  redistribution: *"do not sell or distribute any of these Materials (modified or not) by itself or in a
  texture pack"* / no standalone use of derived "Customer Assets."
- **Verdict: BLOCKED**, confirmed — the AI clause is the primary blocker (not just redistribution as the
  project's existing note implies), and it applies broadly across their terms (no free-vs-paid carve-out
  found in the fetched ToS).

**11. FaceScape (and academic light-stage / face-scan research corpora generally)**
- **Verbatim:** *"The license granted is for internal, non-commercial research, evaluation or testing
  purposes only. Any use of the DATA or its contents to manufacture or sell products or technologies... is
  strictly prohibited."*
- **Verdict: BLOCKED.** Classic research-only trap, confirmed as described in the task brief. Treat any
  university face/body-scan dataset (Multi-PIE, most ICT-3DRFE-style corpora, etc.) as presumptively
  research-only until a commercial license is proven to exist in writing.

**12. Digital Emily / Wikihuman (USC ICT)** — a **mislabeling trap, same shape as the project has hit
before**
- The Wikihuman project's own page states: *"Wikihuman is open to all under Creative Commons License for
  **non-commercial** direct use."* The GitHub mirror (`hpd/DigitalEmily`) labels itself "MIT license" —
  but that almost certainly covers the repo's scripts/README, not USC ICT's underlying scan data license,
  which the project's own site describes as non-commercial. **Could not fetch USC ICT's primary page**
  (`gl.ict.usc.edu` — DNS failure) to get authoritative text.
- **Verdict: BLOCKED as the safer read**, and flagged as **[UNVERIFIED]** pending the primary ICT license
  text — do not trust the "MIT" GitHub label at face value; this is exactly the "aggregator tag is wrong"
  failure mode the project has caught before.

**13. Triplegangers**
- **Verbatim (ToS):** prohibits *"using any content or images on their site for artificial intelligence or
  machine learning without a license from TG"*; requires a separate contract even to download content at
  all (personal or commercial license, negotiated). Publicly went offline in 2024 fighting an AI-scraping
  bot (OpenAI) hammering their servers — they are unusually aggressive about policing exactly this use.
- **Realism:** very high (large commercial scan-double database) — but definitively closed absent a
  bespoke negotiated license.
- **Verdict: BLOCKED under standard terms.** Possible **commission-adjacent lead**: their infrastructure
  for licensing per-use already exists — worth a direct outreach asking for an ML-inclusive commercial
  quote (see Commission section below) rather than assuming it's a dead end.

**14. Basel Face Model (BFM 2017/2019)**
- **Commercial license exists and is real**, unlike most academic datasets: reportedly **EUR 10,000/year**
  or a **EUR 40,000 one-time perpetual license** (via Unitectra, the University of Basel's licensing
  office) — **[UNVERIFIED pricing, from search summary only — not fetched from Unitectra directly]**.
- **Verdict: CONDITIONAL but not recommended.** Fails the "affordable" gate hard for an early-stage
  product, and the realism payoff is poor for the price — BFM is a low-frequency PCA statistical shape/
  texture model (known for a smoothed, slightly "waxy" averaged look), not scan-grade detail. Useful only
  as a data point for what "real" commercial licensing costs look like in this space — a hero commission
  (below) buys more realism for less money.

**15. Quixel Megascans / Fab (Epic)** — low relevance, not a new lead
- Human-specific asset catalog on Megascans/Fab is thin, and **MetaHuman-sourced content is explicitly
  restricted to "UE-Only Content"** — consistent with the project's existing MetaHuman block. Fab's
  Standard License bars redistributing raw source files but (per typical wording, **[UNVERIFIED]** — the
  primary EULA at fab.com/eula returned HTTP 403 on fetch) appears to permit embedding in a shipped
  commercial project the normal way; no explicit AI-training bar was located in available text, but
  should be spot-checked before relying on it. Fab does list some individually CC0/CC-tagged assets
  per-listing separate from the Standard License, but nothing scan-grade for human skin surfaced in this
  pass.
- **Verdict: not a meaningful new lead for skin/texture realism** — deprioritize.

---

### Adjacent finding worth flagging: Adobe Firefly is a real landmine, despite the "commercially safe" marketing

- **Verbatim (Adobe's Generative AI usage terms):** Firefly outputs *"cannot be used... in connection with
  creating, training, or otherwise improving AI and machine learning models."*
- This clause sits directly across our pipeline: Gaussian-splat optimization is, functionally, a training/
  optimization process using imagery as supervision, and we may attach corrective MLPs. Adobe markets
  Firefly as "commercially safe" for IP-indemnification purposes, but that framing is about copyright
  infringement risk in the *training data*, not about what *you're allowed to do downstream* with the
  output — and the downstream restriction is the one that bites us.
- **Verdict: AVOID for texture-generation-as-ML-training-input use**, or get explicit written clarification
  from Adobe that "fitting a per-subject Gaussian-splat avatar with a corrective MLP, using a Firefly
  image as a texture map" does not fall under their ML-training restriction, before relying on it.

---

## Recommended shortlist (ranked)

| Rank | Source | Verdict | Realism | Cost | Why |
|---|---|---|---|---|---|
| 1 | **Lee Perry-Smith / Infinite head scan** (ir-ltd.net) | CLEAN | High (film-grade skin maps) | Free | Zero clause risk, genuinely scan-grade, verified CC-BY 3.0 from primary source |
| 2 | **Skins Vol.0 / Vol.1** (itch.io, SMOKEWORKS) | CLEAN | Moderate-high, MakeHuman-native | Free/donation | Drop-in with existing pipeline, CC-BY 4.0, no AI clause |
| 3 | **Self-hosted SD 1.5/SDXL as a detail/pore synthesizer** | CLEAN | Depends on pipeline built | Free-cheap | OpenRAIL-M has no downstream-use bar; needs real engineering to pay off |
| 4 | **Meshy AI, paid tier** | CLEAN | Moderate (mesh-diffusion, not scan) | ~$0.10-0.40/asset | Already validated elsewhere in this project; extend to skin/texture use |
| 5 | **CC0 skin-surface tiles** (cc0-textures.com) | CLEAN | Low (detail layer only) | Free | Zero risk, use as an overlay not a base identity |
| 6 | **3d.sk commercial subscription** | CONDITIONAL — UNVERIFIED | High (real photo/scan references) | ~€490-1,290/yr (stale figure) | Best redistribution language *found in search*, but must read the live ToS by hand before trusting it |
| 7 | **A commissioned hero scan with rights assigned to us** | CLEAN (self-negotiated) | Highest achievable | See below | The only route where we control the ML-use grant explicitly — closes the exact gap that blocks #6-9 above |

**Everything else researched (3DScanStore/Ten24, Renderpeople, AXYZ, Texturing.xyz, Triplegangers,
FaceScape, Digital Emily/Wikihuman, Basel Face Model, Adobe Firefly, Quixel/Fab)** is BLOCKED or
CONDITIONAL-on-written-vendor-confirmation for this specific pipeline — see per-candidate detail above
before revisiting any of them.

---

## The commission route: buy the rights outright

This is the only option that lets us write the **AI/ML-training grant ourselves** into the contract,
closing the exact gap that blocks nearly every off-the-shelf scan vendor above. Two tiers:

**A. Professional volumetric-capture studio — recommend contacting Infinite-Realities (ir-ltd.net)
directly.** They are notable for a reason beyond the free CC-BY head scan above: their current "Spatial
Capture" service page states, verbatim, that they hold **"a full commercial license with Inria to process
and distribute 3D/4D gaussian splat content"** — i.e., a studio that already operates in exactly our
problem space (volumetric capture → Gaussian splats, with the underlying algorithm IP cleared). No
pricing is published; it's contact-for-quote. **Recommendation:** request a quote, and explicitly
negotiate (a) full IP buyout / work-made-for-hire language, (b) an explicit written grant to run our own
Gaussian optimization and attach corrective MLPs to the captured data, and (c) a model release from the
scanned subject covering commercial use of their likeness in a shipped AI-driven product — a generic "we
own the copyright" contract doesn't automatically include that last piece and needs its own clause.

**B. Freelance photogrammetry/texture artist (Upwork/Fiverr) for smaller, non-hero assets.** Cheap
end-to-end ($20-$330 per Fiverr texture/sculpt gig; Upwork transfers IP to the client on payment under
standard ToS, but the AI/ML-use grant should still be written into the contract explicitly, since standard
freelance ToS doesn't address it). Good for clothing/prop/hair-card textures; unlikely to reach scan-grade
skin realism without real capture equipment on the freelancer's end.

**Realistic price estimate for a hero avatar/skin asset with full rights assigned to us:**
**[estimate only — no vendor quoted a fixed rate card for this exact deliverable in this pass; treat as an
informed range from adjacent pricing signals (scan-store per-project license prices, Twindom booth
economics, freelance day rates for multi-camera photogrammetry rigs), not a confirmed number]**
- **Head/face-only hero scan** (photogrammetry rig or light-stage-adjacent setup, cleanup, textures, full
  IP transfer + ML-use grant written into the contract): **roughly $300–$1,500.**
- **Full-body hero scan** (multi-camera rig, cleanup, PBR texture set, full IP transfer + ML-use grant):
  **roughly $1,500–$6,000**, scaling up toward the higher end for exclusivity guarantees or a dedicated
  studio day rather than a marketplace freelancer.
- Get 2-3 real quotes before budgeting against these numbers — Infinite-Realities, Ten24/3DScanStore's
  "commercial customer" contact, and a Twindom partner studio are the three most credible starting points
  found in this pass.

**C. Self-capture (Polycam/RealityScan-style app + our own rig).** The only option with *literally zero*
third-party license risk, since there's no vendor license to violate — cost is capital equipment + time,
not licensing fees. Still requires a **signed model release** from whoever is scanned, covering commercial
use of their likeness in a shipped, AI-driven, publicly distributed product — that's a publicity-rights
question, separate from (and in addition to) all the copyright-license analysis above, and applies equally
to the commissioned-studio route.

---

## Items flagged [UNVERIFIED] — re-check before relying on any of these

1. **3d.sk** primary Content License Agreement text (403 on two fetch attempts) — highest-priority re-check, most promising lead.
2. **AXYZ Design** primary licensing-info page (JS-rendered, could not extract text) — verdict here is from a secondary summary only.
3. **Digital Emily / USC ICT Wikihuman** primary license (`gl.ict.usc.edu` unreachable) — GitHub "MIT" label likely mislabeled; treat as blocked until the ICT page itself is read.
4. **Fab / Quixel Megascans EULA** (fab.com/eula returned 403) — AI-training-clause status specifically unconfirmed.
5. **3DScanStore/Ten24 and Twindom current price lists** — no current per-scan pricing was fetched from a primary page.
6. **Basel Face Model** EUR 10k/40k pricing — from a search-engine summary, not fetched from Unitectra directly.
