"""
Side-by-side detail comparison: the FROZEN mesh-anchored avatar (poc_avatar.ply) vs a
FREE-optimized densified fit (poc_avatar_hidetail.ply), rendered from IDENTICAL cameras via
gsplat's own reference rasterizer (independent of the WebGL viewer).

Renders a full-body view + a face close-up + a hand close-up for each ply, montaged
LEFT=frozen | RIGHT=free, and prints gaussian counts + anisotropy for each.

  python compare_hidetail.py --mv <dir/transforms.json> --frozen motion_out/poc_avatar.ply \
      --free motion_out/poc_avatar_hidetail.ply --out motion_out/hidetail_compare.png
"""
import argparse, json, os, math, numpy as np, torch
import imageio.v2 as imageio
from gsplat import rasterization
from plyfile import PlyData

ap = argparse.ArgumentParser()
ap.add_argument("--mv", required=True, help="dir with transforms.json (for camera intrinsics)")
ap.add_argument("--frozen", required=True)
ap.add_argument("--free", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--size", type=int, default=640, help="render size for the comparison")
args = ap.parse_args()
dev = "cuda"

meta = json.load(open(os.path.join(args.mv, "transforms.json")))
lens, sensor = meta["lens_mm"], meta["sensor_width_mm"]
flip = torch.diag(torch.tensor([1., -1., -1., 1.]))

def load_ply(path):
    v = PlyData.read(path)["vertex"]
    P = v.count
    xyz = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float32)
    f_dc = np.stack([v[f"f_dc_{i}"] for i in range(3)], 1).astype(np.float32)
    rest_names = sorted([p.name for p in v.properties if p.name.startswith("f_rest_")],
                        key=lambda s: int(s.split("_")[-1]))
    if rest_names:
        f_rest = np.stack([v[n] for n in rest_names], 1).astype(np.float32)
        Kc = (f_rest.shape[1]//3)+1
        f_rest = f_rest.reshape(P, 3, Kc-1).transpose(0, 2, 1)     # (P,Kc-1,3)
    else:
        Kc = 1; f_rest = np.zeros((P, 0, 3), np.float32)
    sh = np.concatenate([f_dc[:, None, :], f_rest], 1)             # (P,Kc,3)
    op = v["opacity"].astype(np.float32)
    sc = np.stack([v[f"scale_{i}"] for i in range(3)], 1).astype(np.float32)
    rot = np.stack([v[f"rot_{i}"] for i in range(4)], 1).astype(np.float32)
    deg = int(round(math.sqrt(Kc)))-1
    t = lambda a: torch.tensor(a, device=dev)
    aniso = np.exp(sc); aniso = (aniso.max(1)/np.clip(aniso.min(1), 1e-9, None))
    return dict(means=t(xyz), sh=t(sh), op=t(op), sc=t(sc), rot=t(rot), deg=deg, P=P,
                aniso_med=float(np.median(aniso)))

def cam_lookat(eye, target, up=(0, 0, 1)):
    eye = np.asarray(eye, np.float32); target = np.asarray(target, np.float32)
    f = target-eye; f /= np.linalg.norm(f)
    up = np.asarray(up, np.float32)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    # OpenCV c2w: x=right, y=down, z=forward
    R = np.stack([r, -u, f], 1)
    c2w = np.eye(4, dtype=np.float32); c2w[:3, :3] = R; c2w[:3, 3] = eye
    return torch.tensor(np.linalg.inv(c2w), device=dev)

def render(g, viewmat, W, Hc, K, bg=0.04):
    out, alpha, _ = rasterization(
        g["means"], torch.nn.functional.normalize(g["rot"], dim=-1), torch.exp(g["sc"]),
        torch.sigmoid(g["op"]), g["sh"], viewmat[None], K[None], W, Hc,
        sh_degree=g["deg"], render_mode="RGB")            # composite over bg via alpha
    rgb = out[0] + bg*(1.0 - alpha[0])
    return (rgb.clamp(0, 1).cpu().numpy()*255).astype(np.uint8)

frozen = load_ply(args.frozen)
free = load_ply(args.free)
print(f"[cmp] frozen P={frozen['P']}  aniso_med={frozen['aniso_med']:.2f}")
print(f"[cmp] free   P={free['P']}  aniso_med={free['aniso_med']:.2f}")

# body centroid / height from the frozen model (both share the world frame)
m = frozen["means"].cpu().numpy()
c = m.mean(0)
zc = m[:, 2]
zmin, zmax = zc.min(), zc.max(); Hb = zmax-zmin
head_z = zmin + 0.90*Hb
# data-driven RIGHT-HAND target: the +X extreme point (arms are out in the A-pose)
hand = m[np.argmax(m[:, 0])]
# face front is world -Y (per blender_render_skin convention: front faces -Y)
shots = [
    ("full",  [c[0], c[1]-2.6, zmin+0.55*Hb], [c[0], c[1], zmin+0.52*Hb], 50),
    ("face",  [c[0], c[1]-0.55, head_z+0.02], [c[0], c[1], head_z], 60),
    ("hand",  [hand[0]+0.06, hand[1]-0.30, hand[2]+0.04], [hand[0]-0.02, hand[1], hand[2]], 65),
]
S = args.size
rows = []
for tag, eye, tgt, flen in shots:
    fx = flen/sensor*S
    K = torch.tensor([[fx, 0, S/2], [0, fx, S/2], [0, 0, 1]], dtype=torch.float32, device=dev)
    vm = cam_lookat(eye, tgt)
    a = render(frozen, vm, S, S, K); b = render(free, vm, S, S, K)
    # 3px white divider
    div = np.full((S, 4, 3), 255, np.uint8)
    rows.append(np.concatenate([a, div, b], 1))
    print(f"[cmp] shot {tag}: rendered frozen|free")
montage = np.concatenate(rows, 0)
imageio.imwrite(args.out, montage)
print(f"[cmp] WROTE {args.out}  (rows: full / face / hand ; LEFT=frozen  RIGHT=free)")
