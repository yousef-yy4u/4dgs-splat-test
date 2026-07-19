#!/usr/bin/env python3
"""
cmu_to_anny.py — retarget a CMU MoCap BVH walk onto the Anny rig and render it (clean, no GPU).
This is the reusable retarget we'll also use for GEM-X / Kimodo-RP later.

Pipeline: parse BVH -> FK to per-joint WORLD rotations -> map CMU joints to Anny bones ->
delta-rotation retarget kernel (D67): P[b] = R_restAnny[b]^T · (C·R_world_cmu·C^T) · R_restAnny[b],
where C = Y-up(BVH) -> Z-up(Anny). Root translation scaled to meters. Renders walk.gif + Blender verts.

    conda run -n 4dgs-data python cmu_to_anny.py --bvh cmu_walk.bvh --step 4 --nmax 60 --yaw 0
Flags: --yaw spins the character (deg) if it faces away; --step decimates frames; --nmax caps frames.
"""
import argparse, os, sys, math, numpy as np, torch, trimesh, pyrender, imageio, anny

def Rx(a): c,s=math.cos(a),math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]],float)
def Ry(a): c,s=math.cos(a),math.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]],float)
def Rz(a): c,s=math.cos(a),math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]],float)
AXR = {"Xrotation":Rx, "Yrotation":Ry, "Zrotation":Rz}

