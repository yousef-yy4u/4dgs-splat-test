# GLASSES.md — AR Productivity Glasses (SSOT for the glasses track)

> **Status:** ACTIVE EXPLORATION (spun out 2026-06-25, decision G1 / PROJECT.md D36). This is a **separate product** from the B2B platform in [PROJECT.md](PROJECT.md) (§0 / D35 — Marker-Anchored AR Asset Platform). **Both are kept.** PROJECT.md remains the SSOT for the platform; THIS file is the SSOT for the glasses.
> **Last updated:** 2026-06-25
> **Maintenance rule (same as PROJECT.md):** update this file whenever a decision, plan, feature spec, or idea changes — in conversation OR in files. Append to the **Decision Log** (§8) when an idea evolves; edit the relevant section when a spec changes. Keep superseded reasoning visible ("superseded by Gx") so the trail survives. Bump "Last updated".
>
> **Shared foundations live in PROJECT.md, don't duplicate them here:** 3-tier phone-offload compute (PROJECT.md §2), software-requirements-from-hardware + additive-display + world-units discipline (§2a), glasses hardware reality / reprojection-must-be-on-glasses (§7, D15/D19), render-cost reality = mesh-first / splats-as-hero (D34), Snap Specs validation (§8b/D13), licensing (§4a). This file references them rather than restating.

---

## 1. Vision (one paragraph)
**AI smart glasses as a personal AR productivity & dev cockpit.** A binocular optical AR display puts the wearer's screens into space — anything they'd see on a laptop or phone, but better expressed as **widgets** than as flat rectangles. They read documents, write code, browse, chat with an AI back-and-forth, and get live conversation transcription/translation — all driven **hands-free**: a **gaze cursor** points, and a deliberate **"click"** confirms. Heavy compute is **offloaded to the user's phone** (consistent with PROJECT.md §2); the glasses stay a thin display+sensor surface.

## 2. The product — what the wearer does
**Display:** binocular AR (both eyes). Capable of showing full screens (laptop/phone equivalents), but the design intent is **widgetized, glanceable surfaces** over raw mirrored windows — content laid out in space, not a floating monitor.

**Core use cases (v1 scope candidates):**
- Read/view: PDF, Word/docs, images, general display.
- **Dev/"vibe-code" productivity:** IDE display + running an agentic coding loop (e.g. Claude Code) by voice/gaze.
- **Live conversation:** real-time transcription + translation (two-way, go back and forth).
- **AI chat:** conversational assistant, back-and-forth, with web search / general lookup.
- **Voice commands** to drive all of the above ("open X", "next", "search …").

> **Reality anchor (PROJECT.md D34):** the floating-screen/widget layer is the ONE AR capability that already ships on phone-offload thin glasses (Xreal / Viture / Rokid / Even Realities / Meta Ray-Ban Display) — but those vendors show a *floating flat screen*, NOT world-locked AR. So this display target is **achievable AND commoditized** → the display is not the moat. World-welding widgets is the harder tier (hits the on-glasses-reprojection wall, §7/D15). Default v1 = body/head-locked widgets, not world-anchored.

## 3. Input model — the differentiator (v1 DECIDED, G1)
Hands-free navigation is the distinctive bet. Hand/gesture input is **explicitly dropped** for this product (user call) — fights the all-day, discreet, no-gorilla-arm goal.

**DECIDED (v1): gaze cursor + a discreet confirm "click." BCI is a research line, not a v1 dependency.**
- **Pointer = eye-tracking cursor.** Proven model — Apple Vision Pro is *gaze-to-target + pinch-to-confirm*; we keep the gaze half, swap the confirm.
  - **Known pitfall — "Midas touch":** gaze ≠ intent (you look around to *read*, not to click) → you MUST have a separate deliberate confirm; you cannot treat every dwell as a click everywhere.
- **Confirm "click" ladder (ship the proven rungs, no exotic HW required):**
  1. **Dwell-to-click** (look + hold ~400ms) — zero extra hardware, standard accessibility pattern. Baseline.
  2. **Silent-speech / micro-voice "select"** — reuses PROJECT.md D18's command-grammar input (prototype with ordinary voice, swap to EMG/subvocal at HW phase).
  3. **Temple-tap / touch** — PROJECT.md D18's discreet backstop.
  4. *(optional)* **sEMG wristband** — the only *shipping* neural input today (Meta), but it's a hands path → only if the user later relaxes the no-hands rule.
- **"Think-to-click" BCI = MONITOR, don't depend on it.** Treated like true compact occlusion in PROJECT.md D12: a research line we swap in IF it matures, not a v1 blocker. Why (honest):
  - A reliable, low-latency, low-false-positive, all-day single-bit click from *thinking it*, off dry electrodes in a normal glasses frame, is **not a shipping consumer capability today.**
  - Closest prior art: **NextMind** — visual-cortex SSVEP selection, but electrodes at the **back of the head**, not a glasses frame; Snap acquired and shelved it (2022).
  - The only **shipping** neural input is **Meta's sEMG wristband** — muscle@wrist, not brain (and a hands path we're dropping).
  - EEG headbands (Muse/Emotiv) never delivered a dependable click in a decade.
  - Swap plan mirrors D18's voice→EMG: identical UX (gaze + confirm), only the confirm *sensor* changes if a clean in-frame neural click ever works.

> **Caveat (mid-2026):** consumer BCI / neural-input claims move fast — re-audit before committing the input HW.

