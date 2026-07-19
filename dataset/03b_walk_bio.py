#!/usr/bin/env python3
"""
03b_walk_bio.py — a MUCH better procedural walk than 03 (still procedural, but applies real gait
biomechanics from D67 so it stops looking like a doll): root forward translation + COM bounce,
posterior knee bend, pelvis yaw + lateral sway, spine counter-rotation, contralateral arm swing.
Renders an animated GIF (walk.gif) + a strip, from a camera that tracks the advancing body.

    conda run -n 4dgs-data python 03b_walk_bio.py --frames 28 --res 320 --kneesign 1
Flip --kneesign if the knees bend the wrong way (forward instead of heel-up-and-back).
"""
import argparse, os, sys, math, numpy as np, torch, trimesh, pyrender, imageio, anny

B = dict(ul_L=2, ul_R=22, ll_L=4, ll_R=24, ua_L=50, ua_R=76, la_L=52, la_R=78, root=0, spine=44)

def pick_backend():
    if sys.platform.startswith("linux"): os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    else: os.environ.pop("PYOPENGL_PLATFORM", None)

def look_at(eye, target, up):
    eye, target, up = map(lambda v: np.asarray(v, np.float64), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f) + 1e-12
    s = np.cross(f, up); s /= np.linalg.norm(s) + 1e-12
    u = np.cross(s, f); m = np.eye(4); m[:3,0]=s; m[:3,1]=u; m[:3,2]=-f; m[:3,3]=eye
    return m

def rodrigues(axis, ang):
    a = np.asarray(axis, np.float64); a = a/(np.linalg.norm(a)+1e-9)
    x,y,z = a; c,s = math.cos(ang), math.sin(ang); C = 1-c
    return np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s],
                     [y*x*C+z*s, c+y*y*C, y*z*C-x*s],
                     [z*x*C-y*s, z*y*C+x*s, c+z*z*C]], np.float64)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=28)
    ap.add_argument("--res", type=int, default=320)
    ap.add_argument("--kneesign", type=float, default=1.0)
    ap.add_argument("--out", default="motion_out")
    a = ap.parse_args()
    pick_backend(); os.makedirs(a.out, exist_ok=True)

    model = anny.Anny(); model.eval()
    with torch.no_grad(): out = model()
    rest_verts = out["vertices"][0].numpy().astype(np.float32)
    tri = np.asarray(model.get_triangular_faces()).reshape(-1,3).astype(np.int64)
    rest_pose = model.get_pose_parameterization(out, "local-bone").detach().clone()
    rest_world = out["rest_bone_poses"][0].numpy()

    # world axes from the rest bbox: up = tallest axis; lateral = X; facing = -Y (body front)
    ext = rest_verts.max(0)-rest_verts.min(0); up_i = int(np.argmax(ext))
    up = np.zeros(3); up[up_i]=1.0; height = float(ext[up_i])
    lateral = np.array([1.0,0,0]); facing = np.array([0,-1.0,0])
    def laxis(b, wax): return rest_world[b][:3,:3].T @ wax

    KS = a.kneesign
    def walk_pose(phase):
        p = rest_pose.clone()
        def setb(b, wax, ang):
            p[0, b, :3, :3] = torch.tensor(rodrigues(laxis(b, wax), ang), dtype=p.dtype)
        LEG, KNEE, ARM, ELB = 0.55, 1.05, 0.42, 0.35
        # legs swing fwd/back about lateral axis (antiphase)
        setb(B["ul_R"], lateral,  LEG*math.sin(phase));         setb(B["ul_L"], lateral,  LEG*math.sin(phase+math.pi))
        # knees: posterior bend, peak during that leg's SWING (heel up-and-back). KS flips direction.
        kf = lambda ph: max(0.0, math.sin(ph))**1.3
        setb(B["ll_R"], lateral, KS*KNEE*kf(phase+math.pi));    setb(B["ll_L"], lateral, KS*KNEE*kf(phase))
        # arms contralateral (right arm forward with left leg)
        setb(B["ua_R"], lateral, ARM*math.sin(phase+math.pi));  setb(B["ua_L"], lateral, ARM*math.sin(phase))
        setb(B["la_R"], lateral, -ELB*max(0,math.sin(phase+math.pi))); setb(B["la_L"], lateral, -ELB*max(0,math.sin(phase)))
        # pelvis yaw (root) + spine counter-rotation (keep shoulders facing forward)
        yaw = 0.14*math.sin(phase)
        setb(B["root"], up, yaw);  setb(B["spine"], up, -1.4*yaw)
        return p

    T = a.frames; V = rest_verts.shape[0]
    seq = np.zeros((T, V, 3), np.float32)
    for f in range(T):
        phase = 2*math.pi*f/T
        with torch.no_grad():
            v = model(pose_parameters=walk_pose(phase), pose_parameterization="local-bone")["vertices"][0].numpy()
        # root motion: forward translation + lateral weight-shift (1x/stride) + vertical bounce (2x/stride)
        fwd    = 1.0 * (f/T)                          # advance ~1 stride across the cycle
        sway   = 0.035 * math.sin(phase)             # weight shift onto stance leg
        bounce = 0.045 * abs(math.sin(phase))        # COM highest at mid-stance, 2x per stride
        seq[f] = v + fwd*facing + sway*lateral + bounce*up
    np.save(os.path.join(a.out,"walk_bio_verts.npy"), seq); np.save(os.path.join(a.out,"faces.npy"), tri)

    # tracking side-3/4 camera: recompute center per frame so the advancing body stays framed
    cam = pyrender.PerspectiveCamera(yfov=np.pi/4); key = pyrender.DirectionalLight(color=np.ones(3), intensity=4.0)
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80,0.66,0.58,1.0], metallicFactor=0, roughnessFactor=0.8)
    r = pyrender.OffscreenRenderer(a.res, a.res); radius = 2.1*height
    frames = []
    for f in range(T):
        v = seq[f]; c = v.mean(0)
        eye = c.astype(np.float64).copy()
        eye[0] += radius*math.cos(0.5); eye[1] += radius*math.sin(0.5); eye[up_i] += 0.10*height
        pose = look_at(eye, c, up)
        sc = pyrender.Scene(bg_color=[0.05,0.05,0.06,1.0], ambient_light=[0.35,0.35,0.38])
        sc.add(pyrender.Mesh.from_trimesh(trimesh.Trimesh(v, tri, process=False), material=mat, smooth=True))
        sc.add(cam, pose=pose); sc.add(key, pose=pose)
        col,_ = r.render(sc); frames.append(col[...,:3])
    r.delete()

    imageio.mimsave(os.path.join(a.out,"walk.gif"), frames, duration=1000/14, loop=0)
    K = 8; idx = np.linspace(0,T-1,K).round().astype(int)
    strip = np.concatenate([frames[i] for i in idx], axis=1)
    imageio.imwrite(os.path.join(a.out,"walk_strip_bio.png"), strip)
    print(f"WROTE {a.out}/walk.gif ({T} frames), walk_strip_bio.png, walk_bio_verts.npy")

if __name__ == "__main__":
    main()
