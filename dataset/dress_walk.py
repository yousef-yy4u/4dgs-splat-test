#!/usr/bin/env python3
"""D98 -- DRESS THE LIVE WALK. Skin fit-at-neutral garments across every walk frame and
land them in the EXACT browser display frame the animated body uses, so clothes walk with
the body in the viewer (the first dressed walking avatar), no per-frame re-fit.

Two halves, split so the HEAVY half runs once offline and the server stays light:

  1. PRECOMPUTE (offline CLI, needs soma+torch+anny) -- `precompute_framedata(stem)`:
     replicate pose_default_walk.py's SOMA->Anny retarget to get, per walk frame, the
     local-bone pose deltas P; from those the per-bone LBS transforms `bone_transforms`
     (the same matrices outfit_lib.skin_garment consumes); and the single per-frame RIGID
     transform (R_fixed, T[t]) that maps Anny's native Z-up meters into the viewer's final
     display frame. R_fixed is the constant Z-up->Y-up map baked by pose_default_walk
     (Vb=[x,z,-y]); the whole rest of the body pipeline (pelvis bounce, per-frame de-drift,
     grounding, and serve_viewer._orient_yup's re-centering) is PURE TRANSLATION, so it
     collapses into T[t]=mean_v(body_display[t] - R_fixed@body_native[t]). We derive T[t]
     from the body itself (replicated native forward(P) vs the served walk verts run through
     _orient_yup) and VERIFY the residual is ~0 -- proving the decomposition is exact and the
     garment, sharing R_fixed+T[t], registers on the body to numerical precision.
     Saved to motion_out/<stem>_framedata.npz.

  2. SERVE (in serve_viewer.py, numpy-only, no soma) -- `dress_walk_buffer(stem, sel, boosts)`:
     load the framedata npz, fit each selected garment ONCE on the neutral body
     (outfit_lib.fit_asset_lbs machinery), skin it to every frame with the cached
     bone_transforms, apply R_fixed+T[t], pack all frames into one buffer. Cached per
     selection; the fit is per-selection, the skin is a couple of numpy einsums per frame.

Run offline once per walk stem:
    python3 dress_walk.py --stem walk_face
"""
import os, sys, io, struct, math, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "motion_out")

# The Z-up (Anny native) -> Y-up (viewer) linear map pose_default_walk.py bakes:
#   Vb = [V[:,0], V[:,2], -V[:,1]]   i.e.  (x,y,z) -> (x, z, -y)
# Everything downstream of it (bounce, de-drift, ground, _orient_yup recenter) is a pure
# per-frame translation, so this constant matrix is the entire rotational part of the
# native->display transform. Verified in precompute_framedata (residual ~1e-7 m).
R_FIXED = np.array([[1., 0, 0],
                    [0, 0, 1],
                    [0, -1, 0]], dtype=np.float64)


def _orient_yup(verts):
    """EXACT copy of serve_viewer._orient_yup (kept in sync by hand -- it is the last stage
    of the body's display transform, and the garment must land in the same frame). See that
    function for the rationale."""
    ext = (verts.max(1) - verts.min(1)).mean(0)
    up_i = int(np.argmax(ext))
    horiz = [i for i in range(3) if i != up_i]
    v = np.empty_like(verts)
    v[..., 0] = verts[..., horiz[0]]
    v[..., 1] = verts[..., up_i]
    v[..., 2] = verts[..., horiz[1]]
    v[..., 1] -= v[..., 1].reshape(-1).min()
    cx = 0.5 * (v[..., 0].max(1, keepdims=True) + v[..., 0].min(1, keepdims=True))
    cz = 0.5 * (v[..., 2].max(1, keepdims=True) + v[..., 2].min(1, keepdims=True))
    v[..., 0] -= cx
    v[..., 2] -= cz
    return v


def framedata_path(stem):
    return os.path.join(OUT, f"{stem}_framedata.npz")


