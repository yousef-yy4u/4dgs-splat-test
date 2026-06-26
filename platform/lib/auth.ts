import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";

// On first authenticated visit, mirror the Clerk user into our DB and give them an Org
// (every asset/anchor belongs to an Org). Idempotent — safe to call on each request.
// Returns the Org id + user id, or null if not signed in.
export async function ensureUserOrg(): Promise<{ orgId: string; userId: string } | null> {
  const cu = await currentUser();
  if (!cu) return null;

  const email = cu.primaryEmailAddress?.emailAddress ?? cu.emailAddresses[0]?.emailAddress;
  if (!email) return null;

  const user = await prisma.user.upsert({
    where: { email },
    update: { authProvider: cu.id, name: cu.fullName ?? undefined },
    create: { email, authProvider: cu.id, name: cu.fullName ?? undefined },
  });

  // Reuse an existing membership, otherwise create a personal Org owned by this user.
  const existing = await prisma.membership.findFirst({ where: { userId: user.id } });
  if (existing) return { orgId: existing.orgId, userId: user.id };

  const org = await prisma.org.create({
    data: {
      name: cu.fullName ? `${cu.fullName}'s workspace` : "My workspace",
      members: { create: { userId: user.id, role: "OWNER" } },
      subscription: { create: {} },
    },
  });
  return { orgId: org.id, userId: user.id };
}
