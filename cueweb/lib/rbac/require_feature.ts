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

import "server-only";

import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";

import { authOptions } from "../auth";
import { authEnabled } from "./config";
import { hasPermission, type PermissionString } from "./permissions";
import { isAdmin, listEffectivePermissionsForUser } from "./db/dal";

export type FeatureCheckOk = {
  ok: true;
  userId: number;
  isAdmin: boolean;
  permissions: ReadonlyArray<string>;
  session: Awaited<ReturnType<typeof getServerSession>>;
};

export type FeatureCheckErr = {
  ok: false;
  response: NextResponse;
};

export type FeatureCheckResult = FeatureCheckOk | FeatureCheckErr;

/**
 * Gate a Next.js API route handler on a single feature/permission
 * string. Usage from `app/api/.../route.ts`:
 *
 *   export async function POST(req: NextRequest) {
 *     const gate = await requireFeature("jobs.kill");
 *     if (!gate.ok) return gate.response;
 *     // ... proceed using gate.userId / gate.permissions ...
 *   }
 *
 * Returns:
 *   - { ok: true, ... }           when the session holds the permission
 *   - { ok: false, response: ...} with a 401 / 403 NextResponse otherwise
 *
 * Permissions are looked up fresh from the DB every call. The JWT
 * mirror in `session.user.permissions` is for UI hints; the source of
 * truth here is `listEffectivePermissionsForUser(userId)`.
 */
export async function requireFeature(
  permission: PermissionString | string,
): Promise<FeatureCheckResult> {
  // Sandbox mode: no auth configured -> all checks pass. CueWeb is
  // unauthenticated, like before the RBAC layer existed.
  if (!authEnabled()) {
    return {
      ok: true,
      userId: -1,
      isAdmin: false,
      permissions: ["*"],
      session: null,
    };
  }
  const session = await getServerSession(authOptions);
  if (!session || !session.user) {
    return {
      ok: false,
      response: NextResponse.json(
        { error: "unauthenticated" },
        { status: 401 },
      ),
    };
  }

  const userIdStr = (session.user as { id?: string }).id;
  const userId = userIdStr ? Number(userIdStr) : NaN;
  if (!Number.isFinite(userId)) {
    return {
      ok: false,
      response: NextResponse.json(
        { error: "unauthenticated" },
        { status: 401 },
      ),
    };
  }

  const permissions = listEffectivePermissionsForUser(userId);
  if (!hasPermission(permissions, permission)) {
    return {
      ok: false,
      response: NextResponse.json(
        { error: "forbidden", missing: permission },
        { status: 403 },
      ),
    };
  }

  return {
    ok: true,
    userId,
    isAdmin: isAdmin(userId),
    permissions,
    session,
  };
}

/**
 * Gate that additionally requires the caller to be in the `admins`
 * table. Use this for /api/admin/* handlers - middleware.ts already
 * blocks at the edge, but the per-route check defends against the
 * unlikely case where someone hand-crafts a request bypassing the
 * matcher.
 */
export async function requireAdmin(): Promise<FeatureCheckResult> {
  // Sandbox mode: pretend the caller is the (only) admin so dev work
  // on the Admin UI is possible without configuring providers.
  if (!authEnabled()) {
    return {
      ok: true,
      userId: -1,
      isAdmin: true,
      permissions: ["*"],
      session: null,
    };
  }
  const session = await getServerSession(authOptions);
  if (!session || !session.user) {
    return {
      ok: false,
      response: NextResponse.json(
        { error: "unauthenticated" },
        { status: 401 },
      ),
    };
  }

  const userIdStr = (session.user as { id?: string }).id;
  const userId = userIdStr ? Number(userIdStr) : NaN;
  if (!Number.isFinite(userId) || !isAdmin(userId)) {
    return {
      ok: false,
      response: NextResponse.json({ error: "forbidden" }, { status: 403 }),
    };
  }

  return {
    ok: true,
    userId,
    isAdmin: true,
    permissions: listEffectivePermissionsForUser(userId),
    session,
  };
}
