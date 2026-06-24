#!/usr/bin/env python
"""Generate the TRELLIS mesh for an image and save as .obj (geometry only, for UniRig rigging)."""
import os, sys
os.environ.setdefault('ATTN_BACKEND', 'xformers')
os.environ.setdefault('SPARSE_BACKEND', 'spconv')
os.environ.setdefault('SPCONV_ALGO', 'native')
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
import trimesh

IMG = sys.argv[1] if len(sys.argv) > 1 else "/home/sov2/projects/TRELLIS/assets/example_image/typical_creature_robot_crab.png"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/sov2/projects/4dgs/generation/out/crab_mesh.obj"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

pipe = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large"); pipe.cuda()
out = pipe.run(Image.open(IMG), seed=1, formats=['mesh'])
m = out['mesh'][0]
v = m.vertices.detach().cpu().numpy()
f = m.faces.detach().cpu().numpy()
trimesh.Trimesh(vertices=v, faces=f, process=False).export(OUT)
print(f"saved {OUT}  verts={v.shape} faces={f.shape}")
