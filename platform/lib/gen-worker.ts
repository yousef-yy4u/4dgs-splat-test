// Thin client for the existing GPU pipeline (generation/server.py — PROJECT.md §9c).
// The web app authors/orchestrates; this Python worker does the heavy image->3D generation.
// Phase 0 talks to it directly over HTTP; a durable queue is added when concurrency needs it.
//
// Worker contract (from generation/server.py):
//   POST /generate   multipart form field "images" (1..4 files) -> { job_id, nviews }
//   GET  /status/:id -> { stage, pct, done, error, result, nviews }
//   GET  /out/:path  -> serves result files (glb, splat ply, ...)

const WORKER_URL = process.env.GEN_WORKER_URL ?? "http://localhost:8077";

export type GenStatus = {
  stage: string;
  pct: number;
  done: boolean;
  error: string | null;
  result: unknown | null;
  nviews: number;
};

export async function submitGeneration(images: Blob[]): Promise<{ jobId: string; nviews: number }> {
  const form = new FormData();
  for (const img of images) form.append("images", img);
  const res = await fetch(`${WORKER_URL}/generate`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`worker /generate ${res.status}: ${await res.text()}`);
  const json = (await res.json()) as { job_id: string; nviews: number };
  return { jobId: json.job_id, nviews: json.nviews };
}

export async function getGenStatus(jobId: string): Promise<GenStatus> {
  const res = await fetch(`${WORKER_URL}/status/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`worker /status ${res.status}`);
  return (await res.json()) as GenStatus;
}

export function workerOutUrl(path: string): string {
  return `${WORKER_URL}/out/${path}`;
}

export async function workerReachable(): Promise<boolean> {
  try {
    const res = await fetch(`${WORKER_URL}/`, { method: "GET", cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
