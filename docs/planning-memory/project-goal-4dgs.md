---
name: project-goal-4dgs
description: Core goal and chosen rendering architecture for the animated-3D side of the glasses project
metadata: 
  node_type: memory
  type: project
  originSessionId: ccb13a99-32a2-4d2b-880e-5c289b6f5a80
---

This is the **rendering/animation side** of the larger product in [[stealth-agent-glasses-product]] (stealth agentic AI smart glasses). Goal of this side: animate ANY 3D thing (human, animal, object) realistically and render it CHEAPLY on phone/edge/glasses with low streaming cost. It is ONE feature, not v1.

**Chosen representation:** animated **meshes** are the right default — cheapest to render/stream, universally browser/edge-renderable. Gaussian splats only when photoreal capture-from-reality is specifically required (see [[rigged-gaussian-splatting]]). Two paradigms were weighed and **Paradigm A (generate animated asset offline, render locally)** chosen over Paradigm B (real-time generative video/world models like PixVerse R1 / Genie 3 — cloud-bound, unfit for glasses).

**Why mesh-default:** cheap on-device render + low streaming cost are hard constraints (glasses GPUs are below phone-class). **How to apply:** prefer mesh/skeletal animation; reach for splats only for captured real subjects. For TEXT/generated assets, splats don't earn their cost (no real appearance to capture) — a PBR mesh is ~as good and far cheaper.

Chosen method to animate: **AnimaX** (outputs animated meshes; Wan2.1 Apache base) — see [[animax-reimplementation-findings]]. Pipeline feasibility/timing corrections in [[generation-pipeline-reality-check]].
