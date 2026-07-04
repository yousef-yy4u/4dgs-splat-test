# SPIKE: animated-beautiful-splats (gaussian-vrm proof-of-concept)

Started 2026-06-24. Tracks the D33 plan (PROJECT.md §10). Step 1 = clone gaussian-vrm + inspect
its skinning API against our PLY/rig. **Step 1 DONE — findings below.** Source studied:
github.com/naruya/gaussian-vrm @ efc2a9b (MIT), fetched to scratchpad (full clone is network-bound;
key files pulled via raw URLs).

## TL;DR — better than expected
- gaussian-vrm's "skinned splat" = **mkkellogg `SplatMesh` (the renderer we already use) + a vertex-shader
  patch** (`gsCustomizeMaterial`, gvrm.js:458-704) that skins each splat's **center AND covariance** from
  the live skeleton's boneTexture. That patch is the entire trick. It's MIT.
- **The patch is compatible with mkkellogg 0.4.7 — the version splat.html already pins.** All 4 string-replace
  anchors (`mat3 cov2Dm = transpose(T) * Vrk * T;`, `splatCenter = uintBitsToFloat`,
  `mat4 transform = transforms[sceneIndex]`, `viewCenter = transformModelViewMatrix`) + APIs
  (`splatDataTextures.baseData.{centers,colors,covariances}`, `updateDataTexturesFromBaseData`,
  `dynamicScene:true`) are present in 0.4.7. No renderer migration needed.
- **Our SH concern is moot.** Our skinned PLY is SH order 0 (`f_dc_0..2` only, no `f_rest_*`) → plain RGB,
  no SH basis to rotate under skinning. One less thing.

## How gaussian-vrm actually skins (the recipe)
Two-level deformation on top of mkkellogg:
1. **Coarse (rigid, per-bone scene split):** PLY is split into N splat-scenes, one per bone
   (`sortSplatsByBones`). Each frame `updateByBones()` sets each scene's `position`/`quaternion` to the
   bone midpoint/rotation. mkkellogg sorts WITHIN a scene once; scenes move rigidly → **no per-frame global
   re-sort** (this is the "sort-on-canonical, render-on-skinned" perf trick our memory flagged as the open
   problem).
2. **Fine (per-splat, in shader):** `gsCustomizeMaterial` patches `SplatMaterial.onBeforeCompile`:
   - uploads mesh pos/normal/skinIndex/skinWeight + per-splat `gsMeshVertexIndex` + `gsRelativePos` as
     data textures;
   - deforms **center**: `splatCenter = meshMatrixWorld * (meshVert + skinMatrix*inverse(skinMatrix0)*relativePos)`;
   - deforms **covariance** (the key bit, gvrm.js:676-701):
     ```glsl
     mat3 skinRotationMatrix = mat3(skinMatrix * inverse(skinMatrix0));
     mat3 relativeRotation   = transpose(gsRotation0) * skinRotationMatrix * gsRotation0;
     // (gaussian-vrm round-trips through a quaternion + a hardcoded y-flip — "maybe bug in quatFromMat3")
     mat3 rotatedVrk = transpose(relativeRotation) * Vrk * relativeRotation;
     mat3 cov2Dm     = transpose(T) * rotatedVrk * T;   // anchor replaced
     ```
   This is the 3DGS-Avatar-style `R_o = T·R_d` applied directly to the 3D covariance Vrk. **This is exactly
   the Gap-2 fix** (our studio shader transforms position only).

## How it maps to OUR pipeline — and where we diverge (simpler)
gaussian-vrm is **VRM/humanoid-coupled**: three-vrm loader, hardcoded `J_Bip_*` bone names, hardcoded bone
indices (57=head, 21/19=feet) for cleanup, and a `.gvrm` zip (model.vrm + model.ply + precomputed
`splatVertexIndices/BoneIndices/RelativePoses`). It binds each splat to a **mesh vertex** and reads skin
weights **from the mesh** in-shader.

We don't need most of that, because **`bind_splat.py` already bakes per-splat 4 bone indices + 4 weights
(`j0..j3`, `w0..w3`)**. So our adaptation is *simpler than gaussian-vrm*:
- skip VRM entirely (we have an arbitrary GLB rig; works for crab/butterfly/human — "both/mixed");
- skip the mesh-vertex indirection + mesh skin-attribute textures — skin each splat directly from its own
  baked j/w;
- reuse studio's existing GLB→skeleton handling and its boneMatrices; capture a rest-pose boneTexture0 like
  gaussian-vrm does;
