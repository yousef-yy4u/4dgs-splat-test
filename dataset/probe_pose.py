#!/usr/bin/env python3
"""Discover Anny's 'local-bone' pose_parameters format so 03_render_motion.py can drive it.
    conda run -n 4dgs-data python probe_pose.py
Key trick: model.get_pose_parameterization(model_output, 'local-bone') returns the REST pose IN the
exact format forward() expects -> we read its shape/dtype, then know how to modify + re-pose.
"""
import inspect, numpy as np, torch, anny

model = anny.Anny(); model.eval()
with torch.no_grad():
    out = model()

print("=== forward signature ===")
print(inspect.signature(model.forward))
print("\n=== get_pose_parameterization signature ===")
print(inspect.signature(model.get_pose_parameterization))

# extract the rest pose in 'local-bone' form
pose = None
for args in [(out, "local-bone"), (out, model.pose_parameterization), (out,)]:
    try:
        pose = model.get_pose_parameterization(*args)
        print(f"\ncalled get_pose_parameterization with {len(args)} args -> OK ({type(pose).__name__})")
        break
    except Exception as e:
        print("attempt failed:", repr(e))

def describe(x, name, depth=0):
    pad = "  " * depth
    if isinstance(x, dict):
        print(f"{pad}{name}: dict keys={list(x.keys())}")
        for k, v in x.items(): describe(v, k, depth + 1)
    elif isinstance(x, (list, tuple)):
        print(f"{pad}{name}: {type(x).__name__} len={len(x)}")
        for i, v in enumerate(x[:3]): describe(v, f"[{i}]", depth + 1)
    elif hasattr(x, "shape"):
        arr = np.asarray(x.detach().cpu() if hasattr(x, "detach") else x)
        print(f"{pad}{name}: {type(x).__name__} shape={tuple(arr.shape)} dtype={arr.dtype}  sample={arr.ravel()[:8]}")
    else:
        print(f"{pad}{name}: {type(x).__name__} = {repr(x)[:160]}")

print("\n=== REST pose_parameters (this is the format forward() wants) ===")
describe(pose, "pose")

# round-trip check: feed the rest pose straight back -> should reproduce the rest vertices
try:
    with torch.no_grad():
        out2 = model(pose_parameters=pose, pose_parameterization="local-bone")
    v0 = out["vertices"]; v1 = out2["vertices"]
    print("\nround-trip max vertex diff (rest pose fed back):",
          float((v1 - v0).abs().max()))
except Exception as e:
    print("\nround-trip failed:", repr(e))

print("\n=== bones (index: name) ===")
for i, l in enumerate(model.bone_labels):
    print(f"{i:3d} {l}")
