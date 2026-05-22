/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  findUserById,
  setUserActive,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const { id } = await params;
  const userId = Number(id);
  if (!Number.isFinite(userId)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  const user = findUserById(userId);
  if (!user) return NextResponse.json({ error: "not_found" }, { status: 404 });

  let body: { active?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  if (typeof body.active !== "boolean") {
    return NextResponse.json({ error: "active boolean required" }, { status: 400 });
  }

  const before = { active: user.active === 1 };
  setUserActive(userId, body.active);
  const after = { active: body.active };

  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "user.update",
    target: `user:${userId}`,
    before,
    after,
  });

  return NextResponse.json({ ok: true });
}
