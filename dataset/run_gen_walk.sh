#!/usr/bin/env bash
# Generate a clean-license walk: Kimodo-SOMA-RP-v1.1 driven by the Qwen3-8B text encoder
# (Apache-2.0, ungated) + Apache-2.0 projection layer -> no Llama gate.
set -euo pipefail
cd /root/4dgs/dataset
mkdir -p kimodo_out
export ANNY_CACHE_DIR="$HOME/.cache/anny"
export TEXT_ENCODER=qwen3-8b
export TEXT_ENCODER_MODE=local
export TEXT_ENCODER_DEVICE=cuda
kimodo_gen "a person walks forward naturally" \
  --model Kimodo-SOMA-RP-v1.1 \
  --duration 5.0 --seed 0 \
  --output kimodo_out/walk.npz --bvh
