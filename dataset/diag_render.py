import os, sys, math, numpy as np, trimesh, pyrender, imageio
os.environ.pop("PYOPENGL_PLATFORM", None)
seq = np.load("motion_out/cmu_walk_verts.npy"); tri = np.load("motion_out/faces.npy")
R = 300
def look(eye, c, up):
    eye=np.asarray(eye,float); c=np.asarray(c,float); up=np.asarray(up,float)
    f=(c-eye); f/=np.linalg.norm(f)+1e-9; s=np.cross(f,up); s/=np.linalg.norm(s)+1e-9; u=np.cross(s,f)
    m=np.eye(4); m[:3,0]=s;m[:3,1]=u;m[:3,2]=-f;m[:3,3]=eye; return m
mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[0.8,0.66,0.58,1],metallicFactor=0,roughnessFactor=0.8)
rr=pyrender.OffscreenRenderer(R,R)
def render(v, eye_dir, label):
    c=v.mean(0); ext=np.abs(v-c).max()*2.4
    eye=c+np.array(eye_dir)*ext
    sc=pyrender.Scene(bg_color=[0.05,0.05,0.06,1],ambient_light=[0.4,0.4,0.4])
    sc.add(pyrender.Mesh.from_trimesh(trimesh.Trimesh(v,tri,process=False),material=mat,smooth=True))
    cam=pyrender.PerspectiveCamera(yfov=np.pi/4); sc.add(cam,pose=look(eye,c,[0,0,1] if eye_dir[2]==0 else [0,1,0]))
    sc.add(pyrender.DirectionalLight(color=np.ones(3),intensity=4),pose=look(eye,c,[0,0,1] if eye_dir[2]==0 else [0,1,0]))
    col,_=rr.render(sc); return col[...,:3]
# a clearly-spread frame; views: FRONT(-Y), SIDE(+X), TOP(+Z)
tiles=[]
for fidx in (15, 37):
    v=seq[fidx]
    tiles.append(np.concatenate([render(v,[0,-1,0],"front"), render(v,[1,0,0],"side"), render(v,[0,0,1],"top")],axis=1))
imageio.imwrite("motion_out/diag.png", np.concatenate(tiles,axis=0))
rr.delete()
print("WROTE motion_out/diag.png  rows=frames[15,37] cols=[FRONT(-Y) | SIDE(+X) | TOP(+Z)]")
# also: how far does the body travel per axis over the clip? (walk direction)
print("root-ish travel per axis (mean pos range):", (seq.mean(1).max(0)-seq.mean(1).min(0)).round(3))
