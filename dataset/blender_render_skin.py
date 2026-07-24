#!/usr/bin/env python3
"""Headless Blender Cycles render of the textured Anny body — PHOTOREAL appearance.
    /root/blender/blender --background --python blender_render_skin.py -- \
        --obj anny_adult.obj --tex <mpfb2/textures dir> --out photoreal --frames 36 --size 640

Skin: procedural (warm base + tonal variation + lip-mask redness + reddish SUBSURFACE + sss/pore bump).
Eyes: 'eye' material group -> sclera/iris/pupil from surface-normal·gaze + glossy cornea.
Turntable orbit; emits PNG frames. Supports a single static frame or a posed OBJ sequence (--seq dir).
"""
import bpy, sys, os, math, glob, argparse, mathutils

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--obj", default=None, help="single static OBJ (turntable)")
ap.add_argument("--seq", default=None, help="dir of frame_*.obj (posed motion) -> render each, fixed cam")
ap.add_argument("--tex", required=True, help="mpfb2/textures dir (sss.png, mpfb_lips.jpg)")
ap.add_argument("--out", required=True)
ap.add_argument("--frames", type=int, default=36)
ap.add_argument("--size", type=int, default=640)
ap.add_argument("--samples", type=int, default=200)
ap.add_argument("--azim", type=float, default=35.0, help="fixed cam azimuth for --seq (deg)")
ap.add_argument("--closeup", action="store_true", help="frame the HEAD (verify eyes/face)")
ap.add_argument("--poses", default=None, help="turntable: also dump camera intrinsics+extrinsics JSON here (for gsplat fitting)")
ap.add_argument("--elevs", default="0", help="turntable (rig=ring): comma-separated elevation angles in "
                 "degrees (e.g. '-15,15,45,75'), one ring per value, --frames split evenly across rings. "
                 "D87: the original single-ring (elev=0) turntable under-constrains the top of the head and "
                 "the underarm/sole regions no ring ever looks at directly -- multiple elevations is the "
                 "same idea as the live viewer's own multi-layer capture rig UI, just applied to this "
                 "offline PoC fit for the first time. Superseded for quality by --rig shells (D98).")
# --- D98: multi-shell, height-layered capture rig ---------------------------------
# The --elevs turntable (D87) is a SINGLE radius: every ring shares one distance and all rings
# converge on the body CENTER, so the top/bottom rings hit the torso at a steep angle and no
# camera ever frames the legs / hips / chest / head HEAD-ON. The shells rig instead stacks
# horizontal RING LAYERS by camera HEIGHT (legs->head), each looking at its OWN band so every
# body region is seen straight-on, and repeats the whole stack at a CLOSER radius for fine
# detail (face/hands). Intrinsics stay identical across all views (one lens) so transforms.json's
# single shared K is exact for every frame -- only the extrinsic (cam.matrix_world) varies.
ap.add_argument("--rig", choices=["ring", "shells"], default="ring",
                help="ring = legacy --elevs turntable; shells = D98 multi-shell height-layer rig.")
ap.add_argument("--layers", type=int, default=4, help="rig=shells: horizontal ring layers stacked by "
                "camera HEIGHT from legs to head (each a full azimuth ring looking at its own band).")
ap.add_argument("--az", type=int, default=24, help="rig=shells: azimuth samples per ring (full 360deg).")
ap.add_argument("--radii", default="auto", help="rig=shells: comma-separated shell radii in metres "
                "(e.g. '3.0,1.6'); 'auto' = [framing_radius, 0.55*framing_radius] (outer frames the whole "
                "body, inner is the fine-detail shell).")
ap.add_argument("--layer-frac", default="0.15,0.90", help="rig=shells: lo,hi look-at heights as a fraction "
                "of body height (0=feet,1=crown); layers are spaced evenly between them.")
ap.add_argument("--elev-spread", type=float, default=0.16, help="rig=shells: camera-height elevation offset "
                "(fraction of body height) applied +/- across layers so the bottom layer looks slightly UP "
                "(underarm/sole/chin coverage) and the top layer slightly DOWN (top-of-head coverage); the "
                "middle layers stay ~head-on. 0 = perfectly horizontal every layer.")
