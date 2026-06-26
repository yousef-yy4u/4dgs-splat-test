# platform — Marker-Anchored AR Asset Platform (web app)

The no-code web app for the D35 product (see repo [`PROJECT.md`](../PROJECT.md) §0 and
[`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md)). This directory is **Phase 0: foundations**.

## What's here so far (Phase 0)
- **Next.js 14 (App Router, TypeScript, Tailwind)** — pinned to 14 because this box runs Node 18;
  bump to Next 16 / Node 20 later (one-time `nvm install 20`).
- **Data model** — [`prisma/schema.prisma`](prisma/schema.prisma). Multi-tenant (`Org`/`User`/`Membership`),
  one-asset-two-surfaces (`Asset` → `Widget` un-anchored + `Anchor` anchored), the GPU pipeline as `Job`,
  the rented-then-owned map as `LocationMap` (provider field), and **governance baked into `Anchor`
  from day one** (owner + `permissionScope` + `spatialClaim` + `moderation`).
- **GPU worker client** — [`lib/gen-worker.ts`](lib/gen-worker.ts). Talks to the existing
  `generation/server.py` (`POST /generate`, `GET /status/:id`). The web app authors; Python generates.
- **Health probe** — [`app/api/health/route.ts`](app/api/health/route.ts) reports DB + worker
  independently so the backbone can come up one piece at a time.

## Stack (Phase 0 + what's next)
| Concern | Choice | Status |
|---|---|---|
| Web framework | Next.js (App Router, TS, Tailwind) | ✅ |
| DB / ORM | Postgres + Prisma | ✅ schema; needs a running DB to migrate |
| GPU pipeline | existing `generation/server.py` (TRELLIS/UniRig) over HTTP | ✅ client wired |
| Auth | Clerk or Auth0 | ⏳ next |
| Billing | Stripe | ⏳ next |
| Storage / CDN | S3-compatible (Cloudflare R2) | ⏳ at publish |
| Un-anchored viewer | `<model-viewer>` → Scene Viewer (Android) / AR Quick Look + USDZ (iOS) | ⏳ Phase 1 |

> **Not at the core:** the 8th Wall binary (revocable, anti-compete license — D38). Anchored SLAM
> stays behind an abstraction so it's swappable.

## Run it
```bash
cd platform
cp .env.example .env        # fill DATABASE_URL (+ GEN_WORKER_URL for the GPU box)
npm install                 # runs prisma generate via postinstall
# with a Postgres reachable at DATABASE_URL:
npm run db:migrate          # creates tables from schema.prisma
npm run dev                 # http://localhost:3000  (health at /api/health)
```
No DB yet? `npm run dev` still serves the app; `/api/health` will report `db: down` until one is wired.

## Next steps (Phase 0 → 1)
1. Stand up Postgres + run the first migration.
2. Add auth (Clerk/Auth0) + Org/Membership creation on sign-up.
3. Asset pipeline end-to-end: image → worker → **GLB (compressed, LOD) + baked USDZ** → S3/CDN.
4. Drop in `<model-viewer>` with the Android/iOS split; verify "view in your room" on real devices.
