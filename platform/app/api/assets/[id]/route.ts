import { NextResponse } from "next/server";
import { ensureUserOrg } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { getGenStatus } from "@/lib/gen-worker";
import { finalizeAsset } from "@/lib/finalize";

export const dynamic = "force-dynamic";

// Poll target: returns the asset, advancing it by checking the GPU worker and
// finalizing (download GLB + bake USDZ) the first time the worker reports done.
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
  const ctx = await ensureUserOrg();
  if (!ctx) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { id } = await params;

  let asset = await prisma.asset.findFirst({
    where: { id, orgId: ctx.orgId },
    include: { jobs: { orderBy: { createdAt: "desc" }, take: 1 }, widgets: true },
  });
  if (!asset) return NextResponse.json({ error: "not found" }, { status: 404 });

  let progress = 0;
  let stage = asset.jobs[0]?.stage ?? null;

  if (asset.status === "PROCESSING") {
    const job = asset.jobs[0];
    if (job?.workerJobId) {
      try {
        const st = await getGenStatus(job.workerJobId);
        progress = st.pct ?? 0;
        stage = st.stage ?? stage;
        if (st.error) {
          await prisma.job.update({ where: { id: job.id }, data: { status: "FAILED", error: st.error } });
          await prisma.asset.update({ where: { id }, data: { status: "FAILED" } });
        } else if (st.done) {
          // claim finalize once: only proceed if we flip stage away from "finalizing"
          const claim = await prisma.job.updateMany({
            where: { id: job.id, stage: { not: "finalizing" }, status: { not: "SUCCEEDED" } },
            data: { stage: "finalizing" },
          });
          if (claim.count > 0) {
            await finalizeAsset(id, st);
          }
        }
      } catch (e) {
        // transient worker hiccup — leave PROCESSING, let the client poll again
        console.error(`[asset ${id}] status check failed`, e);
      }
      asset = await prisma.asset.findFirst({
        where: { id, orgId: ctx.orgId },
        include: { jobs: { orderBy: { createdAt: "desc" }, take: 1 }, widgets: true },
      });
    }
  }

  return NextResponse.json({
    id: asset!.id,
    name: asset!.name,
    status: asset!.status,
    genMode: asset!.genMode,
    animated: asset!.animated,
    glbUrl: asset!.glbUrl,
    usdzUrl: asset!.usdzUrl,
    widget: asset!.widgets[0] ?? null,
    stage,
    progress,
    error: asset!.jobs[0]?.error ?? null,
  });
  } catch (e) {
    // Always return JSON (the client polls and parses this) — never an empty/HTML 500 body.
    console.error("[asset status] handler error", e);
    return NextResponse.json({ error: "status check failed" }, { status: 500 });
  }
}
