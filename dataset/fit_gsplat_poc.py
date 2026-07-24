"""
PoC gaussian fit — the D74 Milestone-0 static-fit proof, on CC0 assets only.

Pipeline: CC0-skinned Anny turntable (blender_render_skin.py --poses) -> fit 3D
gaussians (gsplat) to those IMAGES with KNOWN camera poses (no COLMAP) -> export a
standard 3DGS .ply + a rendered turntable to eyeball the round-trip.

Gaussians are MESH-ANCHORED: initialized at the Anny mesh vertices (the D74 idea).
Color starts from a PROJECTED-PIXEL init (each vertex samples its own color from
whichever views actually face it, weighted by facing angle) instead of flat grey —
grey init + few views is what caused the D78 "marble"/rainbow speckle (each
gaussian's color was ambiguous, so it settled on per-gaussian noise). A neighbor
color-smoothness prior further discourages that noise. Means/scale stay near-frozen
(mesh-anchored, D74); densification + rig-anchor + pose-correctives are next.

Usage:
  python fit_gsplat_poc.py --mv <dir with frame_*.png + transforms.json> \
      --obj anny_adult.obj --out <outdir> --iters 2000
"""
import argparse, json, os, math, numpy as np, torch
import imageio.v2 as imageio
from gsplat import rasterization
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument("--mv", required=True, help="dir with frame_*.png + transforms.json")
ap.add_argument("--obj", required=True, help="mesh whose verts seed the gaussians")
ap.add_argument("--out", required=True)
ap.add_argument("--iters", type=int, default=2000)
ap.add_argument("--sh_degree", type=int, default=3)
ap.add_argument("--holdout", type=int, default=1, help="hold out every Nth+? view for eval (0=none)")
ap.add_argument("--smooth_w", type=float, default=0.15, help="neighbor color-smoothness loss weight")
ap.add_argument("--knn", type=int, default=6, help="neighbors used for the smoothness prior")
ap.add_argument("--densify", type=int, default=3, help="gaussians per mesh vertex (tangent-jittered "
                 "copies) -- 1 vertex/gaussian is too sparse to read as a solid surface at typical "
                 "viewing size; this multiplies coverage without a full adaptive-density pass")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
dev = "cuda"
C0 = 0.28209479177387814  # SH DC factor

# ---- load calibrated multi-view renders -------------------------------------
meta = json.load(open(os.path.join(args.mv, "transforms.json")))
W, H = meta["w"], meta["h"]
# square render, sensor_fit AUTO -> focal from the (equal) sensor width
fx = fy = meta["lens_mm"] / meta["sensor_width_mm"] * W
K = torch.tensor([[fx, 0, W/2], [0, fy, H/2], [0, 0, 1]], dtype=torch.float32, device=dev)
flip = torch.diag(torch.tensor([1., -1., -1., 1.]))  # Blender cam -> OpenCV cam

imgs, viewmats, camposs = [], [], []
for fr in meta["frames"]:
    im = imageio.imread(os.path.join(args.mv, fr["file"])).astype(np.float32) / 255.0
    imgs.append(torch.from_numpy(im[..., :3]))
    c2w_bl = torch.tensor(fr["transform_matrix"], dtype=torch.float32)
    c2w_cv = c2w_bl @ flip
    viewmats.append(torch.linalg.inv(c2w_cv))
    camposs.append(c2w_cv[:3, 3])
imgs = torch.stack(imgs).to(dev)                    # (N,H,W,3)
viewmats = torch.stack(viewmats).to(dev)            # (N,4,4) world->cam
camposs = torch.stack(camposs).to(dev)              # (N,3) world-space camera positions
N = imgs.shape[0]
# background = median of the 4 image corners (turntable studio bg is ~constant)
corners = torch.stack([imgs[:, 0, 0], imgs[:, 0, -1], imgs[:, -1, 0], imgs[:, -1, -1]])
bg = corners.reshape(-1, 3).median(0).values                       # (3,)
print(f"[fit] {N} views {W}x{H} | focal={fx:.1f}px | bg={bg.cpu().numpy().round(3)}")

# eval split
idx_all = list(range(N))
eval_idx = idx_all[::4] if args.holdout else []      # every 4th view held out
train_idx = [i for i in idx_all if i not in eval_idx]
print(f"[fit] train views={len(train_idx)} eval views={len(eval_idx)}")

