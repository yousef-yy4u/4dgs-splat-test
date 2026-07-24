"""MPFB2-engine garment pre-fit -> Anny rest-body transfer (the D102 real-ceiling fix).

WHY: our `mhclo_fit.fit_mhclo` is a per-vertex AFFINE approximation (3 basemesh verts +
barycentric weights + a fixed offset) evaluated against Anny's reimplemented basemesh. It is
only approximate (D89: ~4-30% of a garment's verts land a few mm inside the body even at
neutral, worst on the low-poly bottoms and on hair that needs real volume off the scalp), and
it CANNOT add geometry -- the CC0 MakeHuman garment cages are tiny (jean shorts = 285 v / 250
tri), so even a perfect fit + cloth sim reads as a shrink-wrapped low-poly proxy, not cloth.

MPFB2's OWN fitting engine (`HumanService.add_mhclo_asset`, D89-proven) does two things ours
cannot: (1) a real multi-pass fit (`ClothesService.fit_clothes_to_human`) that seats the cage
cleanly with almost no interior verts, and (2) `subdiv_levels` Catmull-Clark subdivision that
turns the 285-vert shorts into ~4000 verts / the 1095-vert shirt into ~17000 -- actual
geometry that can fold and drape. MPFB can't be a per-request dependency, so we drive it OFFLINE
(`mpfb_fit_blender.py` -> `/root/blender/blender -b -P mpfb_fit_blender.py` ->
`motion_out/mpfb_out/<name>_sd<N>_verts/_faces.npy`, durable+gitignored) and
this module TRANSFERS the MPFB-fitted garment onto OUR neutral rest body, then re-derives the
body binding so the existing D96/D101 LBS-skin + XPBD cloth path drives it unchanged.

THE TRANSFER (pose-correct, not rigid): MPFB's basemesh and Anny's `topology="makehuman"`
basemesh share the SAME 19,158-vertex ordering (both are MakeHuman `base.obj`) but sit in
DIFFERENT poses -- MPFB's default relaxed pose vs Anny's raw T-pose (a rigid Procrustes leaves
a 31 mm residual, so rigid registration is WRONG). Instead we transfer each garment vertex
through the shared mesh LOCALLY: find its nearest triangle on the MPFB-posed base, record
(barycentric u,v,w + signed offset h along that triangle's normal), then reconstruct on the
SAME triangle of the Anny rest base. Local barycentric+normal transfer is exactly pose-robust,
and the reconstructed garment sits at neutral on our rest body in the exact space the .mhclo
path already produces -- so `outfit_lib.skin_garment` / `dress_walk` consume it identically.
The binding for LBS weights is the triangle's 3 body-vertex indices + barycentric weights,
the same shape `mhclo_fit` returns as bind_idx/bind_w.
"""
import os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# Durable (gitignored) MPFB raw-fit exports, regenerable via scratchpad/mpfb_fit_all.py in
# blender+MPFB2. Falls back to the scratch dir if the durable copy isn't present.
_DURABLE = os.path.join(HERE, "motion_out", "mpfb_out")
_SCRATCH = "/tmp/claude-0/-root-4dgs/6ebfbfea-f964-438f-9846-94417a4ee155/scratchpad/mpfb_out"
MPFB_OUT = os.environ.get("MPFB_OUT", _DURABLE if os.path.isdir(_DURABLE) else _SCRATCH)

# Per-SLOT prefit policy (D102). Clothing is Catmull-Clark subdivided (sd1 = ~4x the CC0 cage's
# polys) so the XPBD sim has geometry to fold, and inflated OUTWARD by `ease` metres so it starts
# with an air-gap instead of hugging the skin (the "painted on" look). sd1 (not sd2) is the
# default: sd2 (~16x) gives slightly finer wrinkles but the per-frame dressed-walk buffer is
# verts*150frames*12 bytes -> sd2 shirt alone is ~35 MB on the wire vs ~8 MB at sd1, and the sim
# bake is ~8 min vs ~2 min, for a marginal fold-detail gain. Bump to 2 here (+ re-bake) if wire
# size stops mattering (e.g. a compressed/delta-encoded garment format). Hair is sd1 (LBS-static,
# not simulated; sd2 hair blows up the buffer), no ease (sits tight to the scalp). eyebrows: no
# MPFB prefit -> affine.
_SLOT_SUBDIV = {"top": 1, "bottom": 1, "hair": 1, "eyebrows": 1}
_SLOT_EASE   = {"top": 0.016, "bottom": 0.010, "hair": 0.0, "eyebrows": 0.0}

