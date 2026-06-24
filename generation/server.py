#!/usr/bin/env python
"""
4dgs STUDIO server — drop an image (or several views) and watch the full pipeline run:
  image(s) -> TRELLIS (mesh + splat) -> clean_mesh -> UniRig skeleton -> UniRig skin
           -> rigged GLB + decimated splat -> rendered in the browser.

TRELLIS is loaded ONCE and kept resident (the ~40s cost) so each generation is fast.
The UniRig stages run as subprocesses in the unirig-venv (bpy needs py3.11; TRELLIS needs
py3.12 — two venvs, so we shell out). One job at a time (single GPU), others queue.

Run (from anywhere):
  PYTHONPATH=/home/sov2/projects/TRELLIS XFORMERS_DISABLED=1 ATTN_BACKEND=xformers \
  SPARSE_BACKEND=spconv SPCONV_ALGO=native \
  /home/sov2/projects/gen-venv/bin/python /home/sov2/projects/4dgs/generation/server.py
Then open http://<server>:8000  (or tunnel the port to your phone/laptop).
"""
import os, sys, time, uuid, threading, subprocess, shutil, traceback

# --- TRELLIS env (must be set before importing trellis) ---
os.environ.setdefault('ATTN_BACKEND', 'xformers')
os.environ.setdefault('SPARSE_BACKEND', 'spconv')
os.environ.setdefault('SPCONV_ALGO', 'native')
os.environ.setdefault('XFORMERS_DISABLED', '1')
TRELLIS_DIR = '/home/sov2/projects/TRELLIS'
if TRELLIS_DIR not in sys.path:
    sys.path.insert(0, TRELLIS_DIR)

# --- paths ---
BASE       = '/home/sov2/projects/4dgs'
GEN        = os.path.join(BASE, 'generation')
GEN_OUT    = os.path.join(GEN, 'out')
RESULTS    = os.path.join(GEN, 'studio_out')          # served to the browser
UPLOADS    = os.path.join(GEN, 'studio_uploads')
UNIRIG     = '/home/sov2/projects/UniRig'
UNIRIG_PY  = '/home/sov2/projects/unirig-venv/bin/python'
GEN_PY     = sys.executable                            # this server runs in gen-venv
for d in (GEN_OUT, RESULTS, UPLOADS):
    os.makedirs(d, exist_ok=True)

from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, Response

# ----------------------------------------------------------------------------
# pipeline plumbing
# ----------------------------------------------------------------------------
PIPE = None
PIPE_LOCK = threading.Lock()      # only one GPU job at a time
JOBS = {}                         # job_id -> dict(stage, pct, done, error, result)

def log(job, stage, pct, msg=''):
    JOBS[job].update(stage=stage, pct=pct)
    print(f"[{job[:8]}] {pct:3d}% {stage} {msg}", flush=True)

def load_pipe():
    global PIPE
    if PIPE is None:
        from trellis.pipelines import TrellisImageTo3DPipeline
        print('[startup] loading TRELLIS (one-time ~40s)…', flush=True)
        t = time.time()
        PIPE = TrellisImageTo3DPipeline.from_pretrained('microsoft/TRELLIS-image-large')
        PIPE.cuda()
        print(f'[startup] TRELLIS ready in {time.time()-t:.1f}s', flush=True)
    return PIPE

def glb_joint_count(glb_path):
    """Parse the GLB JSON chunk for skins[0].joints length (the real bone count)."""
    try:
        import struct, json
        with open(glb_path, 'rb') as f:
            data = f.read()
        n = struct.unpack('<I', data[12:16])[0]
        js = json.loads(data[20:20+n])
        return len(js['skins'][0]['joints']) if js.get('skins') else 0
    except Exception:
        return 0

