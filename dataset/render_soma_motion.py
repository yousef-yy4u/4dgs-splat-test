#!/usr/bin/env python3
"""Render a Kimodo NPZ motion through SOMALayer(anny) -> posed Anny(SOMA-topology) vertices ->
pyrender (EGL headless) -> a tracking-camera walk.gif + an 8-camera multiview.png of a mid-stride frame.

    PYOPENGL_PLATFORM=egl python render_soma_motion.py kimodo_out/walk.npz --out motion_out --stem walk

Feeds Kimodo's LOCAL (parent-relative) rotation matrices with pose2rot=False, absolute_pose=False, and
root_positions as transl -- SOMALayer's OFFICIAL SOMA->Anny retarget (no hand-rolled kernel).
"""
import os, sys, argparse, math, numpy as np, torch
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

ap = argparse.ArgumentParser()
ap.add_argument("npz")
ap.add_argument("--out", default="motion_out")
ap.add_argument("--stem", default="walk")
ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--size", type=int, default=480)
ap.add_argument("--up", type=int, default=-1, help="up axis 0/1/2; -1 = auto (largest sequence extent)")
ap.add_argument("--identity", default="adult",
                help="'adult' (neutral ~1.64m), 'baby' (zeros), or 11 comma floats "
                     "[gender,age,muscle,weight,height,proportions,cup,firm,afr,asn,cau]")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

# --- SHIM: soma 0.1.0 passes local_changes=None into anny 0.5; its try/except catches only KeyError,
#     not the TypeError from subscripting None. Coerce None -> {}.
from soma import SOMALayer
import anny.models.phenotype as _ph
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(_orig):
            def _p(self, *a, local_changes=None, **k):
                return _orig(self, *a, local_changes=(local_changes or {}), **k)
            return _p
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

# --- load Kimodo NPZ ----------------------------------------------------------
d = np.load(args.npz)
print("NPZ keys:", list(d.keys()))
local = d["local_rot_mats"].astype(np.float32)    # [T, J, 3, 3]  parent-relative
root  = d["root_positions"].astype(np.float32)    # [T, 3]
T, J = local.shape[0], local.shape[1]
print(f"frames T={T}  joints J={J}  root span={root.max(0)-root.min(0)}")

# --- SOMALayer(anny) ----------------------------------------------------------
layer = SOMALayer(identity_model_type="anny", device=args.device); layer.eval()
# identity = [gender, age, muscle, weight, height, proportions, cup, firm, afr, asn, cau], each in [0,1].
# zeros -> age=0 = INFANT (the "alien baby"); 0.5 age -> ~25yr adult (~1.64m).
if args.identity == "adult":
    idv = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.34, 0.33, 0.33]
elif args.identity == "baby":
    idv = [0.0]*11
else:
    idv = [float(x) for x in args.identity.split(",")]; assert len(idv) == 11
identity = torch.tensor([idv], dtype=torch.float32, device=args.device)
print("identity (adult neutral):", idv)
faces = layer.faces
faces_np = (faces.detach().cpu().numpy() if hasattr(faces, "detach") else np.asarray(faces))
tri = faces_np.reshape(-1, faces_np.shape[-1]).astype(np.int64)
if tri.shape[1] == 4:
    tri = np.concatenate([tri[:, [0,1,2]], tri[:, [0,2,3]]], axis=0)

verts_seq = np.empty((T, 0, 3), dtype=np.float32)
frames = []
with torch.no_grad():
    for t in range(T):
        poses = torch.from_numpy(local[t]).to(args.device).unsqueeze(0)       # (1,J,3,3)
        transl = torch.from_numpy(root[t]).to(args.device).unsqueeze(0)       # (1,3)
        out = layer(poses, identity, transl=transl, pose2rot=False, absolute_pose=False)
        v = out["vertices"][0].detach().cpu().numpy()
        if verts_seq.shape[1] == 0:
            verts_seq = np.empty((T, v.shape[0], 3), dtype=np.float32)
        verts_seq[t] = v
print("vertices sequence:", verts_seq.shape)
np.save(os.path.join(args.out, f"{args.stem}_verts.npy"), verts_seq)

