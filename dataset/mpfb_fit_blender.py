"""MPFB2-fit the WHOLE clothing+hair catalog, named by asset dirname, at subdiv 1 and 2.
Exports basemesh + per-asset (world verts + faces) npy into mpfb_out/.
Run: /root/blender/blender -b -P mpfb_fit_blender.py   (MPFB2 must be enabled in this Blender)
"""
import importlib, sys, bpy, numpy as np, os, glob

OUT = "/root/4dgs/dataset/motion_out/mpfb_out"   # durable, gitignored (read by mpfb_prefit)
os.makedirs(OUT, exist_ok=True)
SRC = "/root/4dgs/dataset/motion_out/assets_src"
SUBDIV = [1, 2]

# (asset_type, glob) -> discover every mhclo
JOBS = []
for sub, atype in [("clothing/tops", "Clothes"), ("clothing/bottoms", "Clothes"), ("hair", "Hair")]:
    for mh in sorted(glob.glob(f"{SRC}/{sub}/*/*.mhclo")):
        name = os.path.basename(os.path.dirname(mh))       # asset dirname == catalog name
        JOBS.append((name, mh, atype))


def dynamic_import(pkg, key):
    for amod in sys.modules:
        if amod.endswith(pkg):
            return getattr(importlib.import_module(amod), key)
    raise ValueError(pkg)


HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")


def fresh():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    return HumanService.create_human()


def geo(obj, dg):
    ev = obj.evaluated_get(dg); me = ev.to_mesh(); mw = obj.matrix_world
    V = np.array([list(mw @ v.co) for v in me.vertices], np.float64)
    F = []
    for p in me.polygons:
        idx = list(p.vertices)
        for k in range(1, len(idx) - 1):
            F.append((idx[0], idx[k], idx[k + 1]))
    ev.to_mesh_clear()
    return V, np.array(F, np.int64)


base = fresh()
Vb = np.array([list(base.matrix_world @ v.co) for v in base.data.vertices], np.float64)
np.save(f"{OUT}/basemesh_verts.npy", Vb)
print(f"[mpfb] base {Vb.shape}")

for name, path, atype in JOBS:
    for sd in SUBDIV:
        if os.path.exists(f"{OUT}/{name}_sd{sd}_verts.npy"):
            continue
        base = fresh()
        try:
            asset = HumanService.add_mhclo_asset(path, base, asset_type=atype,
                                                 subdiv_levels=sd, material_type="NONE")
            for mod in asset.modifiers:
                if mod.type == 'SUBSURF':
                    mod.levels = sd; mod.render_levels = sd
            dg = bpy.context.evaluated_depsgraph_get()
            V, F = geo(asset, dg)
            np.save(f"{OUT}/{name}_sd{sd}_verts.npy", V)
            np.save(f"{OUT}/{name}_sd{sd}_faces.npy", F)
            print(f"[mpfb] {name:34s} sd={sd} {len(V):6d}v {len(F):6d}f")
        except Exception as e:
            print(f"[mpfb] FAIL {name} sd={sd}: {e}")
print("[mpfb] DONE")
