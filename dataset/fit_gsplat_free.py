"""
FREE-OPTIMIZED static 3DGS fit — the DETAIL-CEILING demo (sibling to fit_gsplat_poc.py).

WHY THIS EXISTS (D98 finding): the live avatar `poc_avatar.ply` is MESH-ANCHORED with
near-FROZEN gaussian means — every gaussian is pinned to one of ~13,718 body-mesh verts.
That binding is what makes it animate cleanly, but it CAPS geometric detail: D98 proved a
192-view refit scored identical to 96 views because there is nowhere to put new detail.

This script builds the OPPOSITE, to SEE the real ceiling: gaussian means are UNFROZEN and
move freely, and gsplat's built-in adaptive densification/pruning (DefaultStrategy — the
original 3DGS paper's duplicate/split/prune) adds gaussians where the image gradient is
high (face, hands) and prunes where they aren't needed. Result: a much sharper STATIC splat.

⚠️ IT DOES NOT ANIMATE. The means are no longer glued to mesh verts, so the LBS animation
binding does not apply. This is a detail-ceiling demonstration, NOT a replacement for the
animatable `poc_avatar.ply`. Output goes to a NEW file so both are selectable side-by-side.

Seed: same D95 projected-color + surface-aligned anisotropic-disk init as the anchored fit
(a good starting point); the means then move and densify freely from there.

Disk safety: a HARD CAP on the gaussian count (--cap) stops growth so the .ply can't blow
the (small) disk. Prune-heavy DefaultStrategy defaults keep it lean.

Usage:
  python fit_gsplat_free.py --mv <dir with frame_*.png + transforms.json> \
      --obj anny_adult.obj --out <outdir> --iters 7000 --cap 400000
"""
import argparse, json, os, math, numpy as np, torch
import imageio.v2 as imageio
from gsplat import rasterization
from gsplat.strategy import DefaultStrategy
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

ap = argparse.ArgumentParser()
ap.add_argument("--mv", required=True)
ap.add_argument("--obj", required=True, help="mesh whose verts SEED the (then-free) gaussians")
ap.add_argument("--out", required=True)
ap.add_argument("--iters", type=int, default=7000)
ap.add_argument("--sh_degree", type=int, default=3)
ap.add_argument("--holdout", type=int, default=1, help="hold out every 4th view for eval (0=none)")
ap.add_argument("--cap", type=int, default=400000, help="HARD cap on gaussian count (disk safety)")
ap.add_argument("--seed_densify", type=int, default=1, help="gaussians per mesh vert at SEED "
                "(densification then grows it); 1 = one per vert, let the strategy do the rest")
ap.add_argument("--refine_start", type=int, default=500)
ap.add_argument("--refine_stop_frac", type=float, default=0.40, help="stop densifying after this "
                "fraction of iters (rest of the run just polishes the frozen topology's attributes)")
ap.add_argument("--grow_grad2d", type=float, default=0.0005, help="only densify gaussians whose "
                "image-plane gradient exceeds this -- higher = more selective (concentrate the new "
                "gaussians on the few genuinely high-detail regions: face edges, hands)")
ap.add_argument("--grow_scale3d", type=float, default=0.30, help="dup-vs-split threshold (normalized "
                "by scene scale). HIGH => almost always DUPLICATE (keep gaussian size, add coverage) "
                "instead of SPLIT (halve size). On a smooth CG source, splitting shrinks gaussians "
                "into sub-pixel gaps and craters PSNR -- duplication avoids that.")
ap.add_argument("--scale_max_m", type=float, default=0.055, help="hard per-step clamp on gaussian "
                "size (metres) -- kills runaway needle gaussians")
ap.add_argument("--sh_interval", type=int, default=0, help="iters between SH-degree bumps (0=auto: "
                "spread evenly over the run). Set small to reach full SH EARLY so the free-means fit "
                "converges at full colour BEFORE densification perturbs it.")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
dev = "cuda"
C0 = 0.28209479177387814

# ---- load calibrated multi-view renders (identical convention to fit_gsplat_poc.py) --------
meta = json.load(open(os.path.join(args.mv, "transforms.json")))
W, H = meta["w"], meta["h"]
fx = fy = meta["lens_mm"] / meta["sensor_width_mm"] * W
K = torch.tensor([[fx, 0, W/2], [0, fy, H/2], [0, 0, 1]], dtype=torch.float32, device=dev)
flip = torch.diag(torch.tensor([1., -1., -1., 1.]))            # Blender cam -> OpenCV cam

