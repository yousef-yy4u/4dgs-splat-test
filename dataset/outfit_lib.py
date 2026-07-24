"""
Shared body-pose + garment-fitting helpers used by both the offline `compose_avatar.py`
script and the live viewer server (`viewer/serve_viewer.py`'s catalog/compose endpoints).
Pulled out as a single module (D84) so the two call sites can't drift apart the way the
arms-down rotation angle did (75deg in compose_avatar.py was never validated against an
actual render and overshot the wrist past straight-down into a forward curl -- root-caused
by numerically tracking where the upperarm01->wrist rest vector actually lands, see
ARMS_DOWN_DEG below).

Anny frame reminder: Z-up (height), Y = front/back depth, X = left/right. Rotating the
upper-arm bone about the world Y axis swings the T-pose arm (pointing along +-X) down
toward -Z without touching front/back offset -- the right axis for "put the arm at your
side". The angle is NOT 90 (that would swing the arm fully vertical relative to the
*rotation*, but the T-pose arm isn't perfectly horizontal to begin with and the pivot is
the shoulder joint, not the origin) -- 40/-40 was found by rendering the bare body at
several angles and reading the wrist's position relative to the shoulder pivot; at 40 the
wrist lands ~[0.04, -0.22, -0.45] relative to the upperarm01.L pivot, i.e. almost directly
below the shoulder. 75 (the original guess) overshoots to ~[-0.21, -0.22, -0.40] -- past
vertical and curling back up in FRONT of the torso.
"""
import math, os
import numpy as np
import torch

ARMS_DOWN_DEG = 40.0
ADULT = dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5)

# --------------------------------------------------------------------------------------
# ARM ABDUCTION (D-selfcollision): the retargeted Kimodo walk swings the hands to the
# front-centre of the pelvis, driving up to ~1000 hand/forearm verts as deep as ~65 mm
# INTO the torso/pelvis volume on 133/150 frames (measured by ray-cast containment against
# the body-minus-lower-arms mesh; frame 0 / rest is clean). Nothing tells the hand the torso
# is solid, so the body self-penetrates. The fix is at the SKELETON level, not the mesh: add
# a small OUTWARD abduction to each whole arm so the arms hang a little away from the body and
# the hands swing fore-aft BESIDE the hips instead of across the pelvis front. Verified: -/+13
# deg drives penetration to exactly 0 verts on every previously-worst frame while the pose
# still reads as a natural relaxed walk (arms clear the torso with a small gap). Applied in
# WORLD space (about Anny's native fore-aft axis) to the ENTIRE arm subtree so the whole arm
# rotates rigidly about the shoulder -- the gait's fore-aft swing and the elbow/hand articulation
# are preserved, only the resting lateral offset changes. MUST be applied identically in
# pose_default_walk.py (the displayed body) and dress_walk.py (the garment bone_transforms) or
# the garments drift off the arms; both call `apply_arm_abduction` with this same default.
ARM_ABDUCT_DEG = 13.0


def _rodrigues(axis, ang):
    axis = np.asarray(axis, float)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def _bone_subtree(root, parents):
    """All bone indices in the subtree rooted at `root` (inclusive), given a parent array."""
    out = {root}
    changed = True
    while changed:
        changed = False
        for b in range(len(parents)):
            if parents[b] in out and b not in out:
                out.add(b); changed = True
    return out


def apply_arm_abduction(D, bone_labels, parents, deg=ARM_ABDUCT_DEG):
    """Premultiply each arm-subtree bone's WORLD-orientation delta (a list of (3,3) numpy
    matrices, one per bone, as built by the walk retarget) by an outward rotation about Anny's
    native fore-aft axis, so both arms hold slightly away from the body and the hands clear the
    torso during the walk (see ARM_ABDUCT_DEG). Left arm rotates -deg, right +deg (verified sign:
    this swings the hands OUTWARD, away from the pelvis). Returns a NEW list; `deg`=0 is a no-op.
    Call this identically from every place that reconstructs the walk pose (pose_default_walk.py
    AND dress_walk.py) so the body and its garments stay registered."""
    if not deg:
        return list(D)
    uaL = bone_labels.index("upperarm01.L")
    uaR = bone_labels.index("upperarm01.R")
    subL = _bone_subtree(uaL, parents)
    subR = _bone_subtree(uaR, parents)
    AL = _rodrigues([0., 1, 0], math.radians(-deg))   # native fore-aft axis
    AR = _rodrigues([0., 1, 0], math.radians(+deg))
    return [(AL @ D[b]) if b in subL else (AR @ D[b]) if b in subR else D[b]
            for b in range(len(D))]


