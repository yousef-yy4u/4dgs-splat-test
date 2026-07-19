# 00_bootstrap_windows.ps1 — set up THIS Windows laptop as the dataset-pipeline DEV box.
# (Full-dataset rendering + training happen on the rented NVIDIA box — see 00_bootstrap.sh.)
#
# Why a conda env: system Python 3.13 fights the graphics-stack wheels (pyrender/PyOpenGL, bpy,
# Open3D all prefer <=3.12). We use Python 3.11 — the sweet spot. PyTorch here is CPU-only
# (this AMD Vega iGPU has no CUDA/ROCm path); that's fine for posing/skinning Anny.
#
# Run from an Anaconda/Miniconda PowerShell prompt:
#   powershell -ExecutionPolicy Bypass -File .\00_bootstrap_windows.ps1
$ErrorActionPreference = "Stop"
$ENV_NAME = "4dgs-data"

Write-Host "=== creating conda env '$ENV_NAME' (Python 3.11) ===" -ForegroundColor Cyan
conda create -y -n $ENV_NAME python=3.11

Write-Host "=== PyTorch (CPU build) ===" -ForegroundColor Cyan
conda run -n $ENV_NAME pip install torch --index-url https://download.pytorch.org/whl/cpu

Write-Host "=== Anny + headless renderer + IO ===" -ForegroundColor Cyan
# NOTE: NO PYOPENGL_PLATFORM here — on Windows pyrender uses the default hidden-window GL context
# (via the AMD OpenGL driver). Setting egl/osmesa would BREAK rendering on Windows.
conda run -n $ENV_NAME pip install "anny[warp,examples]" pyrender trimesh imageio pillow numpy tqdm opencv-python-headless

Write-Host "=== verify ===" -ForegroundColor Cyan
conda run -n $ENV_NAME python -c "import torch,anny; print('torch',torch.__version__,'cuda',torch.cuda.is_available()); print('anny',getattr(anny,'__version__','?'))"

Write-Host ""
Write-Host "Done. Next:" -ForegroundColor Green
Write-Host "  conda activate $ENV_NAME"
Write-Host "  python 01_probe_anny.py     # discovers Anny's API + smoke-tests the render path"
Write-Host ""
Write-Host "If pyrender's render step fails on the AMD GL driver, the robust fallback is Blender bpy" -ForegroundColor Yellow
Write-Host "(Cycles-CPU, truly headless): pip install bpy (version matching Python 3.11) -- ask Claude." -ForegroundColor Yellow
