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

// The worker's /generate result (rigged path). /generate_static returns just { glb, textured }.
export type GenResult = {
  glb: string;            // /out/<file>.glb (rigged GLB for animated; textured GLB for static)
  name: string;
  textured?: boolean;     // static path
  splat?: string;         // rigged path: decimated splat ply
  splat_skinned?: string | null; // rigged path: rig-bound splat (animated-splat hero tier, later)
  rig_ok?: boolean;       // rigged path: false => rigging fell back to a plain (un-animated) mesh
  bones?: number;
  note?: string;
};

// rig-agnostic motion-library presets the worker can bake (D42). "wave"/"walk" etc. need bone
// labels + retargeting and come later.
export const MOTIONS = ["idle", "sway", "bob", "spin", "float"] as const;
export type Motion = (typeof MOTIONS)[number];

// mode "static" -> /generate_static (textured mesh, no rig); "animated" -> /generate (rigged + chosen motion).
export async function submitGeneration(
  images: Blob[],
  mode: "static" | "animated" = "static",
  motion: Motion = "idle",
): Promise<{ jobId: string; nviews: number }> {
  const form = new FormData();
  // MUST pass a filename — Flask only treats multipart parts WITH a filename as files
  // (request.files); a nameless Blob lands in request.form and the worker sees no image.
  for (const img of images) {
    const filename = img instanceof File ? img.name : "upload.png";
    form.append("images", img, filename);
  }
  if (mode === "animated") form.append("motion", motion);
  // /generate_static = textured static GLB (mesh-first, gsplat+nvdiffrast bake);
  // /generate = the rigging path (TRELLIS->UniRig->bind_splat) productized for the "animated" surface (D42).
  const endpoint = mode === "animated" ? "/generate" : "/generate_static";
  const res = await fetch(`${WORKER_URL}${endpoint}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`worker ${endpoint} ${res.status}: ${await res.text()}`);
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
