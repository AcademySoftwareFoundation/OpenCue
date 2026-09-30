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

import { getFacilityConfigViews } from "@/lib/facility-server";
import { facilityStorePath, readFacilityAudit } from "@/lib/facility-store";
import { FacilitiesForm } from "./facilities-form";

// Always reflect the current store + audit log (this page reads runtime state).
export const dynamic = "force-dynamic";

/**
 * Admin settings screen for per-facility connection config (J2). Lets an
 * operator edit each facility's REST gateway URL and JWT secret at runtime —
 * persisted to the facility override store, applied without a redeploy — and
 * shows an audit trail of changes.
 *
 * NOTE: when group authorization ships in a deployment (lib/authz.ts /
 * middleware.ts), add `/settings/facilities` to the admin-only paths so this
 * screen is restricted to CUEWEB_ADMIN_GROUPS.
 */
export default async function FacilitiesSettingsPage() {
  const facilities = await getFacilityConfigViews();
  const audit = await readFacilityAudit();
  const storePath = facilityStorePath();

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-xl font-semibold">Cuebot Facilities</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Edit each facility&apos;s REST gateway URL and JWT secret. Changes apply
          immediately (no redeploy) and override the environment defaults. A
          green/red dot in the header <span className="font-medium">Cuebot Facility</span>{" "}
          menu reflects each facility&apos;s live connection health.
        </p>
      </header>

      <FacilitiesForm facilities={facilities} />

      <section className="mt-8">
        <h2 className="mb-2 text-sm font-semibold">Change history</h2>
        {audit.length === 0 ? (
          <p className="text-xs text-muted-foreground">No facility changes recorded yet.</p>
        ) : (
          <div className="overflow-hidden rounded-md border border-border">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 text-muted-foreground">
                <tr>
                  <th className="px-3 py-1.5 font-medium">When</th>
                  <th className="px-3 py-1.5 font-medium">Who</th>
                  <th className="px-3 py-1.5 font-medium">Facility</th>
                  <th className="px-3 py-1.5 font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((e, i) => (
                  <tr key={`${e.at}-${i}`} className="border-t border-border">
                    <td className="px-3 py-1.5 text-muted-foreground">
                      {new Date(e.at).toLocaleString()}
                    </td>
                    <td className="px-3 py-1.5">{e.actor}</td>
                    <td className="px-3 py-1.5 font-medium uppercase">{e.facility}</td>
                    <td className="px-3 py-1.5">{e.changes.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="mt-6 text-[11px] text-muted-foreground">
        Overrides are stored at <code>{storePath}</code>. Point{" "}
        <code>CUEWEB_FACILITY_STORE</code> at a mounted volume to persist them
        across container restarts.
      </p>
    </div>
  );
}
