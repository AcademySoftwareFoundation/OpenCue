/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";
import argon2 from "argon2";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  findUserByExternalId,
  findUserByUsername,
  listGroupsForUser,
  listDirectRolesForUser,
  listUsers,
  upsertUser,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const search = req.nextUrl.searchParams.get("q") ?? "";
  const users = listUsers({ search });
  const enriched = users.map((u) => ({
    ...u,
    groups: listGroupsForUser(u.id).map((g) => g.name),
    directRoles: listDirectRolesForUser(u.id).map((r) => r.name),
  }));
  return NextResponse.json({ users: enriched });
}

export async function POST(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  let body: { username?: unknown; email?: unknown; displayName?: unknown; password?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const username = String(body.username ?? "").trim();
  const password = String(body.password ?? "");
  const email = body.email == null ? null : String(body.email);
  const displayName = body.displayName == null ? null : String(body.displayName);
  if (username.length < 1) {
    return NextResponse.json({ error: "username required" }, { status: 400 });
  }
  if (password.length < 12) {
    return NextResponse.json(
      { error: "Password must be at least 12 characters." },
      { status: 400 },
    );
  }
  if (findUserByUsername(username) || findUserByExternalId(`local:${username}`)) {
    return NextResponse.json({ error: "username already exists" }, { status: 409 });
  }

  const hash = await argon2.hash(password, { type: argon2.argon2id });
  const userId = upsertUser({
    externalId: `local:${username}`,
    username,
    email,
    displayName,
    source: "local",
    passwordHash: hash,
    mustChangePassword: true,
  });

  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "user.create",
    target: `user:${userId}`,
    after: { username, email, displayName, source: "local" },
  });

  return NextResponse.json({ id: userId }, { status: 201 });
}