# ======================================================================================
# 1. PRECOMPUTE (heavy: soma + torch + anny). Run offline via the CLI.
# ======================================================================================
def precompute_framedata(stem="walk_face", npz="kimodo_out/walk.npz", verbose=True):
    import torch
    # --- soma shim (soma passes local_changes=None into anny) ---
    import anny.models.phenotype as _ph
    for _n in dir(_ph):
        _o = getattr(_ph, _n)
        if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
            def _mk(f):
                def g(self, *a, local_changes=None, **k):
                    return f(self, *a, local_changes=(local_changes or {}), **k)
                return g
            _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)
    import anny
    from soma import SOMALayer
    import outfit_lib as ol

    ADULT = ol.ADULT
    IDV11 = [0.5] * 8 + [0.34, 0.33, 0.33]
    SOMA77 = ['Hips', 'Spine1', 'Spine2', 'Chest', 'Neck1', 'Neck2', 'Head', 'HeadEnd', 'Jaw', 'LeftEye', 'RightEye',
     'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'LeftHandThumb1', 'LeftHandThumb2', 'LeftHandThumb3', 'LeftHandThumbEnd',
     'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'LeftHandIndex4', 'LeftHandIndexEnd',
     'LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3', 'LeftHandMiddle4', 'LeftHandMiddleEnd',
     'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'LeftHandRing4', 'LeftHandRingEnd',
     'LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3', 'LeftHandPinky4', 'LeftHandPinkyEnd',
     'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'RightHandThumb1', 'RightHandThumb2', 'RightHandThumb3', 'RightHandThumbEnd',
     'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'RightHandIndex4', 'RightHandIndexEnd',
     'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'RightHandMiddle4', 'RightHandMiddleEnd',
     'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'RightHandRing4', 'RightHandRingEnd',
     'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'RightHandPinky4', 'RightHandPinkyEnd',
     'LeftLeg', 'LeftShin', 'LeftFoot', 'LeftToeBase', 'LeftToeEnd', 'RightLeg', 'RightShin', 'RightFoot', 'RightToeBase', 'RightToeEnd']
    S = {n: i for i, n in enumerate(SOMA77)}
    MAP = {'Hips': 'root', 'Spine1': 'spine05', 'Spine2': 'spine03', 'Chest': 'spine01', 'Neck1': 'neck01', 'Neck2': 'neck02',
     'Head': 'head', 'Jaw': 'jaw', 'LeftEye': 'eye.L', 'RightEye': 'eye.R', 'LeftShoulder': 'clavicle.L', 'LeftArm': 'upperarm01.L',
     'LeftForeArm': 'lowerarm01.L', 'LeftHand': 'wrist.L', 'RightShoulder': 'clavicle.R', 'RightArm': 'upperarm01.R',
     'RightForeArm': 'lowerarm01.R', 'RightHand': 'wrist.R', 'LeftLeg': 'upperleg01.L', 'LeftShin': 'lowerleg01.L',
     'LeftFoot': 'foot.L', 'LeftToeBase': 'toe3-1.L', 'RightLeg': 'upperleg01.R', 'RightShin': 'lowerleg01.R',
     'RightFoot': 'foot.R', 'RightToeBase': 'toe3-1.R'}
    FINGER_MAP = {
     'LeftHandThumb1': 'finger1-1.L', 'LeftHandThumb2': 'finger1-2.L', 'LeftHandThumb3': 'finger1-3.L',
     'LeftHandIndex1': 'finger2-1.L', 'LeftHandIndex2': 'finger2-2.L', 'LeftHandIndex3': 'finger2-3.L',
     'LeftHandMiddle1': 'finger3-1.L', 'LeftHandMiddle2': 'finger3-2.L', 'LeftHandMiddle3': 'finger3-3.L',
     'LeftHandRing1': 'finger4-1.L', 'LeftHandRing2': 'finger4-2.L', 'LeftHandRing3': 'finger4-3.L',
     'LeftHandPinky1': 'finger5-1.L', 'LeftHandPinky2': 'finger5-2.L', 'LeftHandPinky3': 'finger5-3.L',
     'RightHandThumb1': 'finger1-1.R', 'RightHandThumb2': 'finger1-2.R', 'RightHandThumb3': 'finger1-3.R',
     'RightHandIndex1': 'finger2-1.R', 'RightHandIndex2': 'finger2-2.R', 'RightHandIndex3': 'finger2-3.R',
     'RightHandMiddle1': 'finger3-1.R', 'RightHandMiddle2': 'finger3-2.R', 'RightHandMiddle3': 'finger3-3.R',
     'RightHandRing1': 'finger4-1.R', 'RightHandRing2': 'finger4-2.R', 'RightHandRing3': 'finger4-3.R',
     'RightHandPinky1': 'finger5-1.R', 'RightHandPinky2': 'finger5-2.R', 'RightHandPinky3': 'finger5-3.R'}
    MAP.update(FINGER_MAP)   # match pose_default_walk.py's default (fingers on)

    # ----- Anny default mesh + rig (the DISPLAY topology the served body uses) -----
    m = anny.Anny()
    BL = m.bone_labels
    PARENT = list(m.bone_parents)
    bsc = m.get_phenotype_blendshape_coefficients(**ADULT, local_changes={})
    Rr = m.get_rest_model(bsc)["rest_bone_poses"][0, :, :3, :3].double()
    NB = len(BL)
    bone2soma = {BL.index(b): S[s] for s, b in MAP.items() if b in BL and s in S}

    def nearest(b):
        while b >= 0:
            if b in bone2soma:
                return bone2soma[b]
            b = PARENT[b]
        return None
    anc = [nearest(b) for b in range(NB)]

    layer = SOMALayer(identity_model_type="anny", device="cpu"); layer.eval()
    d = np.load(os.path.join(HERE, npz))
    local = torch.from_numpy(d["local_rot_mats"].astype(np.float32))   # (T,77,3,3)
    T = local.shape[0]
    ident = torch.tensor([IDV11], dtype=torch.float32)
    cap = {}; bs = layer.batched_skinning; _orig = bs.pose

    def _cap(*a, **k):
        k = dict(k); k["return_transforms"] = True
        out = _orig(*a, **k); cap["T"] = out[1].detach().double().numpy(); return out
    bs.pose = _cap
    with torch.no_grad():
        layer(local[0].unsqueeze(0), ident, transl=torch.zeros(1, 3), pose2rot=False, absolute_pose=False)
    bind = layer._cached_bind_transforms_world[0].double().numpy()
    Rbind = bind[:, :3, :3]
    Msoma = np.array([[1., 0, 0], [0, 0, -1], [0, 1, 0]]); I3 = np.eye(3)

    # frame selection MUST match pose_default_walk.py (linspace over the whole clip). The
    # served walk_face_verts.npy has F frames; use that F so frame indices line up 1:1.
    served = np.load(os.path.join(OUT, f"{stem}_verts.npy")).astype(np.float64)   # (F,V,3), pre-_orient_yup
    F = served.shape[0]
    sel = np.linspace(0, T - 1, F).astype(int)
    body_display = _orient_yup(served)    # the exact browser frame (matches serve_viewer)

    bone_transforms = np.empty((F, NB, 4, 4), np.float64)
    Tvec = np.empty((F, 3), np.float64)
    resid_max = 0.0
    for k, t in enumerate(sel):
        with torch.no_grad():
            layer.pose(local[t].unsqueeze(0), transl=torch.zeros(1, 3), pose2rot=False, absolute_pose=False)
        Tw = cap["T"][0]
        dR = {j: Msoma @ (Tw[j + 1, :3, :3] @ Rbind[j + 1].T) @ Msoma.T
              for j in set(v for v in anc if v is not None)}
        D = [dR[anc[b]] if anc[b] is not None else I3 for b in range(NB)]
        # self-collision fix (D-selfcollision): IDENTICAL arm abduction to pose_default_walk.py --
        # the displayed body (walk_face_verts.npy) is exported with it, so the garment
        # bone_transforms must carry the same arm pose or the clothes drift off the arms and the
        # rigid native->display residual blows up. Same default (outfit_lib.ARM_ABDUCT_DEG).
        D = ol.apply_arm_abduction(D, BL, PARENT)
        P = torch.eye(4, dtype=torch.float64).repeat(NB, 1, 1)
        for b in range(NB):
            Dp = D[PARENT[b]] if PARENT[b] >= 0 else I3
            Rrb = Rr[b].numpy()
            P[b, :3, :3] = torch.from_numpy(Rrb.T @ Dp.T @ D[b] @ Rrb)
        # native (Z-up) body for this frame -- same call pose_default_walk.py makes
        with torch.no_grad():
            body_native = m.forward(pose_parameters=P.unsqueeze(0), phenotype_kwargs=ADULT,
                                     pose_parameterization="local-bone")["vertices"][0].double().numpy()
        # the per-bone LBS transforms the garment will be skinned with
        bt = ol.bone_transforms_for_pose(P)
        bone_transforms[k] = bt
        # solve the per-frame translation of the rigid native->display map (R_FIXED known)
        mapped = (R_FIXED @ body_native.T).T
        Tvec[k] = (body_display[k] - mapped).mean(0)
        resid = np.abs((mapped + Tvec[k]) - body_display[k]).max()
        resid_max = max(resid_max, resid)
        if verbose and (k % 25 == 0 or k == F - 1):
            print(f"  frame {k:3d}/{F}  rigid-residual {resid*1000:.4f} mm")

    outp = framedata_path(stem)
    np.savez_compressed(outp,
                        bone_transforms=bone_transforms.astype(np.float32),
                        R_fixed=R_FIXED.astype(np.float32),
                        Tvec=Tvec.astype(np.float32),
                        F=np.int64(F))
    print(f"[dress_walk] wrote {outp}  F={F} NB={NB}  max native->display residual "
          f"{resid_max*1000:.4f} mm  ({os.path.getsize(outp)/1e6:.2f} MB)")
    return outp