_cache = {}


def _arms_down_pose_deltas(m, rest):
    """Build the local-bone delta transforms (NB,4,4 torch f64) that relax both arms from
    the raw T-pose to ARMS_DOWN_DEG at the sides. Factored out of `_arms_down_forward` (D96)
    so the SAME deltas drive both the display body's `m.forward` AND the garment's
    LBS bone-transforms (`arms_down_bone_transforms`) -- they must be bit-identical or the
    garment drifts off the body."""
    BL = m.bone_labels
    Rr = rest["rest_bone_poses"][0, :, :3, :3].numpy().astype(np.float64)
    NB = len(BL)
    Ppose = torch.eye(4, dtype=torch.float64).unsqueeze(0).repeat(NB, 1, 1)
    world_axis = np.array([0., 1, 0])
    for bone_name, ang_deg in [("upperarm01.L", ARMS_DOWN_DEG), ("upperarm01.R", -ARMS_DOWN_DEG)]:
        b = BL.index(bone_name)
        local_axis = Rr[b].T @ world_axis
        local_axis /= np.linalg.norm(local_axis)
        ang = math.radians(ang_deg)
        K = np.array([[0, -local_axis[2], local_axis[1]],
                      [local_axis[2], 0, -local_axis[0]],
                      [-local_axis[1], local_axis[0], 0]])
        Rloc = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)
        Ppose[b, :3, :3] = torch.from_numpy(Rloc)
    return Ppose


def _arms_down_forward(m):
    """Shared pose math: relax both arms from the raw T-pose to ARMS_DOWN_DEG at the
    sides. Works on any Anny model instance regardless of topology (D89 -- factored out so
    the display-topology and fit-topology basemeshes can't drift apart the way the two
    ever-so-slightly-different pose implementations in compose_avatar.py/serve_viewer.py
    once did, D84)."""
    bsc = m.get_phenotype_blendshape_coefficients(**ADULT, local_changes={})
    rest = m.get_rest_model(bsc)
    Ppose = _arms_down_pose_deltas(m, rest)
    out = m.forward(pose_parameters=Ppose.unsqueeze(0), phenotype_kwargs=ADULT,
                     pose_parameterization="local-bone")
    return out["vertices"][0].detach().cpu().numpy()


def arms_down_basemesh():
    """Anny's default-topology basemesh (13,718 v) posed with arms relaxed at the sides
    instead of the raw T-pose. This is the DISPLAY mesh (what's actually rendered as the
    body) -- for FITTING garments onto, use `arms_down_fit_basemesh()` instead (D89).
    Cached (loading Anny + running the model isn't free)."""
    if "B" in _cache:
        return _cache["B"], _cache["BF"]
    import anny
    m = anny.Anny()
    BF = np.asarray(m.get_triangular_faces())
    B = _arms_down_forward(m)
    _cache["B"], _cache["BF"] = B, BF
    return B, BF


