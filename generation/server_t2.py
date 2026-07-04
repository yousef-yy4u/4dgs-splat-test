#!/usr/bin/env python
"""TRELLIS.2 generation worker (D44) — replaces the v1 TRELLIS + gsplat-bake backend with
TRELLIS.2-4B *native-PBR* for high-fidelity textures. Serves the SAME platform job contract as
server.py (/generate_static, /generate, /status/<job>, /out/<fn>) on :8077, so the platform
(lib/gen-worker.ts) is unchanged.

Runs in the `trellis2` conda env on the RTX 5090.

Commercial-clean stack:
  - Geometry+texture: TRELLIS.2-4B (MIT, native 3D PBR).
  - Background removal: u2net `rembg` (Apache) — NOT the gated/non-commercial briaai/RMBG-2.0.
    We hand TRELLIS.2 an RGBA image, which makes its pipeline skip its own RMBG (SKIP_REMBG=1).
  - Image encoder: DINOv3 (commercial-OK; requires a "Built with DINOv3" attribution).
  - Rigging (animated path): UniRig (MIT) + transfer_rig onto the TRELLIS.2 textured mesh.

Run:
  PORT=8077 conda run -n trellis2 python generation/server_t2.py
"""
import os, sys, time, uuid, threading, subprocess, shutil, traceback

# --- TRELLIS.2 / Blackwell env (set before importing trellis2) ---
os.environ.setdefault('ATTN_BACKEND', 'xformers')
os.environ.setdefault('SKIP_REMBG', '1')                 # we feed RGBA; skip gated RMBG-2.0
os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')
os.environ.setdefault('CUDA_HOME', '/usr/local/cuda-12.5')
os.environ.setdefault('TORCH_CUDA_ARCH_LIST', '9.0+PTX')
os.environ['PATH'] = '/usr/local/cuda-12.5/bin' + os.pathsep + os.environ.get('PATH', '')

BASE = '/home/sov2/projects/4dgs'
GEN = os.path.join(BASE, 'generation')

# gated DINOv3 token (cached after first download), from generation/.env
_env = os.path.join(GEN, '.env')
if os.path.exists(_env) and not os.environ.get('HF_TOKEN'):
    for _l in open(_env):
        _l = _l.strip()
        if _l.startswith('HF_TOKEN=') and _l.split('=', 1)[1].strip():
            _t = _l.split('=', 1)[1].strip().strip('"').strip("'")
            os.environ['HF_TOKEN'] = _t
            os.environ['HUGGINGFACE_HUB_TOKEN'] = _t

T2 = '/home/sov2/projects/TRELLIS.2'
if T2 not in sys.path:
    sys.path.insert(0, T2)

GEN_OUT = os.path.join(GEN, 'out')
RESULTS = os.path.join(GEN, 'studio_out')      # served at /out/<fn>
UPLOADS = os.path.join(GEN, 'studio_uploads')
UNIRIG = '/home/sov2/projects/UniRig'
UNIRIG_PY = '/home/sov2/projects/unirig-venv/bin/python'
GEN_PY = '/home/sov2/projects/gen-venv/bin/python'   # clean_mesh deps (open3d) live here
for d in (GEN_OUT, RESULTS, UPLOADS):
    os.makedirs(d, exist_ok=True)

import numpy as np
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory

PIPE = None
REMBG = None
PIPE_LOCK = threading.Lock()   # one GPU job at a time
JOBS = {}


def log(job, stage, pct, msg=''):
    JOBS[job].update(stage=stage, pct=pct)
    print(f"[{job[:8]}] {pct:3d}% {stage} {msg}", flush=True)


def load_pipe():
    global PIPE, REMBG
    if PIPE is None:
        from trellis2.pipelines import Trellis2ImageTo3DPipeline
        print('[startup] loading TRELLIS.2-4B (~2min)…', flush=True)
        t = time.time()
        PIPE = Trellis2ImageTo3DPipeline.from_pretrained('microsoft/TRELLIS.2-4B')
        PIPE.cuda()
        print(f'[startup] TRELLIS.2 ready in {time.time()-t:.0f}s', flush=True)
    if REMBG is None:
        import rembg
        REMBG = rembg.new_session('u2net')
    return PIPE


def rgba_cut(path):
    """Background-removed RGBA via clean u2net (so TRELLIS.2 skips the gated RMBG-2.0)."""
    import rembg
    return rembg.remove(Image.open(path).convert('RGB'), session=REMBG)


def export_glb(mesh, out_glb, texture_size=1024, decimation=100000):
    import o_voxel
    mesh.simplify(16777216)   # nvdiffrast limit
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs,
        coords=mesh.coords, attr_layout=mesh.layout, voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation, texture_size=texture_size,
        remesh=True, remesh_band=1, remesh_project=0, verbose=False,
    )
    glb.export(out_glb, extension_webp=False)
    return glb