# ======================================================================================
# 2. SERVE (numpy-only). Imported by serve_viewer.py.
# ======================================================================================
_framedata_cache = {}   # stem -> dict(bone_transforms, R_fixed, Tvec, F)
_dressed_cache = {}     # (stem, sel-key, boost-key) -> packed bytes


def load_framedata(stem):
    hit = _framedata_cache.get(stem)
    fp = framedata_path(stem)
    if not os.path.exists(fp):
        return None
    mt = os.path.getmtime(fp)
    if hit and hit["mtime"] == mt:
        return hit
    z = np.load(fp)
    fd = {"mtime": mt,
          "bone_transforms": z["bone_transforms"].astype(np.float64),
          "R_fixed": z["R_fixed"].astype(np.float64),
          "Tvec": z["Tvec"].astype(np.float64),
          "F": int(z["F"])}
    _framedata_cache[stem] = fd
    return fd


# flat vertex color per garment slot -- mirrors serve_viewer._PART_COLOR (kept in sync).
_SLOT_COLOR = {"hair": (0x3a, 0x24, 0x18), "eyebrows": (0x1a, 0x0f, 0x0c),
               "top": (0x38, 0x4d, 0x6b), "bottom": (0x26, 0x28, 0x33)}

# per-slot NEUTRAL surface-push margin (meters), D98/Task-2. Garments are fit at the neutral
# T-pose then skinned; pushing the REST garment off the REST body ONCE (before skinning) clears
# the pose-INDEPENDENT affine-approximation floor (the ~6-8% of verts that sit a few mm inside
# even at neutral -> opaque z-fighting -> the skin-through "horrible pants" patches the user saw)
# for the cost of a single proximity pass, and LBS carries the clearance through the walk. A
# per-FRAME push would also catch the small pose-dependent fold residual (~1%) but costs ~150x
# more (a couple minutes vs 0.5s) -- not worth it for a live endpoint. Clothing needs a real
# gap (loose garments read as draped, not shrink-wrapped); hair/eyebrows sit tight to the scalp.
_SLOT_PUSH = {"top": 0.012, "bottom": 0.012, "hair": 0.004, "eyebrows": 0.003}


