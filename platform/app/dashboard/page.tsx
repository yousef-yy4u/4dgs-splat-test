import { currentUser } from "@clerk/nextjs/server";
import { ensureUserOrg } from "@/lib/auth";
import { prisma } from "@/lib/db";
import AssetCreator from "./AssetCreator";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const user = await currentUser();
  const org = await ensureUserOrg();
  const assets = org
    ? await prisma.asset.findMany({
        where: { orgId: org.orgId },
        orderBy: { createdAt: "desc" },
        include: { widgets: true },
        take: 30,
      })
    : [];

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      <p className="mt-1 text-sm text-neutral-500">
        {user?.primaryEmailAddress?.emailAddress ?? user?.id}
      </p>

      <div className="mt-8">
        <AssetCreator />
      </div>

      <h2 className="mt-10 font-semibold">Your assets</h2>
      {assets.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-500">None yet — create one above.</p>
      ) : (
        <ul className="mt-3 divide-y divide-neutral-200 dark:divide-neutral-800">
          {assets.map((a) => (
            <li key={a.id} className="flex items-center justify-between py-3 text-sm">
              <span>
                {a.name}{" "}
                <span className="text-neutral-400">· {a.status.toLowerCase()}</span>
              </span>
              {a.widgets[0] ? (
                <a className="text-blue-600 underline" href={`/v/${a.widgets[0].slug}`} target="_blank">
                  view in 3D ↗
                </a>
              ) : (
                <span className="text-neutral-400">unpublished</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
