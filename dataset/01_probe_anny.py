#!/usr/bin/env python3
"""
01_probe_anny.py — discover Anny's REAL API and smoke-test the headless render path.

Claude can't reach your GPU box and the web docs don't give exact method signatures, so this script
introspects the installed Anny package (instead of assuming), then tries to render a neutral body
offscreen. It is READ-ONLY: it instantiates the model and renders one 256x256 PNG, nothing else.

    python 01_probe_anny.py

Then PASTE THE ENTIRE OUTPUT back to Claude (and note whether probe_render.png looks like a gray
human). That output is what the Phase-1 render harness gets written against.

First run may take several minutes (Anny caches its assets on first instantiation).
"""
import inspect
import sys
import traceback

def hdr(t): print("\n" + "=" * 70 + f"\n {t}\n" + "=" * 70)
def sig(obj, name):
    """Print inspect.signature for attr `name` on obj, if it exists and is callable."""
    a = getattr(obj, name, None)
    if a is None:
        return
    try:
        print(f"  {name}{inspect.signature(a)}")
    except (TypeError, ValueError):
        print(f"  {name}  (callable, signature unavailable)")

# --- environment -------------------------------------------------------------
hdr("ENVIRONMENT")
print("python:", sys.version.split()[0])
for mod in ("torch", "warp", "numpy", "trimesh", "pyrender"):
    try:
        m = __import__(mod)
        print(f"{mod}:", getattr(m, "__version__", "?"))
    except Exception as e:
        print(f"{mod}: NOT IMPORTABLE ({e})")
