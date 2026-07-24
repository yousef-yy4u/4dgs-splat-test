#!/usr/bin/env python3
"""Export the Anny body as a browser-ready textured GLB (real PBR skin, no splats).

This is the "try textured meshes BEFORE committing to gaussian splats" path. It takes the
same real MakeHuman-UV PBR skin that `blender_render_skin.py --skin_*` feeds to Cycles and
packs it into a standard glTF 2.0 asset that three.js can render directly:

  * skin  -> baseColorTexture (sRGB) + normalTexture + metallicRoughnessTexture
             (the SMOKEWORKS ORM map is already G=roughness / B=metallic packed, which is
             exactly glTF's convention, so it drops in with no channel surgery)
             metallicFactor forced to 0 (matte skin -- same call as the D41 textured GLBs).
  * eyes  -> split into their own primitive with the D81 gaze-ramp iris baked to VERTEX
             COLORS (the Cycles eye shader is procedural and can't survive glTF), plus a
             low roughness so the cornea stays wet-looking.

    python export_skin_glb.py --obj motion_out/_refit96/anny_adult.obj \
        --skin_basecolor <...BaseColor...png> --skin_normal <...Normal...png> \
        --skin_orm <...ORM...png> --texres 2048 --out motion_out/skin_test.glb
"""
import argparse, os, numpy as np, trimesh
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--obj", required=True, help="anny_adult.obj (UVs + skin/eye material groups)")
ap.add_argument("--skin_basecolor", required=True)
ap.add_argument("--skin_normal", default=None)
ap.add_argument("--skin_orm", default=None, help="occlusion/roughness/metallic (G=roughness)")
ap.add_argument("--texres", type=int, default=2048, help="square texture edge shipped in the GLB")
ap.add_argument("--out", required=True)
args = ap.parse_args()

# Anny's OBJ is already Y-up with feet on the ground (see export_textured_obj.py), which is
# three.js's frame -- nothing to rotate here. Gaze/face-forward in that frame is +Z.
GAZE = np.array([0.0, 0.0, 1.0], np.float32)

# D81's sclera->limbal ring->iris->pupil ramp, as (dot-product stop, linear RGB) control points.
# The sclera is brighter/cooler here than in D81: that ramp was tuned so eyes don't read as bright
# specks at FULL-BODY distance, but at face close-up its 0.42 grey goes gold under a warm key light.
EYE_RAMP = [(0.00, (0.76, 0.75, 0.74)), (0.62, (0.74, 0.73, 0.73)), (0.70, (0.06, 0.05, 0.04)),
            (0.80, (0.26, 0.16, 0.08)), (0.92, (0.38, 0.24, 0.12)), (0.966, (0.20, 0.12, 0.06)),
            (0.983, (0.01, 0.01, 0.01)), (1.00, (0.01, 0.01, 0.01))]


def load_tex(path, res, srgb):
    im = Image.open(path).convert("RGB")
    if max(im.size) != res:
        im = im.resize((res, res), Image.LANCZOS)
    return im


def iris_texture(res=512):
    """Rasterise the D81 gaze ramp into a flat iris disc.

    The Cycles eye shader evaluates the ramp per PIXEL from the surface normal. Each Anny
    eyeball is only ~80 vertices, so baking the same ramp to vertex colours smears the pupil
    across the whole eye. Rasterising it into a texture and giving the eyeballs a gaze-aligned
    planar UV reproduces the shader properly at any poly count.
    """
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    rho = np.sqrt(((xx + 0.5) / res * 2 - 1) ** 2 + ((yy + 0.5) / res * 2 - 1) ** 2)
    # UV radius rho == sin(angle from gaze); the ramp is keyed on cos(angle) = dot(n, gaze).
    fac = np.sqrt(np.clip(1.0 - np.clip(rho, 0, 1) ** 2, 0, 1))
    stops = np.array([s for s, _ in EYE_RAMP], np.float32)
    cols = np.array([c for _, c in EYE_RAMP], np.float32)
    rgb = np.stack([np.interp(fac, stops, cols[:, i]) for i in range(3)], -1)
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 1e-8, 1), 1/2.4) - 0.055)
    return Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8), "RGB")


def eye_uv(verts):
    """Gaze-aligned planar UVs for the eyeballs, per eye (each eyeball gets its own centre)."""
    uv = np.zeros((len(verts), 2), np.float32)
    side = verts[:, 0] >= verts[:, 0].mean()          # split L/R eyeball by x
    for m in (side, ~side):
        if not m.any():
            continue
        c = verts[m].mean(0)
        d = verts[m] - c
        perp = d - np.outer(d @ GAZE, GAZE)           # drop the gaze component
        r = np.abs(perp).max() if np.abs(perp).max() > 0 else 1.0
        uv[m, 0] = 0.5 + perp[:, 0] / (2 * r)
        uv[m, 1] = 0.5 + perp[:, 1] / (2 * r)
    return np.clip(uv, 0.0, 1.0)


scene_in = trimesh.load(args.obj, process=False, group_material=True)
parts = scene_in.geometry if isinstance(scene_in, trimesh.Scene) else {"skin": scene_in}
# trimesh names the split geometries after the FILE, not the `usemtl` group, so recover the
# skin/eye split from the OBJ itself: the eye group is whichever part is far smaller.
order = sorted(parts, key=lambda k: len(parts[k].faces))
eye_key = order[0] if len(parts) > 1 else None
print(f"[glb] loaded {args.obj}: {len(parts)} material group(s); eye group = {eye_key}")

base = load_tex(args.skin_basecolor, args.texres, srgb=True)
norm = load_tex(args.skin_normal, args.texres, srgb=False) if args.skin_normal else None
orm = load_tex(args.skin_orm, args.texres, srgb=False) if args.skin_orm else None

out = trimesh.Scene()
for name, geo in parts.items():
    is_eye = (name == eye_key)
    g = geo.copy()
    if is_eye:
        mat = trimesh.visual.material.PBRMaterial(
            name="eye", baseColorTexture=iris_texture(), metallicFactor=0.0, roughnessFactor=0.10)
        g.visual = trimesh.visual.TextureVisuals(uv=eye_uv(np.asarray(g.vertices)), material=mat)
    else:
        mat = trimesh.visual.material.PBRMaterial(
            name="skin", baseColorTexture=base, normalTexture=norm, metallicRoughnessTexture=orm,
            metallicFactor=0.0, roughnessFactor=1.0 if orm else 0.55)
        uv = geo.visual.uv if getattr(geo.visual, "uv", None) is not None else None
        g.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
        if uv is None:
            print("[glb] WARN: no UVs on the skin group -- textures will not map")
    # trimesh only writes a glTF NORMAL accessor when the mesh already has cached vertex
    # normals -- without it three.js lights the whole body black (no normals => no shading).
    _ = g.vertex_normals
    out.add_geometry(g, geom_name=name)
    print(f"[glb]   {name}: {len(g.vertices)} v / {len(g.faces)} f  eye={is_eye}  normals={len(g.vertex_normals)}")

os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
out.export(args.out, include_normals=True)
print(f"[glb] WROTE {args.out}  ({os.path.getsize(args.out)/1e6:.1f} MB, textures @ {args.texres}px)")