def _neutral_rest_trimesh():
    """The NEUTRAL (raw T-pose) fit-topology body (19158 v) as a trimesh, for pushing the
    rest garment off the rest body before skinning. Cached. This is the exact surface the
    garment's .mhclo binding was fit against, so clearance measured here is the clearance the
    binding actually needs."""
    import trimesh
    import outfit_lib as ol
    key = "_rest_tm"
    hit = _framedata_cache.get(key)
    if hit is not None:
        return hit
    d = ol._neutral_fit_data()
    tm = trimesh.Trimesh(vertices=d["rest_verts"], faces=np.asarray(d["model"].get_triangular_faces()),
                         process=False)
    _framedata_cache[key] = tm
    return tm


def _push_rest(rest_g, margin, iters=6):
    """Push rest-garment verts to >= `margin` clearance off the neutral rest body surface
    (same algorithm as outfit_lib.push_off_surface, but against the T-pose fit body rather
    than the arms-down display body)."""
    import trimesh
    if not margin:
        return rest_g
    tm = _neutral_rest_trimesh()
    fn = tm.face_normals
    out = rest_g.copy()
    for _ in range(iters):
        cp, _dist, tid = trimesh.proximity.closest_point(tm, out)
        signed = np.einsum('ij,ij->i', out - cp, fn[tid])
        need = signed < margin
        if not need.any():
            break
        out[need] = cp[need] + margin * fn[tid][need]
    return out


_SLOT_TO_BOOST_KEY = {"hair": "hair", "eyebrows": "eyebrows", "top": "clothing", "bottom": "clothing"}


def _fit_selection(sel, catalog_paths, boosts, rest_verts):
    """Fit each selected garment ONCE on the neutral body. Returns a list of
    (slot, rest_g, faces_g, Wg): rest garment verts (Ng,3), pruned faces, and the inherited
    (Ng,NB) LBS weight matrix -- everything pose-independent. Shared by the rigid-LBS buffer
    and the cloth bake so both start from bit-identical fitted garments."""
    import outfit_lib as ol
    import mpfb_prefit as mp
    fitted = []
    for slot, aid in sel.items():
        if not aid:
            continue
        path = catalog_paths.get(aid)
        if not path:
            continue
        boost = boosts.get(_SLOT_TO_BOOST_KEY.get(slot))   # None -> outfit_lib per-kind default
        # D102: route the neutral fit through mpfb_prefit.fit_rest -- MPFB2-engine prefit
        # (subdivided + eased, real geometry to drape) when an offline export exists for this
        # asset, else our affine fit_mhclo fallback (boost still applies to the fallback only).
        try:
            a = mp.fit_rest(path, slot, rest_verts, offset_boost=boost)
        except Exception as e:
            print(f"[dress_walk] skip {aid}: {e}"); continue
        # prune stray long-edge triangles ONCE on the neutral fit (stable face set across frames)
        # and clear the pose-independent interior floor at neutral (see _SLOT_PUSH); slice the
        # binding rows by the SAME kept mask so the inherited LBS weights stay aligned.
        kept, faces_g = _prune_edges(a["verts"], a["faces"])
        rest_g = a["verts"][kept]
        rest_g = _push_rest(rest_g, _SLOT_PUSH.get(slot, 0.004))
        Wg = ol._garment_bone_weights(a["bind_idx"][kept], a["bind_w"][kept])   # (Ng,NB) LBS weights
        fitted.append((slot, rest_g, faces_g, Wg))
    return fitted


def _skin_display(rest_g, Wg, BT, Rf, Tv):
    """LBS-skin one rest garment to every frame and map into the viewer display frame.
    Returns (F,Ng,3) float64."""
    F = BT.shape[0]
    homog = np.concatenate([rest_g, np.ones((len(rest_g), 1))], axis=1)   # (Ng,4)
    out = np.empty((F, len(rest_g), 3), np.float64)
    for t in range(F):
        Tp = np.einsum('bij,nj->bni', BT[t], homog)               # (NB,Ng,4)
        native = np.einsum('nb,bni->ni', Wg, Tp[..., :3])         # (Ng,3) Anny Z-up
        out[t] = (Rf @ native.T).T + Tv[t]                        # -> display frame
    return out


def _pack_owk(faces_all, verts_all, col):
    """Pack faces/verts/colors into the OWK1 buffer (verts already in display frame)."""
    F, V, _ = verts_all.shape
    Ftri = len(faces_all)
    out = io.BytesIO()
    out.write(b"OWK1")
    out.write(struct.pack("<III", F, V, Ftri))
    out.write(np.ascontiguousarray(faces_all, np.uint32).tobytes())
    out.write(np.ascontiguousarray(verts_all, np.float32).tobytes())
    out.write(np.ascontiguousarray(col, np.uint8).tobytes())
    return out.getvalue()


