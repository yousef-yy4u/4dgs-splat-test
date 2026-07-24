#!/usr/bin/env python3
"""4DGS Studio — live editor/viewer backend.

Serves an interactive three.js "game-engine" scene (viewer.html) where you
place the avatar, arrange a capture-camera rig, browse/switch subject models,
upload skin/hair/clothing packages, and upload multi-view T-pose captures to
fit gaussians onto a model. Replaces the old separate-render tab soup with one
final-product scene.

    python3 serve_viewer.py --port 8000 --out ../motion_out

PERF: the per-model vertex trajectory ([T,V,3] float32, ~32MB for the SOMA
mesh) was the whole "slow first render" — it shipped raw over the SSH tunnel.
Now positions are quantized to uint16 (per-axis min/range in the header) and
the whole blob is gzipped on the wire (~5-6x smaller). The browser dequantizes.

Endpoints:
    GET  /                      viewer.html (the Studio)
    GET  /models.json           discovered subject models [{stem,label,thumb,frames,verts}]
    GET  /status.json?stem=     {ready, mtime, T, V, F, fps, ...} for one model
    GET  /data.bin?stem=        gzipped, quantized faces+verts blob (v2)
    GET  /thumb/<stem>.png       thumbnail for a model (multiview/strip fallback)
    GET  /assets.json?kind=     uploaded skin|hair|clothing|capture packages
    GET  /asset/<kind>/<name>   raw uploaded file
    POST /upload/<kind>         raw body + X-Filename header -> stored under assets/<kind>/
    POST /fit                   queue a gaussian-fit job from an uploaded capture (D74 pipeline)
    GET  /vendor/...            three.js modules
    (legacy image endpoints kept for back-compat: /<stem>.gif etc.)
"""
import os, io, sys, json, time, gzip, struct, argparse, threading, http.server, socketserver
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8000)
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "motion_out"))
ap.add_argument("--stem", default="walk", help="default model shown on load")
ap.add_argument("--fps", type=float, default=30.0)
ap.add_argument("--host", default="0.0.0.0")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(args.out)
ASSETS = os.path.join(OUT, "assets")           # skin/hair/clothing uploads
CAPTURES = os.path.join(OUT, "captures")        # multi-view person T-pose uploads
JOBS = os.path.join(OUT, "fit_jobs")            # queued gaussian-fit jobs (D74 worker consumes)
for d in (ASSETS, CAPTURES, JOBS):
    os.makedirs(d, exist_ok=True)
for k in ("skin", "hair", "clothing"):
    os.makedirs(os.path.join(ASSETS, k), exist_ok=True)

FACES = os.path.join(OUT, "faces.npy")
MAGIC = b"4DGS"
ASSET_KINDS = ("skin", "hair", "clothing", "capture")

