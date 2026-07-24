import imageio.v2 as imageio, numpy as np
frames = imageio.mimread("motion_out/walk.gif")
idx = np.linspace(0, len(frames)-1, 6).astype(int)
strip = np.concatenate([np.asarray(frames[i])[..., :3] for i in idx], axis=1)
imageio.imwrite("motion_out/walk_cycle_strip.png", strip)
print("frames:", len(frames), "-> strip idx", idx.tolist(), "->", strip.shape)
