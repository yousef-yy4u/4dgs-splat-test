#!/usr/bin/env python3
"""
02_render_slice.py — the first REAL render harness increment.

Renders one neutral Anny body from N cameras arranged in a ring around it, writes each view as a
PNG, and assembles a contact-sheet grid so you can eyeball all angles at once. Also introspects the
POSE parameterization (printed at the end) so the next step can drive motion (the 4D part).

Uses Anny's REAL API discovered by 01_probe_anny.py:
  - model() -> dict with 'vertices' [1,V,3] and 'bone_poses' [1,B,4,4]
  - model.get_triangular_faces() -> triangles (model.faces are QUADS -> must triangulate)

    conda run -n 4dgs-data python 02_render_slice.py --cams 8 --res 320

Output: slice_out/view_XX.png + slice_out/contact_sheet.png
"""
import argparse, os, sys, math

def pick_backend():
    # Linux GPU box is headless -> EGL; Windows/mac dev box has a desktop -> default hidden-window GL.
    if sys.platform.startswith("linux"):
        os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    else:
        os.environ.pop("PYOPENGL_PLATFORM", None)

def look_at(eye, target, up):
    """4x4 camera-to-world pose for pyrender (camera looks down its -Z)."""
    import numpy as np
    eye, target, up = map(lambda v: np.asarray(v, np.float64), (eye, target, up))
    f = target - eye; f /= (np.linalg.norm(f) + 1e-12)      # forward (-Z is toward target)
    s = np.cross(f, up); s /= (np.linalg.norm(s) + 1e-12)   # right (+X)
    u = np.cross(s, f)                                       # true up (+Y)
    m = np.eye(4)
    m[:3, 0] = s; m[:3, 1] = u; m[:3, 2] = -f; m[:3, 3] = eye
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", type=int, default=8)
    ap.add_argument("--res", type=int, default=320)
    ap.add_argument("--out", default="slice_out")
    args = ap.parse_args()

    pick_backend()
    import numpy as np, torch, trimesh, pyrender, imageio, anny
    print("render backend:", os.environ.get("PYOPENGL_PLATFORM", "default (hidden-window GL)"))
    os.makedirs(args.out, exist_ok=True)

    # --- build a neutral Anny body -------------------------------------------------
    model = anny.Anny()
    model.eval()
    with torch.no_grad():
        out = model()
    verts = out["vertices"][0].detach().cpu().numpy().astype(np.float32)   # [V,3]
    tri = model.get_triangular_faces()
    tri = (tri.detach().cpu().numpy() if hasattr(tri, "detach") else np.asarray(tri))
    tri = tri.reshape(-1, 3).astype(np.int64)                              # [F,3] proper triangles
    print(f"mesh: {verts.shape[0]} verts, {tri.shape[0]} triangles")

    mesh_t = trimesh.Trimesh(vertices=verts, faces=tri, process=False)

    # --- frame the body: centroid + up-axis = axis of largest extent (robust to Y/Z-up) ---
    c = verts.mean(0)
    ext = verts.max(0) - verts.min(0)
    up_i = int(np.argmax(ext))                      # tallest axis = up (standing human)
    horiz = [i for i in range(3) if i != up_i]
    up = np.zeros(3); up[up_i] = 1.0
    height = float(ext[up_i]); radius = 1.6 * height
    print(f"up-axis={up_i} height={height:.3f} cam-radius={radius:.3f}")

    # --- scene + lights ------------------------------------------------------------
    scene = pyrender.Scene(bg_color=[0.05, 0.05, 0.06, 1.0], ambient_light=[0.35, 0.35, 0.38])
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.72, 0.73, 0.78, 1.0],
                                             metallicFactor=0.0, roughnessFactor=0.85)
    scene.add(pyrender.Mesh.from_trimesh(mesh_t, material=mat, smooth=True))
    cam = pyrender.PerspectiveCamera(yfov=np.pi / 4.0)
    key = pyrender.DirectionalLight(color=np.ones(3), intensity=4.0)

    renderer = pyrender.OffscreenRenderer(args.res, args.res)
    tiles = []
    for i in range(args.cams):
        theta = 2 * math.pi * i / args.cams
        eye = c.astype(np.float64).copy()
        eye[horiz[0]] += radius * math.cos(theta)
        eye[horiz[1]] += radius * math.sin(theta)
        eye[up_i]     += 0.10 * height              # slight above-center framing
        pose = look_at(eye, c, up)
        cn = scene.add(cam, pose=pose)
        ln = scene.add(key, pose=pose)              # light rides with the camera
        color, _ = renderer.render(scene)
        scene.remove_node(cn); scene.remove_node(ln)
        imageio.imwrite(os.path.join(args.out, f"view_{i:02d}.png"), color)
        tiles.append(color)
    renderer.delete()

    # --- contact sheet -------------------------------------------------------------
    cols = min(4, args.cams); rows = math.ceil(args.cams / cols)
    R = args.res
    sheet = np.full((rows * R, cols * R, 3), 12, np.uint8)
    for i, t in enumerate(tiles):
        r, cc = divmod(i, cols)
        sheet[r*R:(r+1)*R, cc*R:(cc+1)*R] = t[..., :3]
    sheet_path = os.path.join(args.out, "contact_sheet.png")
    imageio.imwrite(sheet_path, sheet)
    print(f"WROTE {sheet_path}  ({rows}x{cols} grid of {args.cams} views)")

    # --- introspect the POSE API (so the next step can drive motion) ---------------
    print("\n" + "=" * 60 + "\n POSE PARAMETERIZATION (for the 4D/motion step)\n" + "=" * 60)
    pp = getattr(model, "pose_parameterization", None)
    print("model.pose_parameterization:", type(pp).__name__, "->", repr(pp)[:400])
    for name in ("get_pose_parameterization", "bone_labels", "phenotype_labels", "bone_parents"):
        a = getattr(model, name, None)
        if a is None: continue
        try:
            v = a() if callable(a) else a
        except Exception as e:
            v = f"(err {e})"
        s = repr(v)
        print(f"model.{name}:", s[:300] + (" ..." if len(s) > 300 else ""))
    print("\nDONE — view slice_out/contact_sheet.png; paste this output back to Claude.")

if __name__ == "__main__":
    main()
