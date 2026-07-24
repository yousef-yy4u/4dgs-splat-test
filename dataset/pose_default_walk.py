#!/usr/bin/env python3
"""Pose the DEFAULT-topology (13,718-v, UV'd) Anny mesh with REAL skeletal skinning,
driven by the Kimodo SOMA walk retargeted onto Anny's own 163-bone rig.

Replaces the broken deformation-transfer (build_moving_textured.py) that mangled hands/arms:
this uses Anny's OWN forward-kinematic skinning, so unmapped bones (hands, feet, fingers)
stay RIGID and articulated -- no blend mush.

Retarget (world-delta, FK-matched to Anny's local-bone parameterization):
  * Drive from SOMALayer's INTERNAL world joint transforms T_world (the exact transforms that
    produce the known-good 18,056-v SOMA walk) -> guaranteed consistent with the good motion.
  * SOMA world rotation delta of joint j from its rest:   dR[j] = Rw_soma[j] . Rbind_soma[j]^T
  * For each Anny bone b, let D[b] = dR of b's NEAREST MAPPED ancestor in the Anny hierarchy
    (self if b is mapped). We want Anny bone b's WORLD orientation = D[b] . Rrest_anny[b].
  * Anny 'local-bone' FK gives  pose[b] = transform[parent] . rest[b] . P[b]; solving for the
    per-bone local delta:   P[b] = Rrest_anny[b]^T . D[parent_b]^T . D[b] . Rrest_anny[b]
    (D[parent of root] = I). Unmapped bones between two mapped bones collapse to P=I (rigid).

  python pose_default_walk.py --out obj_seq --frames 48
  python pose_default_walk.py --out obj_seq --frames 48 --preview   # + gray pyrender limb-check gif
"""
import os, argparse, numpy as np, torch
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("ANNY_CACHE_DIR", os.path.expanduser("~/.cache/anny"))

ap = argparse.ArgumentParser()
ap.add_argument("--npz", default="kimodo_out/walk.npz")
ap.add_argument("--out", required=True)
ap.add_argument("--frames", type=int, default=48)
ap.add_argument("--no-fingers", action="store_true", help="skip finger retarget (leave hands in rest)")
ap.add_argument("--arm-abduct", type=float, default=None,
                 help="outward arm abduction (deg) to stop the hands swinging into the torso; "
                      "default = outfit_lib.ARM_ABDUCT_DEG (the self-collision fix). 0 disables.")
ap.add_argument("--preview", action="store_true", help="also write a gray pyrender preview gif")
ap.add_argument("--stem", default=None,
                 help="also export <stem>_verts.npy/_faces.npy/_eyemeta.json into motion_out/ for the "
                      "live viewer (this DEFAULT topology has real eyeball geometry; the SOMA-topology "
                      "models the viewer used before this do not)")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

# --- SHIM (soma passes local_changes=None into anny) ---
import anny.models.phenotype as _ph
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(f):
            def g(self, *a, local_changes=None, **k): return f(self, *a, local_changes=(local_changes or {}), **k)
            return g
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

import anny
from anny.face_segmentation import get_face_segmentation_mask
from soma import SOMALayer
import outfit_lib
ARM_ABDUCT = outfit_lib.ARM_ABDUCT_DEG if args.arm_abduct is None else args.arm_abduct

ADULT = dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5)
IDV11 = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.34, 0.33, 0.33]