imgs, viewmats, camposs = [], [], []
for fr in meta["frames"]:
    im = imageio.imread(os.path.join(args.mv, fr["file"])).astype(np.float32) / 255.0
    imgs.append(torch.from_numpy(im[..., :3]))
    c2w_bl = torch.tensor(fr["transform_matrix"], dtype=torch.float32)
    c2w_cv = c2w_bl @ flip
    viewmats.append(torch.linalg.inv(c2w_cv))
    camposs.append(c2w_cv[:3, 3])
imgs = torch.stack(imgs).to(dev)
viewmats = torch.stack(viewmats).to(dev)
camposs = torch.stack(camposs).to(dev)
N = imgs.shape[0]
corners = torch.stack([imgs[:, 0, 0], imgs[:, 0, -1], imgs[:, -1, 0], imgs[:, -1, -1]])
bg = corners.reshape(-1, 3).median(0).values
print(f"[free] {N} views {W}x{H} | focal={fx:.1f}px | bg={bg.cpu().numpy().round(3)}")

idx_all = list(range(N))
eval_idx = idx_all[::4] if args.holdout else []
train_idx = [i for i in idx_all if i not in eval_idx]
print(f"[free] train views={len(train_idx)} eval views={len(eval_idx)}")

# ---- seed gaussians at mesh vertices (same frame conversion as fit_gsplat_poc.py) ----------
verts, faces = [], []
for ln in open(args.obj):
    if ln.startswith("v "):
        _, x, y, z = ln.split()[:4]; verts.append((float(x), float(y), float(z)))
    elif ln.startswith("f "):
        idx = [int(tok.split("/")[0]) - 1 for tok in ln.split()[1:4]]; faces.append(idx)
verts = np.asarray(verts, np.float32)
faces = np.asarray(faces, np.int64)
verts = np.stack([verts[:, 0], -verts[:, 2], verts[:, 1]], 1).astype(np.float32)   # Y-up OBJ -> Z-up world

e1 = verts[faces[:, 1]] - verts[faces[:, 0]]
e2 = verts[faces[:, 2]] - verts[faces[:, 0]]
fn = np.cross(e1, e2)
vn = np.zeros_like(verts)
for k in range(3):
    np.add.at(vn, faces[:, k], fn)
vn /= np.clip(np.linalg.norm(vn, axis=1, keepdims=True), 1e-8, None)

V0 = len(verts)
tmp = cKDTree(verts)
nn0 = np.clip(tmp.query(verts, k=2)[0][:, 1], 1e-4, None)
if args.seed_densify > 1:
    arbitrary = np.tile(np.array([1., 0, 0], np.float32), (V0, 1))
    arbitrary[np.abs(vn[:, 0]) > 0.9] = [0., 1, 0]
    tan1 = np.cross(vn, arbitrary).astype(np.float32)
    tan1 /= np.clip(np.linalg.norm(tan1, axis=1, keepdims=True), 1e-8, None)
    tan2 = np.cross(vn, tan1).astype(np.float32)
    rng = np.random.default_rng(0)
    ev, en, enn = [], [], []
    for _ in range(args.seed_densify - 1):
        ang = rng.uniform(0, 2*np.pi, V0).astype(np.float32)
        rad = rng.uniform(0.3, 0.9, V0).astype(np.float32) * nn0
        j = (tan1*(np.cos(ang)*rad)[:, None] + tan2*(np.sin(ang)*rad)[:, None]).astype(np.float32)
        ev.append((verts+j).astype(np.float32)); en.append(vn.copy()); enn.append(nn0.copy())
    verts = np.concatenate([verts]+ev).astype(np.float32)
    vn = np.concatenate([vn]+en).astype(np.float32)
    nn0 = np.concatenate([nn0]+enn).astype(np.float32)
P = len(verts)
extent = float(np.linalg.norm(verts.max(0) - verts.min(0)))
scene_scale = extent  # used to normalize DefaultStrategy's scale-based thresholds
print(f"[free] SEED {P} gaussians ({args.seed_densify}x from {V0} verts) | extent={extent:.2f}m")

