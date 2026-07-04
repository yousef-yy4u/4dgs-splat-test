"use client";

import { useEffect, useRef, useState } from "react";

type AssetState = {
  id: string;
  name: string;
  status: "DRAFT" | "PROCESSING" | "READY" | "FAILED";
  genMode: "STATIC" | "ANIMATED";
  animated: boolean;
  glbUrl: string | null;
  usdzUrl: string | null;
  widget: { slug: string } | null;
  stage: string | null;
  progress: number;
  error: string | null;
};

const MV = "https://unpkg.com/@google/model-viewer@4.0.0/dist/model-viewer.min.js";

export default function AssetCreator() {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"static" | "animated">("static");
  const [motion, setMotion] = useState("idle");
  const MOTIONS = ["idle", "sway", "bob", "spin", "float"] as const;
  const [asset, setAsset] = useState<AssetState | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!document.querySelector("script[data-mv]")) {
      const s = document.createElement("script");
      s.type = "module";
      s.src = MV;
      s.dataset.mv = "1";
      document.head.appendChild(s);
    }
    return () => {
      if (poll.current) clearInterval(poll.current);
    };
  }, []);

  function startPolling(id: string) {
    if (poll.current) clearInterval(poll.current);
    let fails = 0;
    const stop = () => {
      if (poll.current) clearInterval(poll.current);
      setBusy(false);
    };
    const tick = async () => {
      // Tolerate transient errors (empty body, 5xx, network blips) — generation is long-running
      // and a single bad poll shouldn't crash the UI. Give up only after several in a row.
      let j: AssetState | null = null;
      try {
        const res = await fetch(`/api/assets/${id}`, { cache: "no-store" });
        if (res.ok) {
          const text = await res.text();
          if (text) j = JSON.parse(text) as AssetState;
        }
      } catch {
        /* fall through to the failure path */
      }
      if (!j) {
        if (++fails >= 5) {
          stop();
          setErr("Lost contact with the server while generating. Refresh to check status.");
        }
        return;
      }
      fails = 0;
      setAsset(j);
      if (j.status === "READY" || j.status === "FAILED") {
        stop();
        if (j.status === "FAILED") setErr(j.error || "generation failed");
      }
    };
    void tick();
    poll.current = setInterval(tick, 2500);
  }

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setErr(null);
    setAsset(null);
    setQr(null);
    try {
      const fd = new FormData();
      fd.append("image", file);
      fd.append("name", name || file.name);
      fd.append("mode", mode);
      if (mode === "animated") fd.append("motion", motion);
      const res = await fetch("/api/assets", { method: "POST", body: fd });
      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || j.error || "upload failed");
      startPolling(j.assetId);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  async function onPublish() {
    if (!asset) return;
    const res = await fetch(`/api/assets/${asset.id}/publish`, { method: "POST" });
    const j = await res.json();
    if (res.ok) {
      setAsset({ ...asset, widget: j.widget });
      const url = `${window.location.origin}/v/${j.widget.slug}`;
      const QR = (await import("qrcode")).default;
      setQr(await QR.toDataURL(url, { width: 220, margin: 1 }));
    }
  }

  const viewerUrl =
    asset?.widget && typeof window !== "undefined"
      ? `${window.location.origin}/v/${asset.widget.slug}`
      : null;
  const embed = viewerUrl
    ? `<iframe src="${viewerUrl}" width="480" height="480" style="border:0" allow="xr-spatial-tracking; camera; gyroscope; accelerometer"></iframe>`
    : "";

  return (
    <div className="rounded-xl border border-neutral-200 p-5 dark:border-neutral-800">
      <h2 className="font-semibold">Create a 3D asset from a product image</h2>

      <form onSubmit={onUpload} className="mt-4 flex flex-col gap-3">
        <div className="flex gap-2">
          {(["static", "animated"] as const).map((m) => (
            <button
              key={m}
              type="button"
              suppressHydrationWarning
              onClick={() => setMode(m)}
              disabled={busy}
              className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${
                mode === m
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : "border-neutral-300 text-neutral-600 dark:border-neutral-700 dark:text-neutral-300"
              }`}
            >
              {m === "static" ? "Static 3D" : "Animated 3D"}
            </button>
          ))}
        </div>
        <p className="text-xs text-neutral-400">
          {mode === "static"
            ? "Textured mesh, mesh-first (D34). Best for products."
            : "Rigged + an animation that plays in AR. Best for mascots/characters. Falls back to static if the shape can't be rigged."}
        </p>
        {mode === "animated" && (
          <label className="flex items-center gap-2 text-xs text-neutral-500">
            Motion
            <select
              value={motion}
              suppressHydrationWarning
              onChange={(e) => setMotion(e.target.value)}
              disabled={busy}
              className="rounded border border-neutral-300 px-2 py-1 text-xs capitalize dark:border-neutral-700 dark:bg-neutral-900"
            >
              {MOTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        )}
        <input
          type="file"
          accept="image/*"
          suppressHydrationWarning
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <input
          type="text"
          placeholder="Asset name (optional)"
          value={name}
          suppressHydrationWarning
          onChange={(e) => setName(e.target.value)}
          className="rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          type="submit"
          suppressHydrationWarning
          disabled={!file || busy}
          className="w-fit rounded bg-black px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-black"
        >
          {busy ? "Generating…" : "Generate 3D"}
        </button>
      </form>

      {asset && asset.status === "PROCESSING" && (
        <p className="mt-4 text-sm text-neutral-500">
          Generating… {asset.stage ? `(${asset.stage})` : ""} {asset.progress ? `${asset.progress}%` : ""}
        </p>
      )}
      {err && <p className="mt-4 text-sm text-red-600">{err}</p>}

      {asset && asset.status === "READY" && asset.glbUrl && (
        <div className="mt-5">
          <model-viewer
            src={asset.glbUrl}
            ios-src={asset.usdzUrl ?? undefined}
            camera-controls
            auto-rotate={!asset.animated}
            autoplay={asset.animated || undefined}
            touch-action="pan-y"
            style={{ width: "100%", height: "320px", background: "#f4f4f5", borderRadius: 8 }}
          />
          <p className="mt-1 text-xs text-neutral-400">
            {asset.animated ? "Animated ✓ · " : ""}GLB {asset.glbUrl ? "✓" : "✗"} · USDZ{" "}
            {asset.usdzUrl ? "✓ (iOS)" : "✗ (Android/desktop only)"}
          </p>
          {asset.genMode === "ANIMATED" && !asset.animated && (
            <p className="mt-1 text-xs text-amber-600">
              This shape couldn&apos;t be rigged — published as a static 3D model instead.
            </p>
          )}

          {!asset.widget ? (
            <button
              onClick={onPublish}
              className="mt-3 rounded bg-black px-4 py-1.5 text-sm font-medium text-white dark:bg-white dark:text-black"
            >
              Publish &ldquo;view in 3D&rdquo;
            </button>
          ) : (
            <div className="mt-4 space-y-3 text-sm">
              <div>
                <div className="font-medium">Shareable link</div>
                <a className="break-all text-blue-600 underline" href={viewerUrl ?? "#"} target="_blank">
                  {viewerUrl}
                </a>
              </div>
              <div>
                <div className="font-medium">Embed</div>
                <textarea
                  readOnly
                  value={embed}
                  className="mt-1 w-full rounded border border-neutral-300 p-2 font-mono text-xs dark:border-neutral-700 dark:bg-neutral-900"
                  rows={3}
                />
              </div>
              {qr && (
                <div>
                  <div className="font-medium">Print QR</div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={qr} alt="QR to viewer" width={140} height={140} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
