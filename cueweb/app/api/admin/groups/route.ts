/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  findGroupByName,
  listGroups,
  listRolesForGroup,
  upsertGroup,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function GET() {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const groups = listGroups().map((g) => ({
    ...g,
    roles: listRolesForGroup(g.id).map((r) => r.name),
  }));
  return NextResponse.json({ groups });
}

export async function POST(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  let body: { name?: unknown; description?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const name = String(body.name ?? "").trim();
  if (name.length < 1) {
    return NextResponse.json({ error: "name required" }, { status: 400 });
  }
  if (findGroupByName(name)) {
    return NextResponse.json({ error: "group already exists" }, { status: 409 });
  }
  const description = body.description == null ? null : String(body.description);

  const id = upsertGroup({ name, description, source: "local" });
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "group.create",
    target: `group:${id}`,
    after: { name, description, source: "local" },
  });
  return NextResponse.json({ id }, { status: 201 });
}
