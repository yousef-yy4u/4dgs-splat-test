import { spawn } from "child_process";

// Bake a GLB into a USDZ for iOS AR Quick Look, via Blender (bpy) headless.
// Co-located: the Next server runs on the same box as the GPU pipeline, so it can
// shell out to the unirig-venv python that has bpy. No new deps, no nvdiffrast.
const BPY_PYTHON = process.env.BPY_PYTHON ?? "/home/sov2/projects/unirig-venv/bin/python";
const GLB_TO_USDZ = process.env.GLB_TO_USDZ ?? "/home/sov2/projects/4dgs/generation/glb_to_usdz.py";

export function bakeUsdz(glbPath: string, usdzPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const proc = spawn(BPY_PYTHON, [GLB_TO_USDZ, glbPath, usdzPath]);
    let err = "";
    proc.stderr.on("data", (d) => (err += d.toString()));
    proc.on("error", reject);
    proc.on("close", (code) =>
      code === 0 ? resolve() : reject(new Error(`usdz bake exited ${code}: ${err.slice(-600)}`)),
    );
  });
}
