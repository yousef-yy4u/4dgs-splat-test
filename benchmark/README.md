# 4dgs Splat Render Benchmark

A single self-contained web page (`index.html`, no dependencies, no backend) that measures **how many Gaussian splats this device can draw at framerate.** Output = the **splat budget** that the whole product is sized to (see PROJECT.md §9a).

> ⚠️ **Untested by the author** — this was written without a GPU/browser to run it. You are the first to run it. If you see an error in the red text at the top of the page, copy it back and it'll get fixed.

## What it measures
- Renders N synthetic gaussian splats, orbiting camera, and reports **sustained FPS**, frame-time p50/p95, and a throttle check (last-30s vs whole-run median).
- **Caveat (honest):** it uses **additive, order-independent blending** so there's no per-frame depth sort. Real alpha-blended 3DGS adds a sort cost (usually GPU/worker radix). So treat these as a **render-throughput budget** — a slightly optimistic ceiling. Good enough for a first per-device budget; we can validate exact numbers later with the real renderer (mkkellogg) on a real asset.

## How to run it

### Laptop (easiest)
Just open `index.html` in Chrome or Edge (double-click it, or right-click → open with browser). Done.

### iPhone — pick ONE:

**Option A — no setup, public URL (simplest):**
Drag the `benchmark/` folder onto [netlify.com/drop](https://app.netlify.com/drop) (or push to GitHub Pages / Vercel). You get a URL. Open it in **Safari on the iPhone**. The same URL works on the laptop too. *Nothing is computed in the cloud — the page is static; rendering runs on the phone's GPU.*

**Option B — serve from your laptop (nothing leaves your network):**
You're in VS Code → install the **"Live Server"** extension → right-click `index.html` → **"Open with Live Server"**. It shows a URL like `http://192.168.1.23:5500`. On the iPhone (same Wi-Fi as the laptop) open that URL in Safari.
- To find your laptop IP manually: open **Command Prompt** on Windows, run `ipconfig`, and read the **IPv4 Address** under your Wi-Fi adapter (usually `192.168.x.x`). The benchmark author cannot provide this — it's your laptop's local address, only visible on your machine.

## How to use it
1. Pick a splat count (start at 100k).
2. Tap **Start 5-min run**. Leave it running 5 minutes (catches thermal throttling — phones slow down after a few minutes).
3. Read the green RESULT box: sustained median FPS + verdict (🟢≥60 / 🟡30–60 / 🔴<30) + throttle drop.
4. Record the row, bump to the next splat count, repeat.
5. Run once **mono**, once **Stereo: ON** (stereo ≈ the real AR cost — two eyes).
6. The **largest splat count that stays 🟢** = that device's splat budget. Fill the table below.

## Results table (fill this in)

| Device | GPU (shown on page) | Mode | Splat count | Sustained FPS | Last-30s FPS | Verdict |
|---|---|---|---|---|---|---|
| iPhone 14 | | mono | | | | |
| iPhone 14 | | stereo | | | | |
| Laptop (iGPU) | | mono | | | | |
| Laptop (iGPU) | | stereo | | | | |
