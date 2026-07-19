#!/usr/bin/env bash
# 00_bootstrap.sh — stand up a freshly rented GPU box (RunPod / Vast / Lambda, Ubuntu + CUDA) for the
# 4D avatar dataset pipeline. Headless / SSH-only friendly. Idempotent-ish; safe to re-run.
#
#   bash 00_bootstrap.sh
#
# Assumes a PyTorch CUDA base image (torch already installed & matching the box's CUDA). If torch is
# missing, see the NOTE block below. Nothing here needs a GUI.
set -euo pipefail

echo "=================================================================="
echo " 4DGS dataset box bootstrap"
echo "=================================================================="

# --- 0. sanity: GPU present ---------------------------------------------------
echo "--- nvidia-smi ---"
nvidia-smi || { echo "!! no nvidia-smi — is this a GPU box?"; exit 1; }

# --- 1. system libs for headless EGL offscreen rendering (pyrender) -----------
# libegl1/libgl1 = EGL+GL; the rest cover common pyrender/OpenGL runtime needs.
echo "--- apt: EGL / GL runtime ---"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y || apt-get update -y
PKGS="libegl1 libgl1 libgles2 libglib2.0-0 libsm6 libxext6 libxrender1 freeglut3-dev git"
sudo apt-get install -y $PKGS || apt-get install -y $PKGS

# --- 2. python env ------------------------------------------------------------
# Use the box's existing python (base images ship torch there). A venv would shadow the CUDA torch,
# so we install INTO the base env with --user off. If you prefer isolation, create a venv that
# inherits system site-packages: python -m venv --system-site-packages .venv && source .venv/bin/activate
echo "--- python / torch check ---"
python - <<'PY'
import sys
print("python:", sys.version.split()[0])
try:
    import torch
    print("torch:", torch.__version__, "| cuda avail:", torch.cuda.is_available(),
          "| device:", (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"))
except Exception as e:
    print("!! torch not importable:", e)
    print("   NOTE: install the torch build matching this box's CUDA, e.g.:")
    print("   pip install torch --index-url https://download.pytorch.org/whl/cu124")
PY

# --- 3. pip deps: Anny + headless renderer + IO -------------------------------
echo "--- pip: anny + pyrender + trimesh + io ---"
python -m pip install --upgrade pip
# anny[warp] pulls NVIDIA Warp for fast mesh eval; examples adds the demo utils.
python -m pip install "anny[warp,examples]"
python -m pip install pyrender trimesh imageio pillow numpy tqdm opencv-python-headless

# --- 4. env vars (headless EGL + Anny cache) ----------------------------------
# pyrender must use EGL (no display). Anny caches multi-minute first-load assets — pin it to fast/roomy disk.
CACHE_DIR="${ANNY_CACHE_DIR:-$HOME/.cache/anny}"
mkdir -p "$CACHE_DIR"
{
  echo ''
  echo '# --- 4dgs dataset pipeline env (added by 00_bootstrap.sh) ---'
  echo 'export PYOPENGL_PLATFORM=egl'
  echo "export ANNY_CACHE_DIR=$CACHE_DIR"
} >> "$HOME/.bashrc"
export PYOPENGL_PLATFORM=egl
export ANNY_CACHE_DIR="$CACHE_DIR"
echo "PYOPENGL_PLATFORM=$PYOPENGL_PLATFORM   ANNY_CACHE_DIR=$ANNY_CACHE_DIR"

echo "=================================================================="
echo " bootstrap done. Next: python 01_probe_anny.py   (paste its output back)"
echo " (open a new shell or 'source ~/.bashrc' so the env vars take effect)"
echo "=================================================================="