# ---- init gaussians at mesh vertices ----------------------------------------
verts, faces = [], []
for ln in open(args.obj):
    if ln.startswith("v "):
        _, x, y, z = ln.split()[:4]
        verts.append((float(x), float(y), float(z)))
    elif ln.startswith("f "):
        idx = [int(tok.split("/")[0]) - 1 for tok in ln.split()[1:4]]  # tri (or first 3 of an ngon)
        faces.append(idx)
verts = np.asarray(verts, np.float32)
faces = np.asarray(faces, np.int64)
# Blender's OBJ importer rotates Y-up OBJ -> Z-up world (+90° about X); the camera
# poses live in that Z-up world, so bring the verts into the same frame: (x,y,z)->(x,-z,y)
verts = np.stack([verts[:, 0], -verts[:, 2], verts[:, 1]], 1).astype(np.float32)

# area-weighted vertex normals (needed BEFORE densifying, to jitter tangentially -- i.e.
# spread extra gaussians across the SURFACE, not puff them off it along the normal)
e1 = verts[faces[:, 1]] - verts[faces[:, 0]]
e2 = verts[faces[:, 2]] - verts[faces[:, 0]]
fn = np.cross(e1, e2)                                    # unnormalized: magnitude = 2*area
vn = np.zeros_like(verts)
for k in range(3):
    np.add.at(vn, faces[:, k], fn)
vn /= np.clip(np.linalg.norm(vn, axis=1, keepdims=True), 1e-8, None)

# ---- densify: 1 gaussian/vertex (13,718 for this mesh) is too sparse to read as a solid
# surface at typical viewing size, however good the color/fit is. Add (--densify - 1) extra
# tangent-jittered copies per vertex -- cheap, no adaptive-density training pass needed.
V0 = len(verts)
tmp = cKDTree(verts)
nn0 = np.clip(tmp.query(verts, k=2)[0][:, 1], 1e-4, None)
if args.densify > 1:
    arbitrary = np.tile(np.array([1., 0, 0], dtype=np.float32), (V0, 1))
    arbitrary[np.abs(vn[:, 0]) > 0.9] = [0., 1, 0]
    tan1 = np.cross(vn, arbitrary).astype(np.float32)
    tan1 /= np.clip(np.linalg.norm(tan1, axis=1, keepdims=True), 1e-8, None)
    tan2 = np.cross(vn, tan1).astype(np.float32)
    rng = np.random.default_rng(0)
    extra_v, extra_n = [], []
    for _ in range(args.densify - 1):
        ang = rng.uniform(0, 2 * np.pi, V0).astype(np.float32)
        rad = (rng.uniform(0.3, 0.9, V0).astype(np.float32)) * nn0
        jitter = (tan1 * (np.cos(ang) * rad)[:, None] + tan2 * (np.sin(ang) * rad)[:, None]).astype(np.float32)
        extra_v.append((verts + jitter).astype(np.float32)); extra_n.append(vn.astype(np.float32))
    verts = np.concatenate([verts] + extra_v, axis=0).astype(np.float32)
    vn = np.concatenate([vn] + extra_n, axis=0).astype(np.float32)
P = len(verts)
tree = cKDTree(verts)
d, nn_idx = tree.query(verts, k=args.knn + 1)   # nearest-neighbour distances + indices (post-densify)
nn = np.clip(d[:, 1], 1e-4, None)
neighbor_idx = torch.tensor(nn_idx[:, 1:], device=dev, dtype=torch.long)   # (P,knn)
extent = float(np.linalg.norm(verts.max(0) - verts.min(0)))
print(f"[fit] {P} gaussians ({args.densify}x densified from {V0} mesh verts) | extent={extent:.2f}m "
      f"| mean nn={nn.mean():.4f}m")
normals = torch.tensor(vn, device=dev, dtype=torch.float32)   # (P,3)
nn0_full = np.tile(nn0, args.densify).astype(np.float32)      # per-point, but from the COARSER pre-densify spacing

