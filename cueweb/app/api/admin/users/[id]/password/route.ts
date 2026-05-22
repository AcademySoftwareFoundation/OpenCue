/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";
import argon2 from "argon2";

import { requireAdmin } from "@/lib/rbac/require_feature";
import {
  appendAudit,
  findUserById,
  setUserPassword,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

const MIN_LEN = 12;

// Admin-driven password reset. Sets a new password and flips
// must_change_password=1 so the user is prompted to change it on
// next sign-in.
export async function POST(
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
  if (user.source !== "local") {
    return NextResponse.json(
      { error: "Only local users have a password." },
      { status: 400 },
    );
  }

  let body: { password?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const password = String(body.password ?? "");
  if (password.length < MIN_LEN) {
    return NextResponse.json(
      { error: `Password must be at least ${MIN_LEN} characters.` },
      { status: 400 },
    );
  }

  const hash = await argon2.hash(password, { type: argon2.argon2id });
  setUserPassword(userId, hash, true);

  appendAudit({
    actorId: gate.userId,
    actorLabel: String(gate.userId),
    action: "user.password_reset",
    target: `user:${userId}`,
  });

  return NextResponse.json({ ok: true });
}
