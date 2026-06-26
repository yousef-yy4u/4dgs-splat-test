import { NextResponse } from "next/server";
import { ensureUserOrg } from "@/lib/auth";
import { prisma } from "@/lib/db";

export const dynamic = "force-dynamic";

function makeSlug(): string {
  return Math.random().toString(36).slice(2, 10);
}

// Publish a READY asset as an un-anchored "view in 3D" widget.
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const ctx = await ensureUserOrg();
  if (!ctx) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { id } = await params;

  const asset = await prisma.asset.findFirst({
    where: { id, orgId: ctx.orgId },
    include: { widgets: true },
  });
  if (!asset) return NextResponse.json({ error: "not found" }, { status: 404 });
  if (asset.status !== "READY") {
    return NextResponse.json({ error: "asset not ready" }, { status: 400 });
  }
  if (asset.widgets[0]) return NextResponse.json({ widget: asset.widgets[0] });

  const widget = await prisma.widget.create({ data: { assetId: id, slug: makeSlug() } });
  return NextResponse.json({ widget });
}
