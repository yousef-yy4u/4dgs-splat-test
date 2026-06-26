#!/usr/bin/env python
"""
GLB -> USDZ baker (for iOS AR Quick Look).

The un-anchored "view in 3D" surface needs TWO formats from one asset:
  - GLB  -> Android Scene Viewer / WebXR (via <model-viewer> `src`)
  - USDZ -> iOS AR Quick Look          (via <model-viewer> `ios-src`)
iOS Safari has no WebXR, so the iPhone path is Apple's native AR Quick Look + a USDZ.

Runs headless in Blender (bpy) — no nvdiffrast / no extra deps (bpy is already in unirig-venv).

Usage (unirig-venv has bpy 4.2):
  /home/sov2/projects/unirig-venv/bin/python generation/glb_to_usdz.py in.glb out.usdz
"""
import sys
import bpy


def glb_to_usdz(glb_path: str, usdz_path: str) -> None:
    # Clean scene.
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import the GLB (glTF is Y-up; Blender is Z-up — the importer handles the convert).
    bpy.ops.import_scene.gltf(filepath=glb_path)

    # Export USDZ. AR Quick Look wants Y-up + meters; Blender's USD exporter applies the
    # Z-up -> Y-up convention and packages a .usdz when the path ends in .usdz.
    bpy.ops.wm.usd_export(
        filepath=usdz_path,
        export_textures=True,
        export_materials=True,
        use_instancing=False,
        convert_orientation=True,
        export_global_forward_selection="NEGATIVE_Z",
        export_global_up_selection="Y",
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: glb_to_usdz.py <in.glb> <out.usdz>", file=sys.stderr)
        sys.exit(2)
    glb, usdz = sys.argv[1], sys.argv[2]
    glb_to_usdz(glb, usdz)
    print(f"wrote {usdz}")
