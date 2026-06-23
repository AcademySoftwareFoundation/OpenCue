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

import { getServerSession } from "next-auth";
import { NextRequest, NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { getUserGroups, isEffectiveAdmin, isGateActive } from "@/lib/authz";
import { readAudit, readAuditFacets, type AuditResult } from "@/lib/audit-store";

// Always read the live trail (this route reflects runtime state).
export const dynamic = "force-dynamic";

/**
 * Read API backing the Admin -> CueWeb Audit page. Returns the audit trail
 * (newest first) with optional filtering + pagination, plus filter facets.
 *
 * Access: the middleware already gates `/api/admin/*` behind CUEWEB_ADMIN_GROUPS
 * when the authz gate is active; this handler additionally enforces the same
 * decision in case the gate is active but the matcher is ever bypassed. When
 * the gate is inactive the data is open (matching the rest of CueWeb's
 * no-auth/sandbox behavior and the "show to everyone" requirement).
 */
export async function GET(request: NextRequest) {
  if (isGateActive()) {
    const session = await getServerSession(authOptions).catch(() => null);
    const groups = getUserGroups(session as { groups?: unknown } | null);
    if (!session?.user || !isEffectiveAdmin(groups)) {
      return NextResponse.json(
        { error: "You are not authorized to view the CueWeb audit trail." },
        { status: 403 },
      );
    }
  }

  const sp = request.nextUrl.searchParams;
  const num = (key: string): number | undefined => {
    const v = Number(sp.get(key));
    return Number.isFinite(v) ? v : undefined;
  };
  const str = (key: string): string | undefined => {
    const v = sp.get(key);
    return v && v.trim() ? v.trim() : undefined;
  };

  const result = str("result");
  const page = await readAudit({
    limit: num("limit"),
    offset: num("offset"),
    actor: str("actor"),
    category: str("category"),
    result: result === "success" || result === "error" ? (result as AuditResult) : undefined,
    since: str("since"),
    until: str("until"),
    search: str("search"),
  });

  const facets = await readAuditFacets();

  return NextResponse.json({ ...page, facets });
}