- (optional, later) add the per-bone scene split for sort-amortization once correctness is proven.

What we LIFT verbatim (MIT): the `cov2Dm` covariance-rotation snippet + the boneTexture0/skinMatrix0 rest-pose
capture. That's the part that turns dots into correctly-oriented ellipsoids.

## BUG found in bind_splat.py (must fix for anisotropic rendering)
`bind_splat.py:113-131` transforms **only x,y,z** into the mesh frame; it copies `scale_0..2` and `rot_0..3`
UNCHANGED. The registration applies a similarity (scale `s`, rotation `R`) to fix TRELLIS's splat-vs-mesh
frame mismatch (often a ~90° axis swap). For the Points/dots renderer that's invisible (points have no
orientation). For a real anisotropic renderer **every ellipsoid would be mis-oriented by `R` and mis-scaled
by `s`**. Fix: rotate the quaternion `rot_0..3` by `R` and multiply `scale_0..2` by `s` (or by `log(s)` in
log-scale space — check whether scales are stored raw or log) when writing the skinned PLY. Emit `(s,R,t)`
into the PLY/sidecar too, for debugging.

## Step-2 status (2026-06-24): bind fix DONE + verified; PoC BUILT, awaiting in-browser validation
- **bind_splat.py FIXED + numerically verified.** Now bakes the registration rotation+scale into each
  splat's covariance (orientation+size), not just position. Verification on gen_3594c97a: `A_total` is a
  clean similarity (singular values [1.985,1.985,1.985], det +7.83); per-splat `(detΣ'/detΣ)^(1/6)=1.9853`
  with **zero variance** (every ellipsoid scaled by exactly the registration scale); anisotropy preserved
  exactly. Rotation *direction* (quaternion convention) still needs visual confirmation.
- **split_by_bone.py** (new): skinned PLY → one plain-3DGS PLY per dominant bone + manifest.json. Ran on
  gen_3594c97a → 25 bone scenes in studio_out/poc_3594c97a/.
- **poc_splat_anim.html** (new): loads the rig + per-bone splat scenes via mkkellogg DropInViewer
  (dynamicScene, SH degree 0), parents the viewer under the SkinnedMesh (mirroring studio's working dots),
  and drives each bone-scene rigidly by `D_b = bindMatrixInverse·boneMatrices[b]·bindMatrix` (the exact
  transform studio's per-point shader uses — so correct-by-construction for single-bone splats, with seams
  AT joints, the known rigid-skinning limitation). Sway animation + mesh-ref toggle. Served at
  **/out/poc_splat_anim.html** (copied into studio_out so no TRELLIS-reloading restart) and **/poc** (after
  next restart). Stack: three@0.170 + mkkellogg vendored module (single three instance via importmap).
- **NEEDS GPU/BROWSER VALIDATION (user):** open http://localhost:8077/out/poc_splat_anim.html — check
  (1) ellipsoids not dots, (2) upright/oriented like the mesh ref (else flip quaternion convention in
  bind_splat.py), (3) animate → splat follows skeleton aligned with mesh ref. Risks to watch: mkkellogg
  DropInViewer nested under a SkinnedMesh may not honor the parent world transform in all paths (fallback:
  wrap the viewer in its own wrapFixed group + compute D_b in geometry frame); the quaternion-convention
  assumption in the bind fix.

## PoC plan (step 2 — original notes)
New viewer (fork of benchmark/splat.html, which already loads mkkellogg 0.4.7):
1. load skinned PLY via `GS.Viewer`/`DropInViewer` with `dynamicScene:true`, SH degree 0;
2. build per-splat j/w data textures (indexed by splatIndex, mirroring gaussian-vrm's gsMeshVertexIndex upload);
3. load the rigged GLB (studio already does this) → SkinnedMesh skeleton → boneTexture (+ capture rest boneTexture0);
4. patch `splatMesh.material.onBeforeCompile`: skin center (`bindMatrixInverse * skinMatrix * inverse(skinMatrix0) * bindMatrix * center`) + rotate Vrk by `mat3(skinMatrix*inverse(skinMatrix0))`;
5. drive bones with studio's existing sway/manual-rotation animation;
6. **needs in-browser GPU validation** (can't be verified headless) — render side-by-side vs the current
   THREE.Points dots, same asset + skeleton + motion.
Watch-outs: bone-index alignment (our j = GLB skin-joint order = three.js skeleton order — should match);
the quaternion y-flip hack in gaussian-vrm (frame convention — expect to re-derive for our frames);
fix bind_splat.py first or the ellipsoids will be rotated wrong.