# Optional REAL PBR skin (D100 SMOKEWORKS, MakeHuman UV drop-in). When --skin_basecolor is
# given, build_skin() swaps its procedural noise base for the real 4K BaseColor (+ optional
# Normal / ORM-roughness maps), so a free 3DGS fit can show REAL pore/surface detail instead
# of only sharper geometry off a smooth CG source. Default (no flag) = unchanged procedural skin.
ap.add_argument("--skin_basecolor", default=None, help="real PBR base-color texture (MakeHuman UV)")
ap.add_argument("--skin_normal", default=None, help="real PBR normal map (raw, non-color)")
ap.add_argument("--skin_orm", default=None, help="real PBR occlusion/roughness/metallic map (green=roughness)")
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)
SSS = os.path.join(args.tex, "sss.png")
LIPS = os.path.join(args.tex, "mpfb_lips.jpg")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = args.size
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Punchy'
except Exception: scene.view_settings.view_transform = 'Filmic'

# GPU
prefs = bpy.context.preferences.addons['cycles'].preferences
dev = "CPU"
for want in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = want; prefs.get_devices()
        if [d for d in prefs.devices if d.type == want]:
            for d in prefs.devices: d.use = (d.type == want)
            scene.cycles.device = 'GPU'; dev = want; break
    except Exception as e: print("dev", want, e)
print(f"[blender] device={dev}")

def tex_node(nt, path, colorspace='Non-Color'):
    n = nt.nodes.new("ShaderNodeTexImage")
    try:
        n.image = bpy.data.images.load(path); n.image.colorspace_settings.name = colorspace
    except Exception as e: print("tex load warn", path, e)
    return n

