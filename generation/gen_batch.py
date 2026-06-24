#!/usr/bin/env python
"""
4dgs generation — batch image->3D. Loads TRELLIS ONCE (the ~40s cost) and emits BOTH
a mesh (.obj, for rigging) and a gaussian splat (.ply, for the viewer/binding) per image
in a single inference call (formats=['mesh','gaussian']).

Usage (gen-venv, from /home/sov2/projects/TRELLIS):
  /home/sov2/projects/gen-venv/bin/python /home/sov2/projects/4dgs/generation/gen_batch.py \
      name1=/abs/img1.png name2=/abs/img2.jpg ...
Outputs: generation/out/<name>_mesh.obj  and  generation/out/<name>.ply
"""
import os, sys, time
os.environ.setdefault('ATTN_BACKEND', 'xformers')
os.environ.setdefault('SPARSE_BACKEND', 'spconv')
os.environ.setdefault('SPCONV_ALGO', 'native')

from PIL import Image
import trimesh
import plyfile
from trellis.pipelines import TrellisImageTo3DPipeline

OUT_DIR = "/home/sov2/projects/4dgs/generation/out"
os.makedirs(OUT_DIR, exist_ok=True)

jobs = []
for a in sys.argv[1:]:
    name, _, path = a.partition('=')
    assert path, f"expected name=path, got {a!r}"
    jobs.append((name, path))
assert jobs, "no jobs given"

print(f"[load] TRELLIS pipeline …", flush=True)
t = time.time()
pipe = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
pipe.cuda()
print(f"[load] ready in {time.time()-t:.1f}s", flush=True)

for name, path in jobs:
    print(f"\n[gen] {name}  <- {path}", flush=True)
    img = Image.open(path)
    t = time.time()
    out = pipe.run(img, seed=1, formats=['mesh', 'gaussian'])
    print(f"[gen] {name} inference {time.time()-t:.1f}s", flush=True)

    mesh_path = os.path.join(OUT_DIR, f"{name}_mesh.obj")
    m = out['mesh'][0]
    v = m.vertices.detach().cpu().numpy(); f = m.faces.detach().cpu().numpy()
    trimesh.Trimesh(vertices=v, faces=f, process=False).export(mesh_path)
    print(f"[gen] {name} mesh -> {mesh_path}  verts={v.shape[0]:,} faces={f.shape[0]:,}", flush=True)

    ply_path = os.path.join(OUT_DIR, f"{name}.ply")
    out['gaussian'][0].save_ply(ply_path)
    n = plyfile.PlyData.read(ply_path)['vertex'].count
    print(f"[gen] {name} splat -> {ply_path}  ({n:,} splats)", flush=True)

print("\n[done]", flush=True)
