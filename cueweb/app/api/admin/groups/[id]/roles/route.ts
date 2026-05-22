/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  attachRoleToGroup,
  detachRoleFromGroup,
  findGroupById,
  findRoleByName,
  listRolesForGroup,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  const { id } = await params;
  const groupId = Number(id);
  if (!Number.isFinite(groupId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!findGroupById(groupId)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json({ roles: listRolesForGroup(groupId) });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  const { id } = await params;
  const groupId = Number(id);
  if (!Number.isFinite(groupId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!findGroupById(groupId)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  let body: { roleName?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const role = findRoleByName(String(body.roleName ?? ""));
  if (!role) return NextResponse.json({ error: "role_not_found" }, { status: 404 });

  attachRoleToGroup(groupId, role.id);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "group.role_attach",
    target: `group:${groupId}`,
    after: { roleName: role.name },
  });
  return NextResponse.json({ ok: true });
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  const { id } = await params;
  const groupId = Number(id);
  if (!Number.isFinite(groupId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!findGroupById(groupId)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  const roleName = req.nextUrl.searchParams.get("roleName") ?? "";
  const role = findRoleByName(roleName);
  if (!role) return NextResponse.json({ error: "role_not_found" }, { status: 404 });

  detachRoleFromGroup(groupId, role.id);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "group.role_detach",
    target: `group:${groupId}`,
    before: { roleName: role.name },
  });
  return NextResponse.json({ ok: true });
}
