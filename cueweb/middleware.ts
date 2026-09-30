/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Server-side authorization gate. This runs before any page or proxy route is
 * served - a single chokepoint, rather than a check sprinkled across pages.
 *
 * Behavior is environment-driven (see lib/authz.ts):
 *   - Gate off (default; CUEWEB_AUTHZ_ENABLED not truthy) or authentication
 *     disabled (no NEXT_PUBLIC_AUTH_PROVIDER): allow everything, so the sandbox
 *     / no-auth deployment - and any site that wants to defer access control to
 *     a future OpenCue-wide layer - is unchanged.
 *   - When enabled: require a signed-in user, then enforce CUEWEB_ALLOWED_GROUPS
 *     for the whole app and CUEWEB_ADMIN_GROUPS for the CueCommander
 *     administration pages. Both empty ⇒ no restriction.
 *
 * Group membership is resolved once at sign-in and stamped on the JWT
 * (lib/auth.ts); this Edge middleware only reads it.
 */

import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

import { getUserGroups, isAdminPath, isAuthzEnabled, isUserAdmin, isUserAllowed } from "@/lib/authz";

const AUTH_ENABLED = Boolean(process.env.NEXT_PUBLIC_AUTH_PROVIDER);

// The gate only does anything when auth is configured and it has not been
// explicitly switched off. Evaluated per request so the runtime env applies.
const gateActive = () => AUTH_ENABLED && isAuthzEnabled();

export default withAuth(
  function middleware(req) {
    // No auth provider, or the gate is disabled: nothing to enforce.
    if (!gateActive()) return NextResponse.next();

    const { pathname } = req.nextUrl;
    const isApi = pathname.startsWith("/api/");
    const groups = getUserGroups(req.nextauth.token);

    const deny = (reason: string) => {
      if (isApi) {
        return NextResponse.json({ error: reason }, { status: 403 });
      }
      const url = req.nextUrl.clone();
      url.pathname = "/unauthorized";
      url.search = "";
      return NextResponse.redirect(url);
    };

    if (!isUserAllowed(groups)) {
      return deny("You are not authorized to use CueWeb.");
    }
    if (isAdminPath(pathname) && !isUserAdmin(groups)) {
      return deny("You are not authorized to use the CueCommander administration pages.");
    }
    return NextResponse.next();
  },
  {
    callbacks: {
      // Gate "is the user signed in" here so unauthenticated users are sent to
      // the sign-in page. When the gate is inactive, let everything through.
      authorized: ({ token }) => (gateActive() ? !!token : true),
    },
    pages: { signIn: "/login" },
  },
);

// Run on everything except: the auth endpoints, the unauthenticated infra
// endpoints (health probe, Prometheus metrics), the login / unauthorized pages,
// and static assets (avoids a redirect loop and needless work on assets).
export const config = {
  matcher: [
    "/((?!api/auth|api/health|api/metrics|login|unauthorized|_next/static|_next/image|favicon.ico|icon.png).*)",
  ],
};
