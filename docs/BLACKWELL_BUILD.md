# LHM++ on Blackwell (RTX 5090, sm_120) — working build recipe

Reproduces the env that runs LHM++ inference + `to_gs_ply.py` on the 5090 (CUDA 12.5 toolkit,
torch 2.11/cu128). Conda env: `lhmpp` (cloned from `trellis2`). Achieved 2026-07-04: first
160k-gaussian avatar PLY out of `LHMPP-700M` (runs in SMPLX-FREE mode).

## The 5 things that make it work on Blackwell
1. **Arch = `9.0+PTX`, NOT `12.0`.** CUDA 12.5's nvcc can't target `compute_120` ("nvcc fatal:
   Unsupported gpu architecture 'compute_120'"). Compile every CUDA ext for sm_90 + PTX and let the
   driver JIT to sm_120. Set for ALL builds: `export TORCH_CUDA_ARCH_LIST="9.0+PTX" CUDA_HOME=/usr/local/cuda-12.5 FORCE_CUDA=1`.
2. **spconv: use `spconv-cu126` (2.3.8 / cumm 0.7.11), NOT `spconv-cu120`.** cu120's cumm 0.4.11
   SIGFPEs (`cumm/tensorview from_numpy` → `implicit_gemm`) because it doesn't know sm_120. cu126's
   newer cumm handles it. This was THE final blocker.
3. **xformers has no sm_120 kernel** (flash needs <=256 head_dim, cutlass needs <=sm9.0, fa2/fa3
   reject float32) → monkeypatch `xformers.ops.memory_efficient_attention` -> torch SDPA. Same fix as
   D52 SV4D. Lives in `_compat/sitecustomize.py` (auto-applied via `PYTHONPATH=./_compat:$PYTHONPATH`).
4. **chumpy 0.70** (smplx/FLAME dep) imports numpy aliases removed in numpy>=1.24. `_compat/sitecustomize.py`
   restores `numpy.bool/int/float/...`. Install chumpy with `--no-build-isolation` (its setup.py imports pip).
5. **huggingface_hub 0.34.4** (has DDUFEntry for diffusers 0.39, still <1.0 for modelscope). Force with
   `--force-reinstall --no-deps`, AND patch `core/utils/model_download_utils.py` (the `if not _hf_version_ok`
   block was `pip install huggingface_hub==0.23.2` on every startup → changed to `if False and ...`).

## Deps built from source for 9.0+PTX (all `--no-build-isolation`)
pytorch3d (@stable), lib/pointops (bundled), torch_scatter, diff_gaussian_rasterization
(ashawkey — Inria NC, EVAL-ONLY, swap for gsplat in clean build), simple-knn (camenduru).
Pure-python: gsplat 1.4.0, open3d, pyrender, typeguard==2.13.3, + the requirements.txt set unpinned.

## Run (T-pose image -> gaussian PLY)
```
conda activate lhmpp
export PYTHONPATH=/home/sov2/projects/LHM-plusplus/_compat:$PYTHONPATH
export TORCH_CUDA_ARCH_LIST="9.0+PTX" CUDA_HOME=/usr/local/cuda-12.5 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/sov2/projects/LHM-plusplus
python scripts/inference/to_gs_ply.py --model_name LHMPP-700M-PixelShuffle \
  --model_path ./checkpoints/LHMPP-700M \
  --image_glob "./assets/example_aigc_images/<img>.jpg" --output out.ply
```
Weights: `checkpoints/LHMPP-700M` (HF `3DAIGC/LHMPP-700M`, CC-BY-NC — eval only). Priors:
`pretrained_models/huggingface/...LHMPP-Prior` (must fully download incl. voxel_grid/cano_1_volume.npz
931MB + voxel_192.pth 779MB — the tool's mid-run fetch grabs only small files). Needs ~20GB VRAM peak
(fits an idle window; runs alongside qwen when the box has room).