# ---- splat (.ply) -> compact browser buffer -------------------------------
# D87: was packing a single scalar "size" (mean of the 3 log-scale axes), throwing away the
# gaussian's actual SHAPE (rotation quaternion + per-axis scale) and forcing the renderer to
# draw every gaussian as an isotropic circle. Real 3D Gaussian Splatting renders each gaussian
# as its true oriented ELLIPSE (the projection of its 3D covariance onto the screen plane) --
# collapsing that to "same-size circle for everything" is a big part of why this read as
# uniform bubbly foam rather than the sharp look real 3DGS viewers have (the other part is the
# fit itself: this mesh-anchored fit's gaussians happen to already be near-isotropic in THIS
# checkpoint, measured ratio ~1.1 median -- see D87's refit for more/sharper views). Packs a
# 3DGS .ply into: uint32 count, then per-gaussian
#   float32 x,y,z | float32 cov_xx,cov_xy,cov_xz,cov_yy,cov_yz,cov_zz | uint8 r,g,b,a
#   (40 bytes each). Covariance = R*S*S^T*R^T (R from the fitted rotation quaternion, S =
# diag(exp(scale_0,1,2))) -- computed once here (cheap, cached by mtime) so the client only
# has to project it through the current view matrix each frame, not rebuild it from scratch.
_splat_cache = {}   # path -> (mtime, bytes)
def build_splat_buffer(fp):
    mt = os.path.getmtime(fp)
    hit = _splat_cache.get(fp)
    if hit and hit[0] == mt:
        return hit[1]
    from plyfile import PlyData
    v = PlyData.read(fp)["vertex"].data
    C0 = 0.28209479177387814
    xyz = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float32)
    dc = np.stack([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]], 1).astype(np.float32)
    rgb = np.clip(0.5 + C0 * dc, 0, 1)
    a = (1.0 / (1.0 + np.exp(-v["opacity"].astype(np.float32))))
    scale = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64))
    quat = np.stack([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], 1).astype(np.float64)  # w,x,y,z
    quat /= np.clip(np.linalg.norm(quat, axis=1, keepdims=True), 1e-9, None)
    w, x, y, z = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
    N = len(xyz)
    R = np.empty((N, 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    M = R * scale[:, None, :]                      # R @ diag(scale), broadcast over columns
    Sigma = M @ M.transpose(0, 2, 1)                # R*S*S^T*R^T, (N,3,3) symmetric
    n = len(xyz)
    out = io.BytesIO()
    out.write(struct.pack("<I", n))
    body = np.zeros(n, dtype=[("p", "<f4", 3), ("cA", "<f4", 3), ("cB", "<f4", 3), ("c", "u1", 4)])
    body["p"] = xyz
    body["cA"] = Sigma[:, 0, :].astype(np.float32)              # Sigma_xx, Sigma_xy, Sigma_xz
    body["cB"] = np.stack([Sigma[:, 1, 1], Sigma[:, 1, 2], Sigma[:, 2, 2]], 1).astype(np.float32)
    body["c"][:, :3] = (rgb * 255).astype(np.uint8)
    body["c"][:, 3] = (a * 255).astype(np.uint8)
    out.write(body.tobytes())
    buf = out.getvalue()
    _splat_cache[fp] = (mt, buf)
    return buf


def discover_splats():
    """Every *.ply directly in OUT is a selectable splat (skips assets_src/ subtree)."""
    out = []
    try:
        for fn in sorted(os.listdir(OUT)):
            if fn.endswith(".ply"):
                fp = os.path.join(OUT, fn)
                out.append({"name": fn[:-4], "size": os.path.getsize(fp),
                            "mtime": os.path.getmtime(fp)})
    except FileNotFoundError:
        pass
    return out


# ---- CC0/CC-BY MakeHuman hair/eyebrows/clothing catalog + on-demand outfit compose -------
# D84: the assets a prior session downloaded+proved (D81/D83) only ever lived in /tmp
# scratch space and were never wired into the live viewer. Persisted a curated, PRE-
# VALIDATED subset under motion_out/assets_src/ (gitignored, like everything else in
# motion_out) and exposed them here so the Hair/Clothing tabs can offer real selectable
# items instead of just an upload dropzone. "Pre-validated" = each asset was fit-tested
# against the arms-down basemesh and rejected if it errored (topology mismatch) or blew
# out past a sane bbox (the D81/D83 flowing-hair extrapolation failure) -- see
# outfit_lib.fit_asset_checked. The catalog only lists what actually passed.
ASSETS_SRC = os.path.join(OUT, "assets_src")
OUTFIT_KINDS = {
    "hair": [("hair", None)],
    "eyebrows": [("eyebrows", None)],
    "clothing": [("clothing/tops", "top"), ("clothing/bottoms", "bottom")],
}
# D85 found these broken by actual render, not just numeric heuristics -- shard-cluster tops
# and a hair asset exploding into a flat halo/ring. D89 root-caused the REAL bug behind most of
# this: `mhclo_fit.py`/`outfit_lib.py` were fitting against Anny's REDUCED, RENUMBERED
# 13,718-vertex default-topology array, while .mhclo binding indices are authored against
# MakeHuman's RAW 19,158-vertex basemesh -- a genuine index-space mismatch, not a precision
# limit (see `outfit_lib.arms_down_fit_basemesh()`). Fixed by fitting against
# `anny.Anny(topology="makehuman", remove_unattached_vertices=False)` instead (verified
# index-space-correct + an exact 0.00mm surface match to the displayed body). Re-rendered
# every asset in the catalog against the fix (not just re-run through the numeric checks --
# same discipline as D86): all 3 toigo_* tops are now genuinely clean garment shapes, removed
# from this list. `elvs_reverse_french_braid_bun` is NOT fixed by this -- still visibly wrong
# (a flat ring/disc around the head instead of a bun; improved in scale/containment from the
# old halo but not correct), even when fit against MPFB2's own basemesh with our own fit math,
# while MPFB2's own real fitting ENGINE (not just its basemesh) handles it correctly -- so the
# residual gap for this one asset is in the fitting algorithm itself (this bun needs real
# volume pulled off the head surface, unlike the other braid-family assets which drape along
# it and DO fit cleanly now), not the basemesh. Kept excluded, honestly, rather than shipping
# a differently-broken result.
_KNOWN_BROKEN = {
    ("hair", "elvs_reverse_french_braid_bun"),
}
_catalog_cache = {}     # kind -> list of catalog entries
_catalog_paths = {}     # (kind,id) -> mhclo path, for the compose endpoint


def _asset_display_name(dirname):
    return dirname.replace("_", " ").replace("-", " ").title()


def build_catalog(kind):
    if kind in _catalog_cache:
        return _catalog_cache[kind]
    from outfit_lib import arms_down_fit_basemesh, fit_asset_checked
    B_fit = arms_down_fit_basemesh()   # D89: correct (19158v, index-space-exact) fit basemesh
    feet_z = float(B_fit[:, 2].min())
    entries = []
    for subdir, slot in OUTFIT_KINDS.get(kind, []):
        root = os.path.join(ASSETS_SRC, subdir)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            adir = os.path.join(root, name)
            mhclo = os.path.join(adir, name + ".mhclo")
            if not os.path.isfile(mhclo):
                continue
            aid = f"{slot or kind}:{name}"
            import mpfb_prefit as mp
            if mp.has_prefit(name):
                # D102: this asset has an offline MPFB2-engine prefit -> it's validated by
                # MPFB's own fitting engine (subdivided + eased), which handles cases our affine
                # fitter can't (e.g. elvs_reverse_french_braid_bun -- excluded since D85 because
                # affine explodes it into a flat ring; MPFB fits it as a real bun). Trust it and
                # skip the affine envelope check (the compose/dress paths use the prefit anyway).
                pass
            elif (kind, name) in _KNOWN_BROKEN:
                print(f"[studio] catalog SKIP {kind}/{name}: known-broken affine fit, no MPFB prefit")
                continue
            else:
                try:
                    # validate only -- discard the fit; skip the (expensive) surface push since
                    # the geometry is thrown away here (D94)
                    fit_asset_checked(mhclo, B_fit, feet_z, push_margin=0)
                except Exception as e:
                    print(f"[studio] catalog SKIP {kind}/{name}: {e}")
                    continue
            thumb = None
            for cand in (name + ".thumb", "thumb.png", name + ".png"):
                if os.path.isfile(os.path.join(adir, cand)):
                    thumb = cand
                    break
            entries.append({"id": aid, "name": _asset_display_name(name), "slot": slot,
                             "thumb": f"/asset_src/{kind}/{name}/thumb" if thumb else None})
            _catalog_paths[aid] = mhclo
            if thumb:
                _catalog_paths[("thumb", kind, name)] = os.path.join(adir, thumb)
    _catalog_cache[kind] = entries
    print(f"[studio] catalog {kind}: {len(entries)} usable asset(s)")
    return entries


_PART_COLOR = {   # flat vertex color per part kind (baked, no texture map yet)
    "body": (0xca, 0xa8, 0x92), "hair": (0x3a, 0x24, 0x18), "eyebrows": (0x1a, 0x0f, 0x0c),
    "top": (0x38, 0x4d, 0x6b), "bottom": (0x26, 0x28, 0x33),
}
_compose_cache = {}   # selection tuple -> bytes


# D92: user wants to control garment size manually (D91's per-kind defaults were a starting
# point, not the last word). slot->boost-dict-key map so the /compose.bin `?hair_boost=&
# clothing_boost=` query params (one shared knob for top+bottom, since both are "clothing" in
# outfit_lib's kind detection) reach the right assets.
_SLOT_TO_BOOST_KEY = {"hair": "hair", "eyebrows": "eyebrows", "top": "clothing", "bottom": "clothing"}


def build_compose_buffer(sel, boosts=None):
    """sel: dict of kind->asset-id (hair/eyebrows/top/bottom, any may be None). boosts: optional
    dict of slot-kind->offset_boost override (D92 manual sizing, see _SLOT_TO_BOOST_KEY) -- falls
    back to outfit_lib's per-kind default (D91) for any kind not given. Fits the selected assets
    onto the arms-down basemesh (outfit_lib -- same pose math the offline compose_avatar.py uses)
    and packs body+parts into one static mesh buffer:
    MAGIC 'CMP1' + uint32 V + uint32 F + V*3 float32 pos + F*3 uint32 idx + V*3 uint8 color.
    Faces (uint32) come BEFORE colors (uint8), not after -- the color block's byte length
    (V*3) isn't guaranteed to be a multiple of 4, and a client `new Uint32Array(buf, offset,
    ...)` throws a RangeError if `offset` isn't 4-byte-aligned (found live: D85). Colors go
    LAST since nothing after them needs alignment."""
    boosts = boosts or {}
    key = (tuple(sorted(sel.items())), tuple(sorted(boosts.items())))
    hit = _compose_cache.get(key)
    if hit is not None:
        return hit
    import outfit_lib as ol
    import mpfb_prefit as mp
    B, BF = ol.arms_down_basemesh()
    feet_z = float(B[:, 2].min())
    rest_verts = ol._neutral_fit_data()["rest_verts"]
    BT = ol.arms_down_bone_transforms()
    parts = [("body", B, BF)]
    for slot, aid in sel.items():
        if not aid:
            continue
        path = _catalog_paths.get(aid)
        if not path:
            continue
        boost = boosts.get(_SLOT_TO_BOOST_KEY.get(slot))   # None -> outfit_lib's per-kind default
        try:
            # D102: fit ONCE on the neutral body via mpfb_prefit.fit_rest -- the MPFB2-engine
            # prefit (subdivided + eased, real geometry/drape) when an offline export exists for
            # this asset, else our affine fit_mhclo fallback (boost applies to the fallback only).
            # Then skin to the arms-down preview pose with the skeleton (LBS, D96) -- same
            # machinery that dresses the walking body. Light push kept as a safety net.
            a = mp.fit_rest(path, slot, rest_verts, offset_boost=boost)
        except Exception as e:
            print(f"[studio] compose SKIP {aid}: {e}")
            continue
        posed = ol.skin_garment(a["verts"], a["bind_idx"], a["bind_w"], BT)
        posed, _ = ol.push_off_surface(posed, margin=0.006)
        parts.append((slot, posed, a["faces"]))

    Vtot = sum(len(v) for _, v, _ in parts)
    Ftot = sum(len(f) for _, _, f in parts)
    pos = np.empty((Vtot, 3), np.float32)
    col = np.empty((Vtot, 3), np.uint8)
    faces = np.empty((Ftot, 3), np.uint32)
    vo = fo = 0
    for slot, v, f in parts:
        n = len(v)
        pos[vo:vo + n] = v
        col[vo:vo + n] = _PART_COLOR.get(slot, (0x99, 0x99, 0x99))
        faces[fo:fo + len(f)] = f + vo
        vo += n; fo += len(f)

    # ground the composed mesh at z=0 (feet), matching the animated body's own convention
    # (server-side `_orient_yup` does the same) -- without this the raw Anny frame's feet
    # sit at z=feet_z (~-0.85), and after the client's Z-up->Y-up rotation the whole outfit
    # preview renders sunk below the floor plane (found live: D85).
    pos[:, 2] -= feet_z

    out = io.BytesIO()
    out.write(b"CMP1")
    out.write(struct.pack("<II", Vtot, Ftot))
    out.write(pos.tobytes())
    out.write(faces.tobytes())
    out.write(col.tobytes())
    buf = out.getvalue()
    _compose_cache[key] = buf
    return buf


# stem -> {mtime, blob(gzipped), meta}
_cache = {}
_lock = threading.Lock()


def _label_for(stem):
    m = {"walk": "Neutral · walk", "walk_adult": "Adult · walk", "walk_face": "Face detail · walk"}
    return m.get(stem, stem.replace("_", " "))


def _faces_path(stem):
    """Per-stem faces file if present (different topology than the shared SOMA one), else FACES."""
    per_stem = os.path.join(OUT, f"{stem}_faces.npy")
    return per_stem if os.path.exists(per_stem) else FACES


def discover_models():
    """Every *_verts.npy in OUT is a switchable subject model."""
    models = []
    try:
        for fn in sorted(os.listdir(OUT)):
            if fn.endswith("_verts.npy"):
                stem = fn[:-len("_verts.npy")]
                path = os.path.join(OUT, fn)
                try:
                    # header-only read to get shape cheaply
                    with open(path, "rb") as f:
                        ver = np.lib.format.read_magic(f)
                        shape, _, _ = np.lib.format._read_array_header(f, ver)
                    T, V = (shape + (0, 0))[:2]
                except Exception:
                    T = V = 0
                models.append({"stem": stem, "label": _label_for(stem),
                               "thumb": f"/thumb/{stem}.png", "frames": int(T), "verts": int(V)})
    except FileNotFoundError:
        pass
    return models


def _orient_yup(verts):
    """Up axis -> +Y, feet -> ground plane, and WALK IN PLACE at the origin.

    Up = axis of largest MEAN per-frame extent (a walk translates several
    body-heights, so whole-sequence argmax would pick the travel axis, not the
    vertical). The motion's forward root-translation is REMOVED per frame (each
    frame re-centered horizontally on its own body centroid) so the avatar stays
    pinned to the start marker and demonstrates the motion in place -- like a
    Blender/game-engine preview -- instead of walking off across the scene. The
    vertical bounce is kept (feet stay near the ground plane)."""
    ext = (verts.max(1) - verts.min(1)).mean(0)
    up_i = int(np.argmax(ext))
    horiz = [i for i in range(3) if i != up_i]
    v = np.empty_like(verts)
    v[..., 0] = verts[..., horiz[0]]
    v[..., 1] = verts[..., up_i]
    v[..., 2] = verts[..., horiz[1]]
    v[..., 1] -= v[..., 1].reshape(-1).min()                 # feet -> ground (global)
    # per-frame horizontal re-centering: kill root travel, keep the gait in place
    cx = 0.5 * (v[..., 0].max(1, keepdims=True) + v[..., 0].min(1, keepdims=True))
    cz = 0.5 * (v[..., 2].max(1, keepdims=True) + v[..., 2].min(1, keepdims=True))
    v[..., 0] -= cx
    v[..., 2] -= cz
    return v


def build_blob(stem):
    """(Re)pack faces+quantized-verts for `stem`; gzip. Returns (blob, meta) or (None, meta)."""
    verts_path = os.path.join(OUT, f"{stem}_verts.npy")
    faces_path = _faces_path(stem)
    if not os.path.exists(verts_path) or not os.path.exists(faces_path):
        meta = {"ready": False, "waiting_for": os.path.basename(verts_path)}
        return None, meta
    mtime = os.path.getmtime(verts_path)
    with _lock:
        c = _cache.get(stem)
        if c and c["mtime"] == mtime and c["blob"] is not None:
            return c["blob"], c["meta"]
    try:
        verts = np.load(verts_path).astype(np.float32)     # [T,V,3]
        faces = np.load(faces_path).astype(np.uint32)       # [F,3]
    except (ValueError, OSError):
        return None, {"ready": False, "waiting_for": os.path.basename(verts_path)}
    if verts.ndim != 3 or verts.shape[2] != 3:
        return None, {"ready": False, "waiting_for": os.path.basename(verts_path)}

    verts = _orient_yup(verts)
    T, V, _ = verts.shape
    F = faces.shape[0]

    # per-axis quantization to uint16, then TEMPORAL DELTA (int16) so gzip can
    # exploit the smooth motion -- absolute positions are high-entropy and barely
    # compress; frame-to-frame deltas cluster near 0 (~3.4x smaller on the wire).
    vmin = verts.reshape(-1, 3).min(0)
    vmax = verts.reshape(-1, 3).max(0)
    vrange = np.maximum(vmax - vmin, 1e-6)
    q = np.round((verts - vmin) / vrange * 65535.0).astype(np.uint16)   # [T,V,3]
    d = np.empty_like(q, dtype=np.int16)
    d[0] = q[0].astype(np.int16)
    d[1:] = (q[1:].astype(np.int32) - q[:-1].astype(np.int32)).astype(np.int16)

    # v3 header: MAGIC, ver=3, T, V, F, fps, min[3], range[3]; body = faces(u32) + delta(i16)
    hdr = MAGIC + struct.pack("<IIIIf", 3, T, V, F, float(args.fps))
    hdr += struct.pack("<3f", *vmin.tolist()) + struct.pack("<3f", *vrange.tolist())
    raw = hdr + faces.tobytes() + np.ascontiguousarray(d).tobytes()
    blob = gzip.compress(raw, compresslevel=6)

    meta = {"ready": True, "mtime": mtime, "T": int(T), "V": int(V), "F": int(F),
            "fps": float(args.fps), "raw_bytes": len(raw), "gz_bytes": len(blob),
            "stem": stem}
    with _lock:
        _cache[stem] = {"mtime": mtime, "blob": blob, "meta": meta}
    print(f"[studio] packed {stem}: T={T} V={V} F={F}  {len(raw)/1e6:.1f}MB -> "
          f"{len(blob)/1e6:.1f}MB gz  @ {time.strftime('%H:%M:%S')}")
    return blob, meta


def watcher():
    while True:
        try:
            for m in discover_models():
                build_blob(m["stem"])
        except Exception as e:
            print("[studio] pack error:", e)
        time.sleep(1.5)


def list_assets(kind):
    d = CAPTURES if kind == "capture" else os.path.join(ASSETS, kind)
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            if os.path.isfile(fp):
                out.append({"name": fn, "size": os.path.getsize(fp),
                            "url": f"/asset/{kind}/{fn}"})
    return out


def _thumb_path(stem):
    for cand in (f"{stem}_multiview.png", f"{stem}_strip.png", f"{stem}_cycle_strip.png"):
        p = os.path.join(OUT, cand)
        if os.path.exists(p):
            return p
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, "application/json", json.dumps(obj).encode())

    def _file(self, path, ctype):
        if not path or not os.path.exists(path):
            self._send(404, "text/plain", b"not ready")
            return
        with open(path, "rb") as f:
            self._send(200, ctype, f.read())

    def _qs(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        return {k: v[0] for k, v in q.items()}

    # ---- GET ----
    def do_GET(self):
        p = self.path.split("?")[0]
        qs = self._qs()
        if p in ("/", "/index.html"):
            self._file(os.path.join(HERE, "viewer.html"), "text/html; charset=utf-8")
        elif p in ("/splat", "/splat.html"):
            self._file(os.path.join(HERE, "splat.html"), "text/html; charset=utf-8")
        elif p in ("/skintest", "/skintest.html"):
            # D105: the "textured mesh instead of splats" comparison page.
            self._file(os.path.join(HERE, "skintest.html"), "text/html; charset=utf-8")
        elif p.endswith(".glb"):
            self._file(os.path.join(OUT, os.path.basename(p)), "model/gltf-binary")
        elif p == "/models.json":
            self._json({"models": discover_models(), "default": args.stem})
        elif p == "/status.json":
            stem = qs.get("stem", args.stem)
            _, meta = build_blob(stem)
            self._json(meta)
        elif p == "/data.bin":
            stem = qs.get("stem", args.stem)
            blob, _ = build_blob(stem)
            if blob is None:
                self._send(404, "text/plain", b"no data yet")
            else:
                self._send(200, "application/octet-stream", blob,
                           extra={"Content-Encoding": "gzip"})
        elif p == "/splat.bin":
            name = os.path.basename(qs.get("name", "poc_avatar"))
            fp = os.path.join(OUT, name + ".ply")
            if not os.path.exists(fp):
                self._send(404, "text/plain", b"no splat"); return
            self._send(200, "application/octet-stream", build_splat_buffer(fp))
        elif p == "/splats.json":
            self._json({"splats": discover_splats()})
        elif p == "/catalog.json":
            kind = qs.get("kind", "")
            if kind not in OUTFIT_KINDS:
                self._json({"error": "bad kind"}, 400); return
            self._json({"kind": kind, "assets": build_catalog(kind)})
        elif p.startswith("/asset_src/"):
            rest = p[len("/asset_src/"):].split("/")
            if len(rest) != 3 or rest[0] not in OUTFIT_KINDS or rest[2] != "thumb":
                self._send(404, "text/plain", b"not found"); return
            kind, name, _ = rest
            build_catalog(kind)   # ensure _catalog_paths is populated
            fp = _catalog_paths.get(("thumb", kind, name))
            self._file(fp, "image/png")
        elif p == "/compose.bin":
            sel = {"hair": qs.get("hair") or None, "eyebrows": qs.get("eyebrows") or None,
                   "top": qs.get("top") or None, "bottom": qs.get("bottom") or None}
            if not any(sel.values()):
                self._send(400, "text/plain", b"no selection"); return
            # D92: manual per-kind size override (?hair_boost=&clothing_boost=&eyebrows_boost=,
            # each a uniform x/y/z offset multiplier, see outfit_lib.fit_asset_checked's
            # offset_boost) -- omit a kind to keep D91's tuned default for it.
            boosts = {}
            for kind in ("hair", "eyebrows", "clothing"):
                v = qs.get(f"{kind}_boost")
                if v:
                    try:
                        boosts[kind] = max(0.1, min(10.0, float(v)))
                    except ValueError:
                        pass
            # make sure catalogs (and _catalog_paths) are built before resolving ids
            for k in ("hair", "eyebrows", "clothing"):
                build_catalog(k)
            try:
                buf = build_compose_buffer(sel, boosts)
            except Exception as e:
                self._send(500, "text/plain", str(e).encode()); return
            self._send(200, "application/octet-stream", buf)
        elif p == "/outfit_walk.bin":
            # D98: per-frame DRESSED-WALK buffer -- the selected garments skinned across every
            # walk frame and mapped into the viewer's exact display frame, so clothes walk with
            # the body in lockstep (no per-frame re-fit; the fit is per-selection, the skinning
            # per-frame). Needs the offline framedata (python3 dress_walk.py --stem <stem>).
            import dress_walk
            stem = qs.get("stem", args.stem)
            sel = {"hair": qs.get("hair") or None, "eyebrows": qs.get("eyebrows") or None,
                   "top": qs.get("top") or None, "bottom": qs.get("bottom") or None}
            if not any(sel.values()):
                self._send(400, "text/plain", b"no selection"); return
            boosts = {}
            for kind in ("hair", "eyebrows", "clothing"):
                v = qs.get(f"{kind}_boost")
                if v:
                    try:
                        boosts[kind] = max(0.1, min(10.0, float(v)))
                    except ValueError:
                        pass
            for k in ("hair", "eyebrows", "clothing"):
                build_catalog(k)   # populate _catalog_paths before id resolution
            # D-cloth: cloth=1 (default) serves the BAKED cloth sim (real drape + body
            # collision + top-over-bottom layering) when a bake exists for the selection,
            # else falls back to rigid LBS; cloth=0 forces the old rigid-LBS skinning.
            cloth = qs.get("cloth", "1") != "0"
            try:
                raw = dress_walk.dress_walk_buffer(stem, sel, _catalog_paths, boosts, cloth=cloth)
            except FileNotFoundError as e:
                self._send(503, "text/plain", str(e).encode()); return
            except Exception as e:
                self._send(500, "text/plain", str(e).encode()); return
            self._send(200, "application/octet-stream", gzip.compress(raw, 6),
                       extra={"Content-Encoding": "gzip"})
        elif p == "/eyemeta.json":
            stem = qs.get("stem", args.stem)
            fp = os.path.join(OUT, f"{stem}_eyemeta.json")
            if not os.path.exists(fp):
                self._json({"idx": [], "pupilW": []})   # models without eye geometry (SOMA topology)
            else:
                self._file(fp, "application/json")
        elif p.startswith("/thumb/"):
            stem = p[len("/thumb/"):]
            if stem.endswith(".png"):
                stem = stem[:-4]
            self._file(_thumb_path(stem), "image/png")
        elif p == "/assets.json":
            kind = qs.get("kind", "skin")
            if kind not in ASSET_KINDS:
                self._json({"error": "bad kind"}, 400); return
            self._json({"kind": kind, "assets": list_assets(kind)})
        elif p.startswith("/asset/"):
            parts = p[len("/asset/"):].split("/", 1)
            if len(parts) != 2 or parts[0] not in ASSET_KINDS:
                self._send(404, "text/plain", b"not found"); return
            kind, name = parts
            base = CAPTURES if kind == "capture" else os.path.join(ASSETS, kind)
            fp = os.path.normpath(os.path.join(base, name))
            if not fp.startswith(base):
                self._send(403, "text/plain", b"forbidden"); return
            ext = os.path.splitext(name)[1].lower()
            ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                     "glb": "model/gltf-binary", "ply": "application/octet-stream"}.get(ext.lstrip("."), "application/octet-stream")
            self._file(fp, ctype)
        elif p.startswith("/vendor/"):
            rel = p[len("/vendor/"):]
            fpath = os.path.normpath(os.path.join(HERE, "vendor", rel))
            if not fpath.startswith(os.path.join(HERE, "vendor")):
                self._send(403, "text/plain", b"forbidden")
            else:
                self._file(fpath, "application/javascript")
        # legacy image endpoints (kept; the new UI doesn't surface them as tabs)
        elif p.endswith(".gif"):
            self._file(os.path.join(OUT, os.path.basename(p)), "image/gif")
        elif p.endswith(".png"):
            self._file(os.path.join(OUT, os.path.basename(p)), "image/png")
        else:
            self._send(404, "text/plain", b"not found")

    # ---- POST ----
    def do_POST(self):
        p = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if p == "/log":
            try:
                msg = body.decode("utf-8", "replace")
            except Exception:
                msg = repr(body)
            print("[browser] " + msg, flush=True)
            self._json({"ok": True})
            return
        if p.startswith("/upload/"):
            kind = p[len("/upload/"):]
            if kind not in ASSET_KINDS:
                self._json({"error": "bad kind"}, 400); return
            name = os.path.basename(self.headers.get("X-Filename", "upload.bin"))
            base = CAPTURES if kind == "capture" else os.path.join(ASSETS, kind)
            os.makedirs(base, exist_ok=True)
            fp = os.path.normpath(os.path.join(base, name))
            if not fp.startswith(base):
                self._json({"error": "bad name"}, 400); return
            with open(fp, "wb") as f:
                f.write(body)
            print(f"[studio] uploaded {kind}/{name} ({len(body)} B)")
            self._json({"ok": True, "kind": kind, "name": name, "url": f"/asset/{kind}/{name}"})
        elif p == "/fit":
            # queue a gaussian-fit job: bind an uploaded capture's gaussians onto a model.
            # This is the D74 make-or-break pipeline (per-subject fit + mesh-anchor +
            # correctives). The worker that consumes fit_jobs/ is the next backend milestone;
            # here we persist the job so the UI can show the pipeline queued/running.
            try:
                job = json.loads(body or b"{}")
            except Exception:
                job = {}
            jid = f"fit_{int(os.path.getmtime(__file__))}_{len(os.listdir(JOBS))}"
            job = {"id": jid, "model": job.get("model"), "capture": job.get("capture"),
                   "status": "queued", "note": "per-subject gaussian fit (D74) — worker pending"}
            with open(os.path.join(JOBS, jid + ".json"), "w") as f:
                json.dump(job, f, indent=2)
            print(f"[studio] queued fit job {jid}: {job.get('capture')} -> {job.get('model')}")
            self._json(job)
        else:
            self._send(404, "text/plain", b"not found")


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    threading.Thread(target=watcher, daemon=True).start()
    srv = ThreadingServer((args.host, args.port), Handler)
    print(f"[studio] serving http://{args.host}:{args.port}  (out={OUT})")
    print(f"[studio] models: {[m['stem'] for m in discover_models()]}")
    srv.serve_forever()
