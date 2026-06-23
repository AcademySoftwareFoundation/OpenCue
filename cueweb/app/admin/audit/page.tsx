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
import { redirect } from "next/navigation";

import { authOptions } from "@/lib/auth";
import { getUserGroups, isEffectiveAdmin, isGateActive } from "@/lib/authz";
import { auditStorePath, readAudit, readAuditFacets } from "@/lib/audit-store";
import { AuditTable } from "./audit-table";

// The audit trail is runtime state; never statically cache this page.
export const dynamic = "force-dynamic";

/**
 * Admin -> CueWeb Audit — the web audit system. Shows who performed which
 * action, when, against which target, and whether it succeeded, across every
 * state-changing CueWeb operation (captured at the gateway chokepoint, see
 * lib/audit.ts) plus sign-in/out events.
 *
 * Access control: admin-only. The middleware gates `/admin/*` behind
 * CUEWEB_ADMIN_GROUPS when the authz gate is active; this server component
 * re-checks the same decision (defense in depth). When no group-based
 * authorization is configured (gate inactive), the page is visible to everyone
 * — matching CueWeb's default open behavior.
 */
export default async function CueWebAuditPage() {
  if (isGateActive()) {
    const session = await getServerSession(authOptions).catch(() => null);
    const groups = getUserGroups(session as { groups?: unknown } | null);
    if (!session?.user || !isEffectiveAdmin(groups)) {
      redirect("/unauthorized");
    }
  }

  const initial = await readAudit({ limit: 100 });
  const facets = await readAuditFacets();
  const storePath = auditStorePath();

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-xl font-semibold">CueWeb Audit</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Audit trail of every state-changing action performed through CueWeb —
          who did it, when, the target, the Cuebot facility, and the outcome —
          plus sign-in/out events. Read-only views are not recorded.
        </p>
      </header>

      <AuditTable
        initialRecords={initial.records}
        initialTotal={initial.total}
        facets={facets}
      />

      <p className="mt-6 text-[11px] text-muted-foreground">
        Trail stored at <code className="font-mono">{storePath}</code>. Configure
        the location with <code className="font-mono">CUEWEB_AUDIT_STORE</code>{" "}
        (mount a volume to persist across restarts).
      </p>
    </div>
  );
}
