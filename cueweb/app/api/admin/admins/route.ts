/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  addAdmin,
  appendAudit,
  findUserByEmail,
  findUserByExternalId,
  findUserById,
  findUserByUsername,
  listAdminUserIds,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function GET() {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  const ids = listAdminUserIds();
  const users = ids
    .map((id) => findUserById(id))
    .filter((u): u is NonNullable<typeof u> => !!u)
    .map((u) => ({
      id: u.id,
      username: u.username,
      email: u.email,
      displayName: u.display_name,
      source: u.source,
    }));
  return NextResponse.json({ admins: users });
}

// Add an admin by user id, by external_id (Okta sub / LDAP DN), by
// email, or by username. The user must already exist in the `users`
// table; admins cannot be invented on the fly.
export async function POST(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  let body: {
    userId?: unknown;
    externalId?: unknown;
    email?: unknown;
    username?: unknown;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  let user = null;
  if (body.userId != null) user = findUserById(Number(body.userId));
  else if (typeof body.externalId === "string")
    user = findUserByExternalId(body.externalId);
  else if (typeof body.email === "string") user = findUserByEmail(body.email);
  else if (typeof body.username === "string")
    user = findUserByUsername(body.username);

  if (!user) {
    return NextResponse.json(
      {
        error:
          "User not found. The user must sign in to CueWeb once (or be created in the Users tab) before they can be made an admin.",
      },
      { status: 404 },
    );
  }
  addAdmin(user.id);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "admin.add",
    target: `user:${user.id}`,
    after: { username: user.username, source: user.source },
  });
  return NextResponse.json({ ok: true, userId: user.id });
}
