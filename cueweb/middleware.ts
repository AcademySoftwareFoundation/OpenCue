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

import { NextResponse, type NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

/**
 * Edge-runtime middleware. It only does coarse path gating off the
 * JWT - the heavy-weight per-feature checks live in the Node-runtime
 * `requireFeature(...)` helper used by API route handlers, because
 * better-sqlite3 cannot run on the Edge runtime.
 *
 * Matches:
 *  - /admin/*           : require session and `isAdmin`
 *  - /api/admin/*       : require session and `isAdmin` (returns 403 JSON)
 *
 * Everything else is allowed through; specific routes still gate
 * themselves via requireFeature() at the handler level.
 */
export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Sandbox mode: NEXT_PUBLIC_AUTH_PROVIDER is empty -> no enforcement.
  // CueWeb behaves like it did before RBAC was added.
  if (!process.env.NEXT_PUBLIC_AUTH_PROVIDER) return NextResponse.next();

  const isAdminPath = pathname.startsWith("/admin");
  const isAdminApi = pathname.startsWith("/api/admin");
  if (!isAdminPath && !isAdminApi) return NextResponse.next();

  const token = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET,
  });

  if (!token) {
    if (isAdminApi) {
      return NextResponse.json(
        { error: "unauthenticated" },
        { status: 401 },
      );
    }
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (!token.cuewebIsAdmin) {
    if (isAdminApi) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    const home = req.nextUrl.clone();
    home.pathname = "/";
    return NextResponse.redirect(home);
  }

  return NextResponse.next();
}

export const config = {
  // next-auth's getToken is already lazy about reading the JWT, but
  // we still scope the matcher tightly so we don't add latency to
  // every static asset request.
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
