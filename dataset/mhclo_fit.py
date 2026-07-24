"""
Fit a MakeHuman/MPFB2 .mhclo asset (hair, clothing, eyebrows, eyelashes, beards, hand/
face detail, etc.) onto Anny's default-topology mesh.

WHY THIS WORKS AT ALL: Anny bundles MPFB2/MakeHuman's own basemesh data un-remapped (D71),
so MHCLO's vertex INDICES and coordinate frame line up with an Anny `forward()` output
with NO remapping -- **PROVIDED that output is the RAW 19,158-vertex `topology="makehuman"`
array, not the reduced/renumbered 13,718-vertex default topology** (D89 correction: earlier
revisions of this file used the 13,718-v array here, which happened to line up well enough
for many assets -- e.g. an eyebrows01 fit landing exactly on the brow line -- but silently
mis-indexed assets with large/extrapolated offsets, misdiagnosed for three sessions as a
basemesh-precision limit rather than an index-space mismatch; see
`outfit_lib.arms_down_fit_basemesh()`). See `fit_mhclo()`'s own docstring below for the
verification and the fix.

MHCLO format (plain text, verified against real files 2026-07-23):
  a header (basemesh tag, obj_file, material, z_depth for layering, ...) then a
  `verts 0` section with one line per asset-mesh vertex:
    v1 v2 v3  w1 w2 w3  dx dy dz
  the asset vertex's fitted position = w1*V[v1] + w2*V[v2] + w3*V[v3] + (dx,dy,dz)
  -- an AFFINE combination (w1+w2+w3=1 but individual weights can be negative/>1, used
  to extrapolate points like flowing hair strands beyond the cited triangle) plus a
  fixed local offset. This is a straight weighted sum -- correct even for those
  out-of-triangle weights, no special-casing needed.

Usage (as a library):
  from mhclo_fit import fit_mhclo
  asset = fit_mhclo("path/to/thing.mhclo", anny_basemesh_verts)
  # asset = {"verts": (Nv,3), "faces": (Nf,3) int, "uv": (Nv,2) or None,
  #          "name":..., "material_path":..., "z_depth": int}
"""
import os, numpy as np


def _read_obj(path):
    verts, uv, faces_v, faces_vt = [], [], [], []
    for ln in open(path, encoding="utf-8", errors="replace"):
        if ln.startswith("v "):
            verts.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("vt "):
            uv.append([float(x) for x in ln.split()[1:3]])
        elif ln.startswith("f "):
            idx = [tok.split("/") for tok in ln.split()[1:]]
            vs = [int(t[0]) - 1 for t in idx]
            vts = [int(t[1]) - 1 if len(t) > 1 and t[1] else None for t in idx]
            for k in range(1, len(vs) - 1):        # fan-triangulate ngons
                faces_v.append((vs[0], vs[k], vs[k + 1]))
                faces_vt.append((vts[0], vts[k], vts[k + 1]))
    return (np.asarray(verts, np.float64), np.asarray(uv, np.float64) if uv else None,
            np.asarray(faces_v, np.int64), faces_vt)


