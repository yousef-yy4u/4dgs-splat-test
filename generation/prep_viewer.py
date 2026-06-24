#!/usr/bin/env python
"""Export the rigged crab (mesh + armature) from the skeleton FBX to a decimated GLB
for the web viewer. GLB carries both the mesh and the skeleton, so Three.js can show
mesh + bones from one file. Run with the unirig-venv (has bpy)."""
import bpy, sys

FBX = sys.argv[1] if len(sys.argv) > 1 else "/home/sov2/projects/4dgs/generation/out/crab_skeleton.fbx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/sov2/projects/4dgs/benchmark/assets/crab_rigged.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

# decimate the mesh to ~50k faces for the web
for o in bpy.data.objects:
    if o.type == 'MESH':
        nf = max(1, len(o.data.polygons))
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new('dec', 'DECIMATE')
        mod.ratio = min(1.0, 50000.0 / nf)
        bpy.ops.object.modifier_apply(modifier='dec')
        print(f"mesh '{o.name}': {nf} -> {len(o.data.polygons)} faces")

n_bones = sum(len(a.data.bones) for a in bpy.data.objects if a.type == 'ARMATURE')
print("armature bones:", n_bones)

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True)
print("exported", OUT)
