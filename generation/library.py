#!/usr/bin/env python
"""
4dgs ASSET LIBRARY — the retrieval core (the moat, PROJECT.md §4).

Generation is the rare MISS path; the runtime is RETRIEVAL from a growing, deduplicated
library. This module is that library:
  - storage: generation/library/{index.json, embeddings.npy, assets/<id>/...}
  - embeddings: CLIP (openai/clip-vit-base-patch32, MIT) image+text in one space, so a TEXT
    query or an IMAGE can retrieve assets. An asset's embedding = mean of its view images.
  - dedup-on-write: a new asset whose nearest existing neighbor is >DEDUP_T cosine is treated
    as a duplicate (reuse instead of re-storing) — this IS the flywheel.
  - search: text or image -> cosine top-k.

CLI:
  library.py add <id> <label> <glb> <splat> <img1> [img2 ...]
  library.py search "<text query>" [k]
  library.py list
"""
import os, sys, json, shutil
import numpy as np

LIB = '/home/sov2/projects/4dgs/generation/library'
ASSETS = os.path.join(LIB, 'assets')
INDEX = os.path.join(LIB, 'index.json')
EMB = os.path.join(LIB, 'embeddings.npy')
DEDUP_T = 0.94          # cosine above which a new asset is considered a duplicate
os.makedirs(ASSETS, exist_ok=True)

_clip = {}
def _load_clip():
    if not _clip:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        name = 'openai/clip-vit-base-patch32'
        _clip['dev'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        _clip['model'] = CLIPModel.from_pretrained(name).to(_clip['dev']).eval()
        _clip['proc'] = CLIPProcessor.from_pretrained(name)
        _clip['torch'] = torch
    return _clip

def embed_images(paths):
    c = _load_clip(); torch = c['torch']; m = c['model']
    from PIL import Image
    imgs = [Image.open(p).convert('RGB') for p in paths]
    inp = c['proc'](images=imgs, return_tensors='pt').to(c['dev'])
    with torch.no_grad():                                # vision_model -> visual_projection (shared CLIP space)
        f = m.visual_projection(m.vision_model(pixel_values=inp['pixel_values']).pooler_output)
    f = torch.nn.functional.normalize(f, dim=-1).cpu().numpy()
    v = f.mean(0); v /= (np.linalg.norm(v) + 1e-9)      # mean of views -> unit
    return v.astype(np.float32)

def embed_text(text):
    c = _load_clip(); torch = c['torch']; m = c['model']
    inp = c['proc'](text=[text], return_tensors='pt', padding=True).to(c['dev'])
    with torch.no_grad():
        f = m.text_projection(m.text_model(input_ids=inp['input_ids'], attention_mask=inp.get('attention_mask')).pooler_output)
    f = torch.nn.functional.normalize(f, dim=-1).cpu().numpy()[0]
    return f.astype(np.float32)

def _load():
    idx = json.load(open(INDEX)) if os.path.exists(INDEX) else []
    emb = np.load(EMB) if os.path.exists(EMB) else np.zeros((0, 512), np.float32)
    return idx, emb

def _save(idx, emb):
    json.dump(idx, open(INDEX, 'w'), indent=1)
    np.save(EMB, emb)

def search_vec(v, k=8):
    idx, emb = _load()
    if len(emb) == 0: return []
    sims = emb @ v
    order = np.argsort(-sims)[:k]
    return [{**idx[i], 'score': float(sims[i])} for i in order]

def search_text(text, k=8):
    return search_vec(embed_text(text), k)

def add(asset_id, label, glb, splat, images, category='', scope='global', curation='hand-curated', extra=None):
    """Add an asset. Returns (status, record). status in {'added','duplicate'}."""
    idx, emb = _load()
    v = embed_images(images)
    if len(emb):
        nn = float((emb @ v).max())
        if nn >= DEDUP_T:
            j = int(np.argmax(emb @ v))
            return 'duplicate', {**idx[j], 'dup_score': nn}
    adir = os.path.join(ASSETS, asset_id); os.makedirs(adir, exist_ok=True)
    files = {}
    for key, src in [('glb', glb), ('splat', splat)]:
        if src and os.path.exists(src):
            dst = os.path.join(adir, key + os.path.splitext(src)[1])
            shutil.copy(src, dst); files[key] = os.path.basename(dst)
    thumbs = []
    for n, src in enumerate(images):
        dst = os.path.join(adir, f'view{n}.png')
        shutil.copy(src, dst); thumbs.append(os.path.basename(dst))
    files['views'] = thumbs
    rec = {'id': asset_id, 'label': label, 'category': category, 'scope': scope,
           'curation': curation, 'files': files, **(extra or {})}
    idx.append(rec)
    emb = np.vstack([emb, v[None, :]])
    _save(idx, emb)
    return 'added', rec

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if cmd == 'add':
        aid, label, glb, splat = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        imgs = sys.argv[6:]
        st, rec = add(aid, label, glb, splat, imgs)
        print(st, '->', rec['id'], '|', rec.get('label'), rec.get('dup_score', ''))
    elif cmd == 'search':
        q = sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        for r in search_text(q, k):
            print(f"  {r['score']:.3f}  {r['id']:16s} {r['label']}")
    else:
        idx, emb = _load()
        print(f"{len(idx)} assets:")
        for r in idx: print(f"  {r['id']:16s} {r['label']}  [{r['category']}/{r['scope']}]")
