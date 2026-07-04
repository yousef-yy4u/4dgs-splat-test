#!/usr/bin/env python
"""Export the rigged asset (mesh + armature) from the skinned FBX to a GLB for the web/product
viewer. The GLB carries mesh + skeleton + a baked **idle animation** so it auto-plays in
<model-viewer> (and survives the one-track USDZ bake), and the mesh is **vertex-coloured** from
the gaussian splat so it isn't a gray blob (D42 — productizing the rigged path; the high-fidelity
UV texture-bake is a later upgrade).

Run with the unirig-venv (has bpy 4.2 + numpy + scipy):
  python prep_viewer.py <skinned.fbx> <out.glb> [splat.ply]
"""
import bpy, sys, os, math
import numpy as np

FBX    = sys.argv[1] if len(sys.argv) > 1 else "/home/sov2/projects/4dgs/generation/out/crab_skeleton.fbx"
OUT    = sys.argv[2] if len(sys.argv) > 2 else "/home/sov2/projects/4dgs/benchmark/assets/crab_rigged.glb"
SPLAT  = sys.argv[3] if len(sys.argv) > 3 else None   # gaussian PLY → per-vertex colour
MOTION = sys.argv[4] if len(sys.argv) > 4 else "idle"  # motion-library preset (D42)

C0 = 0.28209479177387814   # SH degree-0 basis → RGB: rgb = 0.5 + C0 * f_dc


def read_gaussian_ply(path):
    """Minimal reader for a binary_little_endian gaussian PLY. Returns (xyz Nx3, rgb Nx3 in 0..1).
    Parses the header for property order (all float32) so we index x/y/z + f_dc_0..2 by name."""
    with open(path, "rb") as f:
        raw = f.read()
    hdr_end = raw.index(b"end_header\n") + len(b"end_header\n")
    header = raw[:hdr_end].decode("ascii", "replace").splitlines()
    if not any("binary_little_endian" in h for h in header):
        raise RuntimeError("only binary_little_endian PLY supported")
    count = 0
    props = []
    for line in header:
        if line.startswith("element vertex"):
            count = int(line.split()[-1])
        elif line.startswith("property"):
            parts = line.split()
            props.append((parts[1], parts[2]))   # (type, name)
    # all gaussian props are float32 here
    names = [n for _, n in props]
    arr = np.frombuffer(raw[hdr_end:hdr_end + count * len(props) * 4], dtype="<f4")
    arr = arr.reshape(count, len(props))
    idx = {n: i for i, n in enumerate(names)}
    xyz = arr[:, [idx["x"], idx["y"], idx["z"]]].astype(np.float64)
    fdc = arr[:, [idx["f_dc_0"], idx["f_dc_1"], idx["f_dc_2"]]]
    rgb = np.clip(0.5 + C0 * fdc, 0.0, 1.0)
    return xyz, rgb


# ── import the skinned FBX ───────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

mesh_objs = []
for o in bpy.data.objects:
    if o.type == "MESH":
        nf = max(1, len(o.data.polygons))
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new("dec", "DECIMATE")
        mod.ratio = min(1.0, 50000.0 / nf)
        bpy.ops.object.modifier_apply(modifier="dec")
        mesh_objs.append(o)
        print(f"mesh '{o.name}': {nf} -> {len(o.data.polygons)} faces")

# NOTE: the high-fidelity texture comes from transfer_rig.py, which skins TRELLIS's proven to_glb
# textured mesh to this armature. The vertex colours below are only the FALLBACK shown if that
# transfer fails (the rigged mesh here is otherwise discarded). (D42)

# ── vertex colour from the gaussian splat (so it's not gray) ─────────────────
if SPLAT and os.path.exists(SPLAT):
    try:
        pts, cols = read_gaussian_ply(SPLAT)
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        for o in mesh_objs:
            me = o.data
            # local coords match the cleaned-OBJ / TRELLIS frame the splat lives in
            # (FBX import puts the axis-convention rotation on the object, not the mesh data).
            vco = np.array([(v.co.x, v.co.y, v.co.z) for v in me.vertices])
            _, nn = tree.query(vco, k=1)
            vc = cols[nn]
            ca = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="POINT")
            for i in range(len(me.vertices)):
                ca.data[i].color = (float(vc[i, 0]), float(vc[i, 1]), float(vc[i, 2]), 1.0)
            # material that drives base colour from the vertex colour → glTF exports COLOR_0.
            mat = bpy.data.materials.new("vcol")
            mat.use_nodes = True
            nt = mat.node_tree
            bsdf = nt.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Metallic"].default_value = 0.0
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.9
                vcn = nt.nodes.new("ShaderNodeVertexColor")
                vcn.layer_name = "Col"
                nt.links.new(vcn.outputs["Color"], bsdf.inputs["Base Color"])
            me.materials.clear()
            me.materials.append(mat)
        print(f"vertex-coloured {len(mesh_objs)} mesh(es) from {os.path.basename(SPLAT)}")
    except Exception as e:
        print(f"vertex-colour skipped: {e}")

# ── bake a looping animation onto the skeleton (motion-library preset) ────────
# All presets are RIG-AGNOSTIC (work on any skeleton — no assumptions about which bone is
# an arm/leg): per-bone presets gently sway the whole skeleton; object presets transform the
# whole armature. Semantic motions (wave, walk) need bone labels + retargeting → later (D42).
LOOP, FPS = 48, 24
KEYS = (0, 12, 24, 36, 48)


def bbox_height(objs):
    zs = [(o.matrix_world @ v.co).z for o in objs for v in o.data.vertices]
    return (max(zs) - min(zs)) if zs else 1.0


arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
n_bones = len(arm.data.bones) if arm else 0
if arm and n_bones > 1:
    bpy.context.scene.render.fps = FPS
    motion = MOTION if MOTION in ("idle", "sway", "bob", "spin", "float") else "idle"
    H = bbox_height(mesh_objs)

    # per-bone skeletal sway (idle / sway)
    if motion in ("idle", "sway"):
        amp = 0.06 if motion == "idle" else 0.13
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        bones = list(arm.pose.bones)
        for pb in bones:
            pb.rotation_mode = "XYZ"
        for f in KEYS:
            t = (f / LOOP) * 2 * math.pi
            for bi, pb in enumerate(bones):
                if bi == 0:
                    continue   # skip root so the body doesn't tip
                ph = bi * 0.6
                pb.rotation_euler = (amp * math.sin(t + ph), amp * math.sin(0.5 * t + ph), 0.0)
                pb.keyframe_insert("rotation_euler", frame=f)
        bpy.ops.object.mode_set(mode="OBJECT")
    else:
        # whole-armature object transforms (bob / spin / float)
        arm.rotation_mode = "XYZ"
        for f in KEYS:
            frac = f / LOOP
            t = frac * 2 * math.pi
            if motion in ("bob", "float"):
                arm.location.z = 0.06 * H * math.sin(t)
            if motion in ("spin", "float"):
                arm.rotation_euler.z = frac * 2 * math.pi * (1 if motion == "spin" else 0.5)
            arm.keyframe_insert("location", frame=f)
            arm.keyframe_insert("rotation_euler", frame=f)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = LOOP
    print(f"baked '{motion}' animation ({n_bones} bones, {LOOP}f loop)")
else:
    motion = "none"
    print(f"no animation (armature bones={n_bones})")

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    export_yup=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
)
print("exported", OUT)
