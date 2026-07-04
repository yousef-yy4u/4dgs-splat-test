---
name: stealth-agent-glasses-product
description: "The 4dgs project's real product — stealth AI-agent smart glasses; two separable products bundled together"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7fa889b7-cdf5-419f-9a65-e527b3ffcb4b
---

The project is **stealth AI smart glasses**, not just a 4D-splat renderer. Two priorities: (1) **stealth** — must look like normal glasses; all audio/visual I/O discrete (bone-conduction audio out, monocular wearer-only HUD, discreet good camera); (2) **autonomous agent** with full user context that manages daily life (scheduling, reminders, shopping, conversations) and can drive phone apps (e.g. open Spotify, pick a song). Comfort constraints: no heat issues, ~8hr battery, LiDAR for physics/occlusion.

Three-tier stack: **cloud server** (NVIDIA GPU, heavy gen + user management) → **phone** (compute offload: local SLAM, physics, lighting estimation) → **glasses** (sensors + discrete I/O accessory).

**Key strategic point I raised:** this bundles two largely independent products — (A) the stealth agent glasses (valuable with zero splatting: mic+HUD+LLM+phone control) and (B) the 4D-splat generation pipeline (a demo feature, the riskiest unsolved part). Recommended building A first, treating B as a later flagship trick.

**Why:** the agent value prop doesn't need Gaussian generation; betting the product on B front-loads the hardest research risk.

**How to apply:** when scoping work, keep the agent-glasses track and the splat-gen track separate; reality-check hardware contradictions (display+LiDAR+stealth+8hr battery are mutually exclusive today) before industrial design. See [[generation-pipeline-reality-check]], [[project-goal-4dgs]].

**Humanoid / telepresence vision (added):** the emotional core of the product — each user has their own private humanoid avatar profile; add family/friends as AR avatars; shared visual sessions on a call so it "feels like the same room"; an AI companion avatar that walks/sits with the user and converses naturally. Clear-eyed cost note: humanoids are kept PRIVATE (correct for privacy) but are ALSO the most expensive to produce (GaussianAvatars-style per-subject optimization, minutes-hours, + live face/body tracking to drive them) and the LEAST dedup-able (every person unique → no flywheel, full cost per user). So the real cost center is the humanoid pipeline, NOT the shareable object library. The AI companion avatar is the easier first win (single asset, pre-built/optimized offline once); live human↔human telepresence (real-time capture+drive both ends) is hardest — prototype companion first. See [[asset-library-architecture]].
