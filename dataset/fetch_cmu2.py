import urllib.request, json, sys
REPO = "una-dinosauria/cmu-mocap"
def api(path):
    u = f"https://api.github.com/repos/{REPO}/contents/{path}"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

top = api("data")
print("data/ entries:", [(e["name"], e["type"]) for e in top][:15])

# find subject-07 folder (walks). structure may be data/07/ or data/subjects/07/
listing = api("data/007")   # subject 007 = walking sequences
bvhs = [x for x in listing if x["name"].endswith(".bvh")]
print("bvh files in data/007:", [x["name"] for x in bvhs][:12])
pick = next((x for x in bvhs if x["name"] in ("007_01.bvh", "07_01.bvh")), bvhs[0] if bvhs else None)
if not pick:
    print("no bvh found"); sys.exit(1)
print("downloading", pick["name"], "from", pick["download_url"])
data = urllib.request.urlopen(urllib.request.Request(pick["download_url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
open("cmu_walk.bvh", "wb").write(data); print("SAVED cmu_walk.bvh", len(data), "bytes")

lines = data.decode(errors="ignore").splitlines()
joints, root_ch, nframes, ftime = [], None, None, None
for l in lines:
    t = l.strip().split()
    if t and t[0] in ("ROOT", "JOINT"): joints.append(t[1])
    if t and t[0] == "CHANNELS" and root_ch is None and len(t) >= 8: root_ch = t[2:]
    if t and t[0] == "Frames:": nframes = int(t[1])
    if l.strip().startswith("Frame Time:"): ftime = float(t[-1])
print("\njoints (%d): %s" % (len(joints), joints))
print("root channels:", root_ch, "| frames:", nframes, "| frame_time:", ftime)
