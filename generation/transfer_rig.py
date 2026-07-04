#!/usr/bin/env python
"""Make an animated asset look as good as the static product: take TRELLIS's PROVEN textured mesh
(to_glb — good xatlas UVs + 1024² texture) and transfer the UniRig skeleton + skin weights onto it,
then carry the baked idle/motion animation. This avoids baking onto the rigged mesh's fragmented
auto-UVs (which wrapped badly). (D42)

  RIGGED  = UniRig GLB (armature + source mesh w/ vertex-group weights + baked animation)
  TEXTURED= to_glb GLB (textured target mesh, no rig)
  OUT     = textured + rigged + animated GLB

Runs in unirig-venv (bpy 4.2):
  python transfer_rig.py <rigged.glb> <textured.glb> <out.glb>
"""
import bpy, sys, mathutils

RIGGED, TEXTURED, OUT = sys.argv[1], sys.argv[2], sys.argv[3]


def world_bbox(o):
    cs = [o.matrix_world @ v.co for v in o.data.vertices]
    mn = mathutils.Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
    mx = mathutils.Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
    return mn, mx


bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. rigged GLB → armature + source mesh (carries skin weights + the animation action)
bpy.ops.import_scene.gltf(filepath=RIGGED)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
src = next((o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 0), None)
if arm is None or src is None:
    raise RuntimeError("rigged GLB has no armature/mesh")

# 2. textured GLB → target mesh (texture + good UVs)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=TEXTURED)
tgt = next((o for o in bpy.data.objects if o.type == "MESH" and o not in before and len(o.data.vertices) > 0), None)
if tgt is None:
    raise RuntimeError("textured GLB has no mesh")

# 3. align target onto source (same object, but to_glb vs UniRig differ by uniform scale + offset;
#    orientation matches — both glTF y-up). Uniform scale by max-extent ratio + centre match.
smn, smx = world_bbox(src)
tmn, tmx = world_bbox(tgt)
ssize = max((smx - smn).x, (smx - smn).y, (smx - smn).z)
tsize = max((tmx - tmn).x, (tmx - tmn).y, (tmx - tmn).z) or 1.0
s = ssize / tsize
scen = (smn + smx) / 2
tcen = (tmn + tmx) / 2
tgt.matrix_world = (
    mathutils.Matrix.Translation(scen)
    @ mathutils.Matrix.Scale(s, 4)
    @ mathutils.Matrix.Translation(-tcen)
    @ tgt.matrix_world
)
bpy.context.view_layer.objects.active = tgt
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 4. transfer skin weights src → tgt (nearest-face interpolated), creating matching vertex groups
dt = tgt.modifiers.new("dt", "DATA_TRANSFER")
dt.object = src
dt.use_vert_data = True
dt.data_types_verts = {"VGROUP_WEIGHTS"}
dt.vert_mapping = "POLYINTERP_NEAREST"
dt.layers_vgroup_select_src = "ALL"
dt.layers_vgroup_select_dst = "NAME"
bpy.context.view_layer.objects.active = tgt
bpy.ops.object.datalayout_transfer(modifier=dt.name)   # create the vertex groups on tgt
bpy.ops.object.modifier_apply(modifier=dt.name)
ngroups = len(tgt.vertex_groups)

# 5. skin tgt to the armature; drop the (gray/fragmented) source mesh
am = tgt.modifiers.new("arm", "ARMATURE")
am.object = arm
tgt.parent = arm
bpy.data.objects.remove(src, do_unlink=True)

# 6. keep the animation range and export
end = max([int(a.frame_range[1]) for a in bpy.data.actions] + [1])
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = end

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    export_yup=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
)
print(f"transferred {ngroups} weight groups onto textured mesh -> {OUT}")
