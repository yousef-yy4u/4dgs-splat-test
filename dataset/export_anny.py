#!/usr/bin/env python3
"""Export a neutral Anny body mesh to OBJ + PLY so it can be imported into Blender for live viewing.
    conda run -n 4dgs-data python export_anny.py
Writes anny_neutral.obj / .ply next to this script. Anny is Z-up (matches Blender), meters (real scale).
"""
import os, numpy as np, torch, trimesh, anny

HERE = os.path.dirname(os.path.abspath(__file__))
model = anny.Anny(); model.eval()
with torch.no_grad():
    out = model()
verts = out["vertices"][0].detach().cpu().numpy().astype(np.float32)
tri = model.get_triangular_faces()
tri = (tri.detach().cpu().numpy() if hasattr(tri, "detach") else np.asarray(tri)).reshape(-1, 3).astype(np.int64)
mesh = trimesh.Trimesh(vertices=verts, faces=tri, process=False)

for ext in ("obj", "ply"):
    p = os.path.join(HERE, f"anny_neutral.{ext}")
    mesh.export(p)
    print("wrote", p)
print(f"verts={verts.shape[0]} tris={tri.shape[0]} bbox={mesh.bounds.tolist()}")