def arms_down_fit_basemesh():
    """The CORRECT basemesh to fit .mhclo assets against (D89 -- fixes the D87/D81 'flowing
    hair explodes' bug at its actual root).

    D87 blamed the explosion on "our body is a close-but-not-bit-identical reimplementation
    of MakeHuman's basemesh" and treated it as an inherent precision limit. That was wrong:
    `mhclo_fit.py` was feeding `anny.Anny()`'s REDUCED, RENUMBERED 13,718-vertex array
    into a fitter whose vertex indices (v1/v2/v3 in each .mhclo binding line) are authored
    against MakeHuman's RAW 19,158-vertex basemesh (helper geometry included) -- a genuine
    INDEX-SPACE mismatch, not just float drift. `anny.Anny(topology="makehuman",
    remove_unattached_vertices=False)` gives that exact 19,158-vertex array, and it was
    verified two ways before trusting it: (1) installed the real MPFB2 Blender addon
    (GPL source / CC0 assets / unrestricted output -- see PROJECT.md D89) and confirmed its
    own real fitting engine handles a previously-"unfixably broken" flowing-hair asset
    (`elvs_reverse_french_braid_bun`) cleanly; (2) numerically confirmed this basemesh's
    surface is an EXACT match (0.00mm nearest-neighbor distance, every vertex incl. the
    whole head region) to `arms_down_basemesh()`'s displayed 13,718-vertex surface at the
    same phenotype+pose -- so a garment fit against this array sits correctly on the body
    that's actually rendered, with no separate transfer/remap step and no MPFB2 runtime
    dependency needed. Cached separately from `arms_down_basemesh()` (different vertex
    count)."""
    if "B_fit" in _cache:
        return _cache["B_fit"]
    import anny
    m = anny.Anny(topology="makehuman", remove_unattached_vertices=False)
    B = _arms_down_forward(m)
    _cache["B_fit"] = B
    _cache["BF_fit"] = np.asarray(m.get_triangular_faces())   # D93: needed for surface normals
    return B


# ======================================================================================
# D96: FIT-AT-NEUTRAL-THEN-SKIN-WITH-THE-SKELETON (linear blend skinning)
# --------------------------------------------------------------------------------------
# The problem this replaces: garments were fit by evaluating the .mhclo affine binding at
# the POSED (arms-down 40deg) body. Posing folds the body -- the armpit closes -- and a
# garment vertex anchored (via its 3-body-vertex barycentric binding) to skin inside that
# fold gets dragged deep into the body (measured up to -33mm at 40deg, scaling with the
# pose angle; see PROJECT.md D94). push_off_surface only patches the symptom.
#
# The real fix (this module): fit the garment ONCE on the NEUTRAL/rest body -- Anny's raw
# T-pose `rest_vertices`, where the armpit is maximally OPEN, which is ALSO the exact space
# Anny's own bone-transforms are defined relative to -- then deform the garment with the
# SKELETON exactly as the body deforms, via the same LBS Anny uses for its own mesh:
#   posed_v = sum_bone  weight_bone . (bone_transform_bone . rest_v)
# where bone_transform = posed_bone_pose . rest_bone_pose^-1 (Anny's `get_bone_transforms`)
# and each garment vertex INHERITS its skinning weights from the barycentric blend of the
# skinning weights of its 3 bound body vertices. No re-evaluation of the affine binding at
# a posed state -> no fold-clipping, and it is the SAME machinery needed to dress the
# walking body (pass any per-frame bone_transforms to `fit_asset_lbs`).
#
# Verified numerically: applying this same dense LBS to the BODY's own rest vertices
# reproduces `m.forward(...)`'s posed vertices to 3e-16 (machine precision) -- i.e. we drive
# the garment with the identical transform stack Anny drives the body with.
# ======================================================================================


def _neutral_fit_data():
    """Cached NEUTRAL (raw T-pose) fit-topology body + its skinning data (D96). Returns a
    dict with:
      rest_verts (19158,3) f64 -- Anny's raw `rest_vertices` (T-pose, armpit fully open),
                                  the canonical LBS rest space AND the frame .mhclo bindings
                                  are authored against. Fit garments against THIS, not the
                                  posed arms-down body.
      W (19158,K) f64, I (19158,K) int -- per-body-vertex sparse bone weights / indices.
      rbp (1,163,4,4) f64 -- rest bone poses (for building bone_transforms of any pose).
      model -- the anny makehuman-topology model instance (for get_bone_transforms).
    """
    if "neutral_fit" in _cache:
        return _cache["neutral_fit"]
    import anny
    m = anny.Anny(topology="makehuman", remove_unattached_vertices=False)
    bsc = m.get_phenotype_blendshape_coefficients(**ADULT, local_changes={})
    rest = m.get_rest_model(bsc)
    data = dict(
        model=m,
        rbp=rest["rest_bone_poses"].double(),
        rest_verts=rest["rest_vertices"][0].detach().cpu().numpy().astype(np.float64),
        W=m.vertex_bone_weights.detach().cpu().numpy().astype(np.float64),
        I=m.vertex_bone_indices.detach().cpu().numpy().astype(np.int64),
    )
    _cache["neutral_fit"] = data
    return data


