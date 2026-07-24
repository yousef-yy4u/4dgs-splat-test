# NEW INSTANCE — rebuild this box from the repo

> Written 2026-07-24 when the working box (RTX 3090, 32 GB disk, **99 % full**) was retired for a
> larger one. Read this **first** on the new machine, then [SESSION_HANDOFF.md](SESSION_HANDOFF.md)
> (current state, newest decision = **D105**) and [PROJECT.md](PROJECT.md) (SSOT).

---

## 0. TL;DR — what is and isn't in git

| | in git? | notes |
|---|---|---|
| All pipeline code (`dataset/*.py`, `dataset/viewer/`) | **yes** | including the vendored three.js r160 + addons |
| Docs (PROJECT / SESSION_HANDOFF / research) | **yes** | |
| Kimodo walk motion (`dataset/kimodo_out/walk.npz`) | **yes** | 1.3 MB — regenerating needs the whole Kimodo+Qwen3-8B stack, so it is committed deliberately |
| `dataset/motion_out/` (633 MB) | **NO** (gitignored) | generated blobs **+ the 343 MB asset library** |
| `dataset/gsplat_out/tandt_db.zip` (399 MB) | **NO** | public benchmark download, do not copy — re-fetch only if needed |
| `/root/blender` (1.3 GB), `/root/kimodo*`, `/root/gsplat` | **NO** | external installs, see §2 |

## 1. ⚠️ COPY THIS BEFORE DESTROYING THE OLD BOX

**`dataset/motion_out/assets_src/` — 343 MB, 38 assets.** This is the whole CC0/CC-BY avatar asset
library (15 hair, 13 eyebrows, 7 garments, 5 PBR skin identities, 1 head scan). It is re-downloadable
but it took a full research + acquisition pass (D81/D84/D100) to assemble, and several sources are
name-your-own-price itch.io pages that could disappear.

```bash
# from the NEW box
rsync -avz --progress <old-host>:/root/4dgs/dataset/motion_out/assets_src/ \
                                 /root/4dgs/dataset/motion_out/assets_src/
python dataset/make_assets_manifest.py --src dataset/motion_out/assets_src --out /tmp/check.md
diff <(grep '^- .`' /tmp/check.md) <(grep '^- .`' dataset/ASSETS_MANIFEST.md) && echo "assets verified"
```

If the copy isn't possible, [dataset/ASSETS_MANIFEST.md](dataset/ASSETS_MANIFEST.md) lists every asset,
its author, its licence and a sha256 prefix per file, plus the source portals to re-download from.

**Everything else in `motion_out/` is regenerable** — see §4 for the exact commands. Nothing else needs
copying.

## 2. Rebuild the environment

Pins that matter are in [dataset/ENV_PINS.txt](dataset/ENV_PINS.txt) (captured from the working box).
The torch/CUDA combination is load-bearing — D59 and D70 were both lost days to getting it wrong.

```bash
# Python 3.10, CUDA 12.1+ driver
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install "numpy<2"                     # numpy 1.26.4 — gsplat + anny both break on numpy 2
pip install gsplat==1.5.3 trimesh plyfile imageio pillow scipy roma
pip install "anny[warp]" "py-soma-x[anny]" pyrender
pip install playwright && python -m playwright install chromium    # headless browser verification, D105
```

**Blender 4.2.5 LTS** at `/root/blender` (download the LTS tarball, extract, no install needed), plus the
**MPFB2 addon** (`makehumancommunity/mpfb2`) into
`~/.config/blender/4.2/extensions/user_default/mpfb` — D103's clothing fitter calls it via `bpy`.

**External repos** (clone only if you need to regenerate motion):
- `https://github.com/qian2501/kimodo` → `/root/kimodo-qwen` — the Qwen3-8B fork. **Use this one**, not
  the upstream: upstream needs the gated Llama-3 text encoder (D70).
- `https://github.com/nv-tlabs/kimodo` → `/root/kimodo` — upstream, reference only.
- `https://github.com/nerfstudio-project/gsplat` → `/root/gsplat` — only if pip's gsplat wheel fails.

