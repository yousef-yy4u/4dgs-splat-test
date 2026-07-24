#!/usr/bin/env python3
"""Put the PHOTOREAL skin (default 13,718-v UV mesh) onto the MOVING body (SOMALayer walk).

Deformation transfer: both meshes are the SAME body surface, so map each default vertex to its
K nearest SOMA-rest verts, then add the SOMA per-frame DISPLACEMENT (posed - rest) to the default
rest. This reuses SOMALayer's good motion without a fragile skeleton retarget; each mesh keeps its
own rest shape and only the motion delta transfers.

Writes frame_###.obj (default topology, UVs, skin/eye groups) for Blender --seq.
    python build_moving_textured.py --walk motion_out/walk_verts.npy --out obj_seq --frames 48
"""
import os, argparse, numpy as np
from scipy.spatial import cKDTree
ap = argparse.ArgumentParser()
ap.add_argument("--walk", default="motion_out/walk_verts.npy")   # (T,18056,3) SOMA posed
ap.add_argument("--out", required=True)
ap.add_argument("--frames", type=int, default=48)
ap.add_argument("--k", type=int, default=6)
ap.add_argument("--scratch", default="/tmp/claude-0/-root-4dgs/4b52f132-0c51-4a15-b534-f055ce5ca28d/scratchpad")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

rest_soma = np.load(os.path.join(args.scratch, "rest_soma.npy")).astype(np.float64)   # (18056,3) SOMA frame (Y-up,T-pose)
rest_def  = np.load(os.path.join(args.scratch, "rest_def.npy")).astype(np.float64)    # (13718,3) DEF frame (Z-up,A-pose)
posed = np.load(args.walk).astype(np.float64)                                          # (T,18056,3) SOMA posed
T = posed.shape[0]
print(f"rest_soma {rest_soma.shape}  rest_def {rest_def.shape}  posed {posed.shape}")

# --- align default rest into SOMA frame: def is Z-up (height=Z, depth=Y); soma is Y-up (height=Y, depth=Z)
# permute def (x,y,z) -> (x, z, y). Fix depth/up sign by matching bbox centers & extents.
def_aligned = rest_def[:, [0, 2, 1]].copy()
# match handedness: check front/back — flip depth (new z) if needed so both share sign convention
# center both at origin for correspondence & sign checks
cs = rest_soma.mean(0); cd = def_aligned.mean(0)
soma_c = rest_soma - cs
def_c  = def_aligned - cd
# try sign flips on the depth (z) axis to best overlap the surfaces (min mean NN dist)
best = None
for sz in (1.0, -1.0):
    cand = def_c.copy(); cand[:, 2] *= sz
    d, _ = cKDTree(soma_c).query(cand, k=1)
    md = d.mean()
    if best is None or md < best[0]:
        best = (md, sz)
sz = best[1]
def_c[:, 2] *= sz
print(f"depth sign={sz}  mean NN dist after align={best[0]:.4f}  (body scale ~1.6)")

# --- K-NN correspondence: each default vert -> K soma verts, inverse-distance weights
tree = cKDTree(soma_c)
dist, idx = tree.query(def_c, k=args.k)                 # (Nd,K)
w = 1.0 / (dist + 1e-6); w /= w.sum(1, keepdims=True)   # (Nd,K)

# --- shared faces / uv / eye-mask (default topology) via anny ---
import anny
from anny.face_segmentation import get_face_segmentation_mask
m = anny.Anny()
quad = np.asarray(m.faces.detach().cpu() if hasattr(m.faces,"detach") else m.faces)
ftci = np.asarray(m.face_texture_coordinate_indices.detach().cpu() if hasattr(m.face_texture_coordinate_indices,"detach") else m.face_texture_coordinate_indices)
tc = np.asarray(m.texture_coordinates.detach().cpu() if hasattr(m.texture_coordinates,"detach") else m.texture_coordinates)
eye_mask = np.asarray(get_face_segmentation_mask(m, ["eye_front.L","eye_front.R","eye_back.L","eye_back.R"]).detach().cpu()).astype(bool)

def quad_to_tris(f): return [(f[0],f[1],f[2]),(f[0],f[2],f[3])]
skin_faces, eye_faces = [], []
for qi in range(len(quad)):
    vt = quad_to_tris(quad[qi]); ut = quad_to_tris(ftci[qi])
    tgt = eye_faces if eye_mask[qi] else skin_faces
    tgt += [(vt[0],ut[0]),(vt[1],ut[1])]

def to_blender(V):        # SOMA frame (Y-up) -> Blender Y-up OBJ; drop ground handled per-sequence
    return V

# ground offset: min height over the WHOLE sequence (preserve vertical bounce)
sel = np.linspace(0, T-1, args.frames).astype(int)
# precompute posed_def for ground calc
disp_all = posed[sel] - rest_soma[None]                       # (F,18056,3)
posed_def_seq = (rest_def_frame := def_c[None]) + (disp_all[:, idx] * w[None,...,None]).sum(2)  # (F,13718,3)
# walk IN PLACE: remove per-frame horizontal (X,Z) drift so a fixed camera keeps it framed
# (keep Y = up, incl. vertical bounce)
horiz_c = posed_def_seq[:, :, [0, 2]].mean(1, keepdims=True)     # (F,1,2) per-frame centroid
posed_def_seq[:, :, 0] -= horiz_c[:, :, 0]
posed_def_seq[:, :, 2] -= horiz_c[:, :, 1]
ymin = posed_def_seq[..., 1].min()
posed_def_seq[..., 1] -= ymin

for fi in range(len(sel)):
    Vf = posed_def_seq[fi]
    path = os.path.join(args.out, f"frame_{fi:03d}.obj")
    with open(path, "w") as f:
        for x,y,z in Vf: f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for u,v in tc: f.write(f"vt {u:.6f} {v:.6f}\n")
        for name, group in (("skin", skin_faces), ("eye", eye_faces)):
            f.write(f"usemtl {name}\n")
            for (a,b,c),(ua,ub,uc) in group:
                f.write(f"f {a+1}/{ua+1} {b+1}/{ub+1} {c+1}/{uc+1}\n")
print(f"WROTE {len(sel)} OBJs -> {args.out}  (verts {posed_def_seq.shape[1]})")