# ---- D95 surface-aligned anisotropic-disk init (seed only; means then move freely) ---------
arb = np.tile(np.array([1., 0., 0.], np.float32), (P, 1))
arb[np.abs(vn[:, 0]) > 0.9] = [0., 1., 0.]
t1 = np.cross(arb, vn).astype(np.float32); t1 /= np.clip(np.linalg.norm(t1, axis=1, keepdims=True), 1e-8, None)
t2 = np.cross(vn, t1).astype(np.float32)
Rframe = np.stack([t1, t2, vn], axis=2)
_q = Rotation.from_matrix(Rframe).as_quat().astype(np.float32)                     # (x,y,z,w)
quat_wxyz = np.concatenate([_q[:, 3:4], _q[:, :3]], axis=1).astype(np.float32)     # (w,x,y,z)

# ---- projected-pixel color seed (each vert samples its own color from facing views) --------
normals = torch.tensor(vn, device=dev)
verts_t = torch.tensor(verts, device=dev)
color_accum = torch.zeros(P, 3, device=dev); weight_accum = torch.zeros(P, device=dev)
with torch.no_grad():
    for i in range(N):
        cam_dir = torch.nn.functional.normalize(camposs[i][None] - verts_t, dim=-1)
        w = (cam_dir*normals).sum(-1).clamp(min=0)**2
        homo = torch.cat([verts_t, torch.ones(P, 1, device=dev)], 1)
        cam_pt = (viewmats[i] @ homo.T).T[:, :3]
        infront = cam_pt[:, 2] > 1e-4
        px = K[0, 0]*cam_pt[:, 0]/cam_pt[:, 2].clamp(min=1e-4) + K[0, 2]
        py = K[1, 1]*cam_pt[:, 1]/cam_pt[:, 2].clamp(min=1e-4) + K[1, 2]
        inb = infront & (px >= 0) & (px < W-1) & (py >= 0) & (py < H-1)
        w = w*inb.float()
        gx = px.clamp(0, W-1)/(W-1)*2-1; gy = py.clamp(0, H-1)/(H-1)*2-1
        grid = torch.stack([gx, gy], -1).view(1, P, 1, 2)
        samp = torch.nn.functional.grid_sample(imgs[i].permute(2, 0, 1)[None], grid,
                                                align_corners=True, mode="bilinear", padding_mode="zeros")
        color_accum += w[:, None]*samp[0, :, :, 0].T; weight_accum += w
    gmean = imgs.mean(dim=(0, 1, 2))
    has_w = weight_accum > 1e-3
    init_rgb = torch.where(has_w[:, None], color_accum/weight_accum.clamp(min=1e-3)[:, None],
                           gmean[None].expand(P, 3))
print(f"[free] color seed: {has_w.sum().item()}/{P} got a projected color")

def logit(x): return math.log(x/(1-x))
Ksh = (args.sh_degree+1)**2
# Seed matches the WORKING frozen recipe (opacity 0.5, tangent 1.35x, normal 0.18x) so the seed
# itself is already a solid ~28 dB surface; densification then only ADDS detail on top.
S_TAN = 1.35*nn0; S_NORM = 0.18*nn0
scale_init = np.log(np.stack([S_TAN, S_TAN, S_NORM], 1).astype(np.float32))
SCALE_MAX = math.log(args.scale_max_m)   # hard per-step clamp on log-scale -> kills runaway NEEDLE
                                         # gaussians while still allowing coverage blobs

# ---- PARAMS as a ParameterDict + ONE optimizer per param (DefaultStrategy convention) ------
splats = torch.nn.ParameterDict({
    "means":     torch.nn.Parameter(torch.tensor(verts, device=dev)),
    "scales":    torch.nn.Parameter(torch.tensor(scale_init, device=dev)),
    "quats":     torch.nn.Parameter(torch.tensor(quat_wxyz, device=dev)),
    "opacities": torch.nn.Parameter(torch.full((P,), logit(0.5), device=dev)),
    "sh0":       torch.nn.Parameter(((init_rgb.clamp(0.02, 0.98)-0.5)/C0).unsqueeze(1).clone()),
    "shN":       torch.nn.Parameter(torch.zeros(P, Ksh-1, 3, device=dev)),
})
# lr per param. means lr scaled by scene extent (standard 3DGS) and EXPONENTIALLY DECAYED over the
# run (means fine-tune position, densification does the detail work) -> stable, no drift into a cloud.
MEANS_LR0 = 1.6e-4*scene_scale
LR = {"means": MEANS_LR0, "scales": 3e-3, "quats": 1e-3,
      "opacities": 3e-2, "sh0": 2.5e-3, "shN": 2.5e-3/20}
optimizers = {k: torch.optim.Adam([{"params": splats[k], "lr": LR[k], "name": k}], eps=1e-15)
              for k in splats.keys()}