def dress_walk_buffer(stem, sel, catalog_paths, boosts=None, cloth=True):
    """Build the per-frame dressed-garment buffer for the current selection.

    sel: dict slot->asset-id (hair/eyebrows/top/bottom, any None). catalog_paths: the
    server's {asset-id -> mhclo path} map. boosts: slot-kind->offset_boost override.
    cloth: if True (default) and a baked-cloth cache exists on disk for this exact selection,
    serve the BAKED CLOTH (real drape + body collision + top-over-bottom layering, D-cloth);
    otherwise fall back to the rigid-LBS skinning (garments track the skeleton, no drape).

    Returns gzip-able bytes:
      MAGIC 'OWK1' | u32 F | u32 V | u32 Ftri | faces(u32 Ftri*3) | verts(f32 F*V*3) |
      colors(u8 V*3, last).
    Faces before verts before colors so both typed-array views stay 4-byte aligned (the
    color block's V*3 length isn't guaranteed a multiple of 4 -- same rule as compose.bin).
    Verts are already in the viewer's display frame (R_fixed + T[t] applied) so the client
    drops the mesh straight into the scene with no group rotation/offset.
    """
    import outfit_lib as ol
    boosts = boosts or {}
    fd = load_framedata(stem)
    if fd is None:
        raise FileNotFoundError(f"no framedata for stem '{stem}' -- run: python3 dress_walk.py --stem {stem}")

    key = (stem, tuple(sorted(sel.items())), tuple(sorted(boosts.items())), bool(cloth))
    hit = _dressed_cache.get(key)
    if hit is not None:
        return hit

    # --- baked cloth path: only clothing (top/bottom) is simulated; hair/eyebrows stay LBS
    # and are appended. If a bake for the clothing selection exists on disk, use it. ---
    if cloth:
        baked = _load_cloth_bake(stem, sel, boosts)
        if baked is not None:
            buf = _compose_cloth_buffer(stem, sel, catalog_paths, boosts, baked, fd)
            _dressed_cache[key] = buf
            return buf

    F = fd["F"]; BT = fd["bone_transforms"]; Rf = fd["R_fixed"]; Tv = fd["Tvec"]
    rest_verts = ol._neutral_fit_data()["rest_verts"]
    fitted = _fit_selection(sel, catalog_paths, boosts, rest_verts)

    if not fitted:
        raise ValueError("no garments fitted for selection")

    # concat parts into one mesh (shared vertex buffer); precompute homogeneous rest verts.
    Ng_list = [len(rg) for _, rg, _, _ in fitted]
    V = sum(Ng_list)
    Ftri = sum(len(f) for _, _, f, _ in fitted)
    rest_all = np.empty((V, 3), np.float64)
    W_all = np.zeros((V, BT.shape[1]), np.float64)
    faces_all = np.empty((Ftri, 3), np.uint32)
    col = np.empty((V, 3), np.uint8)
    vo = fo = 0
    for slot, rg, fg, Wg in fitted:
        n = len(rg)
        rest_all[vo:vo + n] = rg
        W_all[vo:vo + n] = Wg
        faces_all[fo:fo + len(fg)] = fg + vo
        col[vo:vo + n] = _SLOT_COLOR.get(slot, (0x99, 0x99, 0x99))
        vo += n; fo += len(fg)

    homog = np.concatenate([rest_all, np.ones((V, 1))], axis=1)   # (V,4)
    verts_all = np.empty((F, V, 3), np.float32)
    for t in range(F):
        Tp = np.einsum('bij,nj->bni', BT[t], homog)               # (NB,V,4)
        native = np.einsum('nb,bni->ni', W_all, Tp[..., :3])      # (V,3) Anny Z-up
        disp = (Rf @ native.T).T + Tv[t]                          # -> viewer display frame
        verts_all[t] = disp.astype(np.float32)

    buf = _pack_owk(faces_all, verts_all, col)
    _dressed_cache[key] = buf
    return buf


def _prune_edges(verts, faces, abs_floor=0.15, rel_mult=5.0):
    """Mirror outfit_lib.drop_edge_outliers but return (kept_vertex_indices, remapped_faces)
    so the caller can slice the .mhclo binding rows by the same mask. Same threshold rule."""
    e0 = np.linalg.norm(verts[faces[:, 0]] - verts[faces[:, 1]], axis=1)
    e1 = np.linalg.norm(verts[faces[:, 1]] - verts[faces[:, 2]], axis=1)
    e2 = np.linalg.norm(verts[faces[:, 2]] - verts[faces[:, 0]], axis=1)
    maxedge = np.maximum(np.maximum(e0, e1), e2)
    thr = max(abs_floor, rel_mult * float(np.median(maxedge)))
    keep_face = maxedge <= thr
    kept = np.unique(faces[keep_face])
    remap = -np.ones(len(verts), np.int64)
    remap[kept] = np.arange(len(kept))
    return kept, remap[faces[keep_face]].astype(np.uint32)


# ======================================================================================
# 3. BAKED CLOTH (D-cloth): XPBD position-based-dynamics garment sim replacing rigid LBS.
# --------------------------------------------------------------------------------------
# The rigid-LBS garments (section 2) shrink-wrap the body: every garment vertex is glued to
# the skeleton, so clothes never drape, never fold, never collide, and have no layer order.
# This bakes a real (numpy-only) cloth simulation OFFLINE into a per-selection cache that the
# EXISTING /outfit_walk.bin path serves (same OWK1 wire format), with a fast LBS fallback for
# any selection that has no bake.
#
# Model: garment mesh = particles; edge STRETCH constraints + adjacent-triangle BEND
# constraints (PBD projection); gravity; ~10 substeps/frame. A soft "follow" pull toward the
# LBS-skinned target keeps the garment tracking the moving limbs (no lag/tunnelling) while a
# waistband(bottoms)/collar(tops) ANCHOR band is hard-pinned so garments don't fall off; the
# free cloth between anchor and body-contact drapes under gravity. COLLISION: the animated body
# is a moving collider each frame (nearest body vertex + its normal -> a local half-space each
# particle must stay a few mm outside); the body's motion pushes the cloth (drives drape).
# LAYERING: bottoms simulate first against the body; tops then simulate against body + the
# baked bottoms (so the shirt sits OUTSIDE the pants). Self-collision (folds vs folds) is
# skipped in v1. Deterministic (no RNG); pre-rolls a couple of walk cycles so cloth settles
# before recording the F-frame loop.
# ======================================================================================
_CLOTH_DEFAULTS = dict(
    fps=30.0, substeps=10, iters=2, gravity=9.8, damp=0.96,
    stretch_k=1.0, bend_k=0.5, follow_k=0.075, preroll_cycles=2, settle_frames=25,
    clearance_bottom=0.008, clearance_top=0.014, layer_gap=0.010, max_step=0.03,
)
_body_collider_cache = {}   # stem -> (Bd, Bn, KD)