def bone_transforms_for_pose(pose_deltas):
    """Return the per-bone LBS transforms (NB,4,4 numpy f64) for a target pose, given
    local-bone delta transforms `pose_deltas` (NB,4,4 torch, as built by
    `_arms_down_pose_deltas` or the walk retarget in pose_default_walk.py). These are the
    exact `bone_transform = posed_bone_pose . rest_bone_pose^-1` matrices Anny applies to its
    own mesh -- feed them to `skin_garment`/`fit_asset_lbs` to deform a garment identically."""
    d = _neutral_fit_data()
    bt, _ = d["model"].get_bone_transforms(
        pose_deltas.unsqueeze(0), d["rbp"], batch_size=1, pose_parameterization="local-bone")
    return bt[0].detach().cpu().numpy().astype(np.float64)


def arms_down_bone_transforms():
    """Cached bone-transforms (NB,4,4) for the ARMS_DOWN_DEG preview pose (D96) -- the LBS
    equivalent of what `arms_down_basemesh()` produces for the display body."""
    if "adbt" in _cache:
        return _cache["adbt"]
    d = _neutral_fit_data()
    Ppose = _arms_down_pose_deltas(d["model"], {"rest_bone_poses": d["rbp"]})
    bt = bone_transforms_for_pose(Ppose)
    _cache["adbt"] = bt
    return bt


def _garment_bone_weights(bind_idx, bind_w):
    """Inherit per-garment-vertex skinning weights from the .mhclo affine binding (D96):
    garment weight over bones = barycentric (w1,w2,w3) blend of the sparse bone weights of
    the 3 bound body vertices. Returns a DENSE (Ng, NB) weight matrix (NB=163 bones, small).
    Negative barycentric weights (extrapolated bindings, e.g. flowing hair) are clamped to 0
    then the row renormalized so the LBS weights stay a partition of unity."""
    d = _neutral_fit_data()
    W, I = d["W"], d["I"]
    NB = len(d["model"].bone_labels)
    Ng = len(bind_idx)
    Wg = np.zeros((Ng, NB), np.float64)
    rows = np.arange(Ng)[:, None]
    for k in range(3):
        vs = bind_idx[:, k]                 # (Ng,) body-vertex index
        bw = bind_w[:, k][:, None]          # (Ng,1) barycentric weight of this anchor
        np.add.at(Wg, (rows, I[vs]), W[vs] * bw)
    Wg = np.clip(Wg, 0.0, None)
    s = Wg.sum(1, keepdims=True)
    Wg /= np.clip(s, 1e-12, None)
    return Wg


def skin_garment(rest_verts, bind_idx, bind_w, bone_transforms):
    """Deform garment REST vertices (fit at the neutral body) to a target pose by the SAME
    LBS the body uses (D96). rest_verts (Ng,3); bind_idx/bind_w (Ng,3) the .mhclo affine
    binding; bone_transforms (NB,4,4) from `bone_transforms_for_pose`. Returns posed
    (Ng,3)."""
    Wg = _garment_bone_weights(bind_idx, bind_w)
    homog = np.concatenate([rest_verts, np.ones((len(rest_verts), 1))], axis=1)  # (Ng,4)
    # transform every rest vertex by every bone, then blend by the inherited weights
    Tp = np.einsum('bij,nj->bni', bone_transforms, homog)      # (NB,Ng,4)
    posed = np.einsum('nb,bni->ni', Wg, Tp[..., :3])           # (Ng,3)
    return posed


