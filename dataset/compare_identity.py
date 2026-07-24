import os, numpy as np, torch, math
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
from soma import SOMALayer
import anny.models.phenotype as _ph
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(f):
            def g(self, *a, local_changes=None, **k): return f(self, *a, local_changes=(local_changes or {}), **k)
            return g
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

layer = SOMALayer(identity_model_type="anny", device="cpu"); layer.eval()
faces = layer.faces
faces_np = faces.detach().cpu().numpy() if hasattr(faces,"detach") else np.asarray(faces)
tri = faces_np.reshape(-1, faces_np.shape[-1]).astype(np.int64)
if tri.shape[1] == 4:
    tri = np.concatenate([tri[:,[0,1,2]], tri[:,[0,2,3]]], axis=0)

# labels: [gender, age, muscle, weight, height, proportions, cupsize, firmness, african, asian, caucasian]
def vec(gender=.5, age=.5, muscle=.5, weight=.5, height=.5, proportions=.5, cup=.5, firm=.5, afr=.34, asn=.33, cau=.33):
    return torch.tensor([[gender,age,muscle,weight,height,proportions,cup,firm,afr,asn,cau]], dtype=torch.float32)

variants = [
    ("zeros (age=0 baby)", torch.zeros(1,11)),
    ("adult neutral",      vec()),
    ("adult male",         vec(gender=1.0, muscle=.6, height=.6, cup=0)),
    ("adult female",       vec(gender=0.0, muscle=.4, height=.4)),
]

import trimesh, pyrender, imageio
def render_front(verts, size=380):
    v = verts
    ext = v.max(0)-v.min(0); up_i = 1; horiz=[0,2]
    c = v.mean(0); H = float(ext[up_i])
    up = np.array([0.,1.,0.])
    eye = c.astype(np.float64).copy(); eye[2] += 2.6*H; eye[1] += 0.05*H
    f=(c-eye); f/=np.linalg.norm(f); s=np.cross(f,up); s/=np.linalg.norm(s); u=np.cross(s,f)
    pose=np.eye(4); pose[:3,0]=s; pose[:3,1]=u; pose[:3,2]=-f; pose[:3,3]=eye
    m=trimesh.Trimesh(vertices=v.astype(np.float32), faces=tri, process=False)
    sc=pyrender.Scene(bg_color=[0.05,0.05,0.06,1.0], ambient_light=[0.4,0.4,0.42])
    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.80,0.66,0.58,1.0], metallicFactor=0, roughnessFactor=0.75)
    sc.add(pyrender.Mesh.from_trimesh(m, material=mat, smooth=True))
    sc.add(pyrender.PerspectiveCamera(yfov=np.pi/4.5), pose=pose)
    sc.add(pyrender.DirectionalLight(color=np.ones(3), intensity=4.0), pose=pose)
    r=pyrender.OffscreenRenderer(size,size); col,_=r.render(sc); r.delete()
    return col

tiles=[]
for name, iv in variants:
    poses=torch.zeros(1,77,3); transl=torch.zeros(1,3)
    with torch.no_grad():
        out=layer(poses, iv, transl=transl)
    v=out["vertices"][0].numpy()
    ext=v.max(0)-v.min(0)
    ratio = ext[1]/max(ext[0],1e-6)
    print(f"{name:22s} bbox={ext.round(3)}  height/armspan={ratio:.2f}")
    tiles.append(render_front(v))
grid=np.concatenate(tiles, axis=1)
imageio.imwrite("motion_out/identity_compare.png", grid)
print("WROTE motion_out/identity_compare.png")
