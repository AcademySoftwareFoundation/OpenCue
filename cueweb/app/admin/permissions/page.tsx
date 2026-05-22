/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { PERMISSION_CATALOG } from "@/lib/rbac/permissions";

export const dynamic = "force-dynamic";

// Read-only catalog of every known permission string. Rendered on the
// server so it stays in sync with the source code without a round-trip.
export default function PermissionsPage() {
  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-foreground/5">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
              Permission
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          {PERMISSION_CATALOG.map((p) => (
            <tr key={p.key} className="border-t">
              <td className="px-3 py-2 align-top">
                <code className="text-xs">{p.key}</code>
              </td>
              <td className="px-3 py-2 align-top text-foreground/80">
                {p.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
