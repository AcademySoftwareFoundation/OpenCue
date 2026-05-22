/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

// Force the RBAC store to an in-memory SQLite DB for every test so
// nothing leaks between cases.
process.env.CUEWEB_RBAC_DB = ":memory:";

import { _resetForTests, getDb } from "@/lib/rbac/db";
import {
  addAdmin,
  adminCount,
  attachRoleToGroup,
  attachRoleToUser,
  detachRoleFromUser,
  findRoleByName,
  findUserByExternalId,
  isAdmin,
  listEffectivePermissionsForUser,
  listEffectiveRolesForUser,
  listGroupsForUser,
  listRoles,
  syncUserGroupMembership,
  upsertGroup,
  upsertUser,
} from "@/lib/rbac/db/dal";
import { BUILTIN_ROLES } from "@/lib/rbac/roles";
import { hasPermission, PERMISSIONS } from "@/lib/rbac/permissions";

beforeEach(() => {
  _resetForTests();
});

afterAll(() => {
  _resetForTests();
});

describe("RBAC store", () => {
  test("migrations run idempotently and seed built-in roles", () => {
    getDb(); // first call runs migrations + seed
    const rolesA = listRoles();
    expect(rolesA.map((r) => r.name)).toEqual(
      expect.arrayContaining([
        BUILTIN_ROLES.SITE_ADMIN,
        BUILTIN_ROLES.OPERATOR,
        BUILTIN_ROLES.VIEWER,
      ]),
    );
    // Second migrations call must not throw or duplicate rows.
    getDb();
    const rolesB = listRoles();
    expect(rolesB.length).toBe(rolesA.length);
  });

  test("site-admin role holds the wildcard permission", () => {
    getDb();
    const siteAdmin = findRoleByName(BUILTIN_ROLES.SITE_ADMIN);
    expect(siteAdmin).not.toBeNull();
    const perms = getDb()
      .prepare("SELECT permission FROM role_permissions WHERE role_id = ?")
      .all(siteAdmin!.id)
      .map((r: any) => r.permission);
    expect(perms).toContain(PERMISSIONS.WILDCARD);
  });

  test("effective permissions combine group and direct role grants", () => {
    getDb();
    const userId = upsertUser({
      externalId: "okta:abc",
      username: "alice",
      email: "alice@example.test",
      displayName: "Alice",
      source: "okta",
    });
    const operatorRole = findRoleByName(BUILTIN_ROLES.OPERATOR)!;
    const viewerRole = findRoleByName(BUILTIN_ROLES.VIEWER)!;
    const groupId = upsertGroup({ name: "gr-render-operators", source: "okta" });
    attachRoleToGroup(groupId, operatorRole.id);
    syncUserGroupMembership(userId, [groupId], "okta");
    attachRoleToUser(userId, viewerRole.id);

    const effectiveRoles = listEffectiveRolesForUser(userId).map((r) => r.name);
    expect(effectiveRoles).toEqual(
      expect.arrayContaining([BUILTIN_ROLES.OPERATOR, BUILTIN_ROLES.VIEWER]),
    );
    const effectivePerms = listEffectivePermissionsForUser(userId);
    expect(effectivePerms).toEqual(
      expect.arrayContaining([
        PERMISSIONS.JOBS_VIEW,
        PERMISSIONS.JOBS_KILL,
        PERMISSIONS.CUECOMMANDER_OPEN,
      ]),
    );
  });

  test("group sync preserves direct user_roles", () => {
    getDb();
    const userId = upsertUser({
      externalId: "okta:bob",
      username: "bob",
      source: "okta",
    });
    const adminRole = findRoleByName(BUILTIN_ROLES.SITE_ADMIN)!;
    attachRoleToUser(userId, adminRole.id);
    const groupA = upsertGroup({ name: "gr-render-leads", source: "okta" });
    syncUserGroupMembership(userId, [groupA], "okta");
    // Re-sync with a different membership list - direct grant must survive.
    const groupB = upsertGroup({ name: "gr-render-viewers", source: "okta" });
    syncUserGroupMembership(userId, [groupB], "okta");

    const roles = listEffectiveRolesForUser(userId).map((r) => r.name);
    expect(roles).toContain(BUILTIN_ROLES.SITE_ADMIN);
    const memberships = listGroupsForUser(userId).map((g) => g.name);
    expect(memberships).toEqual(["gr-render-viewers"]);
  });

  test("detaching a role removes its grants", () => {
    getDb();
    const userId = upsertUser({
      externalId: "local:carol",
      username: "carol",
      source: "local",
    });
    const operator = findRoleByName(BUILTIN_ROLES.OPERATOR)!;
    attachRoleToUser(userId, operator.id);
    expect(listEffectiveRolesForUser(userId).map((r) => r.name)).toContain(
      BUILTIN_ROLES.OPERATOR,
    );
    detachRoleFromUser(userId, operator.id);
    expect(listEffectiveRolesForUser(userId).map((r) => r.name)).not.toContain(
      BUILTIN_ROLES.OPERATOR,
    );
  });

  test("admin add/remove + adminCount + isAdmin", () => {
    getDb();
    const userId = upsertUser({
      externalId: "local:dave",
      username: "dave",
      source: "local",
    });
    expect(isAdmin(userId)).toBe(false);
    expect(adminCount()).toBe(0);
    addAdmin(userId);
    expect(isAdmin(userId)).toBe(true);
    expect(adminCount()).toBe(1);
  });

  test("hasPermission honours the wildcard", () => {
    expect(hasPermission(["*"], "anything.you.want")).toBe(true);
    expect(hasPermission(["jobs.view"], "jobs.kill")).toBe(false);
    expect(hasPermission(["jobs.view", "jobs.kill"], "jobs.kill")).toBe(true);
  });

  test("upsertUser updates existing rows", () => {
    getDb();
    const a = upsertUser({
      externalId: "okta:eve",
      username: "eve",
      source: "okta",
      displayName: "Eve",
    });
    const b = upsertUser({
      externalId: "okta:eve",
      username: "eve.new",
      source: "okta",
      displayName: "Eve Renamed",
    });
    expect(a).toBe(b);
    const fresh = findUserByExternalId("okta:eve");
    expect(fresh?.username).toBe("eve.new");
    expect(fresh?.display_name).toBe("Eve Renamed");
  });
});
