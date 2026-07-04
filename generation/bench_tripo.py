#!/usr/bin/env python
"""Benchmark Tripo (commercial API) on our test images — quality + latency + credit cost, for the
build-vs-buy decision (D43). Cloud API, so NO local VRAM used. Reads TRIPO_API_KEY from
generation/.env (gitignored; this script never prints the key).

  python bench_tripo.py <out_dir> <img1> [img2 ...]
"""
import os, sys, time, json
import requests

BASE = "https://api.tripo3d.ai/v2/openapi"


def load_key():
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    key = os.environ.get("TRIPO_API_KEY", "")
    if not key and os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("TRIPO_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("TRIPO_API_KEY not set (fill generation/.env)")
    return key


def upload(key, path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    ext = "jpeg" if ext == "jpg" else ext
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/upload", headers={"Authorization": f"Bearer {key}"},
                          files={"file": (os.path.basename(path), f, f"image/{ext}")}, timeout=60)
    r.raise_for_status()
    d = r.json().get("data", {})
    token = d.get("image_token") or d.get("file_token") or d.get("token")
    if not token:
        sys.exit(f"upload: no token in response: {r.text[:300]}")
    return token, ("jpg" if ext == "jpeg" else ext)


def create_task(key, token, ftype):
    body = {
        "type": "image_to_model",
        "file": {"type": ftype, "file_token": token},
        "texture": True,
        "pbr": True,
        "texture_quality": "detailed",
    }
    r = requests.post(f"{BASE}/task", headers={"Authorization": f"Bearer {key}",
                      "Content-Type": "application/json"}, json=body, timeout=60)
    if r.status_code != 200:
        print(f"  create_task {r.status_code}: {r.text[:400]}", flush=True)
        # retry with the minimal valid body (some params/tiers reject pbr/texture_quality)
        body = {"type": "image_to_model", "file": {"type": ftype, "file_token": token}}
        r = requests.post(f"{BASE}/task", headers={"Authorization": f"Bearer {key}",
                          "Content-Type": "application/json"}, json=body, timeout=60)
        if r.status_code != 200:
            sys.exit(f"  minimal create_task also {r.status_code}: {r.text[:400]}")
        print("  minimal body accepted", flush=True)
    d = r.json().get("data", {})
    tid = d.get("task_id")
    if not tid:
        sys.exit(f"create task failed: {r.text[:300]}")
    return tid


def poll(key, tid):
    while True:
        r = requests.get(f"{BASE}/task/{tid}", headers={"Authorization": f"Bearer {key}"}, timeout=60)
        r.raise_for_status()
        d = r.json().get("data", {})
        status = str(d.get("status", "")).lower()
        prog = d.get("progress", 0)
        print(f"  [{status}] {prog}%", flush=True)
        if status in ("success", "succeeded", "completed"):
            return d
        if status in ("failed", "cancelled", "error", "unknown", "ban", "expired"):
            sys.exit(f"task {status}: {json.dumps(d)[:400]}")
        time.sleep(4)


def main():
    key = load_key()
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    results = []
    for path in sys.argv[2:]:
        name = os.path.splitext(os.path.basename(path))[0]
        print(f"\n=== {name} ===", flush=True)
        t = time.time()
        token, ftype = upload(key, path)
        tid = create_task(key, token, ftype)
        d = poll(key, tid)
        elapsed = time.time() - t
        output = d.get("output", {}) or d.get("result", {})
        url = output.get("pbr_model") or output.get("model") or output.get("base_model")
        cost = d.get("running_left") or d.get("cost") or d.get("credits")
        out_glb = os.path.join(out, f"{name}_tripo.glb")
        if url:
            g = requests.get(url, timeout=120); g.raise_for_status()
            open(out_glb, "wb").write(g.content)
            mb = len(g.content) / 1e6
        else:
            mb = 0
            print(f"  WARN no model url; output keys={list(output)}")
        print(f"[{name}] {elapsed:.1f}s | {mb:.1f}MB | task {tid}", flush=True)
        results.append({"name": name, "total_s": round(elapsed, 1), "mb": round(mb, 1),
                        "task_id": tid, "glb": out_glb, "had_pbr": bool(output.get("pbr_model"))})
    print("\n=== SUMMARY ===")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
