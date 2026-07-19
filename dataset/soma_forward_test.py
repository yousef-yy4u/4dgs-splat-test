#!/usr/bin/env python3
"""Prove SOMALayer(anny).forward() posts a mesh from SOMA poses, on CPU. Renders a rest-pose front view
and reports the output topology (vertex count) so we know if it matches Anny's default 13,718-v mesh.
    conda run -n 4dgs-data python soma_forward_test.py
"""
import os, sys, numpy as np, torch
if sys.platform.startswith("linux"): os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
else: os.environ.pop("PYOPENGL_PLATFORM", None)
from soma import SOMALayer

# SHIM: soma 0.1.0 passes local_changes=None into anny 0.5's get_phenotype_blendshape_coefficients,
# whose try/except only catches KeyError (not the TypeError from subscripting None). Coerce None->{}.
import anny.models.phenotype as _ph
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(_orig):
            def _p(self, *a, local_changes=None, **k):
                return _orig(self, *a, local_changes=(local_changes or {}), **k)
            return _p
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

layer = SOMALayer(identity_model_type="anny", device="cpu"); layer.eval()
parents = getattr(layer, "parents", None)
parents = parents if parents is not None else getattr(layer, "joint_parent_ids", None)
J = len(parents) if parents is not None else None
S = getattr(layer, "num_shape_components", None)
faces = layer.faces
faces_np = (faces.detach().cpu().numpy() if hasattr(faces, "detach") else np.asarray(faces))
print(f"SOMA joints J={J}  shape_components S={S}  faces={faces_np.shape} dtype={faces_np.dtype}")

poses = torch.zeros(1, J, 3, dtype=torch.float32)       # axis-angle, rest
identity = torch.zeros(1, 11, dtype=torch.float32)      # Anny backend expects 11 phenotype coeffs (not SOMA's 128)
transl = torch.zeros(1, 3, dtype=torch.float32)          # root/hips translation (required, not None)
with torch.no_grad():
    out = layer(poses, identity, transl=transl)          # pose2rot=True default
if isinstance(out, dict):
    print("forward -> dict keys:", list(out.keys()))
    for k, v in out.items():
        print("   ", k, getattr(v, "shape", None))
    verts = out.get("vertices", out.get("verts"))
else:
    verts = out
verts = verts.detach().cpu().numpy()[0] if verts.ndim == 3 else verts.detach().cpu().numpy()
print(f"OUTPUT vertices: {verts.shape}  (Anny default is 13718 -> {'MATCH' if verts.shape[0]==13718 else 'DIFFERENT topology'})")

# render one rest-pose front view
import trimesh, pyrender, imageio, math
tri = faces_np.reshape(-1, faces_np.shape[-1]).astype(np.int64)
if tri.shape[1] == 4:  # quads -> tris
    tri = np.concatenate([tri[:, [0,1,2]], tri[:, [0,2,3]]], axis=0)
m = trimesh.Trimesh(vertices=verts.astype(np.float32), faces=tri, process=False)
c = verts.mean(0); ext = verts.max(0) - verts.min(0); up_i = int(np.argmax(ext)); h = float(ext[up_i])
horiz = [i for i in range(3) if i != up_i]; up = np.zeros(3); up[up_i] = 1.0
eye = c.astype(np.float64).copy(); eye[horiz[1]] += 1.9*h; eye[up_i] += 0.1*h
f = (c - eye); f /= np.linalg.norm(f); s = np.cross(f, up); s /= np.linalg.norm(s); u = np.cross(s, f)
pose = np.eye(4); pose[:3,0]=s; pose[:3,1]=u; pose[:3,2]=-f; pose[:3,3]=eye
sc = pyrender.Scene(bg_color=[0.05,0.05,0.06,1.0], ambient_light=[0.35,0.35,0.38])
mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80,0.66,0.58,1.0], metallicFactor=0, roughnessFactor=0.8)
sc.add(pyrender.Mesh.from_trimesh(m, material=mat, smooth=True))
sc.add(pyrender.PerspectiveCamera(yfov=np.pi/4), pose=pose)
sc.add(pyrender.DirectionalLight(color=np.ones(3), intensity=4.0), pose=pose)
r = pyrender.OffscreenRenderer(320, 320); col, _ = r.render(sc); r.delete()
imageio.imwrite("soma_rest.png", col)
print("WROTE soma_rest.png")
