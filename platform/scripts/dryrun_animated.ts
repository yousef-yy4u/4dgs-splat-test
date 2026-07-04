// Animated-path dry run: reuse an ALREADY-COMPLETED worker job (skip the 5-min regen) and
// exercise the real finalizeAsset (animated USDZ bake + animated flag) + publish. (D42)
import { getGenStatus } from "@/lib/gen-worker";
import { finalizeAsset } from "@/lib/finalize";
import { prisma } from "@/lib/db";

const workerJobId = process.argv[2]; // a completed /generate worker job id
const slug = "anim-" + Math.random().toString(36).slice(2, 8);

async function main() {
  if (!workerJobId) throw new Error("usage: dryrun_animated.ts <completed-worker-job-id>");
  await prisma.org.upsert({ where: { id: "seedorg" }, update: {}, create: { id: "seedorg", name: "Seed Org" } });
  const asset = await prisma.asset.create({
    data: { orgId: "seedorg", name: "Animated dry-run", source: "PRODUCT_IMAGE", genMode: "ANIMATED", status: "PROCESSING" },
  });
  await prisma.job.create({ data: { assetId: asset.id, status: "RUNNING", stage: "generation", workerJobId } });

  const st = await getGenStatus(workerJobId);
  console.log("worker:", { done: st.done, stage: st.stage, result: st.result });
  if (!st.done) throw new Error("worker job not done");

  console.log("FINALIZE: download GLB + bake ANIMATED USDZ…");
  await finalizeAsset(asset.id, st);
  const a = await prisma.asset.findUnique({ where: { id: asset.id } });
  console.log("  ->", { status: a?.status, animated: a?.animated, glb: a?.glbUrl, usdz: a?.usdzUrl });

  await prisma.widget.create({ data: { assetId: asset.id, slug } });
  console.log("VIEW:  /v/" + slug);
  await prisma.$disconnect();
}
main().catch((e) => { console.error(e); process.exit(1); });
