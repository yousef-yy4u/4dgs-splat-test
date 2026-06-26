import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { storageRoot } from "@/lib/storage";

// Serves stored asset files (GLB/USDZ/poster). USDZ MUST be model/vnd.usdz+zip for
// iOS AR Quick Look to recognize it. CORS open so widgets embed cross-origin.
const TYPES: Record<string, string> = {
  ".glb": "model/gltf-binary",
  ".usdz": "model/vnd.usdz+zip",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
};

export async function GET(_req: NextRequest, { params }: { params: Promise<{ file: string[] }> }) {
  const { file } = await params;
  // block path traversal
  const parts = file.filter((p) => p !== ".." && !p.includes("/") && !p.includes("\\"));
  const full = path.join(storageRoot(), ...parts);
  try {
    const data = await fs.readFile(full);
    const ext = path.extname(full).toLowerCase();
    return new NextResponse(new Uint8Array(data), {
      headers: {
        "Content-Type": TYPES[ext] ?? "application/octet-stream",
        "Cache-Control": "public, max-age=31536000, immutable",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch {
    return new NextResponse("Not found", { status: 404 });
  }
}
