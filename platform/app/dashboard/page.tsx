import { currentUser } from "@clerk/nextjs/server";
import { ensureUserOrg } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const user = await currentUser();

  // Mirror the Clerk user into our DB + ensure an Org. Tolerate the DB being down in Phase 0
  // (DATABASE_URL not yet wired) so the auth shell is still demoable.
  let org: { orgId: string; userId: string } | null = null;
  let dbError: string | null = null;
  try {
    org = await ensureUserOrg();
  } catch (e) {
    dbError = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      <p className="mt-2 text-neutral-600 dark:text-neutral-300">
        Signed in as <strong>{user?.primaryEmailAddress?.emailAddress ?? user?.id}</strong>.
      </p>

      <div className="mt-6 rounded-lg border border-neutral-200 p-4 text-sm dark:border-neutral-800">
        {org ? (
          <p>
            Workspace ready · org <code>{org.orgId}</code>
          </p>
        ) : dbError ? (
          <p className="text-amber-600">
            Auth works; DB sync pending — set <code>DATABASE_URL</code> and run{" "}
            <code>npm run db:migrate</code>. ({dbError.split("\n")[0]})
          </p>
        ) : (
          <p>No workspace yet.</p>
        )}
      </div>

      <p className="mt-6 text-xs text-neutral-400">
        Next: asset creation (image → GLB + USDZ) and the &ldquo;view in 3D&rdquo; publish step.
      </p>
    </main>
  );
}