def _perframe_vertex_normals(V, faces):
    """Area-weighted per-vertex normals for a moving mesh V (F,N,3), faces (Ftri,3)."""
    F, N, _ = V.shape
    out = np.zeros((F, N, 3), np.float64)
    for t in range(F):
        v = V[t]
        fn = np.cross(v[faces[:, 1]] - v[faces[:, 0]], v[faces[:, 2]] - v[faces[:, 0]])
        for k in range(3):
            np.add.at(out[t], faces[:, k], fn)
    out /= np.clip(np.linalg.norm(out, axis=2, keepdims=True), 1e-9, None)
    return out


def _body_collider(stem):
    """Body display verts + per-frame vertex normals + per-frame KDTree, cached per stem.
    The body in the SAME display frame the garment lands in (=_orient_yup of the served walk)."""
    hit = _body_collider_cache.get(stem)
    if hit is not None:
        return hit
    from scipy.spatial import cKDTree
    verts = np.load(os.path.join(OUT, f"{stem}_verts.npy")).astype(np.float64)   # (F,Nbv,3)
    faces = np.load(os.path.join(OUT, f"{stem}_faces.npy")).astype(np.int64)
    Bd = _orient_yup(verts)                                                        # display frame
    Bn = _perframe_vertex_normals(Bd, faces)
    KD = [cKDTree(Bd[t]) for t in range(Bd.shape[0])]
    _body_collider_cache[stem] = (Bd, Bn, KD)
    return Bd, Bn, KD


def _build_edges(faces):
    """Unique undirected edges of a triangle mesh."""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=0)
    e = np.sort(e, axis=1)
    return np.unique(e, axis=0)


def _build_bend(faces):
    """Adjacent-triangle opposite-vertex pairs (a simple, stable distance-bend constraint)."""
    from collections import defaultdict
    edge2third = defaultdict(list)
    for tri in faces:
        for a, b, c in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            key = tuple(sorted((int(tri[a]), int(tri[b]))))
            edge2third[key].append(int(tri[c]))
    pairs = [(v[0], v[1]) for v in edge2third.values() if len(v) == 2]
    return np.array(pairs, np.int64) if pairs else np.zeros((0, 2), np.int64)


def _anchor_band(S0, slot):
    """Per-vertex anchor weight in [0,1] from the neutral display garment. Both bottoms
    (waistband) and tops (collar/shoulders) are pinned along the TOP display-Y band so the
    garment hangs from there; everything below is free to drape (soft-followed to the body)."""
    y = S0[:, 1]
    yy = (y - y.min()) / max(y.max() - y.min(), 1e-6)
    lo, hi = (0.78, 0.92) if slot == "bottom" else (0.72, 0.88)
    return np.clip((yy - lo) / (hi - lo), 0.0, 1.0)


