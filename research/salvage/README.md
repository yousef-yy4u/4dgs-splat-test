# SV4D salvage (D58, 2026-07-01)
generative-models/ (SV4D 2.0 build, 23G) was DELETED to reclaim disk for the LHM++
humanoid track (D57/D58). SV4D was the general-object 4D path (deprioritized) + had a
"research-purposes" license flag. Salvaged the non-reclonable bits:
- run_sv4d2_patched.py — the reusable Blackwell (sm_120) attention monkeypatch
  (xformers.memory_efficient_attention -> torch SDPA, rank-aware; head_dim-512). Works for
  ANY sgm/SVD-family model on the 5090. See PROJECT.md D52.
- sv4d2*.yaml — sampling configs.
Results (camel.gif -> 4 novel-view mp4s) are safe in generation/sv4d2_out/.
To revive SV4D: re-clone Stability's generative-models, re-download sv4d2.safetensors (12G,
HF token in generation/.env), re-apply run_sv4d2_patched.py.