⛔ The licensing guardrails in [dataset/GPU_BOX_BRIEF.md](dataset/GPU_BOX_BRIEF.md) still apply:
Kimodo **`*-RP` checkpoints only** (never `*-SEED`, never `*-SMPLX`), Anny **default or `soma` topology
only** (never the `smplx` flag).

## 3. Verify the box works (in this order)

```bash
python -c "import torch,gsplat;print(torch.__version__, torch.cuda.is_available())"   # 2.5.1+cu124 True
/root/blender/blender --version                                                        # 4.2.5 LTS
cd dataset/viewer && python3 serve_viewer.py --port 8000 --out ../motion_out --stem walk_face
```
Then open **`/skintest`** (D105 textured mesh — the current direction) and **`/splat`** (D104 splat).
Headless check, no display needed:
```python
p.chromium.launch(channel="chromium", headless=True,
    args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--no-sandbox"])
```
FPS under SwiftShader is software-rasterised and meaningless; geometry/material/console-error checks are real.

## 4. Regenerate everything else in `motion_out/`

```bash
cd dataset
# 1. base mesh with UVs + skin/eye material groups          (seconds)
python export_textured_obj.py --out motion_out/_refit96/anny_adult.obj

# 2. the browser textured mesh — D105, the current direction (seconds)
SK=motion_out/assets_src/skins/smokeworks_vol1
python export_skin_glb.py --obj motion_out/_refit96/anny_adult.obj \
  --skin_basecolor "$SK/african_female_young_skinTest_A_tinasia_young_BaseColor_Utility - sRGB - Texture.png" \
  --skin_normal    "$SK/african_female_young_skinTest_A_tinasia_young_Normal_Utility - Raw.png" \
  --skin_orm       "$SK/african_female_young_skinTest_A_tinasia_young_OcclusionRoughnessMetallic_Utility - Raw.png" \
  --texres 2048 --out motion_out/skin_test.glb

# 3. the splat (optional now — demoted to a premium path by D105)  (~25 min render + ~10 min fit)
#    exact rig + flags are in motion_out/_refit_d104_realskin/README.txt, reproduced here:
/root/blender/blender -b -P blender_render_skin.py -- --obj motion_out/_refit96/anny_adult.obj \
  --tex $(python -c "import anny,os;print(os.path.join(os.path.dirname(anny.__file__),'data/mpfb2/textures'))") \
  --out <scratch>/mv --poses <scratch>/mv/transforms.json \
  --rig shells --layers 4 --az 24 --radii auto --size 384 --samples 64 --skin_basecolor ... --skin_normal ... --skin_orm ...
python fit_gsplat_poc.py --mv <scratch>/mv --obj motion_out/_refit96/anny_adult.obj --out <scratch>/fit --iters 3500
cp <scratch>/fit/avatar.ply motion_out/poc_avatar.ply    # held-out 27.29 dB is the number to beat

# 4. clothing bake (only if you touch the garment catalogue)      (~10 min)
/root/blender/blender -b -P mpfb_fit_blender.py            # -> motion_out/mpfb_out/
python mpfb_prefit.py
```

The walk itself (`motion_out/walk_face_*.npy/.npz`) comes from `pose_default_walk.py` driven by the
committed `kimodo_out/walk.npz` — no Kimodo/Qwen install needed unless you want *new* motion.

## 5. Disk hygiene (why we moved)

The old box died at 32 GB. The hogs were `/root/.cache` (**20 GB** — pip/HF/playwright), `/root/blender`
(1.3 GB), `dataset/gsplat_out/tandt_db.zip` (399 MB, a public benchmark download that is not used by
anything current). Budget **≥ 200 GB** on the new box and set `HF_HOME` / `PIP_CACHE_DIR` onto the big
volume before installing anything.

## 6. Open threads to pick up

See SESSION_HANDOFF §IMMEDIATE NEXT. The two that matter most after D105:
1. **Commit to the textured-mesh direction** — rig the D105 GLB and drive it (skinned mesh + Audio2Face
   face + Kimodo body), rather than continuing to invest in splat fitting.
2. **⚠️ 6 hair assets carry AGPL3 headers** (see the LICENCE RISK section of
   [dataset/ASSETS_MANIFEST.md](dataset/ASSETS_MANIFEST.md)) — copyleft is disqualifying for a hosted
   avatar service. Re-verify or drop them before anything ships.