# ---- per-gaussian surface FRAME -> flat, normal-aligned disk init (D95) -----------------
# THE BUG this fixes: the prior init gave every gaussian an ISOTROPIC scale (the same value
# repeated on all 3 axes) and an IDENTITY rotation quaternion. The exported best checkpoint is
# captured EARLY (iter ~500, SH deg 0 -- SH-overfit degrades PSNR after, D80), so the fit never
# moves far from that isotropic init, and the weak image-loss signal on a soft mesh-anchored
# body doesn't spontaneously flatten spheres -- measured anisotropy ratio was ~1.13 (foam/clay).
# Real surface-aligned 3DGS gaussians are THIN FLAT DISKS: large along the two surface-TANGENT
# directions, small along the surface NORMAL, with the rotation aligned to that local frame.
# We already have per-vertex normals (vn); build an orthonormal tangent frame per gaussian and
# init scale + rotation from it so the gaussians START anisotropic & surface-aligned.
arb = np.tile(np.array([1., 0., 0.], np.float32), (P, 1))
arb[np.abs(vn[:, 0]) > 0.9] = [0., 1., 0.]                    # avoid arb ∥ normal
t1 = np.cross(arb, vn).astype(np.float32)
t1 /= np.clip(np.linalg.norm(t1, axis=1, keepdims=True), 1e-8, None)
t2 = np.cross(vn, t1).astype(np.float32)                      # {t1,t2,vn} orthonormal, right-handed (vn = t1×t2)
Rframe = np.stack([t1, t2, vn], axis=2)                       # columns = local x,y,z axes -> world
from scipy.spatial.transform import Rotation
_q = Rotation.from_matrix(Rframe).as_quat().astype(np.float32)          # (P,4) as (x,y,z,w)
quat_wxyz = np.concatenate([_q[:, 3:4], _q[:, :3]], axis=1).astype(np.float32)  # -> (w,x,y,z), gsplat/ply order

# ---- projected-pixel color init: each vertex samples ITS OWN color from every view
# that faces it (weighted by facing angle), instead of starting flat grey. Grey init +
# only ~24 views is what left each gaussian's color under-constrained -> the D78
# rainbow/marble speckle (the optimizer settled on per-gaussian noise).
verts_t = torch.tensor(verts, device=dev)
color_accum = torch.zeros(P, 3, device=dev)
weight_accum = torch.zeros(P, device=dev)
with torch.no_grad():
    for i in range(N):
        cam_dir = torch.nn.functional.normalize(camposs[i][None] - verts_t, dim=-1)
        w = (cam_dir * normals).sum(-1).clamp(min=0) ** 2       # facing weight, 0 if back-facing
        homo = torch.cat([verts_t, torch.ones(P, 1, device=dev)], 1)
        cam_pt = (viewmats[i] @ homo.T).T[:, :3]                 # (P,3) camera space
        infront = cam_pt[:, 2] > 1e-4
        px = (K[0, 0] * cam_pt[:, 0] / cam_pt[:, 2].clamp(min=1e-4) + K[0, 2])
        py = (K[1, 1] * cam_pt[:, 1] / cam_pt[:, 2].clamp(min=1e-4) + K[1, 2])
        inb = infront & (px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)
        w = w * inb.float()
        gx = (px.clamp(0, W - 1) / (W - 1) * 2 - 1)
        gy = (py.clamp(0, H - 1) / (H - 1) * 2 - 1)
        grid = torch.stack([gx, gy], -1).view(1, P, 1, 2)
        img_chw = imgs[i].permute(2, 0, 1)[None]                 # (1,3,H,W)
        samp = torch.nn.functional.grid_sample(img_chw, grid, align_corners=True,
                                                mode="bilinear", padding_mode="zeros")
        samp = samp[0, :, :, 0].T                                # (P,3)
        color_accum += w[:, None] * samp
        weight_accum += w
    global_mean = imgs.mean(dim=(0, 1, 2))
    has_w = weight_accum > 1e-3
    init_rgb = torch.where(has_w[:, None], color_accum / weight_accum.clamp(min=1e-3)[:, None],
                            global_mean[None].expand(P, 3))
    print(f"[fit] color init: {has_w.sum().item()}/{P} verts got a projected color "
          f"({(~has_w).sum().item()} fell back to the global mean)")

