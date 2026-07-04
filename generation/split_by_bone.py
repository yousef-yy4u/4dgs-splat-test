#!/usr/bin/env python
"""
Split a skinned splat PLY (from bind_splat.py: x..rot + j0..3/w0..3) into one PLAIN 3DGS PLY per
dominant bone, for the animated-splat PoC (generation/poc_splat_anim.html).

Why: the PoC renders proper anisotropic ellipsoids via mkkellogg's renderer (not dots). mkkellogg can't
skin per-splat, but it CAN move whole splat-scenes rigidly each frame. So we assign each splat to its
dominant bone (argmax of w0..w3) and emit one scene per bone; the viewer then drives each scene by that
bone's rigid transform D_b = bindMatrixInverse * boneMatrices[b] * bindMatrix (same convention as the
studio dot-skinning, but applied per-bone-group instead of per-point). This is single-bone (rigid)
skinning: correct away from joints, with seams AT joints — the known limitation that the per-splat
covariance-skinning shader (gaussian-vrm-style, step 2b) later removes. Each output PLY keeps the
fixed orientation/scale from bind_splat.py and DROPS the j/w columns (mkkellogg doesn't need them).

Usage: split_by_bone.py SKINNED.ply OUTDIR
Writes OUTDIR/bone_<b>.ply for each non-empty bone + OUTDIR/manifest.json {bones:[{bone, file, count}], total}.
"""
import sys, os, json
import numpy as np
from plyfile import PlyData, PlyElement

SKIN, OUTDIR = sys.argv[1], sys.argv[2]
os.makedirs(OUTDIR, exist_ok=True)

d = PlyData.read(SKIN)['vertex'].data
n = len(d)
W = np.stack([d['w0'], d['w1'], d['w2'], d['w3']], 1).astype(np.float64)
J = np.stack([d['j0'], d['j1'], d['j2'], d['j3']], 1).astype(np.int64)
dom = J[np.arange(n), W.argmax(1)]                      # dominant bone per splat
print(f"{n:,} splats over {len(np.unique(dom))} bones (max bone idx {dom.max()})")

# plain-3DGS columns only (drop j*/w*); mkkellogg reads x,y,z,nx..,f_dc*,opacity,scale*,rot*
keep = [nm for nm in d.dtype.names if not (nm[0] in ('j', 'w') and nm[1:].isdigit())]
out_dt = [(nm, d.dtype[nm]) for nm in keep]

manifest = {"bones": [], "total": int(n)}
for b in sorted(np.unique(dom).tolist()):
    mask = dom == b
    cnt = int(mask.sum())
    if cnt == 0:
        continue
    sub = np.empty(cnt, dtype=out_dt)
    for nm in keep:
        sub[nm] = d[nm][mask]
    fn = f"bone_{b}.ply"
    PlyData([PlyElement.describe(sub, 'vertex')], text=False).write(os.path.join(OUTDIR, fn))
    manifest["bones"].append({"bone": int(b), "file": fn, "count": cnt})

with open(os.path.join(OUTDIR, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=1)
print(f"wrote {len(manifest['bones'])} bone PLYs + manifest.json to {OUTDIR}")
