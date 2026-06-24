#!/usr/bin/env python
"""
4dgs generation pipeline — step 1: image -> 3D Gaussian splat (.ply) via TRELLIS.

Gaussian-only (formats=['gaussian']) so we skip the mesh/radiance-field rasterizers
(nvdiffrast / diffoctreerast / kaolin) that have no Blackwell build yet.

Usage:
  cd /home/sov2/projects/TRELLIS
  /home/sov2/projects/gen-venv/bin/python /home/sov2/projects/4dgs/generation/run_trellis.py [image] [out.ply]
"""
import os, sys, time
os.environ.setdefault('ATTN_BACKEND', 'xformers')   # sparse attn needs xformers or flash_attn (no native path)
os.environ.setdefault('SPARSE_BACKEND', 'spconv')
os.environ.setdefault('SPCONV_ALGO', 'native')

from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline

IMG = sys.argv[1] if len(sys.argv) > 1 else "/home/sov2/projects/TRELLIS/assets/example_image/typical_creature_robot_crab.png"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/sov2/projects/4dgs/generation/out/output.ply"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

print(f"[1/3] loading pipeline (downloads weights on first run)…", flush=True)
t = time.time()
pipe = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
pipe.cuda()
print(f"      pipeline ready in {time.time()-t:.1f}s", flush=True)

print(f"[2/3] running image->splat on {IMG} …", flush=True)
img = Image.open(IMG)
t = time.time()
outputs = pipe.run(img, seed=1, formats=['gaussian'])
print(f"      inference done in {time.time()-t:.1f}s", flush=True)

g = outputs['gaussian'][0]
g.save_ply(OUT)
import plyfile
n = plyfile.PlyData.read(OUT)['vertex'].count
print(f"[3/3] saved {OUT}  ({n:,} splats)", flush=True)