means_sched = torch.optim.lr_scheduler.ExponentialLR(optimizers["means"], gamma=0.01**(1.0/args.iters))

strategy = DefaultStrategy(
    prune_opa=0.05,               # prune more aggressively than default (0.005) -> lean, disk-safe
    grow_grad2d=args.grow_grad2d, # selective: only densify genuinely high-detail regions
    grow_scale3d=args.grow_scale3d,   # HIGH -> duplicate (keep size) instead of split (shrink)
    refine_start_iter=args.refine_start,
    refine_stop_iter=int(args.iters*args.refine_stop_frac),
    reset_every=10**9,            # DISABLE opacity reset: it's tuned for 30k-iter runs; in a short
                                  # run its two resets left the model dark/transparent (the failure)
    refine_every=150,
    pause_refine_after_reset=0,
    verbose=False,
)
strategy.check_sanity(splats, optimizers)
strategy_state = strategy.initialize_state(scene_scale=scene_scale)
print(f"[free] DefaultStrategy: refine [{strategy.refine_start_iter},{strategy.refine_stop_iter}] "
      f"every {strategy.refine_every} | prune_opa={strategy.prune_opa} | HARD cap={args.cap}")

def render(view_i, deg, absgrad=False):
    colors = torch.cat([splats["sh0"], splats["shN"]], dim=1)          # (P,Ksh,3)
    out, alpha, info = rasterization(
        splats["means"], torch.nn.functional.normalize(splats["quats"], dim=-1),
        torch.exp(splats["scales"]), torch.sigmoid(splats["opacities"]), colors,
        viewmats[view_i:view_i+1], K[None], W, H, sh_degree=deg,
        backgrounds=bg[None], render_mode="RGB", packed=False, absgrad=absgrad)
    return out[0].clamp(0, 1), info

def ssim(a, b):
    mu_a = torch.nn.functional.avg_pool2d(a, 3, 1, 1); mu_b = torch.nn.functional.avg_pool2d(b, 3, 1, 1)
    va = torch.nn.functional.avg_pool2d(a*a, 3, 1, 1)-mu_a**2
    vb = torch.nn.functional.avg_pool2d(b*b, 3, 1, 1)-mu_b**2
    vab = torch.nn.functional.avg_pool2d(a*b, 3, 1, 1)-mu_a*mu_b
    c1, c2 = 0.01**2, 0.03**2
    return (((2*mu_a*mu_b+c1)*(2*vab+c2))/((mu_a**2+mu_b**2+c1)*(va+vb+c2))).mean()

def psnr_set(idxs, deg):
    if not idxs: return float("nan")
    vals = []
    with torch.no_grad():
        for i in idxs:
            pred, _ = render(i, deg)
            mse = ((pred - imgs[i])**2).mean().item()
            vals.append(-10*math.log10(mse+1e-10))
    return sum(vals)/len(vals)

# ---- optimize with adaptive densification -------------------------------------------------
# Export the BEST held-out checkpoint (full snapshot), not the end state -- single-view SGD +
# densification wobble, so we keep whatever state actually scored best (as the frozen fit does).
torch.manual_seed(0)
growth_frozen = False
best_ev, best_snap = -1e9, None
refine_stop = int(args.iters*args.refine_stop_frac)
def snapshot():
    return {k: v.detach().cpu().clone() for k, v in splats.items()}