def _display_body_trimesh():
    """The DISPLAYED basemesh (13,718 v, `arms_down_basemesh`) as a `trimesh.Trimesh` for
    surface-proximity queries, cached (D94). Push clearance must be measured against the mesh
    that's actually RENDERED, not the 19,158-v fit mesh -- they're the same surface to 0.00mm
    (D89) but have different triangulation at folds like the armpit, so a vertex pushed just
    clear of the fit mesh can still poke through the display mesh (found live: 6 shirt verts
    survived when pushing against the fit mesh; 0 when pushing against the display mesh)."""
    if "tm_disp" in _cache:
        return _cache["tm_disp"]
    import trimesh
    B, BF = arms_down_basemesh()
    tm = trimesh.Trimesh(vertices=B, faces=BF, process=False)
    _cache["tm_disp"] = tm
    return tm


def push_off_surface(verts, margin=0.004, iters=5):
    """Push any garment vertex that's at or inside the body surface back out to at least
    `margin` meters of clearance from the body SURFACE (D93; rewritten D94).

    Why this exists: D91's `offset_boost` uniformly scales each vertex's fitted OFFSET, which
    fixes garments whose offset was simply too small everywhere -- but it cannot fix vertices
    that end up INSIDE the body, and rendering here is OPAQUE (no alpha blending), so a vertex
    even slightly inside doesn't peek through softly: the nearer body surface wins that pixel
    outright, producing the exact patchwork of body-colored islands the user reported.
    Vertices land inside for two reasons, both real: (a) the affine binding is an
    approximation, so ~4% of a garment's verts sit a few mm inside even on the rest body; and
    (b) MUCH worse -- when the body is POSED (arms-down), fold regions like the armpit close,
    and garment vertices anchored to body points inside the fold get dragged deep inside
    (measured up to 33mm at the 40deg arms-down pose, scaling ~linearly with the pose angle;
    see PROJECT.md D94 for the full diagnosis). This is NOT fixable by `offset_boost` (the
    deep verts don't have small offsets -- their ANCHOR point is what's inside the fold) nor
    by co-rotating the offset (tested: no effect -- again, it's the anchor, not the offset).

    The fix that actually works (verified: 0 interior verts remaining at every pose angle,
    clean render at the full 40deg): for each vertex still short of `margin`, find the closest
    point on the body SURFACE (any triangle, via `trimesh.proximity.closest_point`) and move
    the vertex to that point + `margin` along THAT triangle's outward face normal. Using the
    closest-surface-point's own normal (not a nearby vertex's averaged normal) is what makes
    it robust in concave folds like the armpit, where the earlier D93 nearest-VERTEX-normal
    version pointed the wrong way and left the deep cases stuck. Iterated a few times because
    one push can land a vertex near a different part of the surface (e.g. across a fold)."""
    import trimesh
    tm = _display_body_trimesh()
    fn = tm.face_normals
    out = verts.copy()
    n_pushed = 0
    for _ in range(iters):
        cp, dist, tid = trimesh.proximity.closest_point(tm, out)
        # signed clearance: + outside, - inside, via the closest triangle's outward normal
        signed = np.einsum('ij,ij->i', out - cp, fn[tid])
        need = signed < margin
        if not need.any():
            break
        out[need] = cp[need] + margin * fn[tid][need]
        n_pushed = int(need.sum())   # last iteration's count ~= verts that needed any move
    return out, n_pushed


def drop_below_feet(verts, faces, feet_z, margin=0.05):
    """Drop any triangle touching a vertex below the body's own feet (see compose_avatar.py
    for the full rationale -- a residual precision-sensitivity tail from D81/D83)."""
    bad = verts[:, 2] < (feet_z - margin)
    if not bad.any():
        return verts, faces, 0
    keep_face = ~bad[faces].any(axis=1)
    kept_v_idx = np.unique(faces[keep_face])
    remap = -np.ones(len(verts), dtype=np.int64)
    remap[kept_v_idx] = np.arange(len(kept_v_idx))
    return verts[kept_v_idx], remap[faces[keep_face]], int((~keep_face).sum())


