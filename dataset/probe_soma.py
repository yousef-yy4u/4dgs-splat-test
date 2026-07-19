#!/usr/bin/env python3
"""Discover the installed SOMA-X API: can SOMALayer(identity_model_type='anny') run on CPU, what does
it need as input, what vertex count does it output, and are any example motions bundled?
    conda run -n 4dgs-data python probe_soma.py
"""
import importlib, inspect, os, glob, sys, traceback

mod = None
for name in ("soma", "py_soma_x", "somax", "soma_x"):
    try:
        mod = importlib.import_module(name)
        print(f"imported '{name}' from {getattr(mod, '__file__', '?')}")
        break
    except Exception as e:
        print(f"import {name} failed: {type(e).__name__}: {e}")
if mod is None:
    print("!! no soma package importable"); sys.exit(1)

print("top-level names:", [n for n in dir(mod) if not n.startswith('_')])

SL = getattr(mod, "SOMALayer", None)
if SL is None:
    for n in dir(mod):
        o = getattr(mod, n)
        if isinstance(o, type) and ("Layer" in n or "SOMA" in n):
            print("candidate class:", n)
print("SOMALayer:", SL)
if SL is not None:
    try:
        print("SOMALayer.__init__:", inspect.signature(SL.__init__))
    except Exception as e:
        print("sig err:", e)
    for m in ("forward", "__call__"):
        a = getattr(SL, m, None)
        if a:
            try: print(f"SOMALayer.{m}:", inspect.signature(a))
            except Exception: pass

# bundled example motions?
pkgdir = os.path.dirname(mod.__file__)
npzs = glob.glob(os.path.join(pkgdir, "**", "*.npz"), recursive=True)
print("bundled .npz (first 15):", npzs[:15])

# try to instantiate on CPU
if SL is not None:
    for kwargs in [dict(identity_model_type="anny", device="cpu"),
                   dict(identity_model_type="anny"),
                   dict(model_type="anny", device="cpu")]:
        try:
            print(f"\ntrying SOMALayer({kwargs}) ...")
            layer = SL(**kwargs)
            print("  OK ->", type(layer).__name__)
            print("  attrs:", [n for n in dir(layer) if not n.startswith('_')][:50])
            break
        except Exception as e:
            print("  failed:", type(e).__name__, str(e)[:300])
