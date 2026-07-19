#!/usr/bin/env python3
"""
03_render_motion.py — the 4D increment: drive Anny's bones over time (a walk cycle) and render the
MOVING body multi-view. Proves pose -> animate -> multi-cam. Also exports the posed vertex sequence
so the animation can be played live in Blender.

Anny 'local-bone' pose = a (1,163,4,4) tensor of per-bone LOCAL transforms (rest = identity). To swing
a limb anatomically we rotate each bone about the WORLD lateral axis (X) expressed in that bone's rest
frame: local_axis = R_rest_world^T @ [1,0,0]  (the poc_splat_smooth trick).

    conda run -n 4dgs-data python 03_render_motion.py --frames 24 --res 256

Outputs (motion_out/): walk_strip.png (cycle from one camera), multiview.png (one frame, 8 cams),
verts_seq.npy + faces.npy (for Blender playback).
"""
import argparse, os, sys, math, numpy as np, torch, trimesh, pyrender, imageio, anny

# bone indices from probe_pose.py
B = dict(ul_L=2, ul_R=22, ll_L=4, ll_R=24, ua_L=50, ua_R=76, la_L=52, la_R=78)

def pick_backend():
    if sys.platform.startswith("linux"):
        os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    else:
        os.environ.pop("PYOPENGL_PLATFORM", None)

def look_at(eye, target, up):
    eye, target, up = map(lambda v: np.asarray(v, np.float64), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f) + 1e-12
    s = np.cross(f, up); s /= np.linalg.norm(s) + 1e-12
    u = np.cross(s, f)
    m = np.eye(4); m[:3, 0] = s; m[:3, 1] = u; m[:3, 2] = -f; m[:3, 3] = eye
    return m

def rodrigues(axis, ang):
    a = np.asarray(axis, np.float64); a = a / (np.linalg.norm(a) + 1e-9)
    x, y, z = a; c, s = math.cos(ang), math.sin(ang); C = 1 - c
    return np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s],
                     [y*x*C+z*s, c+y*y*C, y*z*C-x*s],
                     [z*x*C-y*s, z*y*C+x*s, c+z*z*C]], np.float64)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--res", type=int, default=256)
    ap.add_argument("--out", default="motion_out")
    args = ap.parse_args()
    pick_backend()
    os.makedirs(args.out, exist_ok=True)
    print("render backend:", os.environ.get("PYOPENGL_PLATFORM", "default (hidden-window GL)"))

    model = anny.Anny(); model.eval()
    with torch.no_grad():
        out = model()
    rest_verts = out["vertices"][0].detach().cpu().numpy().astype(np.float32)
    tri = model.get_triangular_faces()
    tri = (tri.detach().cpu().numpy() if hasattr(tri, "detach") else np.asarray(tri)).reshape(-1, 3).astype(np.int64)
    rest_pose = model.get_pose_parameterization(out, "local-bone").detach().clone()   # (1,163,4,4)
    rest_world = out["rest_bone_poses"][0].detach().cpu().numpy()                       # (163,4,4)

    worldX = np.array([1.0, 0.0, 0.0])
    swing_axis = {b: (rest_world[b, :3, :3].T @ worldX) for b in B.values()}

    def walk_pose(phase):
        p = rest_pose.clone()
        def setb(b, ang):
            R = torch.tensor(rodrigues(swing_axis[b], ang), dtype=p.dtype)
            p[0, b, :3, :3] = R
        LEG, KNEE, ARM = 0.5, 0.8, 0.4
        setb(B["ul_R"], LEG*math.sin(phase));            setb(B["ul_L"], LEG*math.sin(phase+math.pi))
        setb(B["ll_R"], -KNEE*max(0, math.sin(phase)));  setb(B["ll_L"], -KNEE*max(0, math.sin(phase+math.pi)))
        setb(B["ua_R"], ARM*math.sin(phase+math.pi));    setb(B["ua_L"], ARM*math.sin(phase))
        setb(B["la_R"], -0.3*max(0, math.sin(phase+math.pi))); setb(B["la_L"], -0.3*max(0, math.sin(phase)))
        return p

    # posed vertex sequence
    T = args.frames
    V = rest_verts.shape[0]
    seq = np.zeros((T, V, 3), np.float32)
    for f in range(T):
        with torch.no_grad():
            o = model(pose_parameters=walk_pose(2*math.pi*f/T), pose_parameterization="local-bone")
        seq[f] = o["vertices"][0].detach().cpu().numpy()
    print(f"posed {T} frames, {V} verts, {tri.shape[0]} tris")

    # framing from rest pose (stable across the cycle)
    c = rest_verts.mean(0); ext = rest_verts.max(0) - rest_verts.min(0)
    up_i = int(np.argmax(ext)); horiz = [i for i in range(3) if i != up_i]
    up = np.zeros(3); up[up_i] = 1.0; height = float(ext[up_i]); radius = 1.7 * height

    def cam_pose(theta, elev=0.12):
        eye = c.astype(np.float64).copy()
        eye[horiz[0]] += radius*math.cos(theta); eye[horiz[1]] += radius*math.sin(theta)
        eye[up_i] += elev*height
        return look_at(eye, c, up)

    scene_cam = pyrender.PerspectiveCamera(yfov=np.pi/4.0)
    key = pyrender.DirectionalLight(color=np.ones(3), intensity=4.0)
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80, 0.66, 0.58, 1.0],
                                             metallicFactor=0.0, roughnessFactor=0.8)
    r = pyrender.OffscreenRenderer(args.res, args.res)

    def render(verts, cpose):
        sc = pyrender.Scene(bg_color=[0.05, 0.05, 0.06, 1.0], ambient_light=[0.35, 0.35, 0.38])
        m = trimesh.Trimesh(vertices=verts, faces=tri, process=False)
        sc.add(pyrender.Mesh.from_trimesh(m, material=mat, smooth=True))
        sc.add(scene_cam, pose=cpose); sc.add(key, pose=cpose)
        col, _ = r.render(sc)
        return col[..., :3]

    # (1) walk strip: side-favouring 3/4 camera, K sampled frames across the cycle
    strip_cam = cam_pose(0.6)
    K = min(8, T); idxs = np.linspace(0, T-1, K).round().astype(int)
    strip = np.concatenate([render(seq[i], strip_cam) for i in idxs], axis=1)
    imageio.imwrite(os.path.join(args.out, "walk_strip.png"), strip)

    # (2) multiview of a mid-stride frame from 8 ring cameras
    midf = int(round(T*0.25))
    tiles = [render(seq[midf], cam_pose(2*math.pi*k/8)) for k in range(8)]
    Rr = args.res; grid = np.full((2*Rr, 4*Rr, 3), 12, np.uint8)
    for i, t in enumerate(tiles):
        rr, cc = divmod(i, 4); grid[rr*Rr:(rr+1)*Rr, cc*Rr:(cc+1)*Rr] = t
    imageio.imwrite(os.path.join(args.out, "multiview.png"), grid)
    r.delete()

    # (3) export the posed vertex sequence for Blender playback
    np.save(os.path.join(args.out, "verts_seq.npy"), seq)
    np.save(os.path.join(args.out, "faces.npy"), tri)
    print("WROTE walk_strip.png, multiview.png, verts_seq.npy, faces.npy in", args.out)

if __name__ == "__main__":
    main()
