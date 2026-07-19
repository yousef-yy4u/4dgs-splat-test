import urllib.request, numpy as np, sys
URLS = [
    "https://media.githubusercontent.com/media/NVlabs/SOMA-X/main/assets/ROM5.npy",  # git-lfs media
    "https://raw.githubusercontent.com/NVlabs/SOMA-X/main/assets/ROM5.npy",
    "https://github.com/NVlabs/SOMA-X/raw/main/assets/ROM5.npy",
]
out = "ROM5.npy"; ok = False
for u in URLS:
    try:
        print("trying", u)
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=45).read()
        print("  got", len(data), "bytes")
        if len(data) < 300 and b"git-lfs" in data:
            print("  (LFS pointer, not the file):", data[:150]); continue
        open(out, "wb").write(data); ok = True; break
    except Exception as e:
        print("  fail:", type(e).__name__, e)
if not ok:
    print("!! could not fetch ROM5"); sys.exit(1)

a = np.load(out, allow_pickle=True)
print("\nloaded:", type(a).__name__, "shape", getattr(a, "shape", None), "dtype", getattr(a, "dtype", None))
if isinstance(a, np.ndarray) and a.dtype == object and a.shape == ():
    d = a.item(); print("dict keys:", list(d.keys()))
    for k, v in d.items():
        print("  ", k, getattr(v, "shape", None), getattr(v, "dtype", type(v).__name__))
elif isinstance(a, np.ndarray):
    print("array — first values:", a.ravel()[:6])