def export_mesh_obj(mesh, out_obj):
    """Export the raw TRELLIS.2 geometry as OBJ for UniRig (rig-readiness handled by clean_mesh)."""
    import trimesh
    v = mesh.vertices.detach().cpu().numpy() if hasattr(mesh.vertices, 'detach') else np.asarray(mesh.vertices)
    f = mesh.faces.detach().cpu().numpy() if hasattr(mesh.faces, 'detach') else np.asarray(mesh.faces)
    trimesh.Trimesh(vertices=v, faces=f, process=False).export(out_obj)


def glb_joint_count(glb_path):
    try:
        import struct, json
        data = open(glb_path, 'rb').read()
        n = struct.unpack('<I', data[12:16])[0]
        js = json.loads(data[20:20 + n])
        return len(js['skins'][0]['joints']) if js.get('skins') else 0
    except Exception:
        return 0


def run_unirig(script, args, tag, job):
    """Run a UniRig launch script in the unirig-venv (success judged by output file, not exit code)."""
    env = dict(os.environ)
    env['PYTHONPATH'] = UNIRIG
    env['PATH'] = os.path.dirname(UNIRIG_PY) + os.pathsep + env.get('PATH', '')
    p = subprocess.run(['bash', f'launch/inference/{script}'] + args, cwd=UNIRIG, env=env,
                       capture_output=True, text=True)
    print(f"[{job[:8]}] unirig {tag} rc={p.returncode}", flush=True)
    return (p.stdout + p.stderr)[-1500:]


# ----------------------------------------------------------------------------
# pipelines
# ----------------------------------------------------------------------------
def pipeline_static(job, image_paths, name):
    """image -> RGBA -> TRELLIS.2 -> textured PBR GLB (the un-anchored 'view in 3D' product)."""
    with PIPE_LOCK:
        load_pipe()
        log(job, 'preprocess (u2net bg-cut)', 5)
        rgba = rgba_cut(image_paths[0])
        log(job, 'TRELLIS.2 (512)', 25)
        t = time.time()
        mesh = PIPE.run(rgba, pipeline_type='512', seed=1)[0]
        log(job, 'bake PBR texture', 75, f'{time.time()-t:.0f}s')
        out_glb = os.path.join(RESULTS, f'{name}_textured.glb')
        export_glb(mesh, out_glb, texture_size=1024, decimation=100000)
        JOBS[job]['result'] = {'glb': f'/out/{name}_textured.glb', 'name': name, 'textured': True}
        log(job, 'done', 100)
        JOBS[job]['done'] = True


def worker_static(job, paths, name):
    try:
        pipeline_static(job, paths, name)
    except Exception as e:
        traceback.print_exc()
        JOBS[job].update(error=str(e), done=True)


