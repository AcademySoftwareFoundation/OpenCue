/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

process.env.CUEWEB_RBAC_DB = ":memory:";
process.env.CUEWEB_GROUPS_RESOLVER = "okta";

import { _resetForTests } from "@/lib/rbac/db";
import { resolveAndPersist } from "@/lib/rbac/resolvers";
import {
  attachRoleToUser,
  findRoleByName,
  listEffectiveRolesForUser,
  listGroupsForUser,
} from "@/lib/rbac/db/dal";
import { BUILTIN_ROLES } from "@/lib/rbac/roles";

beforeEach(() => {
  _resetForTests();
});

describe("Okta resolver", () => {
  test("upserts user, syncs groups, and survives membership churn", async () => {
    const first = await resolveAndPersist({
      profile: {
        sub: "okta-sub-1",
        email: "alice@example.test",
        name: "Alice",
        preferred_username: "alice",
        groups: ["gr-render-operators", "gr-render-viewers"],
      },
      account: { provider: "okta", providerAccountId: "okta-sub-1" },
      user: null,
      token: null,
    });
    expect(first).not.toBeNull();
    const userId = first!.userId;
    expect(listGroupsForUser(userId).map((g) => g.name).sort()).toEqual([
      "gr-render-operators",
      "gr-render-viewers",
    ]);

    // Promote with a direct role grant.
    const adminRole = findRoleByName(BUILTIN_ROLES.SITE_ADMIN)!;
    attachRoleToUser(userId, adminRole.id);

    // Second sign-in: Okta now reports a different group set.
    const second = await resolveAndPersist({
      profile: {
        sub: "okta-sub-1",
        email: "alice@example.test",
        name: "Alice",
        preferred_username: "alice",
        groups: ["gr-render-leads"],
      },
      account: { provider: "okta", providerAccountId: "okta-sub-1" },
      user: null,
      token: null,
    });
    expect(second!.userId).toBe(userId);
    expect(listGroupsForUser(userId).map((g) => g.name)).toEqual([
      "gr-render-leads",
    ]);

    // Direct role grant must survive the sync.
    const roles = listEffectiveRolesForUser(userId).map((r) => r.name);
    expect(roles).toContain(BUILTIN_ROLES.SITE_ADMIN);
  });

  test("returns null when sub is missing", async () => {
    const result = await resolveAndPersist({
      profile: { email: "noone@example.test", groups: [] },
      account: { provider: "okta" },
      user: null,
      token: null,
    });
    expect(result).toBeNull();
  });
});