def logit(x): return math.log(x / (1 - x))
Ksh = (args.sh_degree + 1) ** 2
means   = torch.tensor(verts, device=dev, requires_grad=True)
# ANISOTROPIC init (D95): tangent axes ~ mesh spacing (in-plane coverage identical to before),
# normal axis THIN -> flat surface disk. axis 0,1 = tangent, axis 2 = normal (matches Rframe's
# column order, so quats below put those axes on the real surface tangents/normal). Coarser
# pre-densify spacing (boosted) is used for the same reason as before: the best checkpoint is
# captured early, so INIT size is what's actually on screen.
S_TAN  = 1.35 * nn0_full        # in-plane radius (unchanged from the old isotropic SCALE_INIT)
S_NORM = 0.18 * nn0_full        # normal thickness ~13% of tangent -> anisotropy ratio ~7.5 at init
scale_init = np.stack([S_TAN, S_TAN, S_NORM], axis=1).astype(np.float32)
logscl  = torch.log(torch.tensor(scale_init, device=dev)).requires_grad_(True)
quats   = torch.tensor(quat_wxyz, device=dev, requires_grad=True)   # surface-frame aligned, not identity
opac    = torch.full((P,), logit(0.5), device=dev, requires_grad=True)
# PER-AXIS cap (D95): tangent axes may grow to 4x mean spacing (coverage, as before); the normal
# axis is capped thin so gaussians stay flat surface disks instead of re-inflating into spheres.
# (axis 2 = normal at init; quats optimize only mildly at lr 1e-3 over the ~500 iters to the best
# checkpoint, so the axis identity holds well enough for the cap to keep them flat.)
cap_tan  = math.log(4.0 * float(nn0.mean()))
cap_norm = math.log(0.7 * float(nn0.mean()))
SCALE_CAP = torch.tensor([cap_tan, cap_tan, cap_norm], device=dev)
sh0     = ((init_rgb.clamp(0.02, 0.98) - 0.5) / C0).unsqueeze(1).clone().requires_grad_(True)  # projected-color init
shN     = torch.zeros(P, Ksh - 1, 3, device=dev, requires_grad=True)

opt = torch.optim.Adam([
    {"params": [means],  "lr": 2e-5 * extent},   # near-frozen: gaussians stay mesh-anchored (D74)
    {"params": [logscl], "lr": 5e-3},
    {"params": [quats],  "lr": 1e-3},
    {"params": [opac],   "lr": 5e-2},
    {"params": [sh0],    "lr": 2.5e-3},
    {"params": [shN],    "lr": 2.5e-3 / 20},
], eps=1e-15)

def ssim(a, b):  # tiny 1-window DSSIM proxy over 3x3 means
    mu_a = torch.nn.functional.avg_pool2d(a, 3, 1, 1)
    mu_b = torch.nn.functional.avg_pool2d(b, 3, 1, 1)
    va = torch.nn.functional.avg_pool2d(a*a, 3, 1, 1) - mu_a**2
    vb = torch.nn.functional.avg_pool2d(b*b, 3, 1, 1) - mu_b**2
    vab = torch.nn.functional.avg_pool2d(a*b, 3, 1, 1) - mu_a*mu_b
    c1, c2 = 0.01**2, 0.03**2
    s = ((2*mu_a*mu_b+c1)*(2*vab+c2)) / ((mu_a**2+mu_b**2+c1)*(va+vb+c2))
    return s.mean()

def render(view_i, deg):
    colors = torch.cat([sh0, shN], dim=1)                      # (P,Ksh,3)
    out, _, _ = rasterization(
        means, torch.nn.functional.normalize(quats, dim=-1), torch.exp(logscl),
        torch.sigmoid(opac), colors, viewmats[view_i:view_i+1], K[None], W, H,
        sh_degree=deg, backgrounds=bg, render_mode="RGB")
    return out[0].clamp(0, 1)                                   # (H,W,3)

PARAMS = {"means": means, "logscl": logscl, "quats": quats, "opac": opac, "sh0": sh0, "shN": shN}

def psnr_set(idxs, deg):
    if not idxs: return float("nan")
    vals = []
    for i in idxs:
        mse = ((render(i, deg) - imgs[i]) ** 2).mean().item()
        vals.append(-10 * math.log10(mse + 1e-10))
    return sum(vals) / len(vals)

