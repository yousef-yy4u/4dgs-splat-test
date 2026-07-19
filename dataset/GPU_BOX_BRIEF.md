# GPU-box task brief — clean motion → Anny render (hand this to Claude Code running ON the rented GPU)

You are running on a **rented NVIDIA GPU box** (Linux, CUDA). Your job: generate **clean-licensed human
motion** with **NVIDIA Kimodo-RP**, drive the **Anny** body model with it via **SOMA-X's `SOMALayer`**, and
render it (multi-view images + a GIF). This was scoped on a separate laptop session; the notes below are
hard-won — follow the guardrails exactly.

## GOAL
`Kimodo-RP (text→motion, SOMA skeleton) → SOMALayer(identity_model_type="anny") → posed Anny vertices → pyrender (EGL headless) → walk.gif + multiview.png`. Produce a **natural walk** first; then idle + a wave.

## ⛔ LICENSING GUARDRAILS (non-negotiable — this is a commercial product meant to scale past $1M)
- **Kimodo: use ONLY the `*-RP` (RigPlay) checkpoints on the SOMA or G1 skeleton** (e.g. `nvidia/Kimodo-SOMA-RP-v1` / `-v1.1`). RP = trained on NVIDIA-owned RigPlay data, **NVIDIA Open Model License = uncapped commercial (clean).**
- **NEVER use `*-SEED` checkpoints** (trained on the revenue-capped BONES-SEED dataset → tainted) and **NEVER `*-SMPLX`** (non-commercial, SMPL-X/MPI).
- **Anny topology: default or `soma` only, NEVER the `smplx` flag** (non-commercial). SOMALayer's anny backend is fine.
- GEM-X (video→motion, `NVlabs/GEM-X`) is also clean (NVIDIA-owned data) if you later want capture-from-video — but do Kimodo-RP first (no filming needed).
- If you accept a HuggingFace license gate for these, the **NVIDIA Open Model License is safe to accept** (uncapped commercial). Do NOT accept/download `bones-studio/seed` (BONES-SEED) — it's a $1M-revenue-capped trap.

## ENVIRONMENT SETUP
Assume a PyTorch CUDA base image. Install into a fresh venv/conda (Python 3.10–3.11 recommended):
```bash
pip install "anny[warp]" "py-soma-x[anny]" pyrender trimesh imageio pillow numpy tqdm
# Kimodo: clone + install per its README, pull an RP-SOMA checkpoint (NOT seed/smplx)
git clone https://github.com/nv-tlabs/kimodo && cd kimodo && pip install -e .   # follow its README
export PYOPENGL_PLATFORM=egl   # headless Linux render backend for pyrender (apt: libegl1 libgl1 if missing)
```
Verify: `python -c "import torch; print(torch.cuda.is_available())"` must be True.

## SOMALayer API + THE TWO REQUIRED SHIMS (verified on CPU; identical on CUDA)
`SOMALayer` auto-downloads its assets from HuggingFace on first use.
```python
import torch, anny.models.phenotype as _ph
from soma import SOMALayer

# SHIM 1: soma 0.1.0 passes local_changes=None into anny 0.5's get_phenotype_blendshape_coefficients,
# whose try/except catches only KeyError (not the TypeError from subscripting None). Coerce None -> {}.
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(f):
            def g(self, *a, local_changes=None, **k): return f(self, *a, local_changes=(local_changes or {}), **k)
            return g
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

layer = SOMALayer(identity_model_type="anny", device="cuda"); layer.eval()
# forward(poses, identity_coeffs, scale_params=None, transl=None, pose2rot=True, ...)
#   poses: (B, 77, 3) axis-angle  (pose2rot=True)  OR (B,77,3,3) rotmats (pose2rot=False)
#   identity_coeffs: (B, 11)  Anny phenotype coeffs (zeros = neutral-ish; NOT the SOMA 128!)
#   transl: (B, 3) root translation  — REQUIRED (SHIM 2: passing None crashes batched_skinning)
# returns dict {"vertices": (B, 18056, 3), "joints": (B, 77, 3)}   <-- NOTE: 18,056-vert SOMA topology,
#   NOT Anny's default 13,718 mesh (asset-consistency caveat for later; fine for motion).
```

## KIMODO-RP → SOMALayer WIRING
- Generate: `kimodo_gen "a person walks naturally"` (or `python -m kimodo.scripts.generate ... --model <RP-SOMA checkpoint>`), duration ~4–6s. Output = `.npz` with per-frame joint positions, **rotation matrices [T,77,3,3]**, foot contacts, and **root trajectory**.
- Feed SOMALayer per frame: pass Kimodo's rotmats with `pose2rot=False` (reshape to what SOMALayer expects — introspect the exact shape), and `transl` = the frame's root translation. `identity_coeffs = torch.zeros(1,11)`.
- Collect `out["vertices"]` per frame → a `(T, 18056, 3)` sequence.

## RENDER (reuse the laptop's proven pattern)
- Faces: `layer.faces` (already triangles). pyrender OffscreenRenderer, EGL. Frame a tracking side-3/4 camera that recomputes the body center per frame (the root translates forward). Output `walk.gif` + an 8-camera `multiview.png` of one mid-stride frame (the multi-view frame = the shape 4DGS training later consumes).
- Skin material: a neutral gray/skin `MetallicRoughnessMaterial`.

## SUCCESS CRITERIA
A **natural walk** GIF where legs stride with correct (posterior) knee bend, arms swing at the sides, and the body advances — driven entirely by Kimodo-RP through SOMALayer's OFFICIAL SOMA→Anny retarget (NO hand-rolled retargeting; that path had arm/foot jank and is abandoned). Then generate `"stand idle"` and `"wave hello"` clips the same way.

## WHY THIS PATH (context)
Clean, scalable motion is a hard licensing moat (Mixamo, BONES-SEED both rejected). Kimodo-RP + GEM-X (NVIDIA Open Model, uncapped commercial) are the clean core; they output the SOMA skeleton which Anny reads NATIVELY via SOMALayer — no fragile hand-rolled retarget. Bank each generated clip as a reusable tagged library asset. Report GPU-hours + cost; **stop the box when done.**
