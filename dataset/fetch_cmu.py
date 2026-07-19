import urllib.request, sys
CANDIDATES = [
    "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data/07/07_01.bvh",
    "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/07/07_01.bvh",
    "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data/07_01.bvh",
    "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/bvh/07/07_01.bvh",
    "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/allasfamc/subjects/07/07_01.bvh",
]
out = "cmu_07_01.bvh"; ok = False
for u in CANDIDATES:
    try:
        print("trying", u)
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        if b"HIERARCHY" in data[:64]:
            open(out, "wb").write(data); print("  SAVED", len(data), "bytes"); ok = True; break
        print("  not a BVH:", data[:60])
    except Exception as e:
        print("  fail:", type(e).__name__, str(e)[:100])
if not ok:
    print("!! no BVH fetched"); sys.exit(1)

lines = open(out).read().splitlines()
joints, root_channels, nframes, ftime = [], None, None, None
for l in lines:
    t = l.strip().split()
    if t and t[0] in ("ROOT", "JOINT"): joints.append(t[1])
    if t and t[0] == "CHANNELS" and root_channels is None and len(t) >= 8: root_channels = t[2:]
    if t and t[0] == "Frames:": nframes = int(t[1])
    if l.strip().startswith("Frame Time:"): ftime = float(t[-1])
print("\njoints (%d):" % len(joints)); print(joints)
print("root channels:", root_channels)
print("frames:", nframes, "frame_time:", ftime)