# ----- SOMA joint names (77) = Kimodo BVH joints minus Root; index = row in local/global/T_world[1:] -----
SOMA77 = ['Hips','Spine1','Spine2','Chest','Neck1','Neck2','Head','HeadEnd','Jaw','LeftEye','RightEye',
 'LeftShoulder','LeftArm','LeftForeArm','LeftHand','LeftHandThumb1','LeftHandThumb2','LeftHandThumb3','LeftHandThumbEnd',
 'LeftHandIndex1','LeftHandIndex2','LeftHandIndex3','LeftHandIndex4','LeftHandIndexEnd',
 'LeftHandMiddle1','LeftHandMiddle2','LeftHandMiddle3','LeftHandMiddle4','LeftHandMiddleEnd',
 'LeftHandRing1','LeftHandRing2','LeftHandRing3','LeftHandRing4','LeftHandRingEnd',
 'LeftHandPinky1','LeftHandPinky2','LeftHandPinky3','LeftHandPinky4','LeftHandPinkyEnd',
 'RightShoulder','RightArm','RightForeArm','RightHand','RightHandThumb1','RightHandThumb2','RightHandThumb3','RightHandThumbEnd',
 'RightHandIndex1','RightHandIndex2','RightHandIndex3','RightHandIndex4','RightHandIndexEnd',
 'RightHandMiddle1','RightHandMiddle2','RightHandMiddle3','RightHandMiddle4','RightHandMiddleEnd',
 'RightHandRing1','RightHandRing2','RightHandRing3','RightHandRing4','RightHandRingEnd',
 'RightHandPinky1','RightHandPinky2','RightHandPinky3','RightHandPinky4','RightHandPinkyEnd',
 'LeftLeg','LeftShin','LeftFoot','LeftToeBase','LeftToeEnd','RightLeg','RightShin','RightFoot','RightToeBase','RightToeEnd']
S = {n: i for i, n in enumerate(SOMA77)}

# ----- SOMA -> Anny bone-label correspondence -----
MAP = {
    'Hips':'root',
    'Spine1':'spine05', 'Spine2':'spine03', 'Chest':'spine01',
    'Neck1':'neck01', 'Neck2':'neck02', 'Head':'head', 'Jaw':'jaw',
    'LeftEye':'eye.L', 'RightEye':'eye.R',
    'LeftShoulder':'clavicle.L', 'LeftArm':'upperarm01.L', 'LeftForeArm':'lowerarm01.L', 'LeftHand':'wrist.L',
    'RightShoulder':'clavicle.R','RightArm':'upperarm01.R','RightForeArm':'lowerarm01.R','RightHand':'wrist.R',
    'LeftLeg':'upperleg01.L', 'LeftShin':'lowerleg01.L', 'LeftFoot':'foot.L', 'LeftToeBase':'toe3-1.L',
    'RightLeg':'upperleg01.R','RightShin':'lowerleg01.R','RightFoot':'foot.R', 'RightToeBase':'toe3-1.R',
}
FINGER_MAP = {
    'LeftHandThumb1':'finger1-1.L','LeftHandThumb2':'finger1-2.L','LeftHandThumb3':'finger1-3.L',
    'LeftHandIndex1':'finger2-1.L','LeftHandIndex2':'finger2-2.L','LeftHandIndex3':'finger2-3.L',
    'LeftHandMiddle1':'finger3-1.L','LeftHandMiddle2':'finger3-2.L','LeftHandMiddle3':'finger3-3.L',
    'LeftHandRing1':'finger4-1.L','LeftHandRing2':'finger4-2.L','LeftHandRing3':'finger4-3.L',
    'LeftHandPinky1':'finger5-1.L','LeftHandPinky2':'finger5-2.L','LeftHandPinky3':'finger5-3.L',
    'RightHandThumb1':'finger1-1.R','RightHandThumb2':'finger1-2.R','RightHandThumb3':'finger1-3.R',
    'RightHandIndex1':'finger2-1.R','RightHandIndex2':'finger2-2.R','RightHandIndex3':'finger2-3.R',
    'RightHandMiddle1':'finger3-1.R','RightHandMiddle2':'finger3-2.R','RightHandMiddle3':'finger3-3.R',
    'RightHandRing1':'finger4-1.R','RightHandRing2':'finger4-2.R','RightHandRing3':'finger4-3.R',
    'RightHandPinky1':'finger5-1.R','RightHandPinky2':'finger5-2.R','RightHandPinky3':'finger5-3.R',
}
if not args.no_fingers:
    MAP.update(FINGER_MAP)

