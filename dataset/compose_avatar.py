"""
Compose a dressed Anny avatar from CC0/CC-BY MakeHuman/MPFB2 .mhclo assets
(hair, eyebrows, clothing, ...) fit via mhclo_fit.py.

This is the pipeline step after mhclo_fit.py's proof-of-concept (D81): given a set of
asset paths, fit each onto Anny's basemesh and either (a) render a combined preview, or
(b) write a combined multi-material OBJ ready for blender_render_skin.py-style texturing
and, downstream, the gaussian fit.

Usage:
  python compose_avatar.py --asset hair01_x/hair/culturalibre_hair_02/culturalibre_hair_02.mhclo \
                            --asset eyebrows01_x/.../mindfront_eyebrows_11.mhclo \
                            --asset shirts01_x/.../elvs_crude_t-shirt_male.mhclo \
                            --asset pants01_x/.../cortu_cargo_pants.mhclo \
                            --out composed --render
"""
import argparse, os, sys, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outfit_lib import arms_down_basemesh, arms_down_fit_basemesh, fit_asset_lbs

ap = argparse.ArgumentParser()
ap.add_argument("--asset", action="append", default=[], help="path to a .mhclo file (repeatable)")
ap.add_argument("--out", required=True)
ap.add_argument("--render", action="store_true", help="also render a pyrender preview")
ap.add_argument("--phenotype", default="adult", choices=["adult"], help="reserved for future phenotypes")
ap.add_argument("--max_offset", type=float, default=0.15, help="clip per-vertex mhclo offsets beyond "
                 "this many meters (bounds rare outlier strands/verts; see mhclo_fit.fit_mhclo)")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

# Fit clothing against a RELAXED pose (arms down), not Anny's raw T-pose -- see outfit_lib.py
# (D84) for the full rationale and how the 40deg arms-down angle was calibrated. Shared with
# the live viewer server so the two can't drift apart again.
B, BF = arms_down_basemesh()
B_fit = arms_down_fit_basemesh()   # D89: correct (19158v, index-space-exact) basemesh for fitting
print(f"[compose] Anny basemesh (arms-down pose): {B.shape}, {BF.shape[0]} faces "
      f"(fitting against {B_fit.shape})")

feet_z = float(B_fit[:, 2].min())
parts = [{"name": "body", "verts": B, "faces": BF}]
for path in args.asset:
    try:
        # D96: fit-once-at-neutral then skin to the arms-down pose (LBS), parity with the
        # live viewer's build_compose_buffer -- see outfit_lib.fit_asset_lbs.
        a = fit_asset_lbs(path, feet_z, max_offset=args.max_offset)
    except Exception as e:
        print(f"[compose] SKIP {path}: {e}")
        continue
    parts.append({"name": a["name"], "verts": a["verts"], "faces": a["faces"], "src": path})
    dropped = a["dropped"]
    note = f"  ({dropped} stray below-feet faces dropped)" if dropped else ""
    print(f"[compose] fit {a['name']:30s} {len(a['verts']):6d} verts  {len(a['faces']):6d} faces{note}")

# ---- write a combined multi-object OBJ (each part keeps its own material group) ----
obj_path = os.path.join(args.out, "avatar.obj")
with open(obj_path, "w") as f:
    f.write("# composed via compose_avatar.py (mhclo_fit.py, D81/D82)\n")
    offset = 0
    for p in parts:
        f.write(f"o {p['name']}\n")
        for x, y, z in p["verts"]:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        f.write(f"usemtl {p['name']}\n")
        for a, b, c in p["faces"]:
            f.write(f"f {a+1+offset} {b+1+offset} {c+1+offset}\n")
        offset += len(p["verts"])
print(f"[compose] WROTE {obj_path}  ({len(parts)} parts, {offset} total verts)")

if args.render:
    import trimesh, pyrender, imageio.v2 as imageio
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    PALETTE = {
        "body": ([0.79, 0.66, 0.57, 1], 0.75, 0.0),
        "eyebrows": ([0.10, 0.06, 0.05, 1], 0.9, 0.0),
    }
    def color_for(name):
        low = name.lower()
        if "eyebrow" in low or "eyelash" in low: return [0.10, 0.06, 0.05, 1], 0.9
        if "hair" in low: return [0.18, 0.10, 0.07, 1], 0.55
        if "shirt" in low or "top" in low or "sweater" in low: return [0.22, 0.30, 0.42, 1], 0.65
        if "pant" in low or "jean" in low or "short" in low: return [0.16, 0.16, 0.20, 1], 0.7
        return [0.79, 0.66, 0.57, 1], 0.75

    scene = pyrender.Scene(bg_color=[14, 16, 20, 255], ambient_light=[0.6, 0.6, 0.65])
    for p in parts:
        col, rough = color_for(p["name"])
        mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=col, roughnessFactor=rough, metallicFactor=0)
        tm = trimesh.Trimesh(vertices=p["verts"], faces=p["faces"], process=False)
        scene.add(pyrender.Mesh.from_trimesh(tm, material=mat, smooth=True))

    # Anny's raw forward() output is Z-UP (height runs along Z, not Y -- verified empirically
    # in D81; Y is the shallow front/back depth axis), so the camera must orbit around Z.
    top = B[:, 2].max()
    ctr = np.array([0.0, 0.0, top * 0.42])
    H = top - B[:, 2].min()
    campos = ctr + np.array([0, -2.3 * H, 0.05 * H])
    fdir = ctr - campos; fdir /= np.linalg.norm(fdir)
    up = np.array([0., 0, 1.]); s = np.cross(fdir, up); s /= np.linalg.norm(s); u = np.cross(s, fdir)
    pose = np.eye(4); pose[:3, 0] = s; pose[:3, 1] = u; pose[:3, 2] = -fdir; pose[:3, 3] = campos
    scene.add(pyrender.PerspectiveCamera(yfov=0.5), pose=pose)
    scene.add(pyrender.DirectionalLight(color=[1, 1, 1], intensity=3.4), pose=pose)
    scene.add(pyrender.DirectionalLight(color=[0.6, 0.7, 1.0], intensity=1.1), pose=np.eye(4))
    r = pyrender.OffscreenRenderer(480, 480)
    img, _ = r.render(scene)
    r.delete()
    out_png = os.path.join(args.out, "composed.png")
    imageio.imwrite(out_png, img)
    print(f"[compose] WROTE {out_png}")
