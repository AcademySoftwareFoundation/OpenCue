/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { adminCount, listGroups, listRoles, listUsers } from "@/lib/rbac/db/dal";

export const dynamic = "force-dynamic";

export default function AdminOverviewPage() {
  // These DB calls run server-side at request time. The middleware has
  // already gated /admin/* on the `admins` flag.
  const totalUsers = listUsers().length;
  const totalGroups = listGroups().length;
  const totalRoles = listRoles().length;
  const totalAdmins = adminCount();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <Stat label="Users" value={totalUsers} />
      <Stat label="Groups" value={totalGroups} />
      <Stat label="Roles" value={totalRoles} />
      <Stat label="Admins" value={totalAdmins} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-card p-4">
      <div className="text-sm text-foreground/70">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
