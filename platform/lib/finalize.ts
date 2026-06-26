import path from "path";
import { prisma } from "@/lib/db";
import { workerOutUrl, type GenStatus } from "@/lib/gen-worker";
import { assetDir, saveAsset, publicUrl } from "@/lib/storage";
import { bakeUsdz } from "@/lib/usdz";

// Worker finished -> pull the GLB, bake a USDZ, store both, mark the asset READY.
// Mesh-first (D34): we publish the mesh GLB; the splat stays a later hero tier.
export async function finalizeAsset(assetId: string, status: GenStatus): Promise<void> {
  const result = status.result as { glb?: string } | null;
  if (!result?.glb) throw new Error("worker result has no glb path");

  // 1. fetch the GLB the worker produced (served at /out/<file>)
  const res = await fetch(workerOutUrl(result.glb.replace(/^\/out\//, "")));
  if (!res.ok) throw new Error(`fetch glb failed: ${res.status}`);
  const glbBuf = Buffer.from(await res.arrayBuffer());
  const glbUrl = await saveAsset(assetId, "model.glb", glbBuf);

  // 2. bake USDZ for iOS (non-fatal: Android/desktop still work without it)
  const dir = assetDir(assetId);
  let usdzUrl: string | null = null;
  try {
    await bakeUsdz(path.join(dir, "model.glb"), path.join(dir, "model.usdz"));
    usdzUrl = publicUrl(assetId, "model.usdz");
  } catch (e) {
    console.error(`[finalize ${assetId}] usdz bake failed:`, e);
  }

  // 3. mark READY
  await prisma.asset.update({
    where: { id: assetId },
    data: { status: "READY", glbUrl, usdzUrl },
  });
  await prisma.job.updateMany({
    where: { assetId },
    data: { status: "SUCCEEDED", stage: "done", finishedAt: new Date() },
  });
}
