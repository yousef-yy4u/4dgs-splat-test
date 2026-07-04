import { NextRequest, NextResponse } from "next/server";
import { ensureUserOrg } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { submitGeneration, MOTIONS, type Motion } from "@/lib/gen-worker";

export const dynamic = "force-dynamic";

// List this org's assets (for the dashboard).
export async function GET() {
  const ctx = await ensureUserOrg();
  if (!ctx) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const assets = await prisma.asset.findMany({
    where: { orgId: ctx.orgId },
    orderBy: { createdAt: "desc" },
    include: { widgets: true },
  });
  return NextResponse.json({ assets });
}

// Create an asset from a product image and kick off generation on the GPU worker.
export async function POST(req: NextRequest) {
  const ctx = await ensureUserOrg();
  if (!ctx) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const form = await req.formData();
  const file = form.get("image");
  const name = ((form.get("name") as string) || "Untitled").slice(0, 120);
  const mode = form.get("mode") === "animated" ? "animated" : "static";
  const motionIn = (form.get("motion") as string) || "idle";
  const motion: Motion = (MOTIONS as readonly string[]).includes(motionIn)
    ? (motionIn as Motion)
    : "idle";
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "image file required" }, { status: 400 });
  }

  const asset = await prisma.asset.create({
    data: {
      orgId: ctx.orgId,
      name,
      source: "PRODUCT_IMAGE",
      genMode: mode === "animated" ? "ANIMATED" : "STATIC",
      animation: mode === "animated" ? { motion } : undefined,
      status: "PROCESSING",
    },
  });
  const job = await prisma.job.create({
    data: { assetId: asset.id, status: "RUNNING", stage: "generation" },
  });

  try {
    const ab = await file.arrayBuffer();
    const blob = new Blob([ab], { type: file.type || "image/png" });
    const { jobId } = await submitGeneration([blob], mode, motion);
    await prisma.job.update({ where: { id: job.id }, data: { workerJobId: jobId } });
  } catch (e) {
    await prisma.job.update({ where: { id: job.id }, data: { status: "FAILED", error: String(e) } });
    await prisma.asset.update({ where: { id: asset.id }, data: { status: "FAILED" } });
    return NextResponse.json({ error: "worker submit failed", detail: String(e) }, { status: 502 });
  }

  return NextResponse.json({ assetId: asset.id });
}