def pipeline_animated(job, image_paths, name, motion='idle'):
    """image -> TRELLIS.2 textured mesh -> UniRig skeleton/skin -> rig transferred onto the
    textured mesh + baked motion. Falls back to the static textured mesh if rigging fails."""
    with PIPE_LOCK:
        load_pipe()
        log(job, 'preprocess (u2net bg-cut)', 5)
        rgba = rgba_cut(image_paths[0])
        log(job, 'TRELLIS.2 (512)', 20)
        t = time.time()
        mesh = PIPE.run(rgba, pipeline_type='512', seed=1)[0]

        # textured PBR mesh (also the static fallback + the surface transfer_rig skins to the rig)
        log(job, 'bake PBR texture', 45, f'{time.time()-t:.0f}s')
        textured_glb = os.path.join(RESULTS, f'{name}_textured.glb')
        export_glb(mesh, textured_glb, texture_size=1024, decimation=100000)
        mesh_obj = os.path.join(GEN_OUT, f'{name}_mesh.obj')
        export_mesh_obj(mesh, mesh_obj)

        # rig-readiness cleanup (open3d lives in gen-venv)
        log(job, 'clean mesh', 55)
        clean_obj = os.path.join(GEN_OUT, f'{name}_clean.obj')
        subprocess.run([GEN_PY, os.path.join(GEN, 'clean_mesh.py'), mesh_obj, clean_obj],
                       capture_output=True, text=True)
        if not os.path.exists(clean_obj):
            raise RuntimeError('mesh cleanup produced no output')

        glb = os.path.join(RESULTS, f'{name}_rigged.glb')
        rig_ok, rig_msg, nbones = True, '', 0
        try:
            shutil.copy(clean_obj, os.path.join(UNIRIG, 'examples', f'{name}.obj'))
            log(job, 'UniRig skeleton', 62)
            skel = f'examples/{name}_skeleton.fbx'
            t1 = run_unirig('generate_skeleton.sh', ['--input', f'examples/{name}.obj', '--output', skel], 'skeleton', job)
            if not os.path.exists(os.path.join(UNIRIG, skel)):
                raise RuntimeError('skeleton stage produced no FBX (mesh likely OOD for the rig model)\n' + t1[-400:])
            log(job, 'UniRig skin', 75)
            skin = f'examples/{name}_skinned.fbx'
            t2 = run_unirig('generate_skin.sh', ['--input', skel, '--output', skin, '--data_name', 'raw_data.npz'], 'skin', job)
            if not os.path.exists(os.path.join(UNIRIG, skin)):
                raise RuntimeError('skin stage produced no FBX\n' + t2[-400:])
            log(job, 'assemble rig + bake motion', 86)
            # prep_viewer: skinned FBX -> rigged GLB + baked `motion` (no splat -> vertex-colour skipped)
            subprocess.run([UNIRIG_PY, os.path.join(GEN, 'prep_viewer.py'),
                            os.path.join(UNIRIG, skin), glb, 'none', motion], capture_output=True, text=True)
            if not os.path.exists(glb):
                raise RuntimeError('GLB assembly failed')
            nbones = glb_joint_count(glb)
            if nbones <= 1:
                rig_ok = False
                rig_msg = f'degenerate skeleton ({nbones} bone) — mesh OOD for the rig model'
        except Exception as e:
            rig_ok = False
            rig_msg = str(e).strip().splitlines()[0][:200]
            print(f"[{job[:8]}] RIG FAILED -> static textured fallback: {rig_msg}", flush=True)

        if rig_ok:
            # transfer the UniRig skeleton+skin onto the PROVEN TRELLIS.2 textured mesh
            log(job, 'apply texture (transfer rig)', 94)
            glb_tex = os.path.join(RESULTS, f'{name}_rigged_tex.glb')
            rt = subprocess.run([UNIRIG_PY, os.path.join(GEN, 'transfer_rig.py'), glb, textured_glb, glb_tex],
                                capture_output=True, text=True)
            if os.path.exists(glb_tex):
                shutil.move(glb_tex, glb)
                result_glb = f'/out/{name}_rigged.glb'
                print(f"[{job[:8]}] rig transferred onto TRELLIS.2 textured mesh", flush=True)
            else:
                rig_ok = False
                rig_msg = 'transfer_rig failed: ' + rt.stderr[-300:]
                result_glb = f'/out/{name}_textured.glb'
        else:
            result_glb = f'/out/{name}_textured.glb'   # static textured fallback

        JOBS[job]['result'] = {
            'glb': result_glb, 'name': name, 'rig_ok': rig_ok,
            'bones': nbones, 'motion': motion if rig_ok else None, 'note': rig_msg,
        }
        log(job, 'done', 100, '' if rig_ok else f'(rig warning: {rig_msg})')
        JOBS[job]['done'] = True


def worker_animated(job, paths, name, motion='idle'):
    try:
        pipeline_animated(job, paths, name, motion)
    except Exception as e:
        traceback.print_exc()
        JOBS[job].update(error=str(e), done=True)


# ----------------------------------------------------------------------------
# web (same contract as server.py)
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024


def _save_uploads(files, name):
    paths = []
    for i, f in enumerate(files):
        p = os.path.join(UPLOADS, f'{name}_{i}.png')
        Image.open(f.stream).convert('RGBA').save(p)
        paths.append(p)
    return paths


@app.route('/')
def index():
    return jsonify(worker='trellis2', ready=PIPE is not None)


@app.route('/generate_static', methods=['POST'])
def generate_static():
    files = request.files.getlist('images')
    if not files:
        return jsonify(error='no images uploaded'), 400
    job = uuid.uuid4().hex
    name = 'gen_' + job[:8]
    paths = _save_uploads(files, name)
    JOBS[job] = dict(stage='queued', pct=0, done=False, error=None, result=None, nviews=len(paths))
    threading.Thread(target=worker_static, args=(job, paths, name), daemon=True).start()
    return jsonify(job_id=job, nviews=len(paths))


@app.route('/generate', methods=['POST'])
def generate():
    """Animated (rigged) textured asset — TRELLIS.2 mesh + UniRig + rig-transfer onto the texture."""
    files = request.files.getlist('images')
    if not files:
        return jsonify(error='no images uploaded'), 400
    job = uuid.uuid4().hex
    name = 'gen_' + job[:8]
    motion = (request.form.get('motion') or 'idle').strip()
    paths = _save_uploads(files, name)
    JOBS[job] = dict(stage='queued', pct=0, done=False, error=None, result=None, nviews=len(paths))
    threading.Thread(target=worker_animated, args=(job, paths, name, motion), daemon=True).start()
    return jsonify(job_id=job, nviews=len(paths))


@app.route('/status/<job>')
def status(job):
    j = JOBS.get(job)
    if not j:
        return jsonify(error='unknown job'), 404
    return jsonify(j)


@app.route('/out/<path:fn>')
def out(fn):
    return send_from_directory(RESULTS, fn)


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', '8077'))
    load_pipe()   # warm the model before accepting requests
    print(f'[startup] TRELLIS.2 worker ready at http://0.0.0.0:{PORT}', flush=True)
    app.run(host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)
