export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-6 py-16">
      <div>
        <p className="text-sm font-medium uppercase tracking-widest text-neutral-500">
          Phase 0 · Foundations
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Marker-Anchored AR Asset Platform
        </h1>
        <p className="mt-4 text-neutral-600 dark:text-neutral-300">
          No-code platform where a business publishes a 3D asset two ways: an instant{" "}
          <strong>&ldquo;view in 3D&rdquo;</strong> web/print widget, and a real-world{" "}
          <strong>marker-anchored</strong> placement pointing to an owner-seeded, cloud-hosted map.
        </p>
      </div>

      <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-300">
        <li>
          → Backbone health:{" "}
          <a className="underline" href="/api/health">
            /api/health
          </a>
        </li>
        <li>→ Data model: <code>prisma/schema.prisma</code> (multi-tenant + governance baked in)</li>
        <li>→ GPU pipeline: the existing <code>generation/server.py</code> (image → GLB + USDZ)</li>
      </ul>

      <p className="text-xs text-neutral-400">
        See <code>platform/README.md</code> and the repo <code>IMPLEMENTATION_PLAN.md</code>.
      </p>
    </main>
  );
}
