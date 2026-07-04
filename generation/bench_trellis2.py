#!/usr/bin/env python
"""Benchmark TRELLIS.2-4B (native-PBR, MIT) on our test images — quality + latency on the 5090.
For the build-vs-buy decision (D43). Run in the `trellis2` conda env.

  conda run -n trellis2 python bench_trellis2.py <out_dir> <img1> [img2 ...]
"""
import os, sys, time, json
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
os.environ.setdefault('ATTN_BACKEND', 'xformers')          # skip flash-attn
os.environ.setdefault('CUDA_HOME', '/usr/local/cuda-12.5')  # Blackwell: build/JIT sm_90 PTX
os.environ.setdefault('TORCH_CUDA_ARCH_LIST', '9.0+PTX')
os.environ.setdefault('SKIP_REMBG', '1')  # bypass gated/non-commercial RMBG-2.0; feed RGBA inputs
os.environ['PATH'] = '/usr/local/cuda-12.5/bin' + os.pathsep + os.environ.get('PATH', '')

# Load the gated-DINOv3 HF token from generation/.env (never printed) BEFORE importing trellis2,
# so the encoder download authenticates.
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env) and not os.environ.get('HF_TOKEN'):
    for _l in open(_env):
        _l = _l.strip()
        if _l.startswith('HF_TOKEN=') and _l.split('=', 1)[1].strip():
            _t = _l.split('=', 1)[1].strip().strip('"').strip("'")
            os.environ['HF_TOKEN'] = _t
            os.environ['HUGGINGFACE_HUB_TOKEN'] = _t

from PIL import Image
import torch
from trellis2.pipelines import Trellis2ImageTo3DPipeline
import o_voxel

OUT = sys.argv[1]
IMAGES = sys.argv[2:]
os.makedirs(OUT, exist_ok=True)

t0 = time.time()
pipe = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
pipe.cuda()
print(f"[load] pipeline ready in {time.time()-t0:.1f}s", flush=True)

results = []
for img_path in IMAGES:
    name = os.path.splitext(os.path.basename(img_path))[0]
    print(f"\n=== {name} ===", flush=True)
    image = Image.open(img_path)
    torch.cuda.synchronize(); t = time.time()
    mesh = pipe.run(image, pipeline_type='512', seed=1)[0]
    torch.cuda.synchronize(); gen_t = time.time() - t
    mesh.simplify(16777216)
    t = time.time()
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs,
        coords=mesh.coords, attr_layout=mesh.layout, voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=200000, texture_size=2048,
        remesh=True, remesh_band=1, remesh_project=0, verbose=False,
    )
    glb_t = time.time() - t
    out_glb = os.path.join(OUT, f"{name}_t2.glb")
    glb.export(out_glb, extension_webp=False)
    sz = os.path.getsize(out_glb) / 1e6
    print(f"[{name}] gen {gen_t:.1f}s + to_glb {glb_t:.1f}s = {gen_t+glb_t:.1f}s | {sz:.1f}MB", flush=True)
    results.append({"name": name, "gen_s": round(gen_t, 1), "glb_s": round(glb_t, 1),
                    "total_s": round(gen_t + glb_t, 1), "mb": round(sz, 1), "glb": out_glb})

print("\n=== SUMMARY ===")
print(json.dumps(results, indent=2))