def drop_edge_outliers(verts, faces, abs_floor=0.15, rel_mult=5.0):
    """Drop any triangle with an edge far longer than the asset's own typical edge length
    (D85) -- the residual D81-class precision-sensitivity tail: a handful of mis-fit
    triangles (a shirt vertex bound with an out-of-triangle extrapolation weight, a hair
    strand vertex landing far from its neighbors) that aren't below the feet so
    `drop_below_feet` doesn't catch them, but read as a long stray gray strip/streak cutting
    across the garment (found on `elvs_crude_t-shirt_male`: 12 triangles with a 0.47-0.57m
    edge vs. a 0.089m median -- a visible diagonal artifact across the shirt). Threshold is
    BOTH absolute (`abs_floor`, tied to real-world scale so it can't misfire on legitimately
    fine/dense meshes like eyebrows, whose edges are all under a few cm) and relative to the
    asset's own median edge (`rel_mult`, so a coarse asset like cargo pants with naturally
    longer edges isn't over-filtered) -- verified against real assets: 0 false drops on
    eyebrows/pants, correctly drops the shirt's 12 stray triangles and ~90 stray hair-strand
    triangles on culturalibre_hair_02."""
    if len(faces) == 0:
        return verts, faces, 0
    e0 = np.linalg.norm(verts[faces[:, 0]] - verts[faces[:, 1]], axis=1)
    e1 = np.linalg.norm(verts[faces[:, 1]] - verts[faces[:, 2]], axis=1)
    e2 = np.linalg.norm(verts[faces[:, 2]] - verts[faces[:, 0]], axis=1)
    maxedge = np.maximum(np.maximum(e0, e1), e2)
    thr = max(abs_floor, rel_mult * float(np.median(maxedge)))
    bad_face = maxedge > thr
    if not bad_face.any():
        return verts, faces, 0
    keep_face = ~bad_face
    kept_v_idx = np.unique(faces[keep_face])
    remap = -np.ones(len(verts), dtype=np.int64)
    remap[kept_v_idx] = np.arange(len(kept_v_idx))
    return verts[kept_v_idx], remap[faces[keep_face]], int(bad_face.sum())


# D91: a single global OFFSET_BOOST made clothing fit properly but made hair visibly WORSE
# (shard/jagged edges) -- clothing's offsets are mild and just needed uniform enlarging, but
# hair's offsets already sit at the extreme end of the D81 extrapolation-weight range, so
# boosting them amplifies whatever small residual fit noise is there instead of just making
# the hairstyle bigger. Empirically checked by rendering each kind at several boost values
# (not guessed): pants/shirts needed ~2.5-3.5x to close the visible skin gaps with no
# distortion; hair started showing jagged/shard edges past ~1.5x with no real coverage gain
# (its own coverage gap -- a bald strip down the back of the head -- turned out to be present
# even at 1.0x, i.e. NOT a sizing issue at all, a separate unsolved problem, see PROJECT.md D91).
_DEFAULT_OFFSET_BOOST = {"hair": 1.2, "eyebrows": 1.0, "clothing": 3.0}


def _offset_boost_for(mhclo_path):
    for kind, boost in _DEFAULT_OFFSET_BOOST.items():
        if f"/{kind}/" in mhclo_path.replace("\\", "/"):
            return boost
    return 1.0


def fit_asset_checked(mhclo_path, B, feet_z, max_offset=0.15, sane_z_pad=0.6, offset_boost=None,
                       push_margin=0.004):
    """fit_mhclo + below-feet filter + a stray-long-edge filter + a surface-clearance push +
    a sanity envelope check. Raises on anything that looks broken (out-of-bounds topology
    mismatch, or a vertex blown out far past the body's own bbox -- the D81/D83
    hair-extrapolation failure mode) so callers (the catalog validator, the compose endpoint)
    can skip/report it instead of silently shipping a corrupted mesh.

    offset_boost: if None (default), auto-picked per asset kind from `mhclo_path` via
    `_offset_boost_for` (D91) -- pass an explicit value to override.
    push_margin: minimum clearance (meters) enforced off the body surface, see
    `push_off_surface()` (D93) -- set to 0/None to disable."""
    from mhclo_fit import fit_mhclo
    if offset_boost is None:
        offset_boost = _offset_boost_for(mhclo_path)
    a = fit_mhclo(mhclo_path, B, max_offset=max_offset, offset_boost=offset_boost)
    if a["faces"] is None:
        raise ValueError("no faces (missing/unreadable obj)")
    v, f, dropped = drop_below_feet(a["verts"], a["faces"], feet_z)
    v, f, dropped_edges = drop_edge_outliers(v, f)
    dropped += dropped_edges
    if push_margin:
        v, n_pushed = push_off_surface(v, margin=push_margin)
        a["pushed"] = n_pushed
    top_z = float(B[:, 2].max())
    if len(v) == 0:
        raise ValueError("empty after below-feet filter")
    vmax_z = float(v[:, 2].max())
    if vmax_z > top_z + sane_z_pad:
        raise ValueError(f"vertex blown out to z={vmax_z:.2f} (body top={top_z:.2f}) "
                          f"-- likely extrapolation blowup, not a real fit")
    a["verts"], a["faces"], a["dropped"] = v, f, dropped
    return a


