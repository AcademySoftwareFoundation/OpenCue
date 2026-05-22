/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { NextRequest, NextResponse } from "next/server";
import argon2 from "argon2";
import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import {
  appendAudit,
  findUserById,
  setUserPassword,
} from "@/lib/rbac/db/dal";

export const runtime = "nodejs";

const MIN_LEN = 12;

// Self-service password change for the signed-in user (source=local
// only). Used by /login/change-password to clear the
// must_change_password flag, and any local user can later use it to
// rotate their own password. Lives under /api/me/* rather than
// /api/admin/* so the admin-only middleware does not block normal
// users from changing their own credentials.
export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const userId = Number(session.user.id);
  if (!Number.isFinite(userId)) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  let body: { currentPassword?: unknown; newPassword?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }
  const currentPassword = String(body.currentPassword ?? "");
  const newPassword = String(body.newPassword ?? "");
  if (newPassword.length < MIN_LEN) {
    return NextResponse.json(
      { error: `Password must be at least ${MIN_LEN} characters.` },
      { status: 400 },
    );
  }
  if (newPassword === currentPassword) {
    return NextResponse.json(
      { error: "New password must differ from the current one." },
      { status: 400 },
    );
  }

  const user = findUserById(userId);
  if (!user || user.source !== "local" || !user.password_hash) {
    return NextResponse.json(
      { error: "This account does not use a local password." },
      { status: 400 },
    );
  }

  try {
    const ok = await argon2.verify(user.password_hash, currentPassword);
    if (!ok) {
      return NextResponse.json(
        { error: "Current password is incorrect." },
        { status: 400 },
      );
    }
  } catch {
    return NextResponse.json(
      { error: "Current password is incorrect." },
      { status: 400 },
    );
  }

  const newHash = await argon2.hash(newPassword, { type: argon2.argon2id });
  setUserPassword(userId, newHash, false);

  appendAudit({
    actorId: userId,
    actorLabel: user.username,
    action: "user.self_password_change",
    target: `user:${userId}`,
  });

  return NextResponse.json({ ok: true });
}