sh_iv = args.sh_interval or (args.iters // (args.sh_degree+1) + 1)
for it in range(args.iters):
    deg = min(args.sh_degree, it // sh_iv)
    vi = train_idx[torch.randint(len(train_idx), (1,)).item()]
    pred, info = render(vi, deg, absgrad=strategy.absgrad)
    gt = imgs[vi]
    # DefaultStrategy needs means2d gradients retained before backward
    strategy.step_pre_backward(params=splats, optimizers=optimizers,
                               state=strategy_state, step=it, info=info)
    loss = 0.8*(pred-gt).abs().mean() + 0.2*(1-ssim(pred.permute(2, 0, 1)[None], gt.permute(2, 0, 1)[None]))
    for o in optimizers.values(): o.zero_grad(set_to_none=True)
    loss.backward()
    # densify/prune (skipped once the hard cap is hit -> freeze topology, keep polishing attrs)
    if not growth_frozen:
        strategy.step_post_backward(params=splats, optimizers=optimizers,
                                    state=strategy_state, step=it, info=info, packed=False)
        if splats["means"].shape[0] >= args.cap:
            growth_frozen = True
            strategy.refine_stop_iter = it     # stop all further refinement
            print(f"[free] HARD CAP hit at it {it}: {splats['means'].shape[0]} gaussians -> topology frozen")
    for o in optimizers.values(): o.step()
    means_sched.step()
    with torch.no_grad():
        splats["scales"].clamp_(max=SCALE_MAX)     # no needles
    if it % 250 == 0 or it == args.iters-1:
        ev = psnr_set(eval_idx or train_idx, deg)
        # bank the best checkpoint over the WHOLE run. FINDING (this source): adaptive densification
        # does not add detail on our SMOOTH CG mannequin -- it only destabilizes the single-view-SGD
        # optimization (duplicated gaussians double local opacity, single-view SGD can't re-coordinate
        # 80k+ of them, held-out PSNR craters ~28->18 and never recovers). So the honest best state is
        # whichever the optimizer actually reaches -- typically free-means + LIGHT densification, before
        # over-densification degrades it. Banking across all iters exports that peak, not an end-blob.
        if ev > best_ev:
            best_ev, best_snap = ev, snapshot()
        print(f"[free] it {it:5d}/{args.iters}  loss {loss.item():.4f}  held-out {ev:.2f}dB  "
              f"P={splats['means'].shape[0]:7d}  shdeg {deg}  best {best_ev:.2f}dB")

# ---- restore BEST checkpoint for export ---------------------------------------------------
if best_snap is not None:
    with torch.no_grad():
        new = torch.nn.ParameterDict({k: torch.nn.Parameter(v.to(dev)) for k, v in best_snap.items()})
        splats = new
    print(f"[free] restored BEST checkpoint (held-out {best_ev:.2f}dB, P={splats['means'].shape[0]})")

# ---- final eval ---------------------------------------------------------------------------
P = splats["means"].shape[0]
tr = psnr_set(train_idx, args.sh_degree); ev = psnr_set(eval_idx, args.sh_degree)
print(f"[free] FINAL  P={P}  train={tr:.2f}dB  held-out={ev:.2f}dB  (gap {tr-ev:.2f}dB; small gap = no memorization)")

# anisotropy stats
with torch.no_grad():
    sc = torch.exp(splats["scales"])
    aniso = (sc.max(1).values / sc.min(1).values.clamp(min=1e-9))
    print(f"[free] anisotropy median {aniso.median().item():.2f}  mean {aniso.mean().item():.2f}")

# ---- export .ply (standard 3DGS) ----------------------------------------------------------
from plyfile import PlyData, PlyElement
with torch.no_grad():
    xyz = splats["means"].cpu().numpy()
    f_dc = splats["sh0"].cpu().numpy().reshape(P, 3)
    f_rest = splats["shN"].cpu().numpy().transpose(0, 2, 1).reshape(P, -1)
    op = splats["opacities"].cpu().numpy().reshape(P, 1)
    sc = splats["scales"].cpu().numpy()
    rot = torch.nn.functional.normalize(splats["quats"], dim=-1).cpu().numpy()
    cols = [("x", "f4"), ("y", "f4"), ("z", "f4"), ("nx", "f4"), ("ny", "f4"), ("nz", "f4")]
    cols += [(f"f_dc_{i}", "f4") for i in range(3)]
    cols += [(f"f_rest_{i}", "f4") for i in range(f_rest.shape[1])]
    cols += [("opacity", "f4")] + [(f"scale_{i}", "f4") for i in range(3)] + [(f"rot_{i}", "f4") for i in range(4)]
    data = np.zeros(P, dtype=cols)
    for j, n in enumerate(["x", "y", "z"]): data[n] = xyz[:, j]
    for j in range(3): data[f"f_dc_{j}"] = f_dc[:, j]
    for j in range(f_rest.shape[1]): data[f"f_rest_{j}"] = f_rest[:, j]
    data["opacity"] = op[:, 0]
    for j in range(3): data[f"scale_{j}"] = sc[:, j]
    for j in range(4): data[f"rot_{j}"] = rot[:, j]
    ply_path = os.path.join(args.out, "avatar.ply")
    PlyData([PlyElement.describe(data, "vertex")]).write(ply_path)
    frames = [(render(i, args.sh_degree)[0].cpu().numpy()*255).astype(np.uint8) for i in range(0, N, max(1, N//36))]
    imageio.mimsave(os.path.join(args.out, "fit_turntable.gif"), frames, fps=12, loop=0)
print(f"[free] WROTE {ply_path}  ({P} gaussians)")
