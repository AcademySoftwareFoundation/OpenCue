/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextRequest, NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import { getDb } from "@/lib/rbac/db";
import type { AuditLogRow } from "@/lib/rbac/db/types";

export const runtime = "nodejs";

const DEFAULT_LIMIT = 100;
const MAX_LIMIT = 500;

export async function GET(req: NextRequest) {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;

  const sp = req.nextUrl.searchParams;
  const limit = Math.min(
    MAX_LIMIT,
    Math.max(1, Number(sp.get("limit") ?? DEFAULT_LIMIT) || DEFAULT_LIMIT),
  );
  const before = Number(sp.get("beforeId") ?? "0") || 0;
  const action = sp.get("action") ?? "";
  const actor = sp.get("actor") ?? "";

  const clauses: string[] = [];
  const args: any[] = [];
  if (before > 0) {
    clauses.push("id < ?");
    args.push(before);
  }
  if (action) {
    clauses.push("action = ?");
    args.push(action);
  }
  if (actor) {
    clauses.push("actor_label LIKE ?");
    args.push(`%${actor}%`);
  }
  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const sql = `SELECT * FROM audit_log ${where} ORDER BY id DESC LIMIT ?`;
  args.push(limit);
  const rows = getDb().prepare(sql).all(...args) as AuditLogRow[];
  return NextResponse.json({ entries: rows });
}
