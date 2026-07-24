#!/usr/bin/env python3
"""Export the DEFAULT-topology Anny mesh (13,718 v) WITH UVs as an OBJ that Blender can texture.
Adult phenotype. Splits EYEBALL faces (eye_front/eye_back, via face segmentation) into a separate
`eye` material group so Blender can shade eyes vs skin differently. Build tris FROM quads so the
eye-face mask stays aligned.

    python export_textured_obj.py --out anny_adult.obj
"""
import os, argparse, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="anny_adult.obj")
args = ap.parse_args()

import anny
from anny.face_segmentation import get_face_segmentation_mask
m = anny.Anny()

adult = dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5)
out = m(phenotype_kwargs=adult)
V = out["vertices"]; V = V.detach().cpu().numpy() if hasattr(V, "detach") else np.asarray(V)
V = V[0] if V.ndim == 3 else V

quad = np.asarray(m.faces.detach().cpu() if hasattr(m.faces, "detach") else m.faces)      # (13710,4) vert idx
ftci = m.face_texture_coordinate_indices
ftci = ftci.detach().cpu().numpy() if hasattr(ftci, "detach") else np.asarray(ftci)        # (13710,4) uv idx
tc = m.texture_coordinates
tc = tc.detach().cpu().numpy() if hasattr(tc, "detach") else np.asarray(tc)                 # (21334,2)

eye_mask = get_face_segmentation_mask(m, ["eye_front.L", "eye_front.R", "eye_back.L", "eye_back.R"])
eye_mask = np.asarray(eye_mask.detach().cpu() if hasattr(eye_mask, "detach") else eye_mask).astype(bool)
print(f"quads={len(quad)} eye_quads={int(eye_mask.sum())} uvs={len(tc)}")

# Anny Z-up -> Blender-friendly Y-up, feet to ground
Vb = np.stack([V[:, 0], V[:, 2], -V[:, 1]], axis=1)
Vb[:, 1] -= Vb[:, 1].min()

def quad_to_tris(f):  # [a,b,c,d] -> (a,b,c),(a,c,d)
    return [(f[0], f[1], f[2]), (f[0], f[2], f[3])]

skin_faces, eye_faces = [], []   # each: ((v,v,v),(uv,uv,uv))
for qi in range(len(quad)):
    vt = quad_to_tris(quad[qi]); ut = quad_to_tris(ftci[qi])
    tgt = eye_faces if eye_mask[qi] else skin_faces
    tgt.append((vt[0], ut[0])); tgt.append((vt[1], ut[1]))

with open(args.out, "w") as f:
    f.write("# Anny adult default-topology mesh with UVs; skin/eye material groups\n")
    for x, y, z in Vb:
        f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
    for u, v in tc:
        f.write(f"vt {u:.6f} {v:.6f}\n")
    for name, group in (("skin", skin_faces), ("eye", eye_faces)):
        f.write(f"usemtl {name}\n")
        for (a, b, c), (ua, ub, uc) in group:
            f.write(f"f {a+1}/{ua+1} {b+1}/{ub+1} {c+1}/{uc+1}\n")
print("WROTE", args.out, "| skin tris", len(skin_faces), "eye tris", len(eye_faces),
      "| height", round(float(Vb[:,1].max()), 3))