# ----- Anny default mesh + rig -----
m = anny.Anny()
BL = m.bone_labels
PARENT = list(m.bone_parents)                                          # (163,) anny hierarchy
bsc = m.get_phenotype_blendshape_coefficients(**ADULT, local_changes={})
rest = m.get_rest_model(bsc)
Rr = rest["rest_bone_poses"][0, :, :3, :3].double()                    # (163,3,3) anny rest world orient
NB = len(BL)

# anny bone idx -> soma joint idx  (mapped bones)
bone2soma = {}
for sname, bname in MAP.items():
    if bname in BL and sname in S:
        bone2soma[BL.index(bname)] = S[sname]
print(f"mapped {len(bone2soma)} anny bones (fingers={'off' if args.no_fingers else 'on'})")

# nearest mapped ancestor (soma joint) for every anny bone; None -> identity delta
def nearest_mapped_soma(b):
    cur = b
    while cur >= 0:
        if cur in bone2soma: return bone2soma[cur]
        cur = PARENT[cur]
    return None
anc_soma = [nearest_mapped_soma(b) for b in range(NB)]

# ----- SOMALayer: capture the internal world joint transforms T_world (the good motion) -----
layer = SOMALayer(identity_model_type="anny", device="cpu"); layer.eval()
d = np.load(args.npz)
local = torch.from_numpy(d["local_rot_mats"].astype(np.float32))       # (T,77,3,3)
root  = d["root_positions"].astype(np.float64)                          # (T,3)
T = local.shape[0]
ident = torch.tensor([IDV11], dtype=torch.float32)

cap = {}
bs = layer.batched_skinning
_orig_pose = bs.pose
def _cap_pose(*a, **k):
    k = dict(k); k["return_transforms"] = True
    out = _orig_pose(*a, **k)
    cap["T"] = out[1].detach().cpu().double().numpy()                  # (B,78,4,4)
    return out
bs.pose = _cap_pose
with torch.no_grad():
    layer(local[0].unsqueeze(0), ident, transl=torch.zeros(1, 3), pose2rot=False, absolute_pose=False)
bind = layer._cached_bind_transforms_world[0].double().numpy()         # (78,4,4) incl Root@0
Rbind = bind[:, :3, :3]                                                 # soma joint j -> row j+1
# SOMA world is Y-up, Anny native is Z-up: map a SOMA-world rotation into Anny's frame.
M = np.array([[1., 0, 0], [0, 0, -1], [0, 1, 0]])                       # (X,Y,Z)_soma -> (X,-Z,Y)_anny

# ----- vertical (pelvis bounce) from SOMA root translation -----
travel = root.max(0) - root.min(0)
fwd = int(np.argmax(travel))
vert = min([a for a in range(3) if a != fwd], key=lambda a: travel[a])
root_bounce = root[:, vert] - root[:, vert].mean()

# ----- topology: quads -> tris with UV, skin/eye groups -----
quad = np.asarray(m.faces.cpu()); ftci = np.asarray(m.face_texture_coordinate_indices.cpu())
tc = np.asarray(m.texture_coordinates.cpu())
# keep front/back separate: eye_front = the outer visible hemisphere (cornea/iris/pupil live
# here), eye_back = the inner hidden hemisphere (never has a pupil) -- used below to place a
# procedural pupil on the live-viewer export without needing a real iris shader/texture.
eye_front_mask = np.asarray(get_face_segmentation_mask(m, ["eye_front.L","eye_front.R"]).cpu()).astype(bool)
eye_back_mask = np.asarray(get_face_segmentation_mask(m, ["eye_back.L","eye_back.R"]).cpu()).astype(bool)
eye_mask = eye_front_mask | eye_back_mask
def q2t(f): return [(f[0],f[1],f[2]),(f[0],f[2],f[3])]
skin_faces, eye_faces, eye_front_faces = [], [], []
for qi in range(len(quad)):
    vt = q2t(quad[qi]); ut = q2t(ftci[qi])
    tris = [(vt[0],ut[0]),(vt[1],ut[1])]
    if eye_mask[qi]:
        eye_faces.extend(tris)
        if eye_front_mask[qi]: eye_front_faces.extend(tris)
    else:
        skin_faces.extend(tris)