## 4. Compute architecture — phone-offload (reuses PROJECT.md §2/§2a/§7)
- **Phone does the heavy lifting** (rendering, apps, SLAM, AI orchestration); glasses = display + sensors + the irreducible **on-glasses reprojection/timewarp** sliver (PROJECT.md §7, D15) needed for any world-locked content.
- For **body/head-locked screens/widgets** (the v1 default), world-lock requirements are *light* → phone-offload is easy. World-welded widgets are the upgrade tier that needs the reprojection co-processor (D34's wall).
- Eye-tracking adds **inward cameras + a tracking pipeline** (run on phone where latency allows; gaze cursor smoothing/prediction is soft-real-time like hand-tracking in D19).
- Cross-device output discipline (world units, ≥2 quality tiers, additive-display rendering) carries verbatim from PROJECT.md §2a.

## 5. Feasibility & risks (honest grading)
| Element | Grade | Note |
|---|---|---|
| Floating screens / widgets on phone-offload glasses | 🟢 Ships today | Commoditized (Xreal/Viture/Even/Meta) → not a moat (D34). |
| Phone-offload compute | 🟢 Proven | Whole project architecture (§2); easy for head-locked screens. |
| Gaze cursor | 🟢 Proven | Vision Pro; adds inward cameras+compute; Midas-touch needs a real confirm. |
| Voice commands + AI loop | 🟢 Proven | Standard; the "vibe-code by voice" angle is product, not research. |
| Live transcribe/translate | 🟢 Proven | Existing models; latency/UX is the work. |
| Discreet confirm (dwell / silent-speech / temple) | 🟡 Mostly proven | Dwell trivial; silent-speech is D18's least-proven IN bet (mitigated by voice stand-in). |
| World-welded widgets (vs head-locked) | 🟡 Hard | Needs on-glasses reprojection (§7/D15) — the D34 wall. |
| **"Think-to-click" BCI in a glasses frame** | 🔴 Research frontier | Not a v1 dependency (G1). The make-or-break IF pursued as core. |
| Glasses hardware (optics/power/heat/FOV) | 🔴 Hardware-era wall | PROJECT.md D34: optics/occlusion/reprojection-power, not compute, is why daily AR glasses don't exist yet. Hardware is LAST. |

**Strategic risk:** the *display* half is commoditized and the *novel* half (BCI) is unproven → the defensible v1 wedge is the **software experience** (the agentic productivity/dev cockpit + gaze-driven UX on top of off-the-shelf display glasses), not the hardware. Mirrors PROJECT.md D13/D34's "compete on software, hardware last."

## 6. Relationship to the platform (PROJECT.md / D35) and original Track A
- **Different product from D35.** D35 = a *B2B* platform where businesses anchor AR assets for *other people's* devices. This = a *personal* AR productivity computer for *the wearer*. Shared: phone-offload (§2), cross-device/world-units/additive-display discipline (§2a). **Both are kept** (user decision) — D35 stays in PROJECT.md, glasses live here.
- **This is a REFRAME of the original Track A** (PROJECT.md §1 — agent/HUD glasses + phone control), NOT a restatement: §1/§6b optimized for **stealth** (discreet *monocular* HUD, silent input, all-day public). A **binocular full-screen IDE/productivity cockpit driven by eye-tracking** is the opposite design point (bigger display, less stealth, gaze-first input). It also **supersedes D18's "silent speech + hand" as the input model for THIS product** → gaze + confirm-ladder (hand dropped).

## 7. Open questions
- [ ] **Widget UX:** what's the widget set + spatial layout model (head-locked vs lazy-follow vs pinned)?
- [ ] **Confirm default:** dwell-to-click vs silent-speech as the primary v1 confirm (settle in UX design).
- [ ] **Display HW target for prototyping:** off-the-shelf binocular display glasses (Xreal/Viture class) as the feel-prototype? (PROJECT.md §7 lists the spectrum.)
- [ ] **Eye-tracking source:** which gaze pipeline (off-the-shelf module vs phone-CV) and its latency budget.
- [ ] **Overlap with PROJECT.md generation/library:** does the cockpit ever *summon* 3D assets, or is it screens/widgets only for v1? (Default: screens/widgets only; 3D is a later layer.)
- [ ] **BCI monitoring trigger:** what evidence would promote "think-to-click" from research to a v1 candidate?

## 8. Decision Log (newest last)
- **G1 — Glasses product spun out into its own SSOT; v1 input = gaze + discreet-confirm ladder, BCI = research (2026-06-25).** User articulated a wearer-facing AR productivity/dev cockpit (binocular AR screens/widgets; PDF/docs, IDE + agentic coding, web, AI chat, live transcribe/translate; voice commands; **phone-offload**; **hands-free** nav). **Kept SEPARATE from the D35 B2B platform — both projects continue** (PROJECT.md = platform SSOT, this file = glasses SSOT; logged as D36 there). Input DECIDED: **eye-tracking cursor + a confirm ladder** (dwell-to-click → silent-speech "select" → temple-tap → optional sEMG wristband); **"think-to-click" BCI treated as a research line to MONITOR, not a v1 dependency** (rationale: noisy in-frame EEG, NextMind shelved, only sEMG-wrist ships — see §3/§5). Hand input dropped. This reframes the original stealth Track A (PROJECT.md §1) toward a less-stealthy binocular cockpit and supersedes D18's input model for this product. (§1–§7; refs PROJECT.md §2/§2a/§7, D12/D13/D18/D34/D35)
