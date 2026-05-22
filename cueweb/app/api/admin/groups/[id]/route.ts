/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  deleteGroup,
  findGroupById,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function DELETE(
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
  const group = findGroupById(groupId);
  if (!group) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  if (group.source !== "local") {
    return NextResponse.json(
      {
        error:
          "Externally-sourced groups cannot be deleted here. Remove them from the source directory.",
      },
      { status: 400 },
    );
  }
  deleteGroup(groupId);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "group.delete",
    target: `group:${groupId}`,
    before: { name: group.name, source: group.source },
  });
  return NextResponse.json({ ok: true });
}