def run_unirig(script, args, tag, job):
    """Run a UniRig launch script in the unirig-venv. Returns (ok, logtail).
    NB: the bpy extract substep often segfaults on EXIT after writing valid output, so we
    judge success by the expected output file existing (checked by the caller), not exit code."""
    env = dict(os.environ)
    env['PYTHONPATH'] = UNIRIG
    env['PATH'] = os.path.dirname(UNIRIG_PY) + os.pathsep + env.get('PATH', '')
    cmd = ['bash', f'launch/inference/{script}'] + args
    p = subprocess.run(cmd, cwd=UNIRIG, env=env, capture_output=True, text=True)
    tail = (p.stdout + p.stderr)[-1500:]
    print(f"[{job[:8]}] unirig {tag} rc={p.returncode}", flush=True)
    return p.returncode == 0, tail

def pipeline(job, image_paths, name):
    """The full image(s) -> rigged asset pipeline. Updates JOBS[job] as it goes."""
    with PIPE_LOCK:
        pipe = load_pipe()
        log(job, 'preprocess', 5)
        imgs = [Image.open(p).convert('RGBA') for p in image_paths]

        # 1. TRELLIS (resident)
        log(job, f'TRELLIS ({len(imgs)} view{"s" if len(imgs)>1 else ""})', 15)
        t = time.time()
        if len(imgs) == 1:
            out = pipe.run(imgs[0], seed=1, formats=['mesh', 'gaussian'])
        else:
            out = pipe.run_multi_image(imgs, seed=1, formats=['mesh', 'gaussian'])
        mesh_obj = os.path.join(GEN_OUT, f'{name}_mesh.obj')
        splat_ply = os.path.join(GEN_OUT, f'{name}.ply')
        import trimesh
        m = out['mesh'][0]
        trimesh.Trimesh(vertices=m.vertices.detach().cpu().numpy(),
                        faces=m.faces.detach().cpu().numpy(), process=False).export(mesh_obj)
        out['gaussian'][0].save_ply(splat_ply)
        log(job, 'TRELLIS done', 40, f'{time.time()-t:.0f}s')

        # 2. mesh cleanup (rig-readiness)
        log(job, 'clean mesh', 50)
        clean_obj = os.path.join(GEN_OUT, f'{name}_clean.obj')
        subprocess.run([GEN_PY, os.path.join(GEN, 'clean_mesh.py'), mesh_obj, clean_obj],
                       capture_output=True, text=True)
        if not os.path.exists(clean_obj):
            raise RuntimeError('mesh cleanup produced no output')

        # stage the clean mesh inside UniRig/examples for tidy npz paths
        shutil.copy(clean_obj, os.path.join(UNIRIG, 'examples', f'{name}.obj'))

        # always produce the web splat first (so even a rig failure still shows the 3D)
        web_splat = os.path.join(RESULTS, f'{name}_splat.ply')
        subprocess.run([GEN_PY, os.path.join(GEN, 'decimate_ply.py'), splat_ply, web_splat, '200000'],
                       capture_output=True, text=True)

        glb = os.path.join(RESULTS, f'{name}_rigged.glb')
        rig_ok, rig_msg, nbones = True, '', 0
        try:
            shutil.copy(clean_obj, os.path.join(UNIRIG, 'examples', f'{name}.obj'))

            # 3. skeleton
            log(job, 'UniRig skeleton', 60)
            skel_fbx = f'examples/{name}_skeleton.fbx'
            _, t1 = run_unirig('generate_skeleton.sh', ['--input', f'examples/{name}.obj', '--output', skel_fbx], 'skeleton', job)
            if not os.path.exists(os.path.join(UNIRIG, skel_fbx)):
                raise RuntimeError('skeleton stage produced no FBX (TRELLIS mesh likely too noisy/OOD for the rig model)\n' + t1[-400:])

            # 4. skin (input MUST be the skeleton FBX so extract reads the armature -> joints)
            log(job, 'UniRig skin', 78)
            skin_fbx = f'examples/{name}_skinned.fbx'
            _, t2 = run_unirig('generate_skin.sh', ['--input', skel_fbx, '--output', skin_fbx, '--data_name', 'raw_data.npz'], 'skin', job)
            if not os.path.exists(os.path.join(UNIRIG, skin_fbx)):
                raise RuntimeError('skin stage produced no FBX\n' + t2[-400:])

            # 5. assemble rigged GLB
            log(job, 'assemble', 90)
            subprocess.run([UNIRIG_PY, os.path.join(GEN, 'prep_viewer.py'),
                            os.path.join(UNIRIG, skin_fbx), glb], capture_output=True, text=True)
            if not os.path.exists(glb):
                raise RuntimeError('GLB assembly failed')
            nbones = glb_joint_count(glb)
            if nbones <= 1:
                rig_ok = False
                rig_msg = f'degenerate skeleton ({nbones} bone) — mesh likely OOD for the rig model; showing mesh+splat'
        except Exception as e:
            rig_ok = False
            rig_msg = str(e).strip().splitlines()[0][:200]
            print(f"[{job[:8]}] RIG FAILED -> plain-mesh fallback: {rig_msg}", flush=True)
            try:
                import trimesh
                trimesh.load(clean_obj, force='mesh').export(glb)   # un-rigged mesh so the viewer still shows it
            except Exception as e2:
                raise RuntimeError(f'rigging failed AND mesh fallback failed: {rig_msg} / {e2}')

        if not (os.path.exists(glb) and os.path.exists(web_splat)):
            raise RuntimeError('no output produced')

        # 6. bind splat -> rig (so the SPLAT animates with the skeleton). Best-effort.
        splat_skinned_url = None
        if rig_ok:
            log(job, 'bind splat to rig', 95)
            sk_ply = os.path.join(RESULTS, f'{name}_splat_skinned.ply')
            r = subprocess.run([GEN_PY, os.path.join(GEN, 'bind_splat.py'), glb, web_splat, sk_ply],
                               capture_output=True, text=True)
            if os.path.exists(sk_ply):
                splat_skinned_url = f'/out/{name}_splat_skinned.ply'
            else:
                print(f"[{job[:8]}] splat-bind failed: {r.stderr[-300:]}", flush=True)

        JOBS[job]['result'] = {
            'glb': f'/out/{name}_rigged.glb',
            'splat': f'/out/{name}_splat.ply',
            'splat_skinned': splat_skinned_url,
            'name': name,
            'rig_ok': rig_ok,
            'bones': nbones,
            'note': rig_msg,
        }
        log(job, 'done', 100, '' if rig_ok else f'(rig warning: {rig_msg})')
        JOBS[job]['done'] = True

def worker(job, image_paths, name):
    try:
        pipeline(job, image_paths, name)
    except Exception as e:
        traceback.print_exc()
        JOBS[job].update(error=str(e), done=True)

# ----------------------------------------------------------------------------
# web
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024   # 200MB upload

@app.route('/')
def index():
    return send_from_directory(GEN, 'studio.html')

@app.route('/generate', methods=['POST'])
def generate():
    files = request.files.getlist('images')
    if not files:
        return jsonify(error='no images uploaded'), 400
    job = uuid.uuid4().hex
    name = 'gen_' + job[:8]
    paths = []
    for i, f in enumerate(files):
        p = os.path.join(UPLOADS, f'{name}_{i}.png')
        Image.open(f.stream).convert('RGBA').save(p)
        paths.append(p)
    JOBS[job] = dict(stage='queued', pct=0, done=False, error=None, result=None, nviews=len(paths))
    threading.Thread(target=worker, args=(job, paths, name), daemon=True).start()
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
    PORT = int(os.environ.get('PORT', '8000'))
    load_pipe()   # warm the model before accepting requests
    print(f'[startup] studio ready at http://0.0.0.0:{PORT}', flush=True)
    app.run(host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)