def fit_mhclo(mhclo_path, basemesh_verts, max_offset=None, offset_boost=1.0):
    """basemesh_verts: (19158,3) Anny's RAW MakeHuman-topology vertex output --
    `outfit_lib.arms_down_fit_basemesh()`, or equivalently
    `anny.Anny(topology="makehuman", remove_unattached_vertices=False).forward(...)`
    (native frame -- do NOT pre-rotate/re-center it; the mhclo offsets are authored
    against that exact raw frame).

    D89 correction: earlier versions of this docstring said (13718,3) -- Anny's DEFAULT
    topology output. That was a genuine bug, not just an approximation: `.mhclo` binding
    indices (v1/v2/v3) are authored against MakeHuman's RAW 19,158-vertex basemesh
    (helper geometry included), while the default topology is a REDUCED, RENUMBERED
    13,718-vertex array -- feeding it in silently mis-indexed some fraction of every
    asset's binding, worst on assets with large/extrapolated offsets (flowing hair,
    draped garments), which is exactly the failure pattern D81/D83/D87 chased for three
    sessions as a "precision" problem. The 19,158-vertex `topology="makehuman"` array is
    index-space-correct AND numerically verified to be an EXACT (0.00mm) surface match to
    the displayed default-topology body at the same phenotype+pose -- see
    `outfit_lib.arms_down_fit_basemesh()`'s docstring for how this was confirmed (incl.
    cross-checking against the real MPFB2 Blender addon's own fitting engine).

    max_offset: if set (meters), clip any per-vertex offset whose magnitude exceeds it
    back to that length (direction preserved). Kept as a defensive backstop for any
    genuinely oversized/malformed asset even after the D89 fix, not as the primary fix
    for the flowing-hair blowup it was originally added for.

    offset_boost: uniform multiplier on the final (already per-axis-scale-calibrated) offset
    (D91). The per-axis scale calibration above tracks OUR basemesh's actual proportions
    correctly in ratio, but even at ratio~1.0 garments consistently rendered visibly
    undersized (skin showing through the front of pants/shirts, hair not fully covering the
    scalp) -- tried reinterpreting `den`'s units instead (D90, `den/10`) but that jumped the
    effective scale ~10x in one step and the user reported it looked "fuzzy, distorted," not
    just bigger. This plain uniform knob (no reinterpretation of the file format, so it can't
    introduce per-axis distortion) is the actual fix -- callers should use
    `outfit_lib.fit_asset_checked()`, which auto-picks a sane per-ASSET-KIND default
    (clothing needs more boost than hair; see its `_DEFAULT_OFFSET_BOOST` for the empirical
    values and why hair specifically does NOT want a big boost). Defaults to 1.0 (no boost)
    here since this bare function doesn't know the asset's kind."""
    d = os.path.dirname(mhclo_path)
    lines = open(mhclo_path, encoding="utf-8", errors="replace").read().splitlines()
    meta = {"name": None, "obj_file": None, "material": None, "z_depth": 0}
    vi = None
    scale_dirs = {}   # axis ('x'/'y'/'z') -> (v1, v2, den)
    for i, ln in enumerate(lines):
        if ln.startswith("name "): meta["name"] = ln.split(None, 1)[1].strip()
        elif ln.startswith("obj_file "): meta["obj_file"] = ln.split(None, 1)[1].strip()
        elif ln.startswith("material "): meta["material"] = ln.split(None, 1)[1].strip()
        elif ln.startswith("z_depth "): meta["z_depth"] = int(ln.split()[1])
        elif ln.startswith(("x_scale ", "y_scale ", "z_scale ")):
            axis, sv1, sv2, den = ln.split()
            # D90 tried treating `den` as MakeHuman decimeters (den/10) -- numerically tidy
            # (moved scale ratios from ~0.10 to ~0.98-1.07) but the user reported the RESULT
            # looked worse: "fuzzy, distorted" instead of just undersized. REVERTED (D91) --
            # raw `den` reproduces the D89 state the user said was correctly SHAPED, just too
            # small; see OFFSET_BOOST below for the actual fix (a plain uniform enlargement,
            # not a per-axis reinterpretation of `den`'s units).
            scale_dirs[axis[0]] = (int(sv1), int(sv2), float(den))
        elif ln.strip() == "verts 0" or ln.startswith("verts 0"):
            vi = i + 1
    if vi is None:
        raise ValueError(f"{mhclo_path}: no 'verts 0' binding section found")

    binding = []
    for ln in lines[vi:]:
        parts = ln.split()
        if len(parts) < 9 or not parts[0].lstrip("-").isdigit():
            break
        binding.append([float(x) for x in parts])
    binding = np.asarray(binding, np.float64)
    v1, v2, v3 = binding[:, 0].astype(int), binding[:, 1].astype(int), binding[:, 2].astype(int)
    w1, w2, w3 = binding[:, 3:4], binding[:, 4:5], binding[:, 5:6]
    off = binding[:, 6:9]

    B = basemesh_verts
    # per-axis offset scale calibration: MakeClothes records the REFERENCE basemesh's
    # distance between two landmark vertices as `den`; the offset on that axis must be
    # rescaled by (OUR basemesh's actual distance between those same two vertices) / den,
    # so the garment's silhouette tracks whatever body proportions our basemesh actually
    # has instead of the (possibly different-proportioned) mesh the asset was authored
    # against. Skipping this is harmless for small/tight assets (eyebrows, eyelashes --
    # offsets are millimeter-scale) but SEVERELY distorts anything with large offsets, like
    # sleeves/hems on clothing (found via a real broken shirt render: ~9x too wide without it).
    scale = np.ones(3)
    for k, axis in enumerate(("x", "y", "z")):
        if axis in scale_dirs:
            sv1, sv2, den = scale_dirs[axis]
            scale[k] = np.linalg.norm(B[sv1] - B[sv2]) / den if den > 1e-9 else 1.0
    off = off * scale[None, :] * offset_boost
    if max_offset is not None:
        mag = np.linalg.norm(off, axis=1, keepdims=True)
        off = np.where(mag > max_offset, off * (max_offset / np.clip(mag, 1e-9, None)), off)

    fitted = B[v1] * w1 + B[v2] * w2 + B[v3] * w3 + off

    faces, uv = None, None
    if meta["obj_file"]:
        obj_path = os.path.join(d, meta["obj_file"])
        if os.path.exists(obj_path):
            ov, ouv, faces, _ = _read_obj(obj_path)
            if len(ov) != len(fitted):
                raise ValueError(f"{mhclo_path}: obj has {len(ov)} verts but binding has "
                                  f"{len(fitted)} -- mismatched asset/binding pair")
            uv = ouv

    return {"verts": fitted, "faces": faces, "uv": uv, "name": meta["name"] or os.path.basename(d),
            "material_path": os.path.join(d, meta["material"]) if meta["material"] else None,
            "z_depth": meta["z_depth"], "mhclo_path": mhclo_path,
            # D96: expose the raw affine binding so a caller can INHERIT skinning weights
            # from the 3 bound body vertices (fit-at-neutral-then-LBS, see outfit_lib.fit_asset_lbs).
            # bind_idx (Ng,3) int body-vertex indices, bind_w (Ng,3) barycentric weights.
            "bind_idx": np.stack([v1, v2, v3], axis=1),
            "bind_w": np.concatenate([w1, w2, w3], axis=1)}


if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mhclo", nargs="+", help="one or more .mhclo files to fit + report on")
    args = ap.parse_args()

    import anny
    ADULT = dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5)
    m = anny.Anny(topology="makehuman", remove_unattached_vertices=False)
    out = m.forward(phenotype_kwargs=ADULT)
    B = out["vertices"][0].detach().cpu().numpy()
    print(f"[mhclo_fit] Anny basemesh (makehuman topology, D89): {B.shape}")
    for p in args.mhclo:
        a = fit_mhclo(p, B)
        nf = len(a["faces"]) if a["faces"] is not None else 0
        print(f"[mhclo_fit] {a['name']:30s} {len(a['verts']):6d} verts  {nf:6d} faces  "
              f"z_depth={a['z_depth']:3d}  bbox={a['verts'].min(0).round(3)}..{a['verts'].max(0).round(3)}")