def parse_bvh(path):
    lines = open(path).read().split("\n")
    names, parents, channels, offsets = [], [], [], []
    pstack, cur, in_end = [], -1, False
    i = 0
    while i < len(lines):
        t = lines[i].strip().split()
        if not t: i += 1; continue
        k = t[0]
        if k in ("ROOT", "JOINT"):
            names.append(t[1]); parents.append(pstack[-1] if pstack else -1)
            channels.append([]); offsets.append((0,0,0)); cur = len(names)-1; in_end = False
        elif k == "End": in_end = True
        elif k == "OFFSET":
            if not in_end: offsets[cur] = tuple(float(x) for x in t[1:4])
        elif k == "CHANNELS": channels[cur] = t[2:]
        elif k == "{": pstack.append(cur)
        elif k == "}": pstack.pop() if pstack else None; in_end = False
        elif k == "Frames:": pass
        elif k == "Frame" and len(t) >= 3 and t[1] == "Time:":
            mot = [list(map(float, ln.split())) for ln in lines[i+1:] if ln.strip()]
            return names, parents, channels, np.array(offsets, float), np.array(mot, float)
        i += 1
    raise RuntimeError("no MOTION block")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bvh", default="cmu_walk.bvh")
    ap.add_argument("--step", type=int, default=4)
    ap.add_argument("--nmax", type=int, default=60)
    ap.add_argument("--yaw", type=float, default=0.0)
    ap.add_argument("--res", type=int, default=320)
    ap.add_argument("--out", default="motion_out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if sys.platform.startswith("linux"): os.environ.setdefault("PYOPENGL_PLATFORM","egl")
    else: os.environ.pop("PYOPENGL_PLATFORM", None)

    names, parents, channels, offsets, motion = parse_bvh(a.bvh)
    name2i = {n:i for i,n in enumerate(names)}
    # per-joint channel column ranges
    col, ranges = 0, []
    for ch in channels:
        ranges.append((col, col+len(ch))); col += len(ch)

    def local_rots_and_root(frame):
        vals = motion[frame]
        Rloc = [np.eye(3)]*len(names); root_pos = np.zeros(3)
        Rloc = list(Rloc)
        for j,(c0,c1) in enumerate(ranges):
            R = np.eye(3)
            for ci,cn in enumerate(channels[j]):
                v = vals[c0+ci]
                if cn.endswith("rotation"): R = R @ AXR[cn](math.radians(v))
                elif cn == "Xposition": root_pos[0] = v
                elif cn == "Yposition": root_pos[1] = v
                elif cn == "Zposition": root_pos[2] = v
            Rloc[j] = R
        return Rloc, root_pos

    def world_rots(Rloc):
        Rw = [None]*len(names)
        for j in range(len(names)):
            Rw[j] = Rloc[j] if parents[j] < 0 else Rw[parents[j]] @ Rloc[j]
        return Rw

    # CMU skeleton height (rest = zero rotations => world pos = cumulative offsets) for translation scale
    wp = [None]*len(names)
    for j in range(len(names)):
        wp[j] = np.array(offsets[j]) if parents[j] < 0 else wp[parents[j]] + np.array(offsets[j])
    wp = np.array(wp); cmu_h = wp[:,1].max() - wp[:,1].min()

    # Anny
    model = anny.Anny(); model.eval()
    with torch.no_grad(): out = model()
    rest_verts = out["vertices"][0].numpy().astype(np.float32)
    tri = np.asarray(model.get_triangular_faces()).reshape(-1,3).astype(np.int64)
    rest_pose = model.get_pose_parameterization(out, "local-bone").detach().clone()
    restA = out["rest_bone_poses"][0].numpy()             # (163,4,4)
    anny_h = float(rest_verts[:,2].max() - rest_verts[:,2].min())
    scale = anny_h / cmu_h

    CMU2ANNY = {
        "Hips":0, "LeftUpLeg":2, "LeftLeg":4, "LeftFoot":6,
        "RightUpLeg":22, "RightLeg":24, "RightFoot":26,
        "LowerBack":47, "Spine":44, "Spine1":43, "Neck":100, "Head":103,
        # arms: upperarm swing only (clavicle/elbow/wrist transfer over-rotated → left at rest for a clean swing)
        "LeftArm":50, "RightArm":76,
    }
    C = Rz(math.radians(a.yaw)) @ Rx(math.radians(90.0))   # Y-up->Z-up (+ optional yaw)

    frames = list(range(0, min(len(motion), a.step*a.nmax), a.step))
    # REFERENCE FRAME: anchor the retarget to CMU's OWN pose at frame 0 (not its T-bind), so Anny's rest
    # (A-pose) maps to CMU-frame-0 and each bone plays the DEVIATION from there → fixes T-vs-A arm/leg
    # placement. delta_j = Rw_current[j] · Rw0[j]^-1.
    Rw0 = world_rots(local_rots_and_root(frames[0])[0])
    seq = np.zeros((len(frames), rest_verts.shape[0], 3), np.float32)
    for fi, fr in enumerate(frames):
        Rloc, root_pos = local_rots_and_root(fr)
        Rw = world_rots(Rloc)
        P = rest_pose.clone()
        for cn, b in CMU2ANNY.items():
            j = name2i.get(cn)
            if j is None: continue
            dR = Rw[j] @ Rw0[j].T                       # deviation from CMU frame-0 pose
            Ranny_world = C @ dR @ C.T
            Rb = restA[b][:3,:3]
            P[0, b, :3, :3] = torch.tensor(Rb.T @ Ranny_world @ Rb, dtype=P.dtype)
        with torch.no_grad():
            v = model(pose_parameters=P, pose_parameterization="local-bone")["vertices"][0].numpy()
        world_t = C @ (root_pos * scale)
        seq[fi] = v + (world_t - (C @ (motion[frames[0]][:3]*scale)))   # start at origin
    np.save(os.path.join(a.out,"cmu_walk_verts.npy"), seq); np.save(os.path.join(a.out,"faces.npy"), tri)

    # tracking side-3/4 camera -> GIF + strip
    ext = rest_verts.max(0)-rest_verts.min(0); up_i=int(np.argmax(ext)); up=np.zeros(3); up[up_i]=1
    height=float(ext[up_i]); radius=2.2*height
    cam=pyrender.PerspectiveCamera(yfov=np.pi/4); key=pyrender.DirectionalLight(color=np.ones(3),intensity=4.0)
    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80,0.66,0.58,1.0],metallicFactor=0,roughnessFactor=0.8)
    r=pyrender.OffscreenRenderer(a.res,a.res); imgs=[]
    def look(eye,c,u):
        f=(c-eye); f/=np.linalg.norm(f)+1e-9; s=np.cross(f,u); s/=np.linalg.norm(s)+1e-9; uu=np.cross(s,f)
        m=np.eye(4); m[:3,0]=s; m[:3,1]=uu; m[:3,2]=-f; m[:3,3]=eye; return m
    for v in seq:
        c=v.mean(0); eye=c.astype(float).copy()
        eye[0]+=radius*math.cos(0.5); eye[1]+=radius*math.sin(0.5); eye[up_i]+=0.12*height
        sc=pyrender.Scene(bg_color=[0.05,0.05,0.06,1.0],ambient_light=[0.35,0.35,0.38])
        sc.add(pyrender.Mesh.from_trimesh(trimesh.Trimesh(v,tri,process=False),material=mat,smooth=True))
        sc.add(cam,pose=look(eye,c,up)); sc.add(key,pose=look(eye,c,up))
        col,_=r.render(sc); imgs.append(col[...,:3])
    r.delete()
    imageio.mimsave(os.path.join(a.out,"cmu_walk.gif"), imgs, duration=1000/15, loop=0)
    K=8; idx=np.linspace(0,len(imgs)-1,K).round().astype(int)
    imageio.imwrite(os.path.join(a.out,"cmu_walk_strip.png"), np.concatenate([imgs[i] for i in idx],axis=1))
    print(f"joints mapped={len(CMU2ANNY)} cmu_h={cmu_h:.2f} scale={scale:.4f} frames={len(frames)}")
    print(f"WROTE {a.out}/cmu_walk.gif, cmu_walk_strip.png, cmu_walk_verts.npy")

if __name__ == "__main__":
    main()