_cache = {}


def _tri_bary(p, a, b, c):
    """Barycentric coords of p projected onto triangle (a,b,c). Vectorized: p,a,b,c (N,3)."""
    v0 = b - a; v1 = c - a; v2 = p - a
    d00 = np.einsum('ij,ij->i', v0, v0); d01 = np.einsum('ij,ij->i', v0, v1)
    d11 = np.einsum('ij,ij->i', v1, v1); d20 = np.einsum('ij,ij->i', v2, v0)
    d21 = np.einsum('ij,ij->i', v2, v1)
    den = np.clip(d00 * d11 - d01 * d01, 1e-12, None)
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    u = 1.0 - v - w
    return u, v, w


def transfer(mpfb_base, anny_base, faces, garment_verts):
    """Transfer garment_verts (Ng,3), fitted against `mpfb_base` (Nv,3), onto `anny_base`
    (Nv,3, SAME vertex ordering + `faces` connectivity), pose-correctly. Returns
    (rest_verts (Ng,3) on anny_base, bind_idx (Ng,3) int, bind_w (Ng,3) barycentric)."""
    import trimesh
    tm = trimesh.Trimesh(vertices=mpfb_base, faces=faces, process=False)
    fn = tm.face_normals
    cp, _dist, tid = trimesh.proximity.closest_point(tm, garment_verts)
    tri = faces[tid]                                        # (Ng,3) body-vertex indices
    a, b, c = mpfb_base[tri[:, 0]], mpfb_base[tri[:, 1]], mpfb_base[tri[:, 2]]
    u, v, w = _tri_bary(cp, a, b, c)                        # bary of the *closest point*
    h = np.einsum('ij,ij->i', garment_verts - cp, fn[tid])  # signed normal offset
    # reconstruct on the Anny rest base: same triangle indices, same bary, offset along the
    # Anny triangle's own normal (pose-correct).
    Aa, Ab, Ac = anny_base[tri[:, 0]], anny_base[tri[:, 1]], anny_base[tri[:, 2]]
    an = np.cross(Ab - Aa, Ac - Aa)
    an /= np.clip(np.linalg.norm(an, axis=1, keepdims=True), 1e-12, None)
    rest = (u[:, None] * Aa + v[:, None] * Ab + w[:, None] * Ac) + h[:, None] * an
    bind_idx = tri.astype(np.int64)
    bind_w = np.stack([u, v, w], axis=1)
    return rest, bind_idx, bind_w


def _load_mpfb(name, subdiv):
    v = np.load(os.path.join(MPFB_OUT, f"{name}_sd{subdiv}_verts.npy"))
    f = np.load(os.path.join(MPFB_OUT, f"{name}_sd{subdiv}_faces.npy")).astype(np.int64)
    return v, f


def prefit_garment(name, subdiv=2, ease=0.0):
    """Return an MPFB-fitted garment transferred onto Anny's neutral rest body, as a dict with
    the SAME shape the .mhclo affine path returns (verts/faces/bind_idx/bind_w) so it drops into
    outfit_lib.skin_garment / dress_walk._fit_selection. Cached to PREFIT_DIR.

    ease: metres to inflate the rest garment outward along the body surface normal BEFORE
    skinning (the CC0 garments hug the body; a small air-gap is what reads as real cloth rather
    than paint). Applied here so the cloth sim starts from an eased shape and drapes it."""
    key = (name, subdiv, round(ease, 4))
    if key in _cache:
        return _cache[key]
    import outfit_lib as ol
    d = ol._neutral_fit_data()
    anny_base = d["rest_verts"]
    faces = np.asarray(d["model"].get_triangular_faces())
    mpfb_base = np.load(os.path.join(MPFB_OUT, "basemesh_verts.npy"))
    gv, gf = _load_mpfb(name, subdiv)
    rest, bind_idx, bind_w = transfer(mpfb_base, anny_base, faces, gv)
    if ease:
        rest = _inflate(rest, anny_base, faces, ease)
    out = {"verts": rest, "faces": gf, "uv": None, "name": name,
           "bind_idx": bind_idx, "bind_w": bind_w, "subdiv": subdiv, "ease": ease}
    _cache[key] = out
    return out


