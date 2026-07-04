#!/usr/bin/env python
"""
Bind a splat point cloud to the rig so it can be GPU-skinned with the SAME skeleton as the
mesh (the flagship "animated splat"). For each splat point we:
  1. register the splat (TRELLIS gaussian frame) INTO the mesh's geometry-local frame
     (a similarity transform found by a 48-candidate signed-permutation + chamfer search —
     robust to TRELLIS's splat-vs-mesh frame mismatch), then
  2. copy the 4 bone indices + 4 weights from the nearest mesh vertex.
Output = a PLY in MESH frame with the original splat columns (incl. colors) PLUS j0..j3 (uint16)
and w0..w3 (float). The viewer renders this in the mesh frame (so splat + mesh finally align)
and skins it on the GPU using the live skeleton's bone matrices.

Usage: bind_splat.py RIGGED.glb SPLAT.ply OUT.ply
"""
import sys, struct, json
import numpy as np
from scipy.spatial import cKDTree
from plyfile import PlyData, PlyElement

GLB, SPLAT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

# ---- minimal GLB accessor reader ----
_CT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
_NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def load_glb(path):
    d = open(path, 'rb').read()
    jlen = struct.unpack('<I', d[12:16])[0]
    js = json.loads(d[20:20+jlen])
    p = 20 + jlen
    blen = struct.unpack('<I', d[p:p+4])[0]
    bin_ = d[p+8:p+8+blen]
    def accessor(i):
        a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
        ct, sz = _CT[a['componentType']]; nc = _NC[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', sz * nc)
        if stride == sz * nc:                                   # tightly packed -> one read
            return np.frombuffer(bin_, dtype='<' + ct, count=a['count'] * nc, offset=off).reshape(a['count'], nc)
        arr = np.empty((a['count'], nc), dtype='<' + ct)        # interleaved -> per-row
        for r in range(a['count']):
            s = off + r * stride
            arr[r] = np.frombuffer(bin_[s:s + sz * nc], dtype='<' + ct, count=nc)
        return arr
    return js, accessor

js, acc = load_glb(GLB)
prim = js['meshes'][0]['primitives'][0]['attributes']
V = acc(prim['POSITION']).astype(np.float64)           # mesh verts, geometry-local
J = acc(prim['JOINTS_0']).astype(np.int32)             # (N,4) bone indices
W = acc(prim['WEIGHTS_0']).astype(np.float64)          # (N,4) weights
W = W / (W.sum(1, keepdims=True) + 1e-9)
print(f"mesh verts={len(V)}  joints/vert=4  bones={len(js['skins'][0]['joints'])}")

# ---- load splat ----
ply = PlyData.read(SPLAT)
sd = ply['vertex'].data
P = np.stack([sd['x'], sd['y'], sd['z']], 1).astype(np.float64)
print(f"splat points={len(P)}")

# ---- register P (splat frame) -> V (mesh frame): similarity via 48 signed-perm + chamfer ----
def signed_perms():
    import itertools
    mats = []
    for perm in itertools.permutations(range(3)):
        for sx in (1, -1):
            for sy in (1, -1):
                for sz in (1, -1):
                    M = np.zeros((3, 3)); s = (sx, sy, sz)
                    for i, pj in enumerate(perm): M[i, pj] = s[i]
                    mats.append(M)
    return mats  # 48 (includes mirrors)

def rms(X): return np.sqrt((X**2).sum(1).mean())
Pc, Vc = P - P.mean(0), V - V.mean(0)
sP = sub = np.random.default_rng(0).choice(len(Pc), min(3000, len(Pc)), replace=False)
sV = np.random.default_rng(1).choice(len(Vc), min(3000, len(Vc)), replace=False)
scale = rms(Vc) / (rms(Pc) + 1e-9)
Pcs = Pc * scale
treeV = cKDTree(Vc[sV])
best = (1e18, None)
for M in signed_perms():
    Pr = Pcs[sP] @ M.T
    dd, _ = treeV.query(Pr, k=1)
    c = dd.mean()
    if c < best[0]: best = (c, M)
chamfer, Mbest = best
print(f"coarse registration chamfer={chamfer:.4f}  scale={scale:.3f}")

# ---- refine with trimmed similarity ICP (Umeyama) for EXACT alignment ----
def umeyama(X, Y):
    muX, muY = X.mean(0), Y.mean(0)
    Xc, Yc = X - muX, Y - muY
    S = (Yc.T @ Xc) / len(X)
    U, D, Vt = np.linalg.svd(S)
    d = np.sign(np.linalg.det(U @ Vt))
    W = np.diag([1, 1, d])
    R = U @ W @ Vt
    s = np.trace(np.diag(D) @ W) / ((Xc ** 2).sum() / len(X))
    t = muY - s * (R @ muX)
    return s, R, t

Vc_full = V - V.mean(0)
treeVfull0 = cKDTree(Vc_full)
A_total = scale * Mbest                                 # linear map on P-centered pts: P_cur = Pc @ A_total.T
P_cur = Pc @ A_total.T                                  # == (Pc * scale) @ Mbest.T, in V-centered frame
for _ in range(8):
    dd, ii = treeVfull0.query(P_cur, k=1)
    keep = dd < (np.median(dd) * 2.5 + 1e-6)            # trim outliers
    s, R, t = umeyama(P_cur[keep], Vc_full[ii[keep]])
    P_cur = s * (P_cur @ R.T) + t
    A_total = (s * R) @ A_total                         # accumulate the SAME map for the covariances below
fin_dd, _ = treeVfull0.query(P_cur, k=1)
print(f"ICP-refined chamfer={fin_dd.mean():.4f}  median={np.median(fin_dd):.4f}")
P_local = P_cur + V.mean(0)                             # splat in mesh geometry frame
sv = np.linalg.svd(A_total, compute_uv=False)
print(f"A_total: det={np.linalg.det(A_total):+.3f}  singular values={sv.round(3)}  (≈equal => uniform-scale similarity)")

# ---- transfer skin weights from nearest mesh vertex ----
treeVfull = cKDTree(V)
dist, idx = treeVfull.query(P_local, k=1)
Jp, Wp = J[idx], W[idx]
print(f"weight transfer: mean nearest dist={dist.mean():.4f}  median={np.median(dist):.4f}")
print(f"weight sums (should be ~1): min={Wp.sum(1).min():.3f} max={Wp.sum(1).max():.3f}")

# ---- transform splat ORIENTATION + SCALE into the mesh frame ----
# The registration applied a rotation+scale (A_total) to the POSITIONS only. Each splat's anisotropic
# covariance Σ = R·diag(s²)·Rᵀ must get the SAME map (Σ' = A·Σ·Aᵀ), or a real anisotropic renderer
# mis-orients (by the registration rotation) and mis-sizes every ellipsoid. Invisible to a point/dot
# renderer (points have no orientation) — which is why this was latent until the animated-splat PoC.
# Method: rebuild Σ, map it, re-extract scale+quat by eigendecomposition (robust to a reflected A_total
# from the signed-perm coarse search; a Gaussian is symmetric under axis sign flips).
# NOTE (verify in-browser): assumes 3DGS conventions — scale stored in LOG space, quaternion order
# (w,x,y,z) in rot_0..3. Confirmed for our TRELLIS PLYs (scale≈-7→exp tiny; |rot|==1). If the PoC shows
# splats consistently rotated/mirrored, revisit the quaternion order here.
from scipy.spatial.transform import Rotation as _Rot
_orient = ('scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3')
has_orient = all(nm in sd.dtype.names for nm in _orient)
if has_orient:
    S_log = np.stack([sd['scale_0'], sd['scale_1'], sd['scale_2']], 1).astype(np.float64)
    Q_wxyz = np.stack([sd['rot_0'], sd['rot_1'], sd['rot_2'], sd['rot_3']], 1).astype(np.float64)
    Q_wxyz /= (np.linalg.norm(Q_wxyz, axis=1, keepdims=True) + 1e-12)
    Rg = _Rot.from_quat(Q_wxyz[:, [1, 2, 3, 0]]).as_matrix()                      # scipy uses (x,y,z,w)
    S = np.exp(S_log)                                                             # actual std-dev scales
    Sigma  = np.einsum('nij,nj,nkj->nik', Rg, S**2, Rg)                           # Σ = R·diag(s²)·Rᵀ
    Sigma2 = np.einsum('ij,njk,lk->nil', A_total, Sigma, A_total)                 # Σ' = A·Σ·Aᵀ
    evals, evecs = np.linalg.eigh(Sigma2)                                         # symmetric PSD
    evals = np.clip(evals, 1e-20, None)
    evecs[np.linalg.det(evecs) < 0, :, 0] *= -1                                   # force proper rotation
    new_log = np.log(np.sqrt(evals)).astype(np.float32)                           # (N,3) log-scale
    new_q = _Rot.from_matrix(evecs).as_quat()[:, [3, 0, 1, 2]].astype(np.float32) # back to (w,x,y,z)
    print(f"orientation/scale baked: mean log-scale {S_log.mean():.3f} -> {new_log.mean():.3f}")
else:
    print("WARN: no scale/rot columns; skipping orientation transform (point cloud, not a splat)")

# ---- write output PLY: original columns (x,y,z + scale/rot replaced) + j0..3,w0..3 ----
names = sd.dtype.names
new_dt = []
for n in names:
    new_dt.append((n, sd.dtype[n]))
for k in range(4): new_dt.append((f'j{k}', 'u2'))
for k in range(4): new_dt.append((f'w{k}', 'f4'))
out = np.empty(len(P), dtype=new_dt)
for n in names: out[n] = sd[n]
out['x'], out['y'], out['z'] = P_local[:, 0], P_local[:, 1], P_local[:, 2]
if has_orient:
    out['scale_0'], out['scale_1'], out['scale_2'] = new_log[:, 0], new_log[:, 1], new_log[:, 2]
    out['rot_0'], out['rot_1'], out['rot_2'], out['rot_3'] = new_q[:, 0], new_q[:, 1], new_q[:, 2], new_q[:, 3]
for k in range(4):
    out[f'j{k}'] = Jp[:, k].astype(np.uint16)
    out[f'w{k}'] = Wp[:, k].astype(np.float32)
PlyData([PlyElement.describe(out, 'vertex')], text=False).write(OUT)
print(f"wrote {OUT}  ({len(P):,} skinned splats, in mesh frame)")