def _simulate_cloth(S, faces, anchor_w, Bd, Bn, KD, clearance, extra=None, P=_CLOTH_DEFAULTS):
    """XPBD/PBD cloth. S (F,Ng,3) LBS target (also the follow + anchor reference); returns the
    recorded per-frame particle positions (F,Ng,3) in the display frame. `extra`, if given, is
    (Vbot, Nbot, KDbot) for an already-baked underlying layer the cloth must also stay outside
    (top-over-bottom). Deterministic; pre-rolls P['preroll_cycles'] walk cycles before recording."""
    F, Ng, _ = S.shape
    edges = _build_edges(faces)
    E0 = np.linalg.norm(S[0][edges[:, 0]] - S[0][edges[:, 1]], axis=1)
    bend = _build_bend(faces)
    B0 = np.linalg.norm(S[0][bend[:, 0]] - S[0][bend[:, 1]], axis=1) if len(bend) else None
    w = (1.0 - anchor_w)                       # inverse mass: pinned band ~0, free ~1
    aw = anchor_w[:, None]
    dt = 1.0 / P["fps"]; sdt = dt / P["substeps"]; g = P["gravity"]
    fk = P["follow_k"]; maxs = P["max_step"]
    # Jacobi PBD: accumulate every constraint's correction for a vertex, then divide by the
    # number of constraints touching it (valence). Summing without this over-corrects
    # high-valence verts and the mesh explodes -- the bug the first bake hit.
    e0, e1 = edges[:, 0], edges[:, 1]
    ecnt = np.zeros(Ng); np.add.at(ecnt, e0, 1.0); np.add.at(ecnt, e1, 1.0)
    ecnt = np.clip(ecnt, 1.0, None)[:, None]
    ewi = w[e0][:, None]; ewj = w[e1][:, None]; edenom = np.clip(ewi + ewj, 1e-9, None)
    if len(bend):
        b0, b1 = bend[:, 0], bend[:, 1]
        bcnt = np.zeros(Ng); np.add.at(bcnt, b0, 1.0); np.add.at(bcnt, b1, 1.0)
        bcnt = np.clip(bcnt, 1.0, None)[:, None]
        bwi = w[b0][:, None]; bwj = w[b1][:, None]; bdenom = np.clip(bwi + bwj, 1e-9, None)

    def solve_stretch(x):
        d = x[e0] - x[e1]
        L = np.linalg.norm(d, axis=1)[:, None]
        n = d / np.clip(L, 1e-9, None)
        C = (L - E0[:, None]) * n * P["stretch_k"]
        dx = np.zeros_like(x)
        np.add.at(dx, e0, -C * ewi / edenom)
        np.add.at(dx, e1,  C * ewj / edenom)
        x += dx / ecnt                          # Jacobi average by valence

    def solve_bend(x):
        if not len(bend):
            return
        d = x[b0] - x[b1]
        L = np.linalg.norm(d, axis=1)[:, None]
        n = d / np.clip(L, 1e-9, None)
        C = (L - B0[:, None]) * n * P["bend_k"]
        dx = np.zeros_like(x)
        np.add.at(dx, b0, -C * bwi / bdenom)
        np.add.at(dx, b1,  C * bwj / bdenom)
        x += dx / bcnt

    def collide(x, t):
        dist, idx = KD[t].query(x)
        bp = Bd[t][idx]; bn = Bn[t][idx]
        signed = np.einsum('ij,ij->i', x - bp, bn)
        bad = signed < clearance
        if bad.any():
            x[bad] += (clearance - signed[bad])[:, None] * bn[bad]
        if extra is not None:
            Vb, Nb, KDb = extra
            db, ib = KDb[t].query(x)
            near = db < 0.07
            sp = np.einsum('ij,ij->i', x - Vb[t][ib], Nb[t][ib])
            bad2 = near & (sp < P["layer_gap"])
            if bad2.any():
                x[bad2] += (P["layer_gap"] - sp[bad2])[:, None] * Nb[t][ib][bad2]

    state = {"x": S[0].copy(), "v": np.zeros_like(S[0]), "Sprev": S[0]}

    def do_frame(t):
        x = state["x"]; v = state["v"]; Sprev = state["Sprev"]
        for sub in range(P["substeps"]):
            frac = (sub + 1) / P["substeps"]
            target = Sprev * (1 - frac) + S[t] * frac
            v[:, 1] -= g * sdt * (w > 0)          # gravity on free verts only
            v *= P["damp"]
            xprev = x.copy()
            x = x + v * sdt
            x += fk * (target - x) * w[:, None]   # soft-follow the skinned body target
            for _ in range(P["iters"]):
                solve_stretch(x)
                solve_bend(x)
                x = aw * target + (1 - aw) * x    # hard-pin the anchor band
            collide(x, t)
            step = x - xprev
            np.clip(step, -maxs, maxs, out=step)  # stability: clamp per-substep displacement
            x = xprev + step
            v = step / sdt
        state["x"] = x; state["v"] = v; state["Sprev"] = S[t]

    # PRE-ROLL a couple of walk cycles so the drape settles. NB: this walk clip is NOT cyclic
    # (the 149->0 loop seam jumps ~155 mm/vert -- the body itself hitches there), so each cycle
    # jolts the cloth at the seam. We therefore do NOT carry that momentum into the record pass:
    # after pre-roll we ZERO the velocity and settle a few frames on the frame-0 pose, then record
    # 0..F-1 in order. The recorded sequence is then internally continuous and frame-0 is clean;
    # the only discontinuity left is the loop wrap itself, which the body already has.
    for _cyc in range(P["preroll_cycles"]):
        for t in range(F):
            do_frame(t)
    state["v"][:] = 0.0; state["Sprev"] = S[0]
    for _ in range(P.get("settle_frames", 20)):
        do_frame(0)
    state["v"][:] = 0.0; state["Sprev"] = S[0]
    rec = []
    for t in range(F):
        do_frame(t)
        rec.append(state["x"].copy())
    return np.asarray(rec)


def _cloth_bake_path(stem, sel, boosts):
    import hashlib
    cs = {k: sel.get(k) for k in ("top", "bottom")}
    key = json.dumps([stem, sorted(cs.items()), sorted((boosts or {}).items())], sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:12]
    return os.path.join(OUT, f"{stem}_cloth_{h}.npz")


def _load_cloth_bake(stem, sel, boosts):
    """Return the baked-cloth npz for this clothing selection, or None (-> LBS fallback).
    Keyed only on top/bottom (+boosts); hair/eyebrows never simulate."""
    if not (sel.get("top") or sel.get("bottom")):
        return None
    fp = _cloth_bake_path(stem, sel, boosts)
    if not os.path.exists(fp):
        return None
    z = np.load(fp, allow_pickle=True)
    return {"slots": list(z["slots"]),
            "verts": {s: z[f"verts_{s}"] for s in z["slots"]},
            "faces": {s: z[f"faces_{s}"] for s in z["slots"]}}


