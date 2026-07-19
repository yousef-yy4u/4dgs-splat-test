# dataset/ — the 4D avatar dataset pipeline

The "real spine" (SESSION_HANDOFF §7): build our own **4D (animated) multi-view** training
data by driving **Anny** with **clean motion** and rendering it from N cameras over time.

## Why this exists / what it is NOT
- **Anny-One** ([download](https://download.europe.naverlabs.com/humans/AnnyOne/), Apache-2.0, ungated)
  already gives ~800k **static** multi-view images (1280², up to 40 cams/scene) with camera params,
  3D pose/shape, and segmentation. It has **no temporal data** (poses sampled from AMASS; characters
  are HumGen3D-clothed with Anny params as the GT label).
- **So our job is the 4D part only:** same subject, same cameras, **moving over time**. Much smaller
  than 800k — it's `subjects × motions × cameras × frames`.

## Platform decision (D64)
- **Pure-Python, headless.** No game engine, no GUI. Anny is a PyTorch model; we render its mesh with
  **pyrender + trimesh (EGL offscreen)** → RGB + depth + mask. Runs over SSH on a rented GPU box.
- **Honest limit:** raw Anny is untextured → these renders are **geometry/motion supervision**
  (multi-view silhouettes, depth, normals, deformation over time), **not photoreal RGB**. Photoreal
  appearance stays with Anny-One (static) or a later heavy textured/Blender-Cycles path.
- **Clean motion only** (self-authored / procedural / audited-Mixamo / D61's GEM-X·Kimodo·SOMA-X) —
  **never AMASS** ([[licensing-landmines]]). Use Anny **default or `soma` topology only, never `smplx`** (NC, D56).

## Two environments (verified D64)
Same Python code runs both places — only the render backend differs:
| | **Laptop (DEV)** — Windows, AMD iGPU, no CUDA | **Rented box (RENDER + TRAIN)** — Linux, NVIDIA |
|---|---|---|
| Setup | `00_bootstrap_windows.ps1` → **conda Python 3.11** env | `00_bootstrap.sh` |
| PyTorch | **CPU-only** (fine for posing/skinning) | CUDA |
| Renderer backend | pyrender **default hidden-window GL** (desktop session; do NOT set egl) | pyrender **EGL** (headless) |
| Use for | write/debug the pipeline, render a **small slice**, eyeball frames | render the **full dataset** (won't fit locally / days to upload), train |

- **Python 3.13 fights the graphics wheels** (pyrender/PyOpenGL, `bpy`, Open3D all prefer ≤3.12) → dev in a **conda 3.11** env, not system 3.13.
- **Fallback renderer** if pyrender misbehaves on the AMD GL driver: **Blender `bpy` + Cycles-CPU** (truly headless, GL-stack-independent; `bpy` is locked to one exact Python minor version).
- **Escape hatch:** local Windows/AMD rendering is the fiddly bit — if it costs more than an hour, just render the slice on a cheap GPU box too (uploads in <1 min).

## Run order
1. **Laptop:** `powershell -ExecutionPolicy Bypass -File .\00_bootstrap_windows.ps1`  ·  **Box:** `bash 00_bootstrap.sh`
2. `python 01_probe_anny.py` — discover Anny's real API + smoke-test the render path (platform-aware backend).
   **Paste its full output back** so the render harness (Phase 1) is written against ground truth.
3. *(next)* `02_render_slice.py` — one body, one motion, N cameras, M frames → a contact-sheet PNG.
4. *(next)* `03_render_dataset.py` — scale to the full `subjects × motions × cams × frames` set + manifest (**on the box**).

## Working loop
Claude writes scripts here (Windows planning archive, no GPU) → you `scp`/pull to the box → run over
SSH → paste terminal output + a couple sample frames → iterate. You *see* every result as rendered
images, not a black box.
