import { spawn } from "child_process";
import { stat } from "node:fs/promises";

// Bake a GLB into a USDZ for iOS AR Quick Look, via Blender (bpy) headless.
// Co-located: the Next server runs on the same box as the GPU pipeline, so it can
// shell out to the unirig-venv python that has bpy. No new deps, no nvdiffrast.
const BPY_PYTHON = process.env.BPY_PYTHON ?? "/home/sov2/projects/unirig-venv/bin/python";
const GLB_TO_USDZ = process.env.GLB_TO_USDZ ?? "/home/sov2/projects/4dgs/generation/glb_to_usdz.py";

export function bakeUsdz(
  glbPath: string,
  usdzPath: string,
  opts: { animation?: boolean } = {},
): Promise<void> {
  return new Promise((resolve, reject) => {
    const args = [GLB_TO_USDZ, glbPath, usdzPath];
    if (opts.animation) args.push("--animation");
    const proc = spawn(BPY_PYTHON, args);
    let err = "";
    proc.stderr.on("data", (d) => (err += d.toString()));
    proc.on("error", reject);
    // Blender's USD exporter routinely writes valid output then SEGFAULTS on exit cleanup
    // (exit code null) — same as the UniRig extract step. Judge success by the output file,
    // not the exit code.
    proc.on("close", async (code) => {
      try {
        const s = await stat(usdzPath);
        if (s.size > 1024) return resolve();
      } catch {
        /* fall through to reject */
      }
      reject(new Error(`usdz bake produced no output (exit ${code}): ${err.slice(-500)}`));
    });
  });
}
