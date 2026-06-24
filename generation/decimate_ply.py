#!/usr/bin/env python
"""
Importance-based decimation of a 3DGS .ply to a target splat count (runtime LOD, D21).
Keeps the top-N splats by importance = sigmoid(opacity) * volume(exp(scale)).
Graceful (vs random subsample): drops the least-visible splats first.

Usage: decimate_ply.py in.ply out.ply [N=200000]
"""
import sys, numpy as np
from plyfile import PlyData, PlyElement

inp, out = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 200000

ply = PlyData.read(inp)
data = ply['vertex'].data
op = 1.0 / (1.0 + np.exp(-data['opacity']))
vol = np.exp(data['scale_0'] + data['scale_1'] + data['scale_2'])
imp = op * vol

if N >= len(data):
    keep = np.arange(len(data))
else:
    keep = np.argpartition(-imp, N)[:N]          # top-N by importance
    keep = keep[np.argsort(-imp[keep])]          # sorted (nice-to-have)

sub = data[keep]
PlyData([PlyElement.describe(sub, 'vertex')], text=False).write(out)
print(f"{len(data):,} -> {len(sub):,} splats  ->  {out}")