def _inflate(rest, body_verts, body_faces, ease, falloff_top_frac=0.35):
    """Push each garment vertex outward along the nearest body-surface normal to add ease / an
    air-gap so the garment stops hugging the silhouette (the "painted on" look). The push is
    RAMPED vertically: ~0 in the top `falloff_top_frac` of the garment's height (shoulders /
    collar of a top, waistband of a bottom -- these should sit ON the body, or the neckline
    balloons into a boxy scoop and the sleeves wing out) and full `ease` below (torso, hem,
    legs -- where real cloth stands off and drapes). Only pushes OUTWARD."""
    import trimesh
    tm = trimesh.Trimesh(vertices=body_verts, faces=body_faces, process=False)
    fn = tm.face_normals
    cp, _dist, tid = trimesh.proximity.closest_point(tm, rest)
    z = rest[:, 2]; zmax = z.max(); H = max(z.ptp(), 1e-6)
    ramp = np.clip((zmax - z) / (falloff_top_frac * H), 0.0, 1.0)   # 0 at top -> 1 below
    return rest + (ease * ramp)[:, None] * fn[tid]


def name_for_path(mhclo_path):
    """The MPFB export name for a catalog .mhclo path == its asset dirname."""
    return os.path.basename(os.path.dirname(mhclo_path))


def has_prefit(name, subdiv=None):
    """True iff an MPFB raw-fit export exists on disk for this asset name (+subdiv)."""
    if subdiv is None:
        return any(os.path.exists(os.path.join(MPFB_OUT, f"{name}_sd{sd}_verts.npy"))
                   for sd in (0, 1, 2))
    return os.path.exists(os.path.join(MPFB_OUT, f"{name}_sd{subdiv}_verts.npy"))


def fit_rest(mhclo_path, slot, rest_verts, offset_boost=None):
    """Unified neutral-rest garment fit shared by every dress path (dressed walk, cloth bake,
    static compose). Returns a dict {verts,faces,bind_idx,bind_w,source}: verts fit at Anny's
    NEUTRAL rest body, ready for outfit_lib.skin_garment / the cloth bake.

    Uses the MPFB2-engine prefit (subdivided + eased per `_SLOT_SUBDIV`/`_SLOT_EASE`) when an
    export exists for this asset, else falls back to our affine `mhclo_fit.fit_mhclo` (with the
    D91/D92 per-kind offset_boost). `offset_boost` only affects the affine fallback."""
    import outfit_lib as ol
    name = name_for_path(mhclo_path)
    subdiv = _SLOT_SUBDIV.get(slot, 2)
    if has_prefit(name, subdiv):
        a = prefit_garment(name, subdiv=subdiv, ease=_SLOT_EASE.get(slot, 0.0))
        return {"verts": a["verts"], "faces": a["faces"].astype(np.int64),
                "bind_idx": a["bind_idx"], "bind_w": a["bind_w"], "source": f"mpfb-sd{subdiv}"}
    from mhclo_fit import fit_mhclo
    if offset_boost is None:
        offset_boost = ol._offset_boost_for(mhclo_path)
    a = fit_mhclo(mhclo_path, rest_verts, max_offset=0.15, offset_boost=offset_boost)
    if a["faces"] is None:
        raise ValueError(f"{name}: no faces (missing/unreadable obj)")
    return {"verts": a["verts"], "faces": a["faces"].astype(np.int64),
            "bind_idx": a["bind_idx"], "bind_w": a["bind_w"], "source": "affine"}


def available():
    """Names with an MPFB export present on disk."""
    if not os.path.isdir(MPFB_OUT):
        return []
    names = set()
    for fn in os.listdir(MPFB_OUT):
        if fn.endswith("_verts.npy") and "_sd" in fn:
            names.add(fn.split("_sd")[0])
    return sorted(names)


if __name__ == "__main__":
    import outfit_lib as ol, trimesh
    d = ol._neutral_fit_data()
    B = d["rest_verts"]; BF = np.asarray(d["model"].get_triangular_faces())
    tm = trimesh.Trimesh(vertices=B, faces=BF, process=False); fn = tm.face_normals
    print(f"[mpfb_prefit] available MPFB exports: {available()}")
    for name in available():
        for sd in (0, 2):
            try:
                a = prefit_garment(name, subdiv=sd)
            except FileNotFoundError:
                continue
            cp, _dd, tid = trimesh.proximity.closest_point(tm, a["verts"])
            sd_ = np.einsum('ij,ij->i', a["verts"] - cp, fn[tid])
            gap = sd_[sd_ >= 0]
            print(f"  {name:14s} sd={sd}  {len(a['verts']):6d}v {len(a['faces']):6d}f  "
                  f"interior={ (sd_<0).mean()*100:5.1f}%  mean_gap="
                  f"{gap.mean()*1000 if len(gap) else 0:5.1f}mm  deepest_in={sd_.min()*1000:6.1f}mm")
