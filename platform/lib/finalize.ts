import path from "path";
import { prisma } from "@/lib/db";
import { workerOutUrl, type GenStatus, type GenResult } from "@/lib/gen-worker";
import { assetDir, saveAsset, publicUrl } from "@/lib/storage";
import { bakeUsdz } from "@/lib/usdz";

// Worker finished -> pull the GLB, bake a USDZ, store both, mark the asset READY.
// Mesh-first (D34): we publish the mesh GLB; the splat stays a later hero tier.
// The animated path (D42) returns a RIGGED GLB with a baked idle clip; rig_ok=false means
// rigging fell back to a plain mesh, so the asset is effectively static (animated=false).
export async function finalizeAsset(assetId: string, status: GenStatus): Promise<void> {
  const result = status.result as GenResult | null;
  if (!result?.glb) throw new Error("worker result has no glb path");

  // animated only when the worker actually produced a rig (rig_ok); static path has no rig_ok.
  const animated = result.rig_ok === true;

  // 1. fetch the GLB the worker produced (served at /out/<file>)
  const res = await fetch(workerOutUrl(result.glb.replace(/^\/out\//, "")));
  if (!res.ok) throw new Error(`fetch glb failed: ${res.status}`);
  const glbBuf = Buffer.from(await res.arrayBuffer());
  const glbUrl = await saveAsset(assetId, "model.glb", glbBuf);

  // 2. bake USDZ for iOS (non-fatal: Android/desktop still work without it).
  //    For animated assets, carry the (single) animation track into AR Quick Look (D39).
  const dir = assetDir(assetId);
  let usdzUrl: string | null = null;
  try {
    await bakeUsdz(path.join(dir, "model.glb"), path.join(dir, "model.usdz"), { animation: animated });
    usdzUrl = publicUrl(assetId, "model.usdz");
  } catch (e) {
    console.error(`[finalize ${assetId}] usdz bake failed:`, e);
  }

  // 3. mark READY
  await prisma.asset.update({
    where: { id: assetId },
    data: { status: "READY", glbUrl, usdzUrl, animated },
  });
  await prisma.job.updateMany({
    where: { assetId },
    data: { status: "SUCCEEDED", stage: "done", finishedAt: new Date() },
  });
}
