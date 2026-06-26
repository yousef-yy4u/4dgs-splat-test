// Full upload→generate→view dry run through the REAL lib code (skips only the Clerk/HTTP
// wrapper). Produces a published widget at /v/<slug>.
import { readFile } from "node:fs/promises";
import { submitGeneration, getGenStatus } from "@/lib/gen-worker";
import { finalizeAsset } from "@/lib/finalize";
import { prisma } from "@/lib/db";

const img =
  process.argv[2] ??
  "/home/sov2/projects/TRELLIS/assets/example_image/typical_vehicle_locomotive.png";
const slug = Math.random().toString(36).slice(2, 10);

async function main() {
  console.log("UPLOAD:", img);
  await prisma.org.upsert({ where: { id: "seedorg" }, update: {}, create: { id: "seedorg", name: "Seed Org" } });
  const asset = await prisma.asset.create({
    data: { orgId: "seedorg", name: "Dry-run " + img.split("/").pop(), source: "PRODUCT_IMAGE", status: "PROCESSING" },
  });
  const job = await prisma.job.create({ data: { assetId: asset.id, status: "RUNNING", stage: "generation" } });

  const buf = await readFile(img);
  const blob = new Blob([new Uint8Array(buf)], { type: "image/png" });
  const { jobId } = await submitGeneration([blob]); // <- real worker submit
  await prisma.job.update({ where: { id: job.id }, data: { workerJobId: jobId } });
  console.log("GENERATE: worker job", jobId);

  let st = await getGenStatus(jobId);
  for (let i = 0; i < 200 && !st.done; i++) {
    process.stdout.write(`\r  [${st.pct}%] ${st.stage}            `);
    if (st.error) throw new Error("worker error: " + st.error);
    await new Promise((r) => setTimeout(r, 4000));
    st = await getGenStatus(jobId);
  }
  process.stdout.write("\n");
  if (st.error) throw new Error("worker error: " + st.error);

  console.log("FINALIZE: download GLB + bake USDZ + store…");
  await finalizeAsset(asset.id, st); // <- real finalize
  const a = await prisma.asset.findUnique({ where: { id: asset.id } });
  console.log("  ->", { status: a?.status, glb: a?.glbUrl, usdz: a?.usdzUrl });

  await prisma.widget.create({ data: { assetId: asset.id, slug } }); // <- real publish
  console.log("VIEW:  /v/" + slug);
  await prisma.$disconnect();
}
main().catch((e) => { console.error(e); process.exit(1); });