tri_all = np.array([a for (a,_) in skin_faces] + [a for (a,_) in eye_faces], dtype=np.int64)

# ----- pose each selected frame -----
sel = np.linspace(0, T-1, args.frames).astype(int)
V_list = []
I3 = np.eye(3)
for k, t in enumerate(sel):
    with torch.no_grad():
        layer.pose(local[t].unsqueeze(0), transl=torch.zeros(1, 3), pose2rot=False, absolute_pose=False)
    Tw = cap["T"][0]                                                    # (78,4,4)
    # world delta per SOMA joint j:  dR[j] = Rw[j] . Rbind[j]^T   (bind index = j+1)
    dR = {}
    for j in set(v for v in anc_soma if v is not None):
        dR[j] = M @ (Tw[j+1, :3, :3] @ Rbind[j+1].T) @ M.T             # world delta, in Anny's frame
    D = [dR[anc_soma[b]] if anc_soma[b] is not None else I3 for b in range(NB)]
    # self-collision fix: hold both arms slightly outward so the hands swing beside the hips
    # instead of into the pelvis (D-selfcollision). MUST match dress_walk.py's identical call.
    D = outfit_lib.apply_arm_abduction(D, BL, PARENT, deg=ARM_ABDUCT)
    P = torch.eye(4, dtype=torch.float64).repeat(NB, 1, 1)
    for b in range(NB):
        Dp = D[PARENT[b]] if PARENT[b] >= 0 else I3
        Rrb = Rr[b].numpy()
        P[b, :3, :3] = torch.from_numpy(Rrb.T @ Dp.T @ D[b] @ Rrb)
    with torch.no_grad():
        out = m.forward(pose_parameters=P.unsqueeze(0), phenotype_kwargs=ADULT, pose_parameterization='local-bone')
    V = out["vertices"][0].double().cpu().numpy()                       # anny native (Z-up), meters
    Vb = np.stack([V[:, 0], V[:, 2] + root_bounce[t], -V[:, 1]], axis=1)  # Z-up -> Y-up + pelvis bounce
    V_list.append(Vb)
posed = np.asarray(V_list)                                             # (F,13718,3)

# walk-in-place: remove per-frame horizontal drift; keep vertical incl bounce; ground globally
h = posed[:, :, [0, 2]].mean(1, keepdims=True)
posed[:, :, 0] -= h[:, :, 0]; posed[:, :, 2] -= h[:, :, 1]
posed[..., 1] -= posed[..., 1].min()

# ----- write OBJ sequence -----
for k in range(len(sel)):
    with open(os.path.join(args.out, f"frame_{k:03d}.obj"), "w") as f:
        for x, y, z in posed[k]: f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for u, v in tc: f.write(f"vt {u:.6f} {v:.6f}\n")
        for name, group in (("skin", skin_faces), ("eye", eye_faces)):
            f.write(f"usemtl {name}\n")
            for (a,b,c),(ua,ub,uc) in group:
                f.write(f"f {a+1}/{ua+1} {b+1}/{ub+1} {c+1}/{uc+1}\n")
print(f"WROTE {len(sel)} OBJs -> {args.out}  (verts {posed.shape[1]})")