try:
    import torch
    print("cuda avail:", torch.cuda.is_available(),
          "| device:", (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"))
except Exception:
    pass

# --- anny package surface ----------------------------------------------------
hdr("ANNY PACKAGE")
try:
    import anny
except Exception as e:
    print("!! cannot import anny:", e); traceback.print_exc(); sys.exit(1)
print("anny.__version__:", getattr(anny, "__version__", "?"))
print("anny.__file__   :", getattr(anny, "__file__", "?"))
print("top-level names :", [n for n in dir(anny) if not n.startswith("_")])

# find the model class (docs say `anny.Anny` post-v0.5; fall back to any capitalized class)
ModelCls = getattr(anny, "Anny", None)
if ModelCls is None:
    for n in dir(anny):
        o = getattr(anny, n)
        if isinstance(o, type) and n[0].isupper():
            ModelCls = o; print("(!) using fallback class:", n); break
if ModelCls is None:
    print("!! no model class found on anny"); sys.exit(1)
print("model class     :", ModelCls.__name__)
try:
    print("__init__ signature:", inspect.signature(ModelCls.__init__))
except Exception as e:
    print("__init__ signature: (unavailable)", e)

# --- instantiate (try the likely forms) --------------------------------------
hdr("INSTANTIATE")
model = None
for label, thunk in [
    ("Anny()",                 lambda: ModelCls()),
    ("Anny(device='cuda')",    lambda: ModelCls(device="cuda")),
    ("Anny(topology='anny')",  lambda: ModelCls(topology="anny")),
]:
    try:
        print(f"trying {label} ...")
        model = thunk(); print(f"  OK -> {type(model)}"); break
    except Exception as e:
        print(f"  failed: {e}")
if model is None:
    print("!! could not instantiate with guessed args — see __init__ signature above."); sys.exit(1)

print("\ninstance public attrs:", [n for n in dir(model) if not n.startswith("_")])
hdr("LIKELY METHODS (signatures)")
for name in ("forward", "__call__", "pose", "set_pose", "repose", "shape", "set_shape",
             "set_phenotype", "phenotype", "get_mesh", "mesh", "vertices", "get_vertices",
             "faces", "get_faces", "skeleton", "joints", "get_joints", "rig", "rigs",
             "topology", "topologies", "to", "eval"):
    sig(model, name)

# --- try to produce a neutral mesh (verts + faces) ---------------------------
hdr("NEUTRAL MESH")
verts = faces = None
def as_np(x):
    try:
        import torch
        if isinstance(x, torch.Tensor): return x.detach().cpu().numpy()
    except Exception: pass
    import numpy as np
    return np.asarray(x)

# 1) forward / __call__ often returns an object or dict with vertices+faces
for label, thunk in [("model()", lambda: model()),
                     ("model.forward()", lambda: model.forward())]:
    try:
        out = thunk(); print(f"{label} -> {type(out)}")
        if isinstance(out, dict):
            print("  dict keys:", list(out.keys()))
            for k in out:
                v = out[k]
                print(f"    {k}: {type(v).__name__} shape={getattr(v,'shape',None)}")
        else:
            print("  attrs:", [n for n in dir(out) if not n.startswith("_")][:40])
        # heuristics to pull verts/faces out of dict or object
        def grab(o, keys):
            for k in keys:
                if isinstance(o, dict) and k in o: return o[k]
                if hasattr(o, k): return getattr(o, k)
            return None
        verts = grab(out, ("vertices", "verts", "v", "posed_vertices"))
        faces = grab(out, ("faces", "f", "triangles", "faces_idx"))
        if verts is not None: break
    except Exception as e:
        print(f"{label} failed: {e}")

# 2) fall back to attribute/method accessors
if verts is None:
    for k in ("vertices", "get_vertices", "v"):
        a = getattr(model, k, None)
        if a is not None:
            verts = a() if callable(a) else a
            if verts is not None: print(f"got vertices via model.{k}"); break
if faces is None:
    for k in ("faces", "get_faces", "topology"):
        a = getattr(model, k, None)
        if a is not None:
            faces = a() if callable(a) else a
            if faces is not None: print(f"got faces via model.{k}"); break

if verts is not None:
    verts = as_np(verts)
    print("vertices shape:", verts.shape, "dtype:", verts.dtype)
if faces is not None:
    faces = as_np(faces)
    print("faces shape:", faces.shape, "dtype:", faces.dtype)

# --- headless render smoke test ----------------------------------------------
hdr("HEADLESS RENDER SMOKE TEST (pyrender/EGL)")
if verts is None or faces is None:
    print("skipped — couldn't extract verts+faces automatically.")
    print(">> Paste the NEUTRAL MESH section above to Claude; the accessor is just named differently.")
else:
    try:
        import os
        # Backend depends on the box: the Linux GPU box is truly headless -> EGL; the Windows dev
        # laptop has a desktop session -> use pyrender's default hidden-window GL (do NOT force egl,
        # which fails on Windows). macOS also uses the default.
        if sys.platform.startswith("linux"):
            os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
        else:
            os.environ.pop("PYOPENGL_PLATFORM", None)
        print("render backend:", os.environ.get("PYOPENGL_PLATFORM", "default (hidden-window GL)"))
        import numpy as np, trimesh, pyrender, imageio
        v = verts.reshape(-1, 3).astype(np.float32)
        f = faces.reshape(-1, 3).astype(np.int64)
        mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
        # center + frame the body
        mesh.vertices -= mesh.vertices.mean(0)
        scale = 1.0 / (np.abs(mesh.vertices).max() + 1e-9)
        mesh.vertices *= scale
        scene = pyrender.Scene(bg_color=[0.05, 0.05, 0.06, 1.0], ambient_light=[0.3, 0.3, 0.3])
        scene.add(pyrender.Mesh.from_trimesh(mesh, smooth=True))
        cam = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
        cpose = np.eye(4); cpose[2, 3] = 2.6
        scene.add(cam, pose=cpose)
        light = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)
        lpose = np.eye(4); lpose[:3, 3] = [1, 2, 2]
        scene.add(light, pose=lpose)
        r = pyrender.OffscreenRenderer(256, 256)
        color, _ = r.render(scene); r.delete()
        imageio.imwrite("probe_render.png", color)
        print("OK -> wrote probe_render.png (256x256).")
        print(">> Does it look like a gray human? (scp it down or serve it). If yes, the render path works.")
    except Exception as e:
        print("render failed:", e); traceback.print_exc()
        print(">> If this is an EGL error: ensure `export PYOPENGL_PLATFORM=egl` and the apt EGL libs installed.")

hdr("DONE — paste EVERYTHING above back to Claude")