# --- up axis from PER-FRAME body height (isolates standing height from forward travel) ----
perframe_ext = (verts_seq.max(1) - verts_seq.min(1)).mean(0)   # (3,) avg body bbox per frame
seq_ext = verts_seq.reshape(-1, 3).max(0) - verts_seq.reshape(-1, 3).min(0)
up_i = args.up if args.up >= 0 else int(np.argmax(perframe_ext))
horiz = [i for i in range(3) if i != up_i]
# forward = the horizontal axis the root travels most along (biggest sequence extent)
horiz = sorted(horiz, key=lambda i: seq_ext[i], reverse=True)   # horiz[0]=forward, horiz[1]=lateral
print(f"per-frame body bbox={perframe_ext}  seq extent={seq_ext}  -> up={up_i} forward={horiz[0]} lateral={horiz[1]}")
H = float(perframe_ext[up_i])   # ~body height in scene units

import trimesh, pyrender, imageio
mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80,0.66,0.58,1.0],
                                         metallicFactor=0.0, roughnessFactor=0.75)

def look_at(eye, center, up):
    f = (center - eye); f /= (np.linalg.norm(f) + 1e-9)
    s = np.cross(f, up); s /= (np.linalg.norm(s) + 1e-9)
    u = np.cross(s, f)
    m = np.eye(4); m[:3,0]=s; m[:3,1]=u; m[:3,2]=-f; m[:3,3]=eye
    return m

up = np.zeros(3); up[up_i] = 1.0

def render_view(verts, cam_center, azim_deg, size, dist_mult=2.6, elev=0.15):
    """azim orbits in the forward/lateral ground plane; camera at dist_mult*H from cam_center."""
    m = trimesh.Trimesh(vertices=verts.astype(np.float32), faces=tri, process=False)
    sc = pyrender.Scene(bg_color=[0.05,0.05,0.06,1.0], ambient_light=[0.35,0.35,0.38])
    sc.add(pyrender.Mesh.from_trimesh(m, material=mat, smooth=True))
    a = math.radians(azim_deg)
    eye = cam_center.astype(np.float64).copy()
    eye[horiz[0]] += dist_mult*H*math.cos(a)   # forward axis
    eye[horiz[1]] += dist_mult*H*math.sin(a)   # lateral axis
    eye[up_i]     += elev*H
    pose = look_at(eye, cam_center.astype(np.float64), up)
    sc.add(pyrender.PerspectiveCamera(yfov=np.pi/4.5), pose=pose)
    # camera-attached headlight (valid pose) + a fill from a offset camera pose
    sc.add(pyrender.DirectionalLight(color=np.ones(3), intensity=4.2), pose=pose)
    fill_eye = cam_center.astype(np.float64).copy()
    fill_eye[horiz[0]] -= dist_mult*H*math.cos(a); fill_eye[horiz[1]] -= dist_mult*H*math.sin(a)
    fill_eye[up_i] += 0.6*H
    sc.add(pyrender.DirectionalLight(color=np.ones(3), intensity=1.8),
           pose=look_at(fill_eye, cam_center.astype(np.float64), up))
    r = pyrender.OffscreenRenderer(size, size); col, _ = r.render(sc); r.delete()
    return col

# --- walk.gif: tracking 3/4 side camera, recompute center per frame -----------
gif = []
for t in range(T):
    c = verts_seq[t].mean(0)
    gif.append(render_view(verts_seq[t], c, azim_deg=35.0, size=args.size))
gif_path = os.path.join(args.out, f"{args.stem}.gif")
imageio.mimsave(gif_path, gif, fps=args.fps, loop=0)
print("WROTE", gif_path, f"({T} frames @ {args.fps}fps)")

# --- multiview.png: one mid-stride frame from 8 synced cameras ----------------
mt = T // 2
c = verts_seq[mt].mean(0)
tiles = [render_view(verts_seq[mt], c, azim_deg=az, size=args.size//2) for az in range(0, 360, 45)]
row1 = np.concatenate(tiles[:4], axis=1); row2 = np.concatenate(tiles[4:], axis=1)
grid = np.concatenate([row1, row2], axis=0)
mv_path = os.path.join(args.out, f"{args.stem}_multiview.png")
imageio.imwrite(mv_path, grid)
print("WROTE", mv_path, "(8 cams, mid-stride frame)")