def build_skin(mat):
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    # ---- REAL PBR skin path (D100 drop-in): real BaseColor/Normal/ORM on the MakeHuman UV ----
    if args.skin_basecolor:
        bc = tex_node(nt, args.skin_basecolor, colorspace='sRGB')
        nt.links.new(uv.outputs["UV"], bc.inputs["Vector"])
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        for k, v in (("Subsurface Weight", 0.18), ("Subsurface Scale", 0.05)):
            try: bsdf.inputs[k].default_value = v
            except Exception: pass
        try: bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.30, 0.18)
        except Exception: pass
        if args.skin_orm:
            orm = tex_node(nt, args.skin_orm, colorspace='Non-Color')
            nt.links.new(uv.outputs["UV"], orm.inputs["Vector"])
            sep = nt.nodes.new("ShaderNodeSeparateColor")           # G = roughness
            nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        else:
            bsdf.inputs["Roughness"].default_value = 0.5
        if args.skin_normal:
            nm = tex_node(nt, args.skin_normal, colorspace='Non-Color')
            nt.links.new(uv.outputs["UV"], nm.inputs["Vector"])
            nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 1.0
            nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return
    # base tonal variation: mix two skin tones by large-scale noise
    n_big = nt.nodes.new("ShaderNodeTexNoise"); n_big.inputs["Scale"].default_value = 3.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.52, 0.29, 0.21, 1)   # deeper cooler skin
    ramp.color_ramp.elements[1].color = (0.70, 0.42, 0.31, 1)   # warmer skin
    nt.links.new(n_big.outputs["Fac"], ramp.inputs["Fac"])
    # lips redder via mask
    lipmix = nt.nodes.new("ShaderNodeMixRGB")
    lipmix.inputs["Color2"].default_value = (0.62, 0.24, 0.22, 1)   # lip red
    lipm = tex_node(nt, LIPS)
    nt.links.new(uv.outputs["UV"], lipm.inputs["Vector"])
    nt.links.new(ramp.outputs["Color"], lipmix.inputs["Color1"])
    nt.links.new(lipm.outputs["Color"], lipmix.inputs["Fac"])
    nt.links.new(lipmix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.52
    for k, v in (("Subsurface Weight", 0.22), ("Subsurface Scale", 0.055)):
        try: bsdf.inputs[k].default_value = v
        except Exception: pass
    try: bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.30, 0.18)
    except Exception: pass
    # bump: sss detail map + fine pores
    sss = tex_node(nt, SSS); nt.links.new(uv.outputs["UV"], sss.inputs["Vector"])
    pores = nt.nodes.new("ShaderNodeTexNoise"); pores.inputs["Scale"].default_value = 340.0
    mixb = nt.nodes.new("ShaderNodeMixRGB"); mixb.inputs["Fac"].default_value = 0.35
    nt.links.new(sss.outputs["Color"], mixb.inputs["Color1"])
    nt.links.new(pores.outputs["Fac"], mixb.inputs["Color2"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.22
    nt.links.new(mixb.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

def build_eye(mat):
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = (0.0, -1.0, 0.0)          # gaze = world -Y (face forward)
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    # Fac = normal.gaze in [~0.4 .. 1.0] over the visible eye front; 1.0 = dead-center.
    # WIDE iris covering most of the visible front, a small dark pupil, and a DIM sclera so the
    # eye doesn't read as a bright speck at full-body distance. Dark limbal ring at the sclera edge.
    cr.elements[0].position = 0.0;   cr.elements[0].color = (0.42, 0.40, 0.39, 1)   # sclera (dim, not white)
    e = cr.elements.new(0.62);  e.color = (0.42, 0.40, 0.39, 1)                      # hold sclera
    e = cr.elements.new(0.70);  e.color = (0.06, 0.04, 0.02, 1)                      # dark limbal ring
    e = cr.elements.new(0.76);  e.color = (0.28, 0.17, 0.08, 1)                      # iris outer (brown)
    e = cr.elements.new(0.90);  e.color = (0.40, 0.25, 0.12, 1)                      # iris mid (brown)
    e = cr.elements.new(0.965); e.color = (0.22, 0.13, 0.06, 1)                      # iris inner
    e = cr.elements.new(0.982); e.color = (0.01, 0.01, 0.01, 1)                      # pupil edge
    cr.elements[-1].position = 1.0; cr.elements[-1].color = (0.01, 0.01, 0.01, 1)    # pupil center
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(dot.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.10               # wet, glossy cornea
    try: bsdf.inputs["Specular IOR Level"].default_value = 0.7
    except Exception: pass
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

def apply_materials(obj):
    for slot in obj.material_slots:
        nm = (slot.name or "").lower()
        mat = slot.material or bpy.data.materials.new(nm)
        slot.material = mat
        (build_eye if "eye" in nm else build_skin)(mat)
    if not obj.material_slots:   # single material fallback
        mat = bpy.data.materials.new("skin"); build_skin(mat); obj.data.materials.append(mat)

def import_obj(path):
    bpy.ops.wm.obj_import(filepath=path)
    o = bpy.context.selected_objects[0]
    for p in o.data.polygons: p.use_smooth = True
    return o

# --- world: soft studio ---
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.065, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5

def frame_body(obj):
    bb = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    mn = mathutils.Vector((min(v[k] for v in bb) for k in range(3)))
    mx = mathutils.Vector((max(v[k] for v in bb) for k in range(3)))
    ext = mx - mn; up = max(range(3), key=lambda k: ext[k])
    hz = [k for k in range(3) if k != up]
    return (mn+mx)*0.5, hz, up, ext[up]

def place(center, hz, up, u0, u1, upo):
    p = center.copy(); p[hz[0]] += u0; p[hz[1]] += u1; p[up] += upo; return p

def setup_lights(center, hz, up):
    for nm, (u0,u1,uo), e, s in [("Key",(2.5,2.6,1.1),380,4.5),
                                 ("Fill",(-3.0,1.8,0.4),160,5.0),
                                 ("Rim",(-0.6,-3.6,1.6),300,3.0)]:
        d = bpy.data.lights.new(nm,'AREA'); d.energy=e; d.size=s
        o = bpy.data.objects.new(nm,d); o.location = place(center,hz,up,u0,u1,uo)
        bpy.context.collection.objects.link(o)
        o.rotation_euler = (center - o.location).to_track_quat('-Z','Y').to_euler()

cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
bpy.context.collection.objects.link(cam); scene.camera = cam; cam_d.lens = 50.0
scene.render.image_settings.file_format = 'PNG'

def render_to(path):
    scene.render.filepath = path; bpy.ops.render.render(write_still=True)

if args.seq:
    objs = sorted(glob.glob(os.path.join(args.seq, "frame_*.obj")))
    print(f"[blender] sequence of {len(objs)} frames")
    # fix camera on the first frame's framing (body translates -> keep a stable studio cam)
    first = import_obj(objs[0]); apply_materials(first)
    center, hz, up, H = frame_body(first)
    setup_lights(center, hz, up)
    vfov = 2*math.atan(cam_d.sensor_width/(2*cam_d.lens)); radius = (H*1.25/2)/math.tan(vfov/2)+0.4
    a = math.radians(args.azim); loc = center.copy()
    loc[hz[0]] += radius*math.sin(a); loc[hz[1]] += radius*math.cos(a)
    cam.location = loc; cam.rotation_euler = (center-loc).to_track_quat('-Z','Y').to_euler()
    bpy.data.objects.remove(first, do_unlink=True)
    for i, op in enumerate(objs):
        o = import_obj(op); apply_materials(o)
        render_to(os.path.join(args.out, f"frame_{i:03d}.png"))
        bpy.data.objects.remove(o, do_unlink=True)
        print(f"[blender] seq frame {i+1}/{len(objs)}")
else:
    obj = import_obj(args.obj); apply_materials(obj)
    center, hz, up, H = frame_body(obj); setup_lights(center, hz, up)
    vfov = 2*math.atan(cam_d.sensor_width/(2*cam_d.lens)); radius = (H*1.15/2)/math.tan(vfov/2)+0.3
    if args.closeup:                         # frame the head (top of body)
        bb = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        top = max(v[up] for v in bb)
        center = center.copy(); center[up] = top - 0.11*H
        radius = 0.55; cam_d.lens = 65
    print(f"[blender] H={H:.3f} radius={radius:.2f} closeup={args.closeup}")
    pose_frames = []
    i = 0
    def shoot(loc, target, tag):
        """place the (fixed-lens) camera at loc looking at target, render, record c2w."""
        global i
        cam.location = loc
        cam.rotation_euler = (target-loc).to_track_quat('-Z','Y').to_euler()
        render_to(os.path.join(args.out, f"frame_{i:03d}.png"))
        if args.poses is not None:
            bpy.context.view_layer.update()   # ensure matrix_world reflects the new pose
            pose_frames.append({"file": f"frame_{i:03d}.png",
                                "transform_matrix": [list(row) for row in cam.matrix_world]})
        print(f"[blender] frame {i+1}  {tag}")
        i += 1

    if args.rig == "shells":
        mn_up = center[up] - H/2.0                          # feet height (world `up` coord)
        radii = ([radius, 0.55*radius] if args.radii == "auto"
                 else [float(x) for x in args.radii.split(",")])
        lo, hi = [float(x) for x in args.layer_frac.split(",")]
        L = max(1, args.layers)
        fracs = [ (lo+hi)/2 ] if L == 1 else [lo + (hi-lo)*j/(L-1) for j in range(L)]
        targets = [mn_up + f*H for f in fracs]              # look-at height per layer
        # camera-height elevation offset per layer: -spread (bottom) .. +spread (top) of H
        eoff = [0.0]*L if L == 1 else [args.elev_spread*(2*j/(L-1)-1) for j in range(L)]
        total = len(radii)*L*args.az
        print(f"[blender] rig=shells: {len(radii)} shell(s) radii={ [round(r,2) for r in radii] } x "
              f"{L} height-layer(s) targets={ [round(t,2) for t in targets] } x {args.az} azimuth = {total} views")
        for si, R in enumerate(radii):
            for li in range(L):
                t_h = targets[li]
                cam_h = max(t_h + eoff[li]*H, mn_up + 0.05)     # keep the camera above the floor
                target = center.copy(); target[up] = t_h
                for k in range(args.az):
                    ang = 2*math.pi*k/args.az
                    loc = center.copy()
                    loc[hz[0]] += R*math.sin(ang); loc[hz[1]] += R*math.cos(ang); loc[up] = cam_h
                    shoot(loc, target, f"shell{si} layer{li}(h={t_h:.2f}) az {k+1}/{args.az}  [{i+1}/{total}]")
    else:
        elevs = [math.radians(float(x)) for x in args.elevs.split(",")]
        n_rings = len(elevs)
        frames_per_ring = max(1, args.frames // n_rings)
        total = frames_per_ring * n_rings
        print(f"[blender] rig=ring: {n_rings} elevation ring(s) {args.elevs} x {frames_per_ring} azimuth = {total} views")
        for elev in elevs:
            # keep the camera's distance-to-subject ~constant across rings (radius shrinks in the
            # horizontal plane as elevation increases, offset by lifting/dropping along `up`)
            r_h = radius*math.cos(elev); r_v = radius*math.sin(elev)
            for k in range(frames_per_ring):
                ang = 2*math.pi*k/frames_per_ring; loc = center.copy()
                loc[hz[0]] += r_h*math.sin(ang); loc[hz[1]] += r_h*math.cos(ang); loc[up] += r_v
                shoot(loc, center, f"elev {math.degrees(elev):.0f}deg az {k+1}/{frames_per_ring}  [{i+1}/{total}]")
    if args.poses is not None:
        import json
        meta = {"camera_model": "OPENCV", "w": args.size, "h": args.size,
                "lens_mm": cam_d.lens, "sensor_width_mm": cam_d.sensor_width,
                "sensor_fit": cam_d.sensor_fit,   # AUTO for square render
                "convention": "blender_cam (Y-up, -Z fwd) c2w; convert to OpenCV in the fitter",
                "frames": pose_frames}
        with open(args.poses, "w") as f: json.dump(meta, f, indent=1)
        print(f"[blender] wrote {len(pose_frames)} poses -> {args.poses}")
print("[blender] DONE ->", args.out)