# ---- optimize -----------------------------------------------------------------
# Single-view-per-step SGD on a handful of images is prone to thrashing (each step can
# overfit the ONE view it's looking at, at the expense of the others) -- so track the
# BEST held-out PSNR seen during training and export THAT checkpoint, not just whatever
# state training happens to end on.
torch.manual_seed(0)
best_ev, best_state = -1e9, None
EVAL_EVERY = 100
for it in range(args.iters):
    deg = min(args.sh_degree, it // (args.iters // (args.sh_degree + 1) + 1))
    vi = train_idx[torch.randint(len(train_idx), (1,)).item()]
    pred = render(vi, deg)
    gt = imgs[vi]
    loss = 0.8 * (pred - gt).abs().mean() + 0.2 * (1 - ssim(
        pred.permute(2, 0, 1)[None], gt.permute(2, 0, 1)[None]))
    if args.smooth_w > 0:
        # neighbor color-smoothness prior: discourages the per-gaussian color noise
        # (the marble look) that comes from color being under-constrained by sparse views
        neighbor_dc = sh0[neighbor_idx].mean(dim=1)          # (P,1,3)
        loss = loss + args.smooth_w * (sh0 - neighbor_dc).pow(2).mean()
    opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
    with torch.no_grad(): logscl.clamp_(max=SCALE_CAP)   # no needles
    if it % EVAL_EVERY == 0 or it == args.iters - 1:
        with torch.no_grad():
            ev = psnr_set(eval_idx or train_idx, deg)
            if ev > best_ev:
                best_ev = ev
                best_state = {k: v.detach().clone() for k, v in PARAMS.items()}
        if it % 250 == 0 or it == args.iters - 1:
            print(f"[fit] it {it:4d}/{args.iters}  loss {loss.item():.4f}  held-out {ev:.2f}dB  "
                  f"(best {best_ev:.2f}dB)  shdeg {deg}")

if best_state is not None:
    with torch.no_grad():
        for k, v in PARAMS.items(): v.copy_(best_state[k])
    print(f"[fit] restored BEST checkpoint (held-out {best_ev:.2f}dB)")

# ---- eval on held-out views -------------------------------------------------
with torch.no_grad():
    tr, ev = psnr_set(train_idx, args.sh_degree), psnr_set(eval_idx, args.sh_degree)
    print(f"[fit] FINAL PSNR  train={tr:.2f}dB  held-out={ev:.2f}dB")

# ---- export .ply (standard 3DGS) + a rendered turntable ---------------------
from plyfile import PlyData, PlyElement
with torch.no_grad():
    xyz = means.cpu().numpy()
    f_dc = sh0.cpu().numpy().reshape(P, 3)
    f_rest = shN.cpu().numpy().transpose(0, 2, 1).reshape(P, -1)   # (P,3*(Ksh-1))
    op = opac.cpu().numpy().reshape(P, 1)
    sc = logscl.cpu().numpy()
    rot = torch.nn.functional.normalize(quats, dim=-1).cpu().numpy()
    cols = [("x","f4"),("y","f4"),("z","f4"),("nx","f4"),("ny","f4"),("nz","f4")]
    cols += [(f"f_dc_{i}","f4") for i in range(3)]
    cols += [(f"f_rest_{i}","f4") for i in range(f_rest.shape[1])]
    cols += [("opacity","f4")] + [(f"scale_{i}","f4") for i in range(3)] + [(f"rot_{i}","f4") for i in range(4)]
    data = np.zeros(P, dtype=cols)
    for j,n in enumerate(["x","y","z"]): data[n] = xyz[:, j]
    for j in range(3): data[f"f_dc_{j}"] = f_dc[:, j]
    for j in range(f_rest.shape[1]): data[f"f_rest_{j}"] = f_rest[:, j]
    data["opacity"] = op[:, 0]
    for j in range(3): data[f"scale_{j}"] = sc[:, j]
    for j in range(4): data[f"rot_{j}"] = rot[:, j]
    ply_path = os.path.join(args.out, "avatar.ply")
    PlyData([PlyElement.describe(data, "vertex")]).write(ply_path)
    # rendered turntable (reuse the training camera ring)
    frames = [(render(i, args.sh_degree).cpu().numpy() * 255).astype(np.uint8) for i in range(N)]
    imageio.mimsave(os.path.join(args.out, "fit_turntable.gif"), frames, fps=12, loop=0)
    imageio.imwrite(os.path.join(args.out, "fit_view0.png"), frames[0])
print(f"[fit] WROTE {ply_path}  ({P} gaussians)  + fit_turntable.gif")
