# 4DGS — Session Handoff (2026-07-24, D105)

> Read this FIRST in a new session, alongside **[PROJECT.md](PROJECT.md)** (SSOT; full decision trail
> in the Decision Log — newest = **D105**). This file = the concrete current state + how to run it + next steps.
> The deep historical narrative (D53–D75) now lives in PROJECT.md's Decision Log; this handoff is kept clean.

---

## ▶ THE PRODUCT (locked, D74)
A **per-subject CAPTURED photoreal Gaussian-splat avatar** that renders **standalone in the browser** and is
driven **live by an LLM** like a game character. **NOT a trained model, NOT a dataset** — each avatar is
**per-subject OPTIMIZATION** (fit gaussians to a real person's multi-view photos, photogrammetry-like),
anchored to the Anny rig with **pose-dependent correctives**, driven by an on-device animation system
(parametric locomotion + clean-mocap clip library) that an LLM directs (D68 two-clock).

**Pipeline:** `multi-view capture → fit gaussians (gsplat, loss vs IMAGES) → anchor to Anny/SOMA rig +
pose correctives → drive live (LLM director + clip library) → standalone WebGPU splat in-browser.`

**The one risk that decides everything:** DEFORMATION quality (making the fitted splat ANIMATE cleanly).
Static fitting = LOW risk — **now empirically confirmed (D78)**. Animating it = the whole bet (mesh-anchor +
pose correctives, fit to the subject's own video; naive fit+LBS = candy-wrapper, don't).

---

## ▶ WHAT THIS SESSION ADDED (D76–D83)

**D76–D77 — Licensing, settled two ways the user pushed on:**
- **MetaHuman** can't be used — not because of "training" (the user correctly noted we only rig now), but
  because its EULA bars **redistribution / SaaS / hosting**, and we ship assets to the browser = worst case.
  (Also: any gaussian bake with corrective MLPs *is* a neural net → trips the ML clause too.)
- **Bought assets** (individual artists / marketplaces): right instinct, but **buy the RIGHTS not the asset** —
  standard marketplace EULAs (TurboSquid/CGTrader/Sketchfab/ArtStation/Fab) added AI-training bars in 2023–25.
  Clear both gates via a **custom addendum** or, best, a **commission/work-for-hire you own outright**.
  Run the PoC on **CC0** (PolyHaven/AmbientCG/MPFB2) so nothing is thrown away.

**D78 — POC EXECUTED (the D74 Milestone-0 static fit, 100% CC0, on this 3090):**
`export_textured_obj.py → blender_render_skin.py --poses (24 calibrated views) → fit_gsplat_poc.py → avatar.ply + turntable`.
Result: recognizable, correctly-posed full-body gaussian avatar; **held-out PSNR 20.2 dB ≈ train 20.3 dB**
(genuine multi-view reconstruction, not memorization) → the "fitting = low risk" gate confirmed clean-license.
Bug fixed: Blender's OBJ importer rotates Y-up→Z-up (+90°X); verts need `(x,y,z)→(x,-z,y)` to match the camera frame.

**D79 — VIEWER: mesh-vs-splat compare in ONE canvas + texture toggle:**
Two left-rail buttons — **Textures** (base-model skin-tone ↔ grey mannequin) and **＋ Splat compare**
(fitted splat rendered beside the animated mesh, same camera/orbit). New `/splat.bin` endpoint (plyfile →
20-byte/gaussian buffer) + a billboarded-gaussian-points ShaderMaterial in viewer.html.

**Honest state of the splat:** it is **CG-in → CG-out** — fit to synthetic Cycles renders of the Anny CG
**mannequin** wearing the procedural CC0 skin, NOT real human photos. Photoreal needs REAL capture; this PoC
only proves the plumbing + fit quality, both now solid (below).

**D80 — Splat button fixed (it rendered nothing) + a real quality pass (PSNR 20.2dB → 25.7dB):**
- **The bug:** the D79 splat shader referenced a `color` attribute that was never declared once `vertexColors`
  got turned off (a three.js gotcha — it only auto-declares that attribute when `vertexColors:true`). The
  shader failed to COMPILE; WebGL compile failures never throw a JS exception, so nothing on the page caught
  it — the splat data loaded fine (confirmed in the server log) and simply drew nothing. **Fixed** by declaring
  `attribute vec3 color;` explicitly. Also forwarded `console.error` → the `/log` telemetry so a repeat of this
  bug-class (silent shader failure) is visible next time, even with no browser devtools on this headless box.
- **The marble/rainbow speckle — root-caused, not just patched:** grey color init + sparse views left every
  gaussian's color under-constrained → the optimizer settled on per-gaussian noise. Fixed with (1) **projected-
  pixel color init** (each gaussian samples its own color from whichever training views actually face it,
  weighted by facing angle), (2) a **neighbor color-smoothness prior**, and (3) **best-held-out-PSNR
  checkpointing** — the training curve showed PSNR peaking early (SH degree 0, ~26dB) then DEGRADING as SH
  degree ramped to 2–3 (too few views to constrain the view-dependent terms, so the optimizer used them to
  re-introduce noise) — exporting the best checkpoint instead of the last one fixes this without hand-tuning
  an SH/iteration schedule. Re-rendered source at 36 views/320px/64 samples (was 24/256/48).
  **Result: held-out PSNR ≈ train PSNR ≈ 25.5–25.7dB, clean skin-toned body from every angle.**
- **Base-model material also upgraded** (still honestly NOT real UV skin): `MeshStandardMaterial` →
  `MeshPhysicalMaterial` with sheen (skin's soft grazing-angle falloff) + a faint clearcoat, plus a cheap
  coherent vertex-color "blotch" so it isn't one flat tone. Real UV-mapped skin is still the bake+retarget
  item in Immediate Next below — this is a lighting/material upgrade, not a texture map.

**D81 — Eyes fixed (real root cause, not a shader tweak), splat "point cloud" fixed (depth sort), and a
commercially-clean hair/clothing/face-detail asset pipeline found + proven:**
- **Eyes:** NOT a rendering bug. Rendered a pyrender headshot of the LIVE animated body (SOMA topology,
  `render_soma_motion.py`) and it has **zero facial geometry** — no eye sockets, no nose, a smooth blob. SOMA's
  topology is a body-motion-transfer mesh; the D72 eyeball geometry only ever existed on the DEFAULT
  13,718-v topology, which the live viewer never actually drove. Fixed by extending `pose_default_walk.py`
  (new `--stem` flag) to export a live-viewer-ready DEFAULT-topology walk with a procedural sclera/pupil
  vertex-color shade (`<stem>_eyemeta.json`, served via a new `/eyemeta.json` endpoint). `walk_face` is now
  the default model. Also fixed a latent bug this surfaced: the server used ONE global `faces.npy` for every
  model — fine while every model shared the SOMA topology, but silently wrong (index-out-of-bounds) for a
  different-topology model. Added `_faces_path()` (per-stem override, falls back to the shared file).
- **Splat "point cloud":** two real fixes — (a) bigger/brighter splats (`uSizeMult`/`uAlphaBoost` shader
  uniforms; the fit's gaussians average only ~26% opacity across a sparse 13.7k-point body, so at their
  literal fitted size/alpha they show gaps) and (b) **per-frame back-to-front depth sorting** — `THREE.Points`
  draws in buffer-index order, NOT depth order, so alpha-blended splats were compositing in arbitrary order;
  this (not the size) was the real reason it read as scattered dots instead of a surface. Sorts a reused
  index buffer by distance from the camera (transformed once into the splat's local space, not per-point) —
  cheap at this gaussian count.
- **Asset research (the user's "find clean hair/face/clothes/hands, add them" ask):** the MakeHuman/MPFB2
  asset-pack catalog — the SAME family D71/D72's skin already comes from — turns out to have essentially
  everything asked for, ALL CC0 or CC-BY (no AI-training bar, no cap, no redistribution restriction,
  anywhere): hair, full clothing range, eyebrows/eyelashes/beards, and realistic hand/nose/ear/cheek/arm
  shape-detail packs. Decoded its `.mhclo` binding format (plain-text: `v1 v2 v3 w1 w2 w3 dx dy dz` per
  asset-vertex — an affine combination of 3 basemesh vertices + a local offset) into a general fitter,
  **`dataset/mhclo_fit.py`**. Downloaded real CC0 packs and PROVED it: an eyebrows asset and a clothing item
  (stocking) both fit Anny's raw native mesh CLEANLY with **zero remapping** (rendered proof:
  `motion_out/mhclo_proof_eyebrows.png`, `motion_out/mhclo_proof_clothing.png`) — confirming Anny's topology
  is bit-compatible enough with MakeHuman's for direct use. **Honest limit, root-caused not hidden:** a
  voluminous/flowing hair asset fit BROKEN (spiky/exploded — `motion_out/mhclo_diag_hair_broken.png`).
  Diagnosed via an ablation (zeroing the offset still produced spikes): hair's affine weights range up to
  `[-2.06, 4.57]` vs. clothing/eyebrows' mild `[-0.34, 1.54]` — at that extrapolation magnitude, tiny
  precision differences between Anny's reimplemented body model (WHO-recalibrated, D56) and MakeHuman's exact
  basemesh get amplified into catastrophic cancellation. **Close-fitting assets work now; flowing hair needs
  either exact basemesh-precision matching or routing through the real MPFB2 Blender addon** (has the
  canonical basemesh internally, sidesteps the problem) — a concrete next step, not yet built.
- **Not yet wired into the pipeline**: `mhclo_fit.py` is proven standalone but nothing merges its output into
  `export_textured_obj.py`/`blender_render_skin.py` or the gaussian fit yet — see Immediate Next.

**D82 — Splat rebuilt on the ACTUAL root cause (user reported D81's fix didn't work — "still just floating
points, nothing there") + evaluated 5 more asset sources the user found:**
- **Root cause:** D80/D81's size/alpha/depth-sort fixes were real improvements but sat on a broken
  foundation — the renderer used `gl.POINTS` + `gl_PointSize`, and this box's WebGL context is
  **ANGLE-over-Direct3D11** (see the boot `slog` in the server log), a backend with long-documented
  unreliable/capped point-sprite size support. No shader uniform tuning can fix that — the GPU driver can
  silently clamp point size regardless of what's requested. **Fixed by rebuilding the splat renderer as
  GPU-instanced camera-facing billboard QUADS** (`THREE.InstancedBufferGeometry`, per-instance
  position/color/size/alpha, vertex shader offsets each quad corner directly in VIEW space where XY is
  already screen-aligned — no `gl_PointSize` anywhere). This is the same technique real production splat
  viewers (antimatter15, mkkellogg) use, for the same reason — it renders identically on every GPU backend.
  Depth-sort updated to match: instancing has no separate draw-order index (instance *i* always reads
  attribute-array slot *i*), so `updateSplatSort()` now physically rewrites the 4 instance attribute arrays
  in camera-distance order each frame, from an untouched original copy (`splatSrc`) so it never drifts.
- **Asset sources evaluated** (Open Source Avatars VRM registry, madjin/awesome-cc0, ToxSam/open-source-avatars,
  Quaternius, itch.io CC0 filter): PolyHaven = already-clean (D73), not character-specific; **awesome-cc0 =
  an unverified curated LINK LIST**, not independently checked per item; **ToxSam's registry = per-collection-
  varying VRM links hosted elsewhere**, not files, nothing checked at the individual-collection level yet;
  **Quaternius = genuinely CC0** but stylized/low-poly game props (nature/vehicles/fantasy), not realistic
  human assets; **itch.io's "CC0" filter = an unenforced marketplace tag**, same per-asset verification burden
  as always. **The decisive finding: VRM is a completely different avatar FORMAT** (its own topology + skeleton
  standard, one unique mesh per avatar) — **zero compatibility with the D81 MHCLO pipeline**, which only works
  because Anny's mesh literally IS MakeHuman's basemesh. A VRM asset would mean replacing Anny wholesale or
  manually re-rigging extracted parts by hand — real separate engineering, not the automatic fit D81 proved.
  **Decision: stay on MakeHuman/MPFB2 for hair/clothing/face-detail** (proven, automatic, already working);
  treat VRM/Quaternius/itch.io as supplementary sources for things MakeHuman doesn't cover (stylized
  props/environment), not the primary route for realistic human assets.

**D83 — Splat STILL hazy after D82's renderer rewrite -> real root cause was DATA sparsity, not the
renderer + assembled a REAL dressed avatar end-to-end from downloaded CC0 assets, finding and fixing
two genuine clothing-fitting bugs along the way:**
- **Splat density:** D82's billboard-quad renderer was correct but 13,718 gaussians (1 per mesh vertex,
  no densification) is just too sparse to ever read as solid, however well it's rendered. Fixed in
  `fit_gsplat_poc.py`: 3x tangent-jittered densification (~41k gaussians) PLUS fixing a self-canceling
  bug where the initial gaussian size was computed from the new finer post-densify spacing -- so each of
  the 3x-more gaussians was also ~3x smaller, and coverage barely improved until the size init/cap were
  switched to reference the ORIGINAL coarser pre-densify spacing. Result: a genuinely solid, gap-free
  body from every angle. Retuned the viewer's `uSizeMult`/`uAlphaBoost` down to match (the data is now
  properly sized, so the old shader-side compensation would over-blur it).
- **Re-checked the GitHub links properly** (raw READMEs fetched directly, not summarized, per the user's
  correction): thebasemesh.com / M3-org/base-meshes = genuine CC0 but PROP-focused (furniture/weapons/
  food/tools; has a Clothing category but as standalone unrigged meshes, no automatic fit) -- not useful
  for realistic human parts. **madjin/100avatars turned out to be MISLABELED "CC0"** in the aggregator --
  its own stated terms are "not to sell...without major modification," a real restriction, not CC0 (a
  companion PolygonalMind repo claims the same content IS CC0 -- an unresolved conflict, don't rely on
  either until clarified). Validates the project's "verify the exact text, don't trust the label" habit
  (D73). Neither source beats the MakeHuman/MPFB2 pipeline already proven in D81.
- **Assembled a real dressed avatar** (new `dataset/compose_avatar.py`): body + CC0 hair + CC0 eyebrows +
  CC0 t-shirt + CC0 cargo pants, all real downloaded assets fit via `mhclo_fit.py`. Two real bugs found
  and fixed in the process (mhclo_fit.py had only been proven on eyebrows/hair/one stocking before this):
  1. **Missing offset-scale calibration** -- mhclo files carry `x_scale/y_scale/z_scale v1 v2 den`
     directives (rescale factor = current-basemesh-distance(v1,v2)/den) that were being silently ignored;
     harmless for small-offset assets (eyebrows) but left large-offset assets (sleeves/hems) ~9x too big.
  2. **T-pose clothing distortion** -- a first shirt render came out as a huge cape/tent shape. Traced via
     direct vertex inspection to CORRECT barycentric binding against genuinely T-pose wrist vertices (Anny's
     raw `forward()` output has arms straight out) -- a sleeve spanning shoulder-to-outstretched-wrist
     inherently looks like a cape; not a fitter bug. Fixed by posing the arms down (~75°, via Anny's own
     `pose_parameters`/'local-bone' API, same mechanism `pose_default_walk.py` uses) BEFORE fitting
     clothing -- shirt width dropped from ~0.96m (arm-span) to ~0.4m (torso-width).
  Also added a stray-outlier filter (drop any fitted triangle landing below the body's own feet -- caught
  a handful of rogue hair-strand/pants faces, the residual D81-class precision-sensitivity tail that
  survives even on otherwise-safe low-extrapolation assets).
- **Honest caveat:** the final composed render (`motion_out/composed_avatar.png`) was verified via
  numerical/color-channel analysis (correct blue-shirt/skin-arm/dark-pants bands, correct order, plausible
  proportions) rather than direct visual confirmation, because the image-viewing tool went down mid-session
  -- a genuine tool outage, not a skipped step. **Visual confirmation of the final composed avatar is still
  owed next session.** `compose_avatar.py` also writes a combined multi-material `.obj`
  (`motion_out/composed_avatar.obj`) ready for the next step: texturing + the gaussian fit on a dressed avatar.

---

## ▶ WHAT THIS SESSION ADDED (D84)

**Arms-crossed pose bug, actually fixed:** D83's 75°/-75° arms-down rotation was never rendered and
checked — it overshoots past vertical, curling the wrist back up in FRONT of the torso (the exact
"crossed" look the user caught, made obvious once clothing was on it). Root-caused numerically
(rotate the rest upperarm→wrist vector about the world Y axis at several angles, read where the
wrist lands relative to the shoulder pivot) and fixed to **40°/-40°**. Re-verified by rendering the
bare body at the new angle AND the full dressed avatar — both confirmed visually
(`motion_out/composed_avatar_v2.png`). Pulled the shared pose+fit math out of `compose_avatar.py`
into **`dataset/outfit_lib.py`** (`arms_down_basemesh()`, `fit_asset_checked()`) so the offline
script and the live server can't drift apart the way this bug required them not to.

**CC0 assets persisted + wired into the live viewer as real selectable items:** the D81/D83 downloaded
hair/eyebrows/clothing packs only ever lived in a prior session's `/tmp` scratch dir. Copied a curated
set into **`dataset/motion_out/assets_src/{hair,eyebrows,clothing/{tops,bottoms}}/`** (gitignored like
the rest of `motion_out`, survives across sessions, ~166MB, disk checked before/after — 1.8GB free).
**Validation is automatic, not a hand-picked list:** `serve_viewer.py`'s `build_catalog()` fit-tests
every asset against the arms-down basemesh and silently drops anything that errors (topology mismatch)
or blows out past a sane bbox envelope (D81/D83's flowing-hair-extrapolation failure) — this caught a
real case live (`elvs_double_mh_braid`) that had passed an earlier, cruder manual check. Result: 14
hair / 13 eyebrows / 5 tops / 2 bottoms usable catalog items. New endpoints: `/catalog.json?kind=`,
`/asset_src/<kind>/<name>/thumb`, `/compose.bin?hair=&eyebrows=&top=&bottom=` (live-fits the selection,
packs body+parts into one static vertex-colored mesh buffer). `viewer.html`'s **Hair** tab now shows
selectable Hair/Eyebrows cards, **Clothing** shows Tops/Bottoms; a new **"＋ Outfit" button** loads the
current selection as a static preview mesh beside the animated body. **Honest scope limit (stated
in-code):** this is a static arms-down "try it on" preview, NOT the walking animation wearing clothes
— per-frame garment re-fit or skeleton LBS binding (see Immediate Next below) is still unsolved.

**Dedicated `/splat` route with a renderer that can't silently fail:** the splat-compare button had
already been through gl.POINTS (D80) → billboard-quad instancing shader (D82) → densification (D83),
and the user still reported "just floating points." Rather than debug a fourth custom-shader
iteration blind (still no headless browser on this box), built **`dataset/viewer/splat.html`** (new
`/splat` route, same top-bar/left-rail/right-panel shell as the Studio) using three.js's own
**`THREE.InstancedMesh`** (native `instanceMatrix`/`instanceColor`, not hand-wired custom shader
attributes) — each gaussian is a small low-poly icosphere scaled to its fitted size. Real 3D geometry
can't degenerate into "a few pixels" the way `gl_PointSize` or a shader corner-offset bug can. Left
rail lists every `.ply` in `motion_out/` (new `/splats.json`) as a selectable card.

**Verification honesty:** everything was verified through the data layer — server endpoints
curl-tested, `/compose.bin`'s exact output bytes re-rendered via `pyrender` to confirm the arms-down
fix holds through the real live code path (not just the offline script), new JS syntax-checked with
`esprima`. **This box still has no headless browser** — and that gap is exactly what let the D85 bugs
below ship in the first place.

## ▶ D85 — the user clicked through it and found 3 real bugs in one pass (all fixed)

1. **`/compose.bin` crashed the browser**: `RangeError: start offset of Uint32Array should be a
   multiple of 4`. Cause: the buffer packed `pos(f32) + color(u8) + faces(u32)` — the color block's
   byte length isn't guaranteed 4-byte-aligned, so the trailing `Uint32Array` view over the faces
   sometimes landed on a bad offset. **Fixed: reordered to `pos + faces + color`** (color last, nothing
   after it needs alignment) in `serve_viewer.py` and `viewer.html`'s parser.
2. **Outfit preview rendered sunk below the floor, with visible distortion**: the compose buffer used
   raw Anny-frame coordinates (feet at z≈-0.85, never grounded) while the main animated body IS grounded
   server-side (`_orient_yup`) — fixed by subtracting the basemesh's own feet-z before packing. Separately,
   **found a real gap in D84's own validation**: `drop_below_feet` only catches outliers below the feet,
   but a mis-fit triangle can just as easily streak ACROSS a garment — confirmed on `elvs_crude_t-shirt_male`
   (12 triangles with a 0.47-0.57m edge vs. 0.089m median) and `culturalibre_hair_02` (~90 similarly blown
   strand triangles). Added `outfit_lib.drop_edge_outliers()` (absolute + relative edge-length threshold,
   verified 0 false drops on eyebrows/pants, correct drops on shirt/hair).
3. **`/splat` looked like "black spheres... foam," not 3DGS**: D84 shipped opaque icospheres specifically
   to *guarantee* something rendered, but opaque geometry can never look like soft gaussian falloff — a
   real design mistake, not an acceptable tradeoff, and the user called it out correctly. Re-examined the
   D80-D83 "point cloud" history with actual numbers: `poc_avatar.ply`'s mean gaussian size (stddev)
   ~0.0072 vs. median neighbor spacing ~0.0015 means good coverage needs `uSizeMult` ≈ 5-6 (radius ≈
   2.5-3x stddev) — **D83 had retuned it down to 1.3, about 4-5x too small**, which alone explains "sparse
   point cloud" regardless of which rendering technique (`gl.POINTS`, billboard quads, or D84's spheres)
   was blamed each time. Rebuilt `splat.html` on alpha-blended GPU-instanced billboard quads (the real
   gaussian-splat look, same technique as the Studio's splat-compare) with the corrected default size.
   Sanity-checked with a standalone `PIL` rasterization at both sizes before shipping — 1.3x visibly
   gappy, 5.0x reads as smooth and solid.

**Still true: no headless browser on this box.** All of the above was re-verified through the data
layer (buffer-format asserts, a `pyrender`/`PIL` re-render of the exact server output) — good enough to
catch real bugs, but not a substitute for an actual browser. **A real click-through is still owed.**

## ▶ D86 — the user's real click-through found D85 wasn't enough (found + fixed)

1. **Shattered garment shards survived D85's edge-length filter.** Root cause: those triangles aren't
   abnormally LONG (which the filter catches), they're normal-length but badly TWISTED —
   self-intersecting shard clusters from complex drape-y/strapless garment topology that doesn't
   survive this project's crude static-basemesh affine fit. No numeric heuristic was going to catch
   this reliably in the time available, so **actually rendered every single catalog item** (all 14
   hair, 13 eyebrows, 5 tops, 2 bottoms — see `motion_out/grid_hair.png`-style contact sheets in this
   session's scratch dir if you want to see the evidence) and found 4 genuinely broken:
   `toigo_basic_tucked_t-shirt`, `toigo_bodice-style_top`, `toigo_fisherman_sweater` (all shard
   clusters), `elvs_reverse_french_braid_bun` (explodes into a flat halo/ring). **Excluded explicitly**
   via `_KNOWN_BROKEN` in `serve_viewer.py`, documented with reasoning — not hidden behind a heuristic.
   Catalog is now 14 hair / 13 eyebrows / 2 tops / 2 bottoms — thinner, but everything left was
   actually looked at, not just numerically screened.
2. **Splat disappeared when zoomed in**: `controls.minDistance` was a fixed 0.2 regardless of the
   loaded model's actual scale — zooming past roughly the body's own half-depth puts the camera
   surrounded by translucent quads on every side (nothing left to see an "outside" surface of), which
   reads as vanishing. Fixed: `minDistance` now scales to each loaded splat's own bbox at load time.
3. **"Isn't this basically a 3DGS of the character in the other viewer, or not — why not?"** — answered
   directly instead of leaving it ambiguous: **verified** (not assumed) that `poc_avatar.ply` uses the
   identical phenotype dict as `walk_face`'s live mesh — same base identity/proportions, genuinely the
   "normal avatar." But it's honestly a SEPARATE asset in three real ways, none of them bugs: (a) a
   static T-pose fit, not bound to the walk animation (gaussians-on-a-skeleton is D74's whole unsolved
   bet, the hardest open problem in this entire project); (b) fit from synthetic Blender renders at a
   measured ~25-26dB held-out PSNR (D80/D83) — that's the actual current quality ceiling, which is why
   it looks softer than a real captured human, not something this pass can fix by relabeling; (c) no
   eye coloring baked in (that's a live JS trick on the animated mesh only). **Did not blindly re-run
   the several-GPU-minute render+fit pipeline** since the existing file already matches on identity and
   is already at D83's latest settings — re-verified instead of re-running for no real gain. Available
   on request if a fresh regenerate (or a real quality-tier bump: more views/iterations) is wanted.

**Still no headless browser.** This round was caught because the user actually clicked through and
sent screenshots + the exact console error — that is genuinely the fastest verification loop available
on this box right now. Keep sending screenshots/errors; don't assume a "looks right in curl" report
means it looks right on screen.

## ▶ D87 — the user pushed back hard on both remaining fronts; honest answers + real fixes

**Splat "point cloud vs. foam bubbly clay toy, I've never seen gaussian splats like this":**
1. **Real bug found:** `build_splat_buffer` packed a single scalar "size" per gaussian (mean of the 3
   log-scale axes), discarding the fitted rotation quaternion and per-axis scale entirely — every splat
   drew as an isotropic circle. Real 3DGS viewers draw each gaussian's true oriented ELLIPSE (the
   projection of its full 3D covariance onto the screen). Fixed: server now packs the full 3D covariance
   (6 floats) per gaussian; the client projects it into camera space and eigendecomposes it every frame
   (closed-form 2x2) to billboard a properly oriented, properly anisotropic ellipse instead of a circle.
   Verified the math numerically (no negative eigenvalues, no NaNs) and with a `matplotlib` ellipse
   simulation of the real data before shipping.
2. **Honest finding: that alone didn't fix the "clay toy" look.** Measured this specific fit's own
   anisotropy — median ratio (longest axis / shortest axis) is ~1.1, i.e. the gaussians are ALREADY
   almost perfectly spherical. There was very little real shape information for the renderer fix to
   recover. The fix is still correct (matters for any future sharper fit) but isn't the whole story.
3. **Real root cause:** `blender_render_skin.py`'s turntable was a SINGLE elevation ring — every one of
   the 36 training views was at the same height, so no camera ever directly saw the top of the head or
   the underarm/sole regions. That's a genuine, previously-unnoticed gap between what the live viewer's
   own capture-rig UI already models (multiple elevation LAYERS) and what the offline PoC script actually
   rendered (one ring). **Fixed:** added `--elevs` (comma-separated ring elevations) to
   `blender_render_skin.py`, re-rendered at **4 rings (-15/15/45/75deg) x 24 azimuth = 96 views** (was 36,
   one ring) — directly answering "heavily increase the camera positions," structured the right way
   (more elevations, not just more azimuth on the same flat ring) rather than just cranking a number up.
   Re-ran `fit_gsplat_poc.py` against the new capture. Kept it static/T-pose (matches the user's own
   "maybe when they're not moving too" instinct) — gaussians still aren't bound to the skeleton (D74's
   unsolved bet), so a moving capture wouldn't give the optimizer anything more to work with right now.
   **Correction: this render+refit was described as "running in the background" but never actually
   completed in that session — see D88 below, which actually ran it.**

**Clothing "this is just too much, I thought it's simple drag-and-drop, I thought these assets are
premade":** said plainly, not defended — **this genuinely isn't drag-and-drop the way it looks.** MHCLO
assets encode a per-vertex AFFINE APPROXIMATION (3 basemesh vertices + weights + a local offset)
authored against MakeHuman's exact canonical basemesh. Our body is Anny's own reimplementation of that
basemesh (WHO-recalibrated, D56) — close, but not bit-identical — so the approximation's quality varies
unpredictably per asset, from perfect (most eyebrows, short hair) to shattered (complex strapless/draped
garments, D85/D86). **Tried to find a quick exact-precision fix** (compared Anny's bundled raw
`base.obj` against its own default-topology output) — inconclusive/negative in the time available, large
non-trivial differences, not a simple truncation or global offset. **Didn't claim a fix that isn't
real.** The actual fix path (already flagged in D81/D83, never attempted): install the real MPFB2
Blender addon (GPL, has MakeHuman's canonical basemesh built in, sidesteps the approximation entirely)
and drive its own real fitting system via `bpy`. That's a genuinely bigger lift (addon install + new
automation) than anything done so far this session — flagged as the next real investment if fitting
needs to work for ANY downloaded asset, not just the curated/verified subset already in the catalog.

---

## ▶ D88 — actually ran the D87 refit (it never survived past that session) and swapped it in

**Nothing was there to pick up.** At the start of this session, no background process, scratch directory,
or fit output existed anywhere on the box — D87's "refitting now, I'll follow up" never got a follow-up
because the session ended before it did. Ran the whole thing for real this time:

1. `export_textured_obj.py` → `blender_render_skin.py --elevs=-15,15,45,75` → `fit_gsplat_poc.py --iters 3500`,
   working dir `dataset/motion_out/_refit96/` (kept, ~24MB, gitignored, for provenance).
2. **Caught a real usage bug before wasting the fit on it:** `--frames` is the TOTAL view count split
   across rings, not per-ring — the first render pass (`--frames 24`) silently produced only 6 azimuths ×
   4 rings = 24 views total, not the intended 96. Caught from the render log's own `[blender] N elevation
   ring(s) ... x M azimuth = TOTAL views` print, discarded, re-ran with `--frames 96` (→ 24/ring × 4 = 96,
   matching D87's stated intent).
3. **Fit result:** held-out PSNR 25.59dB, train 25.58dB — no train/held-out gap, matches D83's established
   quality tier (~25.5–25.7dB). 0 NaNs, 0 negative-eigenvalue issues.
4. **Verified the SPECIFIC thing this rerun was for**, not just the aggregate number: pulled the new fit's
   own rendered top-of-head (75° ring) and underarm (-15° ring) frames out of `fit_turntable.gif` and
   looked at them directly — both are coherent, solid, correctly shaded, not the gappy/blobby look the
   single-ring capture produced.
5. **Honest carry-overs (not fixed by this, don't pretend otherwise):** median anisotropy ratio is ~1.135
   on the new fit, essentially the same as D87's ~1.098 — the gaussians are still nearly spherical, so
   D87's "the ellipse-rendering fix didn't have much real shape to recover" finding holds on the richer
   capture too, it wasn't an artifact of the old thin data. Mean opacity dropped 0.288 → 0.170 vs. the old
   `.ply` (same 41,154 gaussian count, now satisfying more views) — **not yet checked whether `/splat`'s
   `uAlphaBoost` needs retuning for this**, flagged not fixed.
6. **Swapped in:** old file backed up to `motion_out/poc_avatar_d87_singlering.ply.bak`, new fit copied to
   `motion_out/poc_avatar.ply` (+ turntable gif/png refreshed). Confirmed via `curl localhost:8000/splat.bin`
   that the already-running server picked up the new bytes immediately (mtime-based re-read, no restart —
   matches documented behavior). **Still no headless browser on this box — an actual click-through of the
   new splat in `/splat` is still owed, same standing gap as D85/D86.**

---

## ▶ D89 — root-caused and mostly fixed the clothing-fitting bug (installed MPFB2 for diagnosis, fixed the real bug in our own code, no runtime dependency needed)

User approved building the real fix after being told plainly: higher-quality assets would make the
current approximate fitter WORSE, not better (more complex garments extrapolate worse under the same
broken math), so "find better assets" wasn't a real path forward.

1. **Installed the real MPFB2 Blender addon** (`makehumancommunity/mpfb2`, GitHub) as a diagnostic tool.
   Read its license verbatim (not the GitHub label): source GPLv3 (fine, used as a local build tool like
   Blender itself, never shipped), assets CC0, and **its own license doc explicitly states scripted/exported
   output carries no restriction whatsoever**. Packaged `src/mpfb` as a Blender 4.2 extension, installed +
   enabled via `bpy.ops.extensions.package_install_files` / `addon_enable`, persisted to `userpref.blend`.
2. **Used it to falsify the working assumption:** drove MPFB2's own `HumanService.create_human()` +
   `add_mhclo_asset()` to fit `elvs_reverse_french_braid_bun` — the flowing-hair asset D81 blamed on
   "basemesh precision" and excluded ever since — onto MPFB2's own basemesh. It fit CLEANLY, no explosion.
   The asset was never the problem.
3. **Found the actual bug:** `mhclo_fit.py` was fitting garments against Anny's DEFAULT topology output —
   a REDUCED, RENUMBERED 13,718-vertex array — while `.mhclo` binding indices are authored against
   MakeHuman's RAW 19,158-vertex basemesh (confirmed: `anny/data/mpfb2/3dobjs/base.obj`, bundled inside the
   `anny` package itself, is 19,158v). That's a genuine INDEX-SPACE mismatch, not a precision limit — the
   "close but not bit-identical" framing from D87 was never actually verified (an earlier attempt compared
   arrays of different lengths, an apples-to-oranges comparison, abandoned as "inconclusive" rather than
   diagnosed).
4. **The fix already existed in `anny`'s own API:** `anny.Anny(topology="makehuman",
   remove_unattached_vertices=False)` returns the full raw 19,158-vertex array WITH Anny's actual
   phenotype/WHO-recalibration applied. Verified numerically before trusting it: nearest-neighbor surface
   distance to the actually-displayed 13,718v body, same phenotype+pose = **0.00mm everywhere, including
   the whole head region** — an exact match. Garments fit against it sit correctly on the real displayed
   body with **no transfer step and no MPFB2 runtime dependency** — MPFB2 was essential for diagnosis, not
   production.
5. **Fixed + re-validated for real:** added `outfit_lib.arms_down_fit_basemesh()` (19158v, new — kept
   `arms_down_basemesh()` unchanged, 13718v, for what's actually displayed), updated `mhclo_fit.py` and its
   three call sites (`compose_avatar.py`, `serve_viewer.py`'s `build_catalog`/`build_compose_buffer`) to fit
   against the new array. Per D86's own discipline (render everything, don't just trust numeric filters),
   re-validated AND rendered a contact sheet of all 35 catalog assets incl. the 4 previously excluded:
   **all 3 `toigo_*` tops are now genuinely clean garments** (verified via direct close-up renders) —
   un-excluded (clothing catalog: 2 tops → 5 tops).
6. **Honest remaining gap:** `elvs_reverse_french_braid_bun` is STILL broken — improved (a contained flat
   ring/disc instead of the old halo draping down the back) but still visibly wrong, not a bun. Diagnosed
   one step further: fitting it with OUR OWN code against MPFB2's OWN basemesh (removing Anny entirely from
   the equation) still fails, while MPFB2's own real fitting ENGINE on that same basemesh does not — so the
   residual gap for this one asset is in the fitting ALGORITHM (ours vs. MPFB2's, likely subdivision or a
   multi-pass correction we don't do), not the basemesh. The other 3 assets in this asset's own
   extreme-extrapolation-weight family (`elvs_double_mh_braid`, `elvs_french_braid_variation`,
   `elvs_unkempt_french_braid`) were specifically re-checked and DO fit cleanly now — the difference is that
   the broken one needs to build real volume off the head surface (a bun), while the others drape along it
   (braids). Kept excluded, documented honestly in `serve_viewer.py`'s `_KNOWN_BROKEN` with this exact
   finding, not shipped as "fixed" when it isn't.
7. **Live server restarted** (killed PID, relaunched `serve_viewer.py`), confirmed via `curl
   localhost:8000/catalog.json?kind=clothing` that the new counts (5 tops) are live.

**Still owed: an actual browser click-through of the fixed catalog** — verified through data/renders only,
same standing gap as the splat work above.

---

## ▶ D90 — units bug found: garments were ~10% their correct offset size ("fits a smaller avatar")

The user DID click through D89's fix (closing the gap above) and found it wasn't the whole story: hair
sinking into the skull with skin visible through gaps, pants/shirts showing bare skin through the front
"like they're made for a smaller avatar." Precise, accurate report.

1. **Reproduced it first, visually:** rendered the exact composed-avatar output (pants+shirt+hair on the
   arms-down body) — confirmed large symmetric skin-colored patches through the front of both legs and the
   torso, exactly as described.
2. **Root cause, found numerically, not guessed:** `mhclo_fit.py`'s D83 offset-scale-calibration computes
   `scale = our_basemesh_distance(v1,v2) / den` per axis, where `den` comes from the `.mhclo` file. Printed
   the actual numbers: `our_dist` ≈ 0.15–0.24m (correct meters) but `den` ≈ 1.4–2.4 (NOT meters) → `scale`
   ≈ 0.10–0.11 on **every axis of every asset checked** — every garment's outward offset was being shrunk to
   ~10% of its intended size. **This is a units bug**: MakeHuman's basemesh is internally ~10 units tall for
   a ~1.7–1.8m human (native unit = decimeter), and `den` is recorded in that unit while everything else in
   the pipeline is in meters. Dividing `den` by 10 moved all six tested ratios (x/y/z × shirt/pants) to
   0.98–1.07 — squarely where a legitimate small body-proportion calibration should land, confirming the fix
   rather than papering over the symptom.
3. **This bug predates D89** (introduced with the scale-calibration feature in D83 itself) but was invisible
   until now — D89's much larger index-space bug produced far more dramatic breakage (shattering, halos)
   that masked this smaller, consistent 10x error; fixing D89 made this the dominant visible symptom.
4. **Fixed:** one-line unit conversion (`den / 10.0`) at `.mhclo` parse time in `mhclo_fit.py`, documented
   in-line with the exact diagnostic numbers.
5. **Re-verified:** re-rendered the same pants/legs/torso/hair views from before the fix — legs fully
   covered (no skin strips), torso fully covered (shirt properly loose, not skin-tight-with-gaps), hair
   full-volume (was barely covering the crown before). Also re-checked the one D89 exception
   (`elvs_reverse_french_braid_bun`) — **unaffected by this fix**, identical flat-ring result, confirming
   that residual issue really is a separate fitting-algorithm gap (D89), not another units problem.
6. **Live server restarted again**; full 35-asset catalog re-validated (still 35/35) and the contact sheet
   re-rendered + visually reviewed — pants/shirts/hair all read as properly-sized garments now.

**Still owed: an actual browser click-through of THIS fix** — same standing gap, verified through
renders only so far. The user's next click-through is the real test.

---

## ▶ D91 — D90 was wrong (too aggressive); reverted, replaced with a tuned per-kind uniform boost

The user DID click through D90's fix, immediately: **"now you made it worse... fuzzy, distorted... before,
the asset rendered correctly, it's just that the size was sized for a smaller avatar... if we can just
enlarge the asset a little bit... I don't know what you did, but it made it worse."** A precise report:
D89's state (correct SHAPE, wrong size only) was the right baseline; D90 changed something structural.

1. **Reverted D90's `den/10` reinterpretation** in `mhclo_fit.py` — back to raw `den` in the per-axis scale
   calibration, restoring the D89 state.
2. **Added a genuinely separate, uniform `offset_boost` multiplier** (applies identically to x/y/z, so unlike
   D90's per-axis unit reinterpretation it cannot itself introduce directional distortion).
3. **Tuned it empirically, not guessed** — rendered pants/shirt/hair at boost 1.0/1.5/2.0/2.5/3.0/3.5/5.0 and
   looked at each:
   - **Clothing** (pants, shirt): gap closed steadily with NO visible distortion through at least 3.5x.
     Picked **3.0x** as the default.
   - **Hair**: showed NEW jagged/shard silhouette edges by 2.0x (matches "fuzzy, distorted") — AND its own
     coverage gap (a bald strip down the back of the head) was present UNCHANGED even at 1.0x (no boost at
     all), meaning it was never a sizing problem in the first place. Boosting it further only adds
     distortion, doesn't close the gap. Picked a mild **1.2x**.
   - **Eyebrows**: left at **1.0x** (D83 already established their offsets are millimeter-scale, don't need
     calibration).
4. **Implemented as a per-KIND dict** (`outfit_lib._DEFAULT_OFFSET_BOOST`, auto-picked from the asset's path
   in `fit_asset_checked`, overridable) — NOT one global constant like D90's attempt. The finding that
   different asset kinds need different treatment IS the fix.
5. Re-validated the full 35-asset catalog (still 35/35 pass, counts unchanged: 7 clothing / 14 hair / 13
   eyebrows / 2 bottoms already counted in clothing). Re-rendered the exact pants/torso/hair views used to
   catch D90's regression and confirmed the fix directly this time, not assumed. Live server restarted.

**Honestly still open, not fixed by this or anything before it:** hair's bald-strip-down-the-back gap is a
real, separate, unsolved problem — pre-existing at every boost level tested including none at all. Next
step is probably the same kind of investigation D89 gave the reverse-braid-bun (compare against MPFB2's own
fitting engine directly) rather than another scale/offset knob — flagged for next session, see Immediate
Next below.

**Still owed: an actual browser click-through of THIS fix.**

---

## ▶ D92 — manual size sliders added (Hair, Clothing) instead of more guessed defaults

User, after D91: **"clothing and hair need more adjustments, like make them larger can i control it
manually?"** — asked for control, not another round of me picking numbers.

Added a new **"Outfit sizing"** section to the viewer's right panel: two range sliders (Hair, Clothing;
0.5x–6x) that live-refit the `＋ Outfit` preview as they're dragged, starting at D91's tuned defaults
(hair 1.2x, clothing 3.0x) so the UI opens in sync with what was already live.

**Wiring** (client → server): `viewer.html`'s `outfitBoost` state object → `<kind>_boost=` query params
appended to the existing `/compose.bin` request → `serve_viewer.py` parses + clamps them (0.1–10.0) →
`build_compose_buffer(sel, boosts)` (boosts also folded into the compose cache key, so different slider
values don't collide) → `outfit_lib.fit_asset_checked(..., offset_boost=...)`, which now accepts an
explicit override instead of always auto-picking D91's per-kind default. `mhclo_fit.fit_mhclo`'s actual
offset math is unchanged — this is a control surface on top of D91, not new fitting behavior.

**Verified the wiring is real, not just "no errors":** fetched `/compose.bin` at two different
`hair_boost` values via `curl`, parsed the binary buffer, and checked the hair sub-range's bbox actually
moves with the slider value. First attempt at this check compared the WHOLE buffer's bbox and found no
difference — false alarm, the much-larger body dominates the overall bbox; had to isolate just the hair
vertices (`pos[13718:]`, since body verts come first in the buffer) to see the real, correct effect.

**Still owed: an actual browser click-through** — same standing gap as every fix this session. This one
in particular needs eyes-on since it's a new UI control, not just a server-side number.

---

## ▶ D93 — a THIRD, distinct clothing bug: opaque z-buffer clipping, not sizing at all

The user finally sent a **screenshot** (first one this session): a t-shirt with a symmetric, clean-edged
blotchy pattern of skin-colored patches across the chest/torso, and asked the exactly-right diagnostic
question — is this a real gap in the mesh, or is part of it under/overlaid by the body mesh?

1. **Diagnosed from data already on file**, not new guessing: the D91 boost-value test renders (1.0
   through 5.0) already showed these same blotchy regions, barely changing size across that whole range —
   the signature of vertices with a near-ZERO base offset (D91's `offset_boost` multiplies the offset;
   scaling ~0 by anything is still ~0). Some vertices in a garment's own authored binding are MEANT to sit
   almost exactly on the body (seams, snug-fit lines) — boosting the garment's overall offset never moves
   them.
2. **Why it looks like clean blotches, not soft clipping:** the `＋ Outfit` preview is OPAQUE geometry (no
   alpha blending) — a garment vertex even fractionally inside the body doesn't fade through, the nearer
   opaque body surface just wins that pixel outright, with a clean edge exactly at the crossover. This is
   mechanically different from D90 (units) and D91 (uniform undersizing) — a third bug hiding behind the
   same "stuff shows through" symptom.
3. **Fix:** `outfit_lib.push_off_surface()` — computes real outward body-surface normals (from the fit
   basemesh's own face winding, sign-checked against the body centroid, not assumed), builds a KDTree, and
   for every garment vertex enforces a minimum clearance (4mm default) along the nearest body vertex's
   normal. Only vertices actually under the margin move, so it can't inflate already-loose regions the way
   turning `offset_boost` up further would. Wired into `fit_asset_checked` as a new step, on by default,
   complementary to (not replacing) D91's boost.
4. **Verified concretely:** re-rendered the exact shirt from the screenshot before/after — blotchy pattern
   gone, clean coverage (908 of ~1095 vertices needed the push — this was a widespread issue on this asset,
   not a rare edge case). Checked pants too: one small persistent knee-area gap remains, unaffected by
   either D91 or D93 — likely a genuine hole in that specific asset's own mesh, a separate open issue.
   Checked hair: bald center-strip gap unchanged, consistent with it being the same already-known separate
   structural problem (not fixed by this either).
5. Re-validated the full 35-asset catalog (still 35/35, no regressions). Live server restarted.

**Still owed: an actual browser click-through of this fix.**

---

## ▶ D94 — answered "WHY does it still clip" with a real diagnosis + fixed the dominant cause

The user stopped accepting patches: **"the question is why isn't it fitting properly the clothes and hair
still clip."** Right question. Investigated with proper signed-distance-to-SURFACE, not guesses:

1. **Two causes, measured:** (a) the affine binding is approximate — ~4% of a shirt's verts sit a few mm
   (≤7mm) inside even on the neutral T-pose body; (b) the DOMINANT cause — the arms-down POSE folds the body
   (armpit closes), and garment verts anchored to points inside that fold get dragged deep inside. Clean
   trend on one shirt: **4%/−7mm at 0° → 6%/−25mm at 25° → 10%/−33mm at the shipped 40°**, concentrated at
   the armpit.
2. **Ruled out two wrong explanations by direct test** (not assumption): NOT the offset direction
   (implemented proper co-rotation of the offset in the binding-triangle frame → changed deep clipping by
   ~1mm, nothing); NOT near-zero offsets (deep verts have normal ~50mm offsets — it's the barycentric ANCHOR
   that's in the fold). D93's push under-performed because it used the nearest-VERTEX normal, which points
   the wrong way in a concave crease (tested bigger margins → left MORE stuck, not fewer).
3. **Fix:** rewrote `outfit_lib.push_off_surface` to use the closest point on the body SURFACE
   (`trimesh.proximity.closest_point`) + that triangle's own face normal, iterated, measured against the
   DISPLAYED 13,718-v body (not the 19,158-v fit mesh — different armpit triangulation left 6 verts poking
   through otherwise). Drops interior verts 112→~0 at every pose angle; the exact live `/compose.bin` render
   is clean (blotchy patches gone, only legitimate skin — midriff gap, arms, neck — remains).
4. Catalog validation now passes `push_margin=0` (skips the ~1s/asset push since it discards geometry).
   Catalog intact (7 clothing / 14 hair / 13 eyebrows). Server restarted.

**Honest remainder + the REAL fix:** ≤6 verts on the worst asset survive in the deepest armpit fold (not
visually significant). Vertex-pushing is cleanup, not a true solution. The real fix — flagged since
Immediate Next #4 — is to fit the garment ONCE at the neutral/unfolded pose and deform it WITH the skeleton
(LBS), instead of re-evaluating the affine binding at a folded posed state. That kills fold-clipping at the
source AND is the same machinery needed to dress the WALKING body. **Consider doing that next instead of
more push tuning.**

**Still owed: an actual browser click-through of this fix.**

---

## ▶ D95 / D96 / D97 — three parallel subagents (user-directed), all landed

The user launched three background subagents at once. Consolidated here; the parent restarted the
:8000 server so ALL changes are live, and renumbered the two engineering agents (both independently
picked "D95") → splat=D95, clothing=D96 (some clothing code comments / scratch filenames still say
"D95" — harmless, the splat work anchored D95).

### D95 — SPLAT: gaussians are spheres/foam → anisotropic surface-aligned disks
- **Root cause = the DATA, not the custom renderer.** Confirmed by rendering the same `.ply` through
  gsplat's OWN reference rasterizer (independent of `splat.html`) — same foam. `splat.html` already
  packed/projected the full 3D covariance (D87), so with isotropic input it can only draw circles.
- The fit (`fit_gsplat_poc.py`) initialized scale isotropically + identity quats + exported an early
  (iter ~500, SH 0) checkpoint before anything flattened. **Fix (init block only):** init each gaussian
  as a thin surface-aligned disk — orthonormal frame from the mesh vertex normal → rotation quat;
  anisotropic scale (tangents 1.35× spacing, normal 0.18×); per-axis cap (tangents grow to 4×, normal
  capped thin 0.7× so it can't re-inflate).
- **Results:** anisotropy median **1.13 → 7.85**, flatness 7.50, normal-alignment |cos| 0.989, held-out
  **PSNR 25.59 → 30.73 dB (UP — a real gain).** New `poc_avatar.ply` live (old →
  `poc_avatar_preD95.ply.bak`). Proof: `motion_out/d95_{front_full,threequarter,head_closeup,torso_closeup}.png`
  (LEFT old | RIGHT new). Parent verified d95_threequarter.png visually — crisp surface vs. old blob.
- Only `fit_gsplat_poc.py` changed.

### D96 — CLOTHING: fit-once-at-neutral + skeleton LBS (the D94 real fix) + first dressed WALK
- New `outfit_lib.fit_asset_lbs`: fit the MHCLO on anny's raw T-pose `rest_vertices` (19158v, armpit open),
  inherit each garment vertex's skinning weights from the barycentric blend of its 3 bound body vertices,
  deform with the SAME LBS the body uses (**verified to reproduce anny's own posed body to 3e-16**).
  `fit_mhclo` now returns `bind_idx`/`bind_w` for weight inheritance. `build_compose_buffer` +
  `compose_avatar.py` use it; `fit_asset_checked` kept for the catalog validator.
- **Decisive number:** fold-clipping now SHRINKS with pose depth (new shirt: 8.2% @40° → 6.2% @60° →
  5.3% @80°) where the old affine-at-posed GREW (9.7% → 10.1% → 10.7%). LBS wins most exactly in the
  walking regime. Deep (>10mm) clips 12→4 on the shirt.
- **MILESTONE:** `motion_out/d95_walk_dressed.png` — same neutral-fit shirt+pants skinned across 4 real
  walk frames, legs tracking the stride, no per-frame re-fit (reproducer `motion_out/_scratch_d95_walk.py`).
  Parent verified visually.
- **Honest floor kept:** the ~4% pose-INDEPENDENT affine-approximation blotch remains (needs the MPFB2
  engine) so the light D94 surface-push stays as a safety net; the LBS specifically kills the pose-SCALED
  fold-drag. Pants/hair arms-down preview is byte-identical old/new (arms-down only moves the arms).
- **Remaining for LIVE dressed-walk:** apply `pose_default_walk.py`'s post-transform (Z-up→Y-up + bounce +
  de-drift + ground) to the skinned garment and add a per-frame buffer endpoint — clean seam exists
  (`bone_transforms_for_pose(P)` + `skin_garment(...)`).

### D97 — RESEARCH: clean + affordable realistic avatar asset sources
- Full report: **`research/avatar-asset-sources-2026.md`**. Binding constraint is the **no-AI/ML clause**
  (redistribution is usually navigable; the ML clause is what's closing the high-end scan market to us).
- **Clean shortlist:** Lee Perry-Smith "Infinite" head (CC-BY 3.0, film-grade, free, head-only) · SMOKEWORKS
  Skins Vol.0/1 (CC-BY 4.0, MakeHuman-drop-in) · self-hosted Stable Diffusion for pore/detail · commission
  with rights assigned (~$300-1.5k head / ~$1.5-6k body — Infinite-Realities already runs a splat capture
  service with an Inria commercial license).
- **New BLOCKED (verbatim evidence):** Triplegangers, Digital Emily (CC-NC despite mislabeled MIT), Adobe
  Firefly (ToS bars using outputs to train/improve ML). Several licenses flagged UNVERIFIED (403/JS/DNS).

**Still owed across all three: an actual browser click-through** (splat `/splat`, ＋Outfit preview).

---

## ▶ D98 / D99 / D100 / D101 — four parallel subagents (user-directed), all landed

The user directed a second four-front batch. Consolidated here; the parent verified server health
(`/data.bin` 200, `/outfit_walk.bin?...&cloth=1|0` both 200 with the correctly PREFIXED ids —
`top=top:<name>&bottom=bottom:<name>`, NOT bare names) and left PROJECT.md/SESSION_HANDOFF for this
consolidation. Naming note: both engineering agents tagged scratch files `d98_*`; the real split is
below (splat=D98, dressed-walk=D99, research=D100, collision/cloth=D101).

### D98 — SPLAT: zoom-in fixed; multi-shell rig built but refit was a WASH (a real finding)
- **Zoom-in vanish root cause (client-only, `splat.html`):** `zoomToCursor=true` dollies the camera
  ALONG THE CURSOR RAY, not toward the target, so `minDistance` (which only clamps camera→target) never
  bounded closest approach — any off-body zoom flew the camera THROUGH the thin (~0.42 m deep) body into
  the cloud (surrounded by `depthWrite:false` billboards = "disappeared"). D86 had rescaled `minDistance`
  but left the wrong lever on. **Fix:** `zoomToCursor=false`, `zoomSpeed 2.4→1.0`, per-model
  `minDistance=max(depth*0.55,0.12)` parks the camera just outside the surface, `clampTarget()` keeps pan
  on the body. Zoom-out (whole body) preserved. Browser reload picks it up (no server restart).
- **Multi-shell rig (`blender_render_skin.py`, new `--rig shells`; legacy `--rig ring`/`--elevs` kept):**
  the user's exact spec — 2 radial shells (outer R=2.90 m, inner R=1.60 m) × 4 HEIGHT layers (feet 0.05 /
  hips 0.56 / chest 1.14 / head 1.72) × 24 azimuth = **192 views**, all extrinsics validated (every cam
  inward, bottom rings look up / top rings look down, one shared K). Flags `--layers/--az/--radii/--layer-frac/--elev-spread`.
- **Refit result = a WASH, and the reason is the key finding:** apples-to-apples on the SAME 48 held-out
  cameras, new 192-view fit **28.39 dB** vs current D95 file **28.36 dB** — identical. Anisotropy 7.81
  (~same), 41,154 gaussians (same). **Why: the fit is MESH-ANCHORED with near-FROZEN means** (gaussians
  pinned to the 13,718 mesh verts ×3 densify) — richer capture can't add geometric detail, only marginally
  re-tune color/opacity, and D95's 96-view rig already saturated that. **Did NOT swap `poc_avatar.ply`**
  (D95 file stays live); no `.bak` made. Rig code kept in `_refit_d98_shells/` (gitignored, 12 MB).
- **The real detail lever (surfaced to the user, decision pending):** to get sharper zoomed-in detail,
  UNFREEZE the gaussian means + adaptive densification (standard 3DGS) → a much sharper STATIC splat, but
  they're no longer glued to mesh verts so the clean animation binding breaks (reopens the D74 "how do
  free gaussians follow the skeleton" bet). Static-inspect vs animatable-walk is the tradeoff. Not built.

### D99 — CLOTHING: first DRESSED WALK live in the browser
- **New `dataset/dress_walk.py`** (owns the walk-dressing domain): precompute (`--stem walk_face`) replays
  the SOMA→Anny retarget → per-bone LBS transforms + the single per-frame RIGID native→display transform
  `(R_fixed, T[t])`. **Key finding: the whole body display pipeline collapses to ONE constant rotation +
  a pure per-frame translation** — verified exact (native→display residual **0.0001 mm** across 150
  frames), so a garment sharing that transform registers on the body to sub-micron precision. Saved to
  `motion_out/walk_face_framedata.npz`.
- **Serving:** fit each selected garment ONCE at neutral (`fit_mhclo` + `_garment_bone_weights`), LBS-skin
  to every frame, apply `R_fixed+T[t]`, pack an `OWK1` buffer (pos+faces+color, 4-byte aligned). New
  **`/outfit_walk.bin?stem=&hair=&top=&bottom=&*_boost=`** endpoint (gzipped), cached per selection.
- **`viewer.html`:** new **`＋ Dressed walk`** button + `updateDressWalkFrame(frame)` called inside
  `setFrame()` so garment + body advance in lockstep, no per-frame re-fit. Verified via pyrender overlay
  of the EXACT `/outfit_walk.bin` + `/data.bin` bytes across stride frames (`d98_served_registration.png`).
- **Pants pass (secondary):** added a one-time neutral-rest `push_off_surface` on the walk path (missing
  before) → garment interior verts 6–8% → 0–1.4%, thigh skin-through essentially gone. Honest limit:
  `cortu_cargo_pants` is an inherently baggy low-poly asset; recommended `cortu_jeans_shorts` as the
  better-fitting default. LBS binding still reads shrink-wrapped (no drape) — that's what D101 fixes.

### D100 — RESEARCH → ACQUISITION: clean realistic assets pulled + staged
- **Downloaded, license-verified verbatim (not marketplace labels), all FREE:** Lee Perry-Smith "Infinite"
  head (CC-BY 3.0, film-grade, +4K displacement/spec) → `assets_src/heads/` (2 MB); **SMOKEWORKS Skins
  Vol.0+Vol.1 (CC-BY 4.0, 5 full PBR skin identities @4K on the MakeHuman UV)** → `assets_src/skins/`
  (161 MB) — DROP-IN for `blender_render_skin.py`'s `build_skin()`, closes Immediate-Next §5. Each has a
  `PROVENANCE.md` (URL, verbatim license, date).
- **Buy list = effectively empty:** no verified sub-$100 pack beats the free haul; high-realism paid
  vendors (3DScanStore/Renderpeople/Triplegangers/3d.sk) stay BLOCKED on the AI-training clause. Only clean
  paid route = commission-with-rights-assigned (~$300–1.5k, over budget). `research/avatar-asset-sources-2026.md`
  now has an "Acquired / Buy list (2026-07-23)" section. Two labels that looked risky cleared on the actual
  bundled text (Infinite's "based on triplegangers.com" = CC attribution field, not their ToS; SMOKEWORKS'
  "don't resell textures" isn't in the formal CC-BY grant — embedding a baked skin was always allowed).

### D101 — COLLISION: body self-collision fixed + baked XPBD cloth (drape + body-collision + layering)
- **Problem 1 — hands through torso (user's "bigger issue"): FIXED at the skeleton level.** Root cause:
  the Kimodo walk swings hands to the front-CENTRE of the pelvis, driving up to ~1000 hand/forearm verts
  as deep as 65 mm inside the torso on 133/150 frames (rest frame 0 clean → it's the animation, not the
  mesh). Fix: `outfit_lib.apply_arm_abduction` (`ARM_ABDUCT_DEG=13`) rotates each arm subtree rigidly about
  the fore-aft axis at the shoulder so hands swing BESIDE the hips (gait's fore-aft swing preserved) —
  **−13° drives penetration to exactly 0** on every worst frame, still reads as a natural walk. Called
  identically from `pose_default_walk.py` (displayed body) and `dress_walk.py` (garment) so they can't
  drift. Re-exported `walk_face_verts.npy` + regenerated `walk_face_framedata.npz` (residual still 0.0001 mm).
- **Problem 2 — real cloth (baked XPBD): DONE.** `dress_walk.py` §3: garment = particles; stretch (edges)
  + bend (adjacent-tri) constraints Jacobi-averaged by valence (summing corrections exploded the mesh — a
  real bug found+fixed); gravity, 10 substeps×2 iters. HARD anchor band (waistband/collar) pins the garment
  on; SOFT follow toward the LBS target keeps limbs tracked (no lag/tunnel) while gravity+collision drape
  the rest. **Collision:** animated body is a moving collider — nearest body vert + normal → each particle
  stays a few mm outside (8 mm bottoms / 14 mm tops). **Layering:** bottoms sim first vs body; tops then sim
  vs body+baked-bottoms (10 mm gap) → shirt sits OUTSIDE shorts. Pre-roll 2 cycles + settle 25 frames at
  frame-0 pose (this walk is NON-cyclic: 155 mm body jump at the 149→0 loop seam). Deterministic (no RNG).
- **Bake cost ~30 s/outfit** (bottom 5 s / top 21 s) — cheap, as predicted (compute was never the wall).
- **Serving/toggle:** baked to `motion_out/<stem>_cloth_<hash>.npz`, served through `/outfit_walk.bin` via
  a `cloth` flag — **`cloth=1` (default)** uses the bake when present else falls back to rigid LBS; `cloth=0`
  forces LBS. `viewer.html` **"Baked cloth" checkbox** (default on). **Default bottom switched to
  `cortu_jeans_shorts`** (cargo flares into holey bell-bottoms under sim). Only the DEFAULT outfit is
  pre-baked; other combos fall back to LBS live (bake more: `python3 dress_walk.py --bake-cloth --top … --bottom …`).
- **Verified (exact server bytes, no browser):** hands clear torso; cloth visibly looser than shrink-wrap
  LBS; 100% of shirt verts near the shorts sit OUTSIDE them; 0 cloth verts inside the body (15 frames).
- **Honest limits:** intra-garment self-collision (fold-on-fold) NOT simulated (v1 scope); the source walk
  is non-cyclic so the whole avatar (clothed or not) hitches at the loop wrap — a MOTION issue, not scope;
  drape is moderate (follow=0.075 for stability), not dramatic billow; collision uses nearest-body-VERTEX
  (fine for the dense 13,718-v body).

**Still owed across all four: an actual browser click-through** (splat `/splat` zoom, ＋Dressed walk +
"Baked cloth" toggle). No headless browser on this box — all verified via offline render of exact server
bytes + data asserts + gsplat reference rasterizer (splat PSNR).

---

## ▶ D102 / D103 — the two "real ceiling" follow-ups (user-directed), both landed with clarifying findings

The user, after seeing D98–D101, asked two things: (1) build the high-detail STATIC splat to see the true
detail ceiling; (2) go after the clothing "toy" look at the ROOT (MPFB2 engine + better assets), not another
cosmetic tweak. Both done. **The unifying finding: the ceiling on BOTH fronts is the SOURCE, not our code.**

### D102 — HIGH-DETAIL STATIC SPLAT: unfreezing the means does NOT beat mesh-anchored — the SOURCE is the wall
- Built `dataset/fit_gsplat_free.py` (NEW): means UNFROZEN (real 3DGS position LR) + adaptive densification
  via **gsplat's own `DefaultStrategy`** (imported directly — did NOT install the examples' requirements, env
  stayed torch 2.5.1/numpy 1.26). Output `motion_out/poc_avatar_hidetail.ply` (shows as its own `/splat` card;
  **does NOT animate** — unfreezing broke the mesh-vertex binding; animatable model stays `poc_avatar.ply`).
- **The result refutes the D98 hypothesis for this source.** On our smooth CG mannequin, densification
  DESTABILIZES the fit (3 densified configs all cratered held-out to ~17–18 dB — splits keep halving gaussian
  scale into sub-pixel gaps single-view SGD can't re-coordinate; higher SH also overfits, the D80 effect).
  Best-checkpoint lands on the lightly-densified peak: 41,154 gaussians, held-out **26.89 dB**.
  **Apples-to-apples control: the FROZEN mesh-anchored recipe on the SAME real-skin GT also scored 26.89 dB
  — identical.** Unfreezing the means does not raise the ceiling here; it hits the same wall.
- **What DID visibly help: the real skin.** Re-rendered the 192-view rig with the **D100 SMOKEWORKS Vol0
  "Hannah" PBR skin** (added optional `--skin_basecolor/--skin_normal/--skin_orm` to `blender_render_skin.py`'s
  `build_skin()` — clean MakeHuman-UV drop-in). Before/after `motion_out/hidetail_compare.png` (L frozen+procedural
  | R free+real-skin): the visible win — real brows/eyes/lips, nipples, navel, finger/nail definition — comes
  from the REAL SKIN TEXTURE, not from unfreezing. (Absolute PSNR is ~1.5 dB lower than D98's 28.39 because real
  skin is higher-frequency than the old procedural skin — harder to fit, on BOTH recipes.)
- **Honest limiter (now proven from two angles):** the detail ceiling is the **smooth CG SOURCE geometry** —
  D98 showed more cameras don't help, D102 shows unfreezing+densifying doesn't help. Real detail needs a better
  SOURCE: real skin helped the surface; true geometric detail needs a real scan OR baking the normal map as
  displacement geometry (a concrete, buildable next lever — we now HAVE the normal maps from D100).

### D103 — CLOTHING: MPFB2 engine wired in (subdivision + ease) — drape is now real; the ceiling is the ASSETS
- **MPFB2 engine genuinely beats the affine fitter — but on GEOMETRY, not accuracy.** Our CC0 garments are
  tiny (shorts 285v, shirt 1095v) → nothing to fold. MPFB2's Catmull-Clark subdivision gives 4–16× the polys
  (shirt → 4260v sd1 / 16794v sd2), which is what lets cloth actually drape. Fit accuracy is ≈ our affine on
  the DISPLAY body (both ~0–0.5% interior; the higher numbers first seen were measured against the wrong
  19,158v helper mesh). The hair bun (`elvs_reverse_french_braid_bun`, excluded since D85) is a decisive MPFB
  win — affine → two flat "ears" on a bald head; MPFB → a proper bun. **Un-excluded (hair 14→15).**
- **Wiring (offline bake, no per-request MPFB dependency):** `dataset/mpfb_fit_blender.py` (NEW, bpy+MPFB2)
  fits the catalog via `HumanService.create_human()` + `add_mhclo_asset(subdiv_levels=…)` → exports to
  `motion_out/mpfb_out/` (gitignored, 23 MB). `dataset/mpfb_prefit.py` (NEW) transfers each MPFB-fitted garment
  onto Anny's rest body via a pose-correct per-triangle barycentric+normal transfer through the shared 19,158v
  basemesh (a rigid transform leaves 31 mm residual — MPFB default pose ≠ Anny T-pose), re-derives the body
  binding, and adds RAMPED EASE (inflate outward along body normals: 0 at shoulders/waistband → full at hem/legs
  so the collar doesn't balloon). `fit_rest()` is the single entry point every dress path now calls (MPFB prefit
  when an export exists, **affine `fit_mhclo` fallback** otherwise). The existing D96/D101 LBS-skin + XPBD cloth
  path consumes it unchanged. **Config: subdiv=1** for clothing (sd2's finer wrinkles aren't worth 34.8 MB/outfit
  on the wire vs 8.9 MB; one-line knob `_SLOT_SUBDIV` to bump if a compressed garment format lands).
- **Result:** the t-shirt now reads as a loose tee with real folds + loose hem (not shrink-wrap); shorts drape;
  bun covers the scalp. Verified via exact `/outfit_walk.bin`+`/data.bin` bytes (`scratchpad/served_overlay.png`,
  `final_dressed.png`). Default outfit re-baked (MPFB geometry + ease).
- **⚠️ Wire-size flag:** the full default outfit (tee + shorts + **subdivided bun**) is **~40 MB** on the wire
  (`/outfit_walk.bin`, the high-poly hair dominates). Works but heavy — drop hair subdiv or add compression if
  load time bites.
- **Honest ceiling = the ASSETS, not the fitter.** These are boxy proxy garments (straight sleeves, plain
  shorts, no collars/plackets/seams). Subdivision+ease+sim make the PHYSICS real but can't invent tailoring
  that isn't in the source mesh. Breaking it needs **commissioned / Marvelous-Designer-style CC0 garments with
  sewn ease (~$300–1.5k each, over the sub-$100 budget)** — D100 already established no cheap clean pack beats
  the MakeHuman CC0 set. Free assets are now squeezed about as far as they go.

**THE THROUGH-LINE (both fronts):** detail/quality is now SOURCE-limited, not code-limited. Splat detail → needs
real capture (or normal-map displacement); clothing quality → needs better-authored garments. Our pipeline
(fit, drape, collision, animation, rendering) is no longer the bottleneck. **Still owed: browser click-through.**

---

## ▶ HOW TO RUN IT

**Env (this RTX 3090 box; conda base):** torch **2.5.1+cu124** (+ torchvision 0.20.1 / torchaudio 2.5.1 —
anny/soma need ≥2.5), **numpy<2 (1.26.4)**, `anny` 0.5, `py-soma-x` 0.1.0 (imports as `soma`), **gsplat 1.5.3**
(CUDA kernels built, works), pyrender/trimesh/imageio/scipy/**plyfile**/**tyro**. Blender at `/root/blender/blender`
(Cycles OptiX headless). Always `export ANNY_CACHE_DIR=$HOME/.cache/anny`; `PYOPENGL_PLATFORM=egl` for pyrender.
⚠️ **Do NOT `pip install -r /root/gsplat/examples/requirements.txt`** — it pins torch 2.9 / numpy 2.0 and
would break the env. Add packages under a torch/numpy **constraints file**.

**The viewer** (`dataset/viewer/`, currently RUNNING on :8000, reachable over the user's SSH tunnel):
```
cd dataset/viewer && export ANNY_CACHE_DIR=$HOME/.cache/anny
python3 -u serve_viewer.py --port 8000 --out ../motion_out --stem walk_face
```
(`--stem walk_face` = the DEFAULT-topology model with real eye geometry, now the intended default — the
original `walk`/`walk_adult` SOMA-topology models still work and are still selectable, they just have no face.)
⚠️ **Gotcha:** `pkill -f serve_viewer.py` self-matches the launching shell's own command line → it kills itself
(exit 144). Find the PID with `ps aux | grep "[s]erve_viewer.py"` (the `[s]` avoids self-matching) and `kill <pid>`
instead. HTML is served from disk each request → viewer.html edits need only a browser reload; serve_viewer.py
edits (e.g. anything touching `/eyemeta.json`, `_faces_path`, `/splat.bin`) need a server restart to take effect
— this bit us mid-session (edited the server, forgot to restart, spent a round-trip debugging stale behavior).
No headless browser on the box → the page POSTs lifecycle/errors to `/log` (server stdout) and forwards
`console.error` there too (D80/D81 — catches silent WebGL shader failures) + shows a red error bar client-side.

**Re-run the PoC fit** (CC0, a few minutes on the 3090 at this quality tier):
```
cd dataset
python export_textured_obj.py --out <scratch>/anny_adult.obj
/root/blender/blender -b -P blender_render_skin.py -- --obj <scratch>/anny_adult.obj \
    --tex /opt/conda/lib/python3.10/site-packages/anny/data/mpfb2/textures \
    --out <scratch>/mv --frames 36 --size 320 --samples 64 --poses <scratch>/mv/transforms.json
python fit_gsplat_poc.py --mv <scratch>/mv --obj <scratch>/anny_adult.obj --out <scratch>/fit --iters 3500
```
(`fit_gsplat_poc.py` now does projected-pixel color init + a neighbor-smoothness prior + best-checkpoint
export automatically — no extra flags needed for the D80 quality level; see its docstring for the `--smooth_w`/
`--knn` knobs.) Outputs: `avatar.ply` + `fit_turntable.gif`. The viewer reads `motion_out/poc_avatar.ply` via
`/splat.bin` (copy a new fit there — `cp .../avatar.ply motion_out/poc_avatar.ply` — to update Splat-compare;
no server restart needed, `/splat.bin` re-reads on mtime change).

---

## ▶ D104 — the "new splat is distorted" regression, root-caused and fixed (+ 3 answers)

User: *"the new splat is way worse in terms of quality like it's distorted."* They were right, and the cause
was **D102's free fit**, not the new real skin.

### The diagnosis (measured, not guessed)
`poc_avatar_hidetail.ply` (D102: means UNFROZEN + gsplat `DefaultStrategy` densification) vs the frozen fit:

| | frozen | free (D102 hidetail) |
|---|---|---|
| mean drift off the mesh surface | 0 (pinned) | **median 8.9 mm · p99 26 mm · max 39 mm** |
| median opacity | 0.17 | 0.34 |
| gaussians under 0.1 opacity | 27 % | 2.8 % |
| animates? | yes | **no** (unfreezing broke the vertex binding) |

Gaussian spacing on that body is **2.5 mm**, so a 9 mm median drift = every gaussian left its anchor by 3–4
spacings. That, plus the hardened opacity (far fewer soft overlapping disks), *is* the smeared eye band,
garbled mouth, red neck streak and blotchy hands. **The texture was cleared as a cause by control render:**
the Blender GT with the same D100 SMOKEWORKS skin comes out CLEAN (correct brows, lips, hairline, UVs land
perfectly) — the skin is good, the free fit smeared it. D102's own control already said the free fit doesn't
beat frozen (26.89 dB both); it just wasn't kept, so the distorted ply is what got shown.

### The fix (executed + swapped in)
Re-rendered the 192-view shells rig with the SMOKEWORKS Vol0 "Hannah" PBR skin, re-fit **frozen**
(`fit_gsplat_poc.py --iters 3500`, D95 anisotropic-disk init) → **train 27.50 / held-out 27.29 dB**
(0.21 dB gap), 41,154 gaussians, anisotropy median 7.80. **Beats the free fit on the SAME real-skin source
(26.89 dB) and still ANIMATES.** Now live as `motion_out/poc_avatar.ply`.
- superseded: `poc_avatar_hidetail_D102_freefit.ply.bak` (its `/splat` card is gone — the viewer lists `*.ply`
  only) and `poc_avatar_preD104_procedural.ply.bak` (the prior live fit on the old procedural skin).
- provenance/capture: `motion_out/_refit_d104_realskin/` (README + transforms + 192 views + fit log).
- proof: `motion_out/d104_three_way.png` (A prior live | B D102 distorted | C new), `d104_turntable.gif`.
- **Honest remaining weakness:** distortion is gone, blur is not — the face is still soft with dark eye
  smudges. Per D98/D102 that's the smooth CG SOURCE, not the fitter.

### Three answers that came with it
1. **All five D100 SMOKEWORKS skins proven on the FACE** (a first) — `motion_out/d104_skin_matrix.png`:
   Vol0 Hannah/Mike, Vol1 Tinasia/Hwang/Dave + the procedural baseline. All land correctly on Anny's
   MakeHuman UVs and are a large jump over the procedural skin the **live viewer still uses**. Tinasia reads
   most photoreal. **What this exposes:** the weak link on the face is now the **procedural yellow irises +
   smooth face GEOMETRY** — a geometry/eye problem, no longer a texture problem.
2. **MetaHuman: D76's stated blocker is obsolete (Epic relicensed June 2025)** — standard UE terms, free
   under $1 M revenue, usable in **any engine**, and MetaHumans **can be sold/redistributed**. That kills the
   redistribution/SaaS clause D76 called fatal. **What survives is the D97 clause:** use *in* AI workflows is
   allowed, **training or enhancing AI models is not** — and our gaussian fit + corrective MLP sits on that
   line. Net: same conclusion, different reason. Practical: `.mhpkg` behind an Epic account (not fetchable
   from this box), Fab's listing API is Cloudflare-blocked so the **free-pack count is UNVERIFIED**, and
   MetaHuman textures are in **MetaHuman's own UV layout** → need a UV-transfer bake regardless of licence
   (same reason the film-grade Lee Perry-Smith maps in `assets_src/heads/` are still unused).
3. **Meshy for clothing/hair is buildable today, no new binder needed** — D97 already cleared **Meshy PAID
   tier** (paid = you own it, sell without attribution; free tier is CC-BY, never use), ~$20/mo, re-confirmed
   against Meshy's current help centre. `mpfb_prefit.transfer()` takes a **raw `garment_verts` array** and
   binds by nearest-triangle barycentric + signed-normal offset onto Anny's rest body — **no MHCLO metadata
   required**. A Meshy garment only needs alignment/scale to Anny's rest pose, then it feeds the D101 XPBD
   cloth path unchanged. Caveats: Meshy hair is a solid SHELL not cards (fine once baked to gaussians, wrong
   in the mesh preview), and watertight single-sided shells may need cleanup before XPBD. **This is the
   concrete, ~$20/mo answer to D103's "the ceiling is the boxy proxy ASSETS" ($300–1.5k/garment).**

---

## ▶ D105 — DROP THE SPLAT (tested two ways, both say the same thing)

User restated the product — click-to-customise avatars, LLM-driven — with three hard requirements: **browser**,
**MetaHuman-class skin/face/motion** (accessories can compromise), **cheap + commercially clean for selling AND
AI training** — plus: *"splatting is introduced so we can have that realism in the browser, but if we can render
the textures fine in the browser then we should just do that."* **Tested. Textured mesh wins on both axes.**

### Test 1 — the browser (BUILT, RENDERS, verified headless)
`dataset/export_skin_glb.py` (NEW) → Anny + the D100 SMOKEWORKS PBR skin as standard glTF 2.0
(baseColor sRGB + normal + ORM; the ORM's G=roughness/B=metallic packing is already glTF's convention,
so it drops straight in; metallicFactor 0 per D41). `dataset/viewer/skintest.html` (NEW, route **`/skintest`**)
renders it in three.js r160 with PMREM/RoomEnvironment IBL + ACES tone mapping.

| | splat (D104 best ever) | textured mesh (D105) |
|---|---|---|
| wire size | 10.2 MB | **10.0 MB** |
| load | — | **1.2 s** |
| geometry | 41k gaussians | 27,420 triangles + 2048² maps |
| face detail | soft mannequin, dark eye smudges | **skin pores, brow hair, lip + ear detail** |
| animates | mesh-anchored LBS + correctives (unsolved risk) | ordinary skinned mesh (solved for 20 years) |

Proof: `motion_out/d105_splat_vs_mesh.png`, `d105_browser_head.png`, `d105_browser_body.png`.
Consistent with D98/D102 — the splat's blur was never a fit problem; a mesh + real texture sidesteps it.

**Two bugs found + fixed building it:** (a) trimesh omits the glTF **NORMAL accessor** unless vertex normals are
already cached → the whole body rendered **black** in three.js (no normals, no shading); (b) baking D81's
procedural iris ramp to **vertex colours** smears the pupil across the eye, because each Anny eyeball is only
~80 verts — replaced with a rasterised iris texture + gaze-aligned planar UVs. Eyes are still the weakest part
(procedural iris reads gold); real eyes need an actual iris photo texture.

### Test 2 — the licences (the same decision, from the other direction)
**Every premium vendor bars AI TRAINING, not AI USE.** Epic, verbatim:

> "You can use MetaHuman characters and animation in workflows that incorporate artificial intelligence
> technology. However, you may not use MetaHuman characters or animation curves to build or enhance any
> database or train or test artificial intelligence, machine learning, deep learning, neural networks, or
> similar technologies … This includes the use of rendered output from MetaHuman digital characters and
> animation curves, if created to replicate the functionality of MetaHuman."

Our **gaussian fit + corrective MLP is the prohibited act** (optimise on rendered output → produce a digital
human). An **LLM directing a textured mesh at runtime is the permitted act**. Same flip at Reallusion, Daz and
3DScanStore. **Corrects D76/D104 again:** MetaHuman's blocker is neither redistribution (gone in Epic's
June-2025 relicence) nor the AI clause in general — it is **the splat fit specifically**.

### Source verdicts (all eight links)
| Source | Verdict |
|---|---|
| **Reallusion Character Creator** | **Strongest fit.** Real-time game-grade humans, click-to-customise morphs, GLB/FBX out, explicit games/XR/"interactive online services" grant, and uniquely an **Enterprise tier that GRANTS AI-training rights** — the only off-the-shelf clean-for-training licence found. |
| **NVIDIA Audio2Face-3D** | **Adopt for the face.** MIT SDK + NVIDIA Open Model weights + **Apache** training framework, ONNX/NIM. Audio→ARKit-blendshape lip-sync, clean and self-hostable. This is the D62 face layer, solved. |
| **Kimodo / SOMA** | Keep as the body-motion source (D67/D70). |
| **3DScanStore albedo pack** | Usable for **texture-only** use (~£59 + £961 commercial tier). Blocked only if we fit gaussians to it. |
| **Daz 3D** | Usable, but needs the per-figure **Interactive License** — their EULA bars meshes "in any form where it can be extracted", which a browser app always is. |
| **Convai** | The **AI/runtime layer**, avatar-agnostic — a competitor to our director, not an asset source. Buying it gives away the moat. |
| **Lychee Studio** | Generic text→3D, asset licence unverified, not a human specialist. Skip for now. |
| **MetaHuman** | Legally fine for a **mesh** product, blocked for the **splat**, gated behind Epic tooling (`.mhpkg` + Epic account) and its own UV layout. |

### Side win + caveat
**The "no headless browser on this box" gap (open since D98) is CLOSED** — Playwright + Chromium installed and
driving `/skintest`. FPS under SwiftShader is software-rasterised and meaningless; geometry/material/console-error
verification is real. **Caveat: the box is at 99% disk (338 MB free)** — that is what failed the first install.

### Recommendation
Make the shipping product a **textured, rigged mesh** (Reallusion CC or Anny base + real PBR skin + Audio2Face
face + Kimodo body motion + LLM director). Demote gaussian splats from "the realism mechanism" to an optional
premium/offline path. This satisfies all three requirements at once, is the cheapest path, **and retires the
deformation risk this handoff calls "the one risk that decides everything"**.

---

## ▶ IMMEDIATE NEXT (pick up here)

0. **NEW after D104 — two unbuilt levers, both now unblocked:** (a) a **UV-transfer bake** that projects any
   source head (MetaHuman, Lee Perry-Smith "Infinite", a scan) onto Anny's UV layout — unblocks both the
   MetaHuman test and the film-grade LPS maps we already own; (b) **swap the LIVE viewer's base model off the
   procedural skin** onto a real SMOKEWORKS one (this is #7 below, and `d104_skin_matrix.png` shows it ready).

1. **BROWSER-VERIFY the whole batch (D98–D104)** — no headless browser on this box, so all of it is verified
   only via offline render + exact-server-bytes. Open **`/splat`** (zoom IN reveals the face/arms as a crisp
   surface, no vanish — D98; the single `poc_avatar` card is now the D104 real-skin frozen fit, and the
   distorted D102 `poc_avatar_hidetail` card is deliberately gone) and the Studio:
   click **`＋ Dressed walk`** with the **"Baked cloth"** toggle on (clothes walk with the body, real drape +
   folds via MPFB2 geometry, shirt-over-shorts, hands no longer through the torso — D99/D101/D103; try the tee +
   `cortu_jeans_shorts` + `elvs_reverse_french_braid_bun` bun). Use PREFIXED ids in any manual endpoint test
   (`top=top:<name>`, `bottom=bottom:<name>`).
2. **DETAIL CEILING = THE SOURCE, resolved (D98 + D102 — no more "detail knobs" to turn).** Both more cameras
   (D98) AND unfreezing the means + densification (D102) were proven NOT to add detail on our smooth CG-mannequin
   source (D102 control: free fit = frozen fit = 26.89 dB on identical real-skin GT). Real skin (D100) visibly
   helped the SURFACE. The ONLY remaining detail levers are SOURCE-side: (a) **bake the D100 normal maps as
   DISPLACEMENT geometry** before the fit (cheap, buildable now — we have the maps) so the mesh actually carries
   pore/wrinkle relief; (b) **real photo capture** of a real person (the D74 endgame). Do NOT spend more time on
   renderer/fit-side detail — it's saturated.
3. **Real cloth polish (D101/D103 follow-ups):** (a) intra-garment SELF-collision (fold-on-fold) still not
   simulated; (b) **wire-size** — the MPFB subdivided default outfit is ~40 MB on the wire (hair bun dominates);
   drop hair subdiv (`_SLOT_SUBDIV`) or add a compressed garment format; (c) pre-bake more outfit combos (only
   the default is MPFB-baked; others fall back to affine+LBS live, no drape). The real quality ceiling is the
   ASSETS themselves (boxy proxy garments) — see D103; genuine improvement needs commissioned garments (~$300–1.5k,
   over budget) — a spend decision for the user, not an engineering one.
4. **Fix the NON-CYCLIC walk (surfaced by D101):** the source Kimodo clip jumps ~155 mm at the 149→0 loop
   seam, so the whole avatar (clothed or not) hitches every loop. This is a MOTION-source fix (re-loop / blend
   the clip ends), independent of cloth — worth doing since it's visible on the bare body too.
5. **Texture + gaussian-fit the composed avatar**: `compose_avatar.py` (now LBS, D96) writes a
   multi-material `.obj` (body/hair/eyebrows/shirt/pants) — run it through a `blender_render_skin.py`-style
   textured multi-view render, then the D95 gsplat fit (now anisotropic), for the first fully-dressed splat
   avatar.
6. **The clothing-fit accuracy FLOOR (MPFB2 engine) — DONE (D103).** MPFB2 is now wired in as an offline-baked
   fitting path (`mpfb_fit_blender.py` + `mpfb_prefit.py`, `fit_rest()` entry with affine fallback): subdivision
   gives the geometry to drape + fixes the hard cases (bun un-excluded). Residual: only the default outfit is
   MPFB-baked (others fall back to affine+LBS); the real remaining ceiling is the boxy proxy ASSETS, not the fit.
7. **Real skin texture on the base model — NOW UNBLOCKED by D100.** D100 downloaded **real CC-BY PBR skins on
   the MakeHuman UV** (`assets_src/skins/smokeworks_vol{0,1}/`, 5 identities) — drop-in for
   `blender_render_skin.py`'s `build_skin()`. Wire one onto `walk_face`'s material (and/or the fit render) so
   the Textures toggle loads an actual UV map instead of the flat-color+blotch stand-in. The Lee Perry-Smith
   Infinite head (`assets_src/heads/`) is the higher-detail face option if the base face isn't enough.
8. **The FIT WORKER** (the D74 backend milestone): the viewer's Capture tab already uploads multi-view T-pose
   images and `/fit` queues a job to `motion_out/fit_jobs/` — **nothing consumes it yet.** Wire the worker to run
   the (now much-improved) `fit_gsplat_poc.py` pipeline on uploaded REAL captures → emit a splat that drops
   into the Studio scene.
9. **The real bet (D74):** extend the static fit to **rig-anchor + pose correctives + fit to REAL multi-view
   capture** (3DGS-Avatar / Animatable-Gaussians family) and drive it with a couple of LLM-style commands.
   (See item 2 — unfreezing the means for detail is the same architectural fork as this bet.)
10. **Delivery format:** adopt a **compressed splat** (.sog/SOGS/.splat/.ksplat, ~10–20× smaller) at the delivery-
   wiring stage for the on-device/wire-size thesis. Keep `.ply` for debugging now.

---

## ▶ KEY FILES (this session)
**D105 additions/changes:**
- `dataset/export_skin_glb.py` — **NEW.** Anny + real PBR skin → browser-ready glTF 2.0 (baseColor/normal/ORM,
  matte metallic, rasterised iris texture + gaze-aligned eye UVs). `--texres` sets the shipped texture edge.
- `dataset/viewer/skintest.html` — **NEW.** Route `/skintest`: three.js r160 + PMREM/RoomEnvironment IBL + ACES,
  shading toggles (full PBR / albedo-only / normal-off / wireframe), head+body cameras, live fps/tris/wire HUD.
- `dataset/viewer/serve_viewer.py` — routes `/skintest` and `*.glb` (served from OUT as `model/gltf-binary`).
- `dataset/viewer/vendor/addons/{loaders/GLTFLoader.js,environments/RoomEnvironment.js,utils/BufferGeometryUtils.js}`
  — vendored for three r160 (matching the existing pinned revision).
- `dataset/motion_out/{skin_test.glb,d105_splat_vs_mesh.png,d105_browser_head.png,d105_browser_body.png}` — outputs (gitignored).
- Playwright + Chromium installed system-wide; drive it with `p.chromium.launch(channel="chromium", headless=True,
  args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--no-sandbox"])`.

**D104 additions/changes** (no new source files — a re-run + a swap):
- `dataset/motion_out/poc_avatar.ply` — **REPLACED** by the frozen real-skin refit (held-out 27.29 dB). Prior
  live fit kept as `poc_avatar_preD104_procedural.ply.bak`; D102's distorted free fit demoted to
  `poc_avatar_hidetail_D102_freefit.ply.bak` (both `.bak`, so `discover_splats()` ignores them).
- `dataset/motion_out/_refit_d104_realskin/` — **NEW.** README (exact rig + fit commands + the drift numbers),
  `transforms.json`, the 192 real-skin views, `fit.log`, `fix_compare.png`, `three_way.png`. Gitignored (32 MB).
- `dataset/motion_out/d104_three_way.png` / `d104_turntable.gif` / `d104_skin_matrix.png` — **NEW** proof images.

**D102–D103 additions/changes:**
- `dataset/fit_gsplat_free.py` — **NEW (D102).** Free-optimized static 3DGS fit: means UNFROZEN + gsplat
  `DefaultStrategy` densification. Output `poc_avatar_hidetail.ply` (static, does NOT animate). Proved the
  detail ceiling is the SMOOTH CG SOURCE, not the frozen means (free fit = frozen fit = 26.89 dB).
- `dataset/blender_render_skin.py` — **D102: +optional real-PBR-skin path** (`--skin_basecolor/--skin_normal/
  --skin_orm`, MakeHuman-UV drop-in for the D100 SMOKEWORKS skins).
- `dataset/mpfb_fit_blender.py` — **NEW (D103), bpy+MPFB2.** Fits the clothing/hair catalog via MPFB2's own
  `HumanService.create_human()` + `add_mhclo_asset(subdiv_levels=…)`, exports to `motion_out/mpfb_out/` (regen script).
- `dataset/mpfb_prefit.py` — **NEW (D103).** Transfers MPFB-fitted garments onto Anny's rest body (pose-correct
  barycentric+normal transfer through the shared 19,158v basemesh) + ramped ease. `fit_rest()` = the single
  entry point every dress path calls (MPFB prefit when exported, affine `fit_mhclo` fallback otherwise).
- `dataset/dress_walk.py` + `viewer/serve_viewer.py` — **D103: `_fit_selection` / `build_compose_buffer` routed
  through `mpfb_prefit.fit_rest`; `build_catalog` MPFB-aware; bun un-excluded.**
- `dataset/motion_out/poc_avatar_hidetail.ply`, `hidetail_compare.png`, `mpfb_out/` — **D102/D103 outputs** (gitignored).

**D98–D101 additions/changes:**
- `dataset/dress_walk.py` — **NEW (D99).** The walk-dressing engine: offline precompute
  (`--stem walk_face` → `walk_face_framedata.npz`: per-bone LBS transforms + the exact per-frame rigid
  native→display transform) + request-time serving (`dress_walk_buffer` → `OWK1` buffer). **D101: + XPBD
  cloth bake** (`_simulate_cloth`/`_body_collider`/`_anchor_band`/`bake_cloth`, CLI `--bake-cloth --top --bottom`),
  served via the `cloth=` flag (default baked, falls back to LBS). **D101: + arm-abduction** in precompute.
- `dataset/outfit_lib.py` — **D101: +`apply_arm_abduction` (`ARM_ABDUCT_DEG=13`, +`_rodrigues`/`_bone_subtree`)**
  — the shared skeleton-level fix so the walk's hands clear the torso; called by both `pose_default_walk.py`
  and `dress_walk.py` so displayed body + garment can't drift.
- `dataset/pose_default_walk.py` — **D101: `import outfit_lib` + `--arm-abduct` flag**, abduction applied in
  the retarget loop (re-export `walk_face_verts.npy` after any change, then re-run `dress_walk.py --stem`).
- `dataset/viewer/splat.html` — **D98: zoom-in fix** (`zoomToCursor` off, tuned `zoomSpeed`/`minDistance`/
  `maxDistance`, `clampTarget()`), client-only (browser reload).
- `dataset/blender_render_skin.py` — **D98: new `--rig shells`** multi-shell height-layer rig (2 radii × 4
  heights × N azimuth; flags `--layers/--az/--radii/--layer-frac/--elev-spread`; legacy `--rig ring`/`--elevs` kept).
- `dataset/viewer/serve_viewer.py` — **D99: `/outfit_walk.bin`** endpoint (dressed walk); **D101: `cloth=` param.**
- `dataset/viewer/viewer.html` — **D99: `＋ Dressed walk` button** (+ `updateDressWalkFrame` in `setFrame`);
  **D101: "Baked cloth" toggle.**
- `dataset/motion_out/assets_src/skins/`, `assets_src/heads/` — **NEW (D100), gitignored.** Real CC-BY PBR
  skins (SMOKEWORKS Vol.0/1, 5 identities) + Lee Perry-Smith Infinite head, each with a `PROVENANCE.md`.
- `research/avatar-asset-sources-2026.md` — **D100: +"Acquired / Buy list (2026-07-23)"** section.

**Prior-session files:**
- `dataset/fit_gsplat_poc.py` — Mesh-anchored gsplat fit: CC0 renders → projected-color init → smoothness-
  regularized optimization → best-held-out-PSNR checkpoint → **3x densification (D83)** → `.ply` + turntable.
  **D95: anisotropic surface-aligned-disk init** (the spheres/foam fix).
- `dataset/blender_render_skin.py` — **+`--poses`** flag (dumps camera intrinsics/extrinsics JSON for the fit).
- `dataset/pose_default_walk.py` — **+`--stem`** flag (D81): exports a live-viewer-ready DEFAULT-topology
  model (`<stem>_verts/_faces.npy` + `<stem>_eyemeta.json` with procedural pupil placement) instead of just
  an offline OBJ sequence. This is the model that actually has eyes.
- `dataset/mhclo_fit.py` — General MakeHuman/MPFB2 `.mhclo` asset fitter — parses the binding format
  (D83: **+ offset-scale calibration**, **+`max_offset` clamp**), applies it to a basemesh, returns fitted
  verts+faces+UV+material path. **D89: fixed the actual index-space bug** — must be called with the
  19,158v `arms_down_fit_basemesh()` array now, not the old 13,718v default-topology one (see its docstring
  for the full root-cause).
- `dataset/outfit_lib.py` — **NEW (D84).** Shared arms-down basemesh pose (`arms_down_basemesh()`, now
  **40°/-40°**, was D83's unverified 75° that overshot into the crossed-arms bug) + validated asset fitting
  (`fit_asset_checked()` = `mhclo_fit.fit_mhclo` + below-feet filter + a sane-bbox-envelope check). Used by
  both `compose_avatar.py` and `viewer/serve_viewer.py` so they can't drift apart again. **D89: +
  `arms_down_fit_basemesh()`** — the CORRECT (19,158v, index-space-exact, 0.00mm-verified surface match to
  the displayed body) basemesh to fit `.mhclo` assets against; `arms_down_basemesh()` (13,718v) stays the
  DISPLAY mesh only, unchanged. All three fitting call sites now pass the new one.
- `dataset/compose_avatar.py` — Composes a dressed avatar from multiple `.mhclo` assets via `outfit_lib`;
  writes a combined multi-material `.obj` + an optional pyrender preview. D84: refactored onto `outfit_lib`,
  pose bug fixed (see above) — re-verify with `motion_out/composed_avatar_v2.png`, not the older
  `composed_avatar.png` (that one still has the bug).
- `dataset/motion_out/assets_src/` — **NEW (D84), gitignored.** Curated, pre-validated CC0 MakeHuman/MPFB2
  packs copied out of a prior session's `/tmp` scratch (was never durable before). `{hair,eyebrows}/<name>/
  <name>.mhclo` and `clothing/{tops,bottoms}/<name>/<name>.mhclo`. Live catalog count after D89's fit-basemesh
  fix: **14 hair / 13 eyebrows / 5 tops / 2 bottoms** (was 14/13/2/2 after D85/D86's exclusions — 3 tops
  un-excluded by D89; 1 hair asset, `elvs_reverse_french_braid_bun`, stays excluded, see Immediate Next §3).
- `dataset/viewer/serve_viewer.py` — **+`/splat.bin`**, **+`/eyemeta.json`**, **+`_faces_path()`** (per-stem
  faces resolution). **D84: +`/catalog.json?kind=`, `/asset_src/<kind>/<name>/thumb`, `/compose.bin`**
  (builds the Hair/Clothing catalog from `assets_src/` via `outfit_lib`, validates + caches; live-composes
  the selected outfit into a static mesh buffer), **+`/splats.json`, +`/splat` route** (serves `splat.html`).
- `dataset/viewer/viewer.html` — Textures / ＋ Splat compare buttons (splat renderer still the D82/D83
  billboard-quad shader — see `splat.html` below for the new primary route). **D84:** Hair/Clothing tabs now
  render selectable catalog cards (grouped Hair/Eyebrows, Tops/Bottoms) above the existing upload dropzone;
  new **"＋ Outfit"** button + `outfitGroup` loads `/compose.bin` for the current selection into a static
  preview mesh beside the animated body; a "Splat viewer ↗" link in the top bar opens the new route.
- `dataset/viewer/splat.html` — **NEW (D84).** Dedicated `/splat` route, same shell (top bar/left rail/right
  panel) as the Studio. Renders gaussians as a `THREE.InstancedMesh` of low-poly icospheres (native
  per-instance `instanceMatrix`/`instanceColor`, not a hand-wired shader) — chosen because it can't silently
  degenerate into sparse points the way `gl_PointSize` or a custom billboard-quad attribute bug can. Left
  rail lists every `.ply` in `motion_out/` as a selectable card; right panel has size/opacity sliders.
- `dataset/export_textured_obj.py`, `render_soma_motion.py` — existing render/motion scaffold.
- ⚠️ `dataset/viewer/` and most `dataset/*.py` are **untracked in git** (`??`) — commit when ready.

## ▶ STANDING GUARDRAILS (don't relearn the hard way)
- **Appearance = CC0/owned/commissioned ONLY.** Never MetaHuman/Daz/Reallusion/Renderpeople (ML-training bars, D73);
  never ship the raw asset to the browser under a standard EULA (redistribution bars, D76/D77).
- **MakeHuman/MPFB2 asset packs (hair/clothes/eyebrows/eyelashes/beards/hand-face-detail) = VERIFIED CLEAN**
  (D81) — CC0 or CC-BY throughout, no AI bar, no cap, no redistribution restriction. This is the go-to source
  for appearance assets going forward; use `dataset/outfit_lib.py`'s `fit_asset_checked()` (wraps
  `mhclo_fit.py` + validation) to fit them onto Anny (works well for close-fitting assets today; flowing
  hair needs the addon route, see Immediate Next §4).
- **New downloaded assets go in `dataset/motion_out/assets_src/{hair,eyebrows,clothing/{tops,bottoms}}/`**
  (D84) — gitignored but durable (survives across sessions, unlike `/tmp` scratch). Don't hand-curate a
  "safe list" — `outfit_lib.fit_asset_checked`'s bbox-envelope check does that automatically when
  `serve_viewer.py` builds the catalog; a bad asset just silently won't appear as a card.
- **This box's root disk sits ~94-95% full** (32GB, ~1.8GB free as of D84) — `du -sh` a download before
  copying it in; prefer curating a subset over copying a whole asset pack wholesale.
- **Motion = Kimodo-RP / GEM-X / CMU-bake only** (D69); never Bones-SEED/AMASS/SMPL/Mixamo for anything shipped.
- **Anny topology:** default (13,718-v) or `soma` (18,056-v) only; **never the `smplx` topology** (NC trap, D56).
- **Disk:** the 32 GB root has filled to 100% before (caused crashes) — **watch free space before big renders.**
  HF cache (Qwen3-8B ~16 GB) is the big reclaim if motion isn't being regenerated.