def bake_cloth(stem, sel, catalog_paths, boosts=None, verbose=True):
    """Run the XPBD cloth sim for the clothing (top/bottom) in `sel` and cache it to disk.
    Bottoms simulate first (collide vs body); tops second (collide vs body + baked bottoms)."""
    import time as _time
    boosts = boosts or {}
    fd = load_framedata(stem)
    if fd is None:
        raise FileNotFoundError(f"no framedata for stem '{stem}' -- run: python3 dress_walk.py --stem {stem}")
    import outfit_lib as ol
    F = fd["F"]; BT = fd["bone_transforms"]; Rf = fd["R_fixed"]; Tv = fd["Tvec"]
    rest_verts = ol._neutral_fit_data()["rest_verts"]
    cloth_sel = {k: sel.get(k) for k in ("bottom", "top")}   # order: bottom first (layering)
    fitted = _fit_selection(cloth_sel, catalog_paths, boosts, rest_verts)
    order = {"bottom": 0, "top": 1}
    fitted.sort(key=lambda x: order.get(x[0], 9))
    if not fitted:
        raise ValueError("no clothing to bake (need top and/or bottom)")

    Bd, Bn, KD = _body_collider(stem)
    t0 = _time.time()
    baked = {}
    extra = None
    for slot, rest_g, faces_g, Wg in fitted:
        S = _skin_display(rest_g, Wg, BT, Rf, Tv)
        anchor_w = _anchor_band(S[0], slot)
        clearance = _CLOTH_DEFAULTS["clearance_bottom" if slot == "bottom" else "clearance_top"]
        ts = _time.time()
        X = _simulate_cloth(S, faces_g, anchor_w, Bd, Bn, KD, clearance, extra)
        baked[slot] = (X.astype(np.float32), faces_g.astype(np.uint32))
        if verbose:
            print(f"[cloth] {slot}: {len(rest_g)}v {len(faces_g)}tri  baked {X.shape[0]}f "
                  f"in {_time.time()-ts:.1f}s")
        if slot == "bottom":
            from scipy.spatial import cKDTree
            Nbot = _perframe_vertex_normals(X.astype(np.float64), faces_g)
            extra = (X.astype(np.float64), Nbot, [cKDTree(X[t]) for t in range(F)])

    fp = _cloth_bake_path(stem, cloth_sel, boosts)
    save = {"slots": np.array(list(baked.keys()))}
    for s, (X, fg) in baked.items():
        save[f"verts_{s}"] = X
        save[f"faces_{s}"] = fg
    np.savez_compressed(fp, **save)
    if verbose:
        print(f"[cloth] wrote {fp}  ({os.path.getsize(fp)/1e6:.2f} MB)  total {_time.time()-t0:.1f}s")
    return fp


def _compose_cloth_buffer(stem, sel, catalog_paths, boosts, baked, fd):
    """Pack a baked-cloth selection into the OWK1 buffer. The baked top/bottom verts are used
    as-is; any hair/eyebrows in the selection are LBS-skinned (they don't simulate) and appended
    so the dressed-walk mesh still carries them."""
    slots = baked["slots"]
    parts = []   # (slot, verts(F,Ng,3), faces(Ftri,3))
    for s in ("bottom", "top"):
        if s in slots:
            parts.append((s, baked["verts"][s].astype(np.float64), baked["faces"][s].astype(np.int64)))
    # hair/eyebrows via LBS (unchanged)
    extra_sel = {k: sel.get(k) for k in ("hair", "eyebrows") if sel.get(k)}
    if extra_sel:
        BT = fd["bone_transforms"]; Rf = fd["R_fixed"]; Tv = fd["Tvec"]
        import outfit_lib as ol
        rest_verts = ol._neutral_fit_data()["rest_verts"]
        for slot, rest_g, faces_g, Wg in _fit_selection(extra_sel, catalog_paths, boosts, rest_verts):
            parts.append((slot, _skin_display(rest_g, Wg, BT, Rf, Tv), faces_g.astype(np.int64)))

    F = fd["F"]
    V = sum(p[1].shape[1] for p in parts)
    Ftri = sum(len(p[2]) for p in parts)
    verts_all = np.empty((F, V, 3), np.float32)
    faces_all = np.empty((Ftri, 3), np.uint32)
    col = np.empty((V, 3), np.uint8)
    vo = fo = 0
    for slot, X, fg in parts:
        n = X.shape[1]
        verts_all[:, vo:vo + n] = X.astype(np.float32)
        faces_all[fo:fo + len(fg)] = fg + vo
        col[vo:vo + n] = _SLOT_COLOR.get(slot, (0x99, 0x99, 0x99))
        vo += n; fo += len(fg)
    return _pack_owk(faces_all, verts_all, col)


if __name__ == "__main__":
    import argparse
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("ANNY_CACHE_DIR", os.path.expanduser("~/.cache/anny"))
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", default="walk_face")
    ap.add_argument("--npz", default="kimodo_out/walk.npz")
    ap.add_argument("--bake-cloth", action="store_true",
                     help="bake the XPBD cloth sim for --top/--bottom instead of the framedata")
    ap.add_argument("--top", default=None, help="top asset id, e.g. top:elvs_crude_t-shirt_male")
    ap.add_argument("--bottom", default=None, help="bottom asset id, e.g. bottom:cortu_jeans_shorts")
    args = ap.parse_args()
    if args.bake_cloth:
        # resolve asset ids -> mhclo paths from the on-disk catalog (mirror serve_viewer)
        import glob
        cat = {}
        base = os.path.join(OUT, "assets_src")
        for sub, slot in (("clothing/tops", "top"), ("clothing/bottoms", "bottom")):
            for mh in glob.glob(os.path.join(base, sub, "*", "*.mhclo")):
                name = os.path.splitext(os.path.basename(mh))[0]
                cat[f"{slot}:{name}"] = mh
        sel = {"top": args.top, "bottom": args.bottom}
        print(f"[cloth] baking sel={sel}")
        bake_cloth(args.stem, sel, cat, {})
    else:
        precompute_framedata(args.stem, args.npz)