# ----- optional live-viewer export (DEFAULT topology -- has real eyeball geometry,
# unlike the SOMA-topology models the viewer used before this) -----
if args.stem:
    import json
    mo = os.path.join(os.path.dirname(__file__), "motion_out")
    os.makedirs(mo, exist_ok=True)
    np.save(os.path.join(mo, f"{args.stem}_verts.npy"), posed.astype(np.float32))
    np.save(os.path.join(mo, f"{args.stem}_faces.npy"), tri_all.astype(np.uint32))

    # ----- procedural pupil placement: the eye vertex whose REST-pose outward normal is
    # most aligned with its side's mean eye_front normal is the "most outward-facing"
    # point of the cornea bulge -- a reasonable stand-in for the pupil without a real
    # gaze/iris texture. Sclera = everything else (all eye_back + peripheral eye_front).
    V0 = posed[0]                                                    # rest-ish frame, (13718,3)
    eye_vidx = np.unique(np.asarray([a for (a,_) in eye_faces]).reshape(-1))
    front_vidx = np.unique(np.asarray([a for (a,_) in eye_front_faces]).reshape(-1)) if eye_front_faces else eye_vidx
    e1 = V0[tri_all[:,1]] - V0[tri_all[:,0]]; e2 = V0[tri_all[:,2]] - V0[tri_all[:,0]]
    fn = np.cross(e1, e2)
    vn = np.zeros_like(V0)
    for k in range(3): np.add.at(vn, tri_all[:,k], fn)
    vn /= np.clip(np.linalg.norm(vn, axis=1, keepdims=True), 1e-8, None)

    side = np.sign(V0[front_vidx, 0] - V0[eye_vidx, 0].mean())        # split L/R by X sign
    pupil_w = {}
    for s in (-1, 1):
        idx = front_vidx[side == s]
        if len(idx) == 0: continue
        outward = vn[idx].mean(0); outward /= (np.linalg.norm(outward) + 1e-8)
        w = np.clip(vn[idx] @ outward, 0, 1) ** 10                    # sharp -> a small pupil, not a half-sphere
        for i, wi in zip(idx.tolist(), w.tolist()): pupil_w[i] = wi
    eyemeta = {"idx": eye_vidx.tolist(), "pupilW": [pupil_w.get(int(i), 0.0) for i in eye_vidx]}
    with open(os.path.join(mo, f"{args.stem}_eyemeta.json"), "w") as f:
        json.dump(eyemeta, f)
    print(f"WROTE {args.stem}_verts/_faces.npy + _eyemeta.json ({len(eye_vidx)} eye verts, "
          f"{sum(1 for w in eyemeta['pupilW'] if w>0.3)} strong-pupil) -> {mo}")

# ----- optional gray pyrender preview -----
if args.preview:
    import trimesh, pyrender, imageio, math
    def look_at(eye, ctr, up):
        f = ctr-eye; f/=np.linalg.norm(f)+1e-9; s=np.cross(f,up); s/=np.linalg.norm(s)+1e-9; u=np.cross(s,f)
        M=np.eye(4); M[:3,0]=s; M[:3,1]=u; M[:3,2]=-f; M[:3,3]=eye; return M
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.8,0.66,0.58,1], metallicFactor=0, roughnessFactor=0.75)
    ctr = posed.reshape(-1,3).mean(0); ctr[1] = posed[...,1].mean()
    H = posed[...,1].max() - posed[...,1].min(); frames=[]
    for k in range(len(sel)):
        tm = trimesh.Trimesh(vertices=posed[k].astype(np.float32), faces=tri_all, process=False)
        sc = pyrender.Scene(bg_color=[0.05,0.05,0.06,1], ambient_light=[0.35,0.35,0.38])
        sc.add(pyrender.Mesh.from_trimesh(tm, material=mat, smooth=True))
        a=math.radians(35); eye=ctr.astype(float).copy(); eye[2]+=2.6*H*math.cos(a); eye[0]+=2.6*H*math.sin(a); eye[1]+=0.15*H
        pose=look_at(eye, ctr.astype(float), np.array([0.,1,0]))
        sc.add(pyrender.PerspectiveCamera(yfov=np.pi/4.5), pose=pose)
        sc.add(pyrender.DirectionalLight(color=np.ones(3), intensity=4.2), pose=pose)
        r=pyrender.OffscreenRenderer(480,480); col,_=r.render(sc); r.delete(); frames.append(col)
    gp=os.path.join(args.out,"preview_gray.gif"); imageio.mimsave(gp, frames, fps=20, loop=0); print("WROTE", gp)
