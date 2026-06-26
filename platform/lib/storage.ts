import { promises as fs } from "fs";
import path from "path";

// Phase-0 storage: local filesystem under STORAGE_DIR, served via /files/[...].
// Swappable for S3/R2 later — keep all asset file I/O behind this module.
const STORAGE_DIR = process.env.STORAGE_DIR ?? path.join(process.cwd(), "storage");

export function assetDir(assetId: string): string {
  return path.join(STORAGE_DIR, assetId);
}

export function publicUrl(assetId: string, filename: string): string {
  return `/files/${assetId}/${filename}`;
}

export async function saveAsset(
  assetId: string,
  filename: string,
  data: Buffer | Uint8Array,
): Promise<string> {
  const dir = assetDir(assetId);
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, filename), data);
  return publicUrl(assetId, filename);
}

export function storageRoot(): string {
  return STORAGE_DIR;
}
