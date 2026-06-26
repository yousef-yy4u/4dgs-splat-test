import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Protect the app surfaces; public marketing + the un-anchored viewer/widget stay open.
const isProtected = createRouteMatcher(["/dashboard(.*)", "/api/assets(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req)) await auth.protect();
});

export const config = {
  // Run on app routes + APIs, skip Next internals and static files.
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
