import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { workerReachable } from "@/lib/gen-worker";

export const dynamic = "force-dynamic";

// Phase 0 readiness probe: reports each backbone component independently so we can
// stand them up one at a time (DB, GPU worker) without the others having to exist yet.
export async function GET() {
  const checks: Record<string, "ok" | "down"> = {};

  try {
    await prisma.$queryRaw`SELECT 1`;
    checks.db = "ok";
  } catch {
    checks.db = "down";
  }

  checks.genWorker = (await workerReachable()) ? "ok" : "down";

  const ok = Object.values(checks).every((v) => v === "ok");
  return NextResponse.json({ ok, checks }, { status: ok ? 200 : 503 });
}
