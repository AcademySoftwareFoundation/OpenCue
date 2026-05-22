/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  createRole,
  findRoleByName,
  listPermissionsForRole,
  listRoles,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function GET() {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  const roles = listRoles().map((r) => ({
    ...r,
    permissions: listPermissionsForRole(r.id),
  }));
  return NextResponse.json({ roles });
}

export async function POST(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  let body: { name?: unknown; description?: unknown; permissions?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const name = String(body.name ?? "").trim();
  const description = body.description == null ? null : String(body.description);
  const permissions: string[] = Array.isArray(body.permissions)
    ? body.permissions.filter((p): p is string => typeof p === "string")
    : [];
  if (name.length < 1) {
    return NextResponse.json({ error: "name required" }, { status: 400 });
  }
  if (findRoleByName(name)) {
    return NextResponse.json({ error: "role already exists" }, { status: 409 });
  }
  const id = createRole({ name, description, permissions });
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "role.create",
    target: `role:${id}`,
    after: { name, description, permissions },
  });
  return NextResponse.json({ id }, { status: 201 });
}