def fit_asset_lbs(mhclo_path, feet_z, bone_transforms=None, max_offset=0.15, sane_z_pad=0.6,
                  offset_boost=None, push_margin=0.004):
    """D96: the REAL fix for fold-clipping (replaces `fit_asset_checked` for the display path).

    Fit the garment ONCE on the NEUTRAL body (raw T-pose `rest_vertices`, armpit fully open --
    a clean affine fit with minimal clipping), inherit skinning weights from its .mhclo binding,
    then deform it to the target pose with the SAME linear blend skinning Anny uses on its own
    mesh. No re-evaluation of the affine binding at a posed (folded) state -> the armpit
    fold-clipping (up to -33mm at 40deg, D94) is gone at the source, not patched after the fact.

    bone_transforms: (NB,4,4) numpy for the target pose (see `bone_transforms_for_pose`). None ->
    the arms-down preview pose (`arms_down_bone_transforms()`). Pass a per-frame walk transform
    to dress the walking body -- this is the same machinery, no re-fit per frame.

    feet_z: z of the target-posed display body's feet (for grounding checks / drop_below_feet).
    push_margin: a LIGHT final safety-net surface push (D93/D94) -- with fit-at-neutral it now
    touches only a handful of verts (the residual ~4% approximate-binding cases), not the
    hundreds the posed-fit path needed. Set 0 to disable (e.g. per-frame walk, no display body).
    Returns the same dict shape as `fit_asset_checked` (verts/faces/uv/... posed to the target).
    """
    from mhclo_fit import fit_mhclo
    if offset_boost is None:
        offset_boost = _offset_boost_for(mhclo_path)
    if bone_transforms is None:
        bone_transforms = arms_down_bone_transforms()
    B_rest = _neutral_fit_data()["rest_verts"]
    # 1. fit on the NEUTRAL body -> rest-space garment verts + the affine binding
    a = fit_mhclo(mhclo_path, B_rest, max_offset=max_offset, offset_boost=offset_boost)
    if a["faces"] is None:
        raise ValueError("no faces (missing/unreadable obj)")
    # 2. skin the rest garment to the target pose with the inherited weights (LBS)
    posed = skin_garment(a["verts"], a["bind_idx"], a["bind_w"], bone_transforms)
    # 3. the usual robustness filters, now applied to the POSED garment
    v, f, dropped = drop_below_feet(posed, a["faces"], feet_z)
    v, f, dropped_edges = drop_edge_outliers(v, f)
    dropped += dropped_edges
    if push_margin:
        v, n_pushed = push_off_surface(v, margin=push_margin)
        a["pushed"] = n_pushed
    if len(v) == 0:
        raise ValueError("empty after below-feet filter")
    # sanity envelope: reference the posed DISPLAY body's own top, not the neutral fit body
    B_disp, _ = arms_down_basemesh()
    top_z = float(B_disp[:, 2].max())
    vmax_z = float(v[:, 2].max())
    if vmax_z > top_z + sane_z_pad:
        raise ValueError(f"vertex blown out to z={vmax_z:.2f} (body top={top_z:.2f}) "
                          f"-- likely extrapolation blowup, not a real fit")
    a["verts"], a["faces"], a["dropped"] = v, f, dropped
    return a
