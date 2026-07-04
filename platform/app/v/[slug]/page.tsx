import { prisma } from "@/lib/db";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

const MODEL_VIEWER_CDN = "https://unpkg.com/@google/model-viewer@4.0.0/dist/model-viewer.min.js";

// Public "view in 3D" page — the shareable link + iframe-embed + print-QR target.
// One asset, two AR paths: Android Scene Viewer/WebXR via `src` (GLB); iOS AR Quick Look
// via `ios-src` (USDZ), since iOS Safari has no WebXR.
export default async function ViewerPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const widget = await prisma.widget.findUnique({ where: { slug }, include: { asset: true } });
  if (!widget || widget.asset.status !== "READY" || !widget.asset.glbUrl) notFound();
  const a = widget.asset;

  return (
    <>
      {/* eslint-disable-next-line @next/next/no-sync-scripts */}
      <script type="module" src={MODEL_VIEWER_CDN} />
      <main style={{ position: "fixed", inset: 0, background: "#f4f4f5" }}>
        <model-viewer
          src={a.glbUrl ?? undefined}
          ios-src={a.usdzUrl ?? undefined}
          poster={a.posterUrl ?? undefined}
          alt={a.name}
          ar
          ar-modes="webxr scene-viewer quick-look"
          camera-controls
          auto-rotate={!a.animated}
          autoplay={a.animated || undefined}
          shadow-intensity="1"
          touch-action="pan-y"
          style={{ width: "100%", height: "100%", backgroundColor: "#f4f4f5" }}
        >
          <button
            slot="ar-button"
            style={{
              position: "absolute",
              bottom: 20,
              left: "50%",
              transform: "translateX(-50%)",
              padding: "10px 18px",
              borderRadius: 999,
              border: "none",
              background: "#111",
              color: "#fff",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            View in your space
          </button>
        </model-viewer>
        {widget.watermark && (
          <div
            style={{
              position: "absolute",
              bottom: 10,
              right: 12,
              fontSize: 11,
              color: "#71717a",
              fontFamily: "system-ui, sans-serif",
            }}
          >
            view in 3D
          </div>
        )}
      </main>
    </>
  );
}
