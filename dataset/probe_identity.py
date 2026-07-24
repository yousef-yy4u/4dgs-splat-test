import numpy as np, torch
from soma import SOMALayer
import anny.models.phenotype as _ph
for _n in dir(_ph):
    _o = getattr(_ph, _n)
    if isinstance(_o, type) and "get_phenotype_blendshape_coefficients" in _o.__dict__:
        def _mk(f):
            def g(self, *a, local_changes=None, **k): return f(self, *a, local_changes=(local_changes or {}), **k)
            return g
        _o.get_phenotype_blendshape_coefficients = _mk(_o.get_phenotype_blendshape_coefficients)

layer = SOMALayer(identity_model_type="anny", device="cpu"); layer.eval()
im = layer.identity_model
print("identity_model type:", type(im).__name__)
print("num_identity_coeffs:", getattr(im, "num_identity_coeffs", "?"))
inner = getattr(im, "identity_model", None)
print("inner identity_model:", type(inner).__name__ if inner else None)
if inner is not None:
    print("phenotype_labels:", getattr(inner, "phenotype_labels", None))
    am = getattr(inner, "anny_model", None)
    if am is not None:
        print("anny phenotype_labels:", getattr(am, "phenotype_labels", None))
        # try to discover the neutral/default + valid range
        for attr in ("parse_phenotype_kwargs",):
            print("has", attr, hasattr(am, attr))

# height of the zero-coeff body vs a few named phenotype sets
def body_height(identity_coeffs):
    poses = torch.zeros(1, 77, 3); transl = torch.zeros(1,3)
    with torch.no_grad():
        out = layer(poses, identity_coeffs, transl=transl)
    v = out["vertices"][0].numpy()
    ext = v.max(0)-v.min(0)
    return ext, v.shape[0]

ext0, n = body_height(torch.zeros(1, 11))
print("\nzeros(1,11) body bbox extent:", ext0, "verts", n)
