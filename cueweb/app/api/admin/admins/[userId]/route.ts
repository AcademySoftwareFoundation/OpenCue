/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  adminCount,
  appendAudit,
  findUserById,
  isAdmin,
  removeAdmin,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ userId: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const { userId: userIdStr } = await params;
  const userId = Number(userIdStr);
  if (!Number.isFinite(userId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!isAdmin(userId)) {
    return NextResponse.json({ error: "not_admin" }, { status: 404 });
  }
  // Prevent removing the very last admin - otherwise nobody can recover.
  if (adminCount() <= 1) {
    return NextResponse.json(
      { error: "Cannot remove the last admin." },
      { status: 400 },
    );
  }
  removeAdmin(userId);
  const user = findUserById(userId);
  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "admin.remove",
    target: `user:${userId}`,
    before: { username: user?.username ?? null },
  });
  return NextResponse.json({ ok: true });
}
