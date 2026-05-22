/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  deleteRole,
  listPermissionsForRole,
  listRoles,
  updateRolePermissions,
} from "@/lib/rbac/db/dal";
import { isBuiltinRole } from "@/lib/rbac/roles";

export const runtime = "nodejs";

function findById(id: number) {
  return listRoles().find((r) => r.id === id) ?? null;
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const { id } = await params;
  const roleId = Number(id);
  if (!Number.isFinite(roleId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  const role = findById(roleId);
  if (!role) return NextResponse.json({ error: "not_found" }, { status: 404 });

  let body: { permissions?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  if (!Array.isArray(body.permissions)) {
    return NextResponse.json({ error: "permissions array required" }, { status: 400 });
  }
  const before = listPermissionsForRole(roleId);
  const next = (body.permissions as unknown[]).filter(
    (p): p is string => typeof p === "string",
  );
  updateRolePermissions(roleId, next);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "role.update",
    target: `role:${roleId}`,
    before: { permissions: before },
    after: { permissions: next },
  });
  return NextResponse.json({ ok: true });
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const { id } = await params;
  const roleId = Number(id);
  if (!Number.isFinite(roleId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  const role = findById(roleId);
  if (!role) return NextResponse.json({ error: "not_found" }, { status: 404 });
  if (role.builtin === 1 || isBuiltinRole(role.name)) {
    return NextResponse.json(
      { error: "Built-in roles cannot be deleted." },
      { status: 400 },
    );
  }
  deleteRole(roleId);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "role.delete",
    target: `role:${roleId}`,
    before: { name: role.name },
  });
  return NextResponse.json({ ok: true });
}
