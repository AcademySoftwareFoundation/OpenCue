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

import "server-only";

import { getDb } from "./index";
import type { GroupRow, RoleRow, Source, UserRow } from "./types";

// -- Transaction helper -------------------------------------------------

/**
 * Run a synchronous callback inside a single SQLite transaction. Any
 * throw inside `fn` rolls every write made in `fn` back. Use this when
 * a route handler needs to batch a mutation and its audit log row so
 * the two cannot diverge if the audit insert fails.
 *
 * Example:
 *   runInTransaction(() => {
 *     deleteGroup(groupId);
 *     appendAudit({ ... });
 *   });
 */
export function runInTransaction<T>(fn: () => T): T {
  return getDb().transaction(fn)();
}

// -- Users --------------------------------------------------------------

export function findUserByExternalId(externalId: string): UserRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM users WHERE external_id = ?")
      .get(externalId) as UserRow | undefined) ?? null
  );
}

export function findUserByUsername(username: string): UserRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM users WHERE username = ?")
      .get(username) as UserRow | undefined) ?? null
  );
}

export function findUserByEmail(email: string): UserRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM users WHERE email = ?")
      .get(email) as UserRow | undefined) ?? null
  );
}

export function findUserById(id: number): UserRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM users WHERE id = ?")
      .get(id) as UserRow | undefined) ?? null
  );
}

export type UpsertUserInput = {
  externalId: string;
  username: string;
  email?: string | null;
  displayName?: string | null;
  source: Source;
  passwordHash?: string | null;
  mustChangePassword?: boolean;
};

/**
 * Inserts a user if one with this external_id does not exist, otherwise
 * updates the mutable fields. Returns the row's id either way.
 */
export function upsertUser(input: UpsertUserInput): number {
  // Single-statement upsert via SQLite's ON CONFLICT clause. Avoids the
  // check-then-insert race where two concurrent sign-ins for the same
  // external_id both miss the existing row and then one of them fails
  // the UNIQUE constraint on insert. password_hash and
  // must_change_password are intentionally left untouched on update so
  // resolver sign-ins for an existing local user (rare, but possible
  // via the Admin UI) cannot wipe the locally-managed password.
  const db = getDb();
  db.prepare(
    `INSERT INTO users
       (external_id, username, email, display_name, source,
        password_hash, must_change_password)
     VALUES
       (@externalId, @username, @email, @displayName, @source,
        @passwordHash, @mustChangePassword)
     ON CONFLICT(external_id) DO UPDATE SET
       username     = excluded.username,
       email        = excluded.email,
       display_name = excluded.display_name,
       source       = excluded.source,
       updated_at   = strftime('%s','now')`,
  ).run({
    externalId: input.externalId,
    username: input.username,
    email: input.email ?? null,
    displayName: input.displayName ?? null,
    source: input.source,
    passwordHash: input.passwordHash ?? null,
    mustChangePassword: input.mustChangePassword ? 1 : 0,
  });
  const row = db
    .prepare("SELECT id FROM users WHERE external_id = ?")
    .get(input.externalId) as { id: number };
  return row.id;
}

export function setUserPassword(
  userId: number,
  passwordHash: string,
  mustChangePassword: boolean,
): void {
  getDb()
    .prepare(
      `UPDATE users
          SET password_hash        = ?,
              must_change_password = ?,
              updated_at           = strftime('%s','now')
        WHERE id = ?`,
    )
    .run(passwordHash, mustChangePassword ? 1 : 0, userId);
}

export function markUserLoggedIn(userId: number): void {
  getDb()
    .prepare("UPDATE users SET last_login_at = strftime('%s','now') WHERE id = ?")
    .run(userId);
}

export function setUserActive(userId: number, active: boolean): void {
  getDb()
    .prepare(
      "UPDATE users SET active = ?, updated_at = strftime('%s','now') WHERE id = ?",
    )
    .run(active ? 1 : 0, userId);
}

export function listUsers(opts?: { search?: string }): UserRow[] {
  const search = opts?.search?.trim() ?? "";
  if (search.length === 0) {
    return getDb()
      .prepare("SELECT * FROM users ORDER BY username")
      .all() as UserRow[];
  }
  const like = `%${search}%`;
  return getDb()
    .prepare(
      `SELECT * FROM users
        WHERE username     LIKE ?
           OR email        LIKE ?
           OR display_name LIKE ?
        ORDER BY username`,
    )
    .all(like, like, like) as UserRow[];
}

// -- Groups -------------------------------------------------------------

export function findGroupByName(name: string): GroupRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM groups WHERE name = ?")
      .get(name) as GroupRow | undefined) ?? null
  );
}

export function findGroupById(id: number): GroupRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM groups WHERE id = ?")
      .get(id) as GroupRow | undefined) ?? null
  );
}

export function upsertGroup(input: {
  name: string;
  source: Source;
  description?: string | null;
}): number {
  const db = getDb();
  const existing = findGroupByName(input.name);
  if (existing) {
    db.prepare(
      `UPDATE groups
          SET description = @description,
              source      = @source,
              updated_at  = strftime('%s','now')
        WHERE id = @id`,
    ).run({
      id: existing.id,
      description: input.description ?? null,
      source: input.source,
    });
    return existing.id;
  }
  const info = db
    .prepare(
      `INSERT INTO groups (name, description, source)
       VALUES (@name, @description, @source)`,
    )
    .run({
      name: input.name,
      description: input.description ?? null,
      source: input.source,
    });
  return Number(info.lastInsertRowid);
}

export function deleteGroup(id: number): void {
  getDb().prepare("DELETE FROM groups WHERE id = ?").run(id);
}

export function listGroups(): GroupRow[] {
  return getDb().prepare("SELECT * FROM groups ORDER BY name").all() as GroupRow[];
}

// Sync membership for a single user. Inserts any (user_id, group_id)
// pairs that aren't already present and removes pairs of the given
// `source` that are no longer in the resolver's response.
export function syncUserGroupMembership(
  userId: number,
  groupIds: ReadonlyArray<number>,
  source: Source,
): void {
  const db = getDb();
  const sync = db.transaction(() => {
    db.prepare(
      "DELETE FROM user_groups WHERE user_id = ? AND source = ?",
    ).run(userId, source);
    const insert = db.prepare(
      "INSERT OR IGNORE INTO user_groups (user_id, group_id, source) VALUES (?, ?, ?)",
    );
    for (const gid of groupIds) insert.run(userId, gid, source);
  });
  sync();
}

export function listGroupsForUser(userId: number): GroupRow[] {
  return getDb()
    .prepare(
      `SELECT g.* FROM groups g
         JOIN user_groups ug ON ug.group_id = g.id
        WHERE ug.user_id = ?
        ORDER BY g.name`,
    )
    .all(userId) as GroupRow[];
}

// -- Roles --------------------------------------------------------------

export function findRoleByName(name: string): RoleRow | null {
  return (
    (getDb()
      .prepare("SELECT * FROM roles WHERE name = ?")
      .get(name) as RoleRow | undefined) ?? null
  );
}

export function listRoles(): RoleRow[] {
  return getDb()
    .prepare("SELECT * FROM roles ORDER BY builtin DESC, name")
    .all() as RoleRow[];
}

export function listPermissionsForRole(roleId: number): string[] {
  return (
    getDb()
      .prepare(
        "SELECT permission FROM role_permissions WHERE role_id = ? ORDER BY permission",
      )
      .all(roleId) as Array<{ permission: string }>
  ).map((r) => r.permission);
}

export function createRole(input: {
  name: string;
  description?: string | null;
  permissions: ReadonlyArray<string>;
}): number {
  const db = getDb();
  const create = db.transaction(() => {
    const info = db
      .prepare(
        `INSERT INTO roles (name, description, builtin)
         VALUES (@name, @description, 0)`,
      )
      .run({ name: input.name, description: input.description ?? null });
    const roleId = Number(info.lastInsertRowid);
    const insertPerm = db.prepare(
      "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
    );
    for (const p of input.permissions) insertPerm.run(roleId, p);
    return roleId;
  });
  return create();
}

export function updateRolePermissions(
  roleId: number,
  permissions: ReadonlyArray<string>,
): void {
  const db = getDb();
  const update = db.transaction(() => {
    db.prepare("DELETE FROM role_permissions WHERE role_id = ?").run(roleId);
    const insert = db.prepare(
      "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
    );
    for (const p of permissions) insert.run(roleId, p);
    db.prepare(
      "UPDATE roles SET updated_at = strftime('%s','now') WHERE id = ?",
    ).run(roleId);
  });
  update();
}

export function deleteRole(roleId: number): void {
  getDb()
    .prepare("DELETE FROM roles WHERE id = ? AND builtin = 0")
    .run(roleId);
}

// -- Group role attachments --------------------------------------------

export function attachRoleToGroup(groupId: number, roleId: number): void {
  getDb()
    .prepare(
      "INSERT OR IGNORE INTO group_roles (group_id, role_id) VALUES (?, ?)",
    )
    .run(groupId, roleId);
}

export function detachRoleFromGroup(groupId: number, roleId: number): void {
  getDb()
    .prepare("DELETE FROM group_roles WHERE group_id = ? AND role_id = ?")
    .run(groupId, roleId);
}

export function listRolesForGroup(groupId: number): RoleRow[] {
  return getDb()
    .prepare(
      `SELECT r.* FROM roles r
         JOIN group_roles gr ON gr.role_id = r.id
        WHERE gr.group_id = ?
        ORDER BY r.name`,
    )
    .all(groupId) as RoleRow[];
}

// -- User direct role attachments --------------------------------------

export function attachRoleToUser(userId: number, roleId: number): void {
  getDb()
    .prepare(
      "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
    )
    .run(userId, roleId);
}

export function detachRoleFromUser(userId: number, roleId: number): void {
  getDb()
    .prepare("DELETE FROM user_roles WHERE user_id = ? AND role_id = ?")
    .run(userId, roleId);
}

export function listDirectRolesForUser(userId: number): RoleRow[] {
  return getDb()
    .prepare(
      `SELECT r.* FROM roles r
         JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = ?
        ORDER BY r.name`,
    )
    .all(userId) as RoleRow[];
}

// -- Effective roles + permissions (group + direct) --------------------

export function listEffectiveRolesForUser(userId: number): RoleRow[] {
  return getDb()
    .prepare(
      `SELECT DISTINCT r.* FROM roles r
         LEFT JOIN user_roles ur  ON ur.role_id = r.id AND ur.user_id = ?
         LEFT JOIN group_roles gr ON gr.role_id = r.id
         LEFT JOIN user_groups ug ON ug.group_id = gr.group_id AND ug.user_id = ?
        WHERE ur.user_id IS NOT NULL OR ug.user_id IS NOT NULL
        ORDER BY r.name`,
    )
    .all(userId, userId) as RoleRow[];
}

export function listEffectivePermissionsForUser(userId: number): string[] {
  return (
    getDb()
      .prepare(
        `SELECT DISTINCT rp.permission
           FROM role_permissions rp
           JOIN roles r ON r.id = rp.role_id
           LEFT JOIN user_roles ur  ON ur.role_id = r.id AND ur.user_id = ?
           LEFT JOIN group_roles gr ON gr.role_id = r.id
           LEFT JOIN user_groups ug ON ug.group_id = gr.group_id AND ug.user_id = ?
          WHERE ur.user_id IS NOT NULL OR ug.user_id IS NOT NULL`,
      )
      .all(userId, userId) as Array<{ permission: string }>
  ).map((r) => r.permission);
}

// -- Admins -------------------------------------------------------------

export function isAdmin(userId: number): boolean {
  const row = getDb()
    .prepare("SELECT 1 AS x FROM admins WHERE user_id = ?")
    .get(userId);
  return !!row;
}

export function addAdmin(userId: number): void {
  getDb()
    .prepare("INSERT OR IGNORE INTO admins (user_id) VALUES (?)")
    .run(userId);
}

export function removeAdmin(userId: number): void {
  getDb().prepare("DELETE FROM admins WHERE user_id = ?").run(userId);
}

export function listAdminUserIds(): number[] {
  return (
    getDb()
      .prepare("SELECT user_id FROM admins ORDER BY user_id")
      .all() as Array<{ user_id: number }>
  ).map((r) => r.user_id);
}

export function adminCount(): number {
  const row = getDb()
    .prepare("SELECT COUNT(*) AS n FROM admins")
    .get() as { n: number };
  return row.n;
}

// -- Audit log ----------------------------------------------------------

// Defensive JSON serializer for audit payloads. The inputs are `unknown`
// and may - through caller bugs - contain circular references, BigInts,
// or other values that crash JSON.stringify. We never want an audit
// insert to fail the underlying mutation it is recording, so fall back
// to a sentinel string on serialization errors and let the operator see
// the bad payload later via the Audit log tab.
function safeAuditJson(value: unknown): string | null {
  if (value === undefined) return null;
  try {
    return JSON.stringify(value);
  } catch (err) {
    return JSON.stringify({
      error: "unserializable_audit_payload",
      reason: err instanceof Error ? err.message : String(err),
    });
  }
}

export function appendAudit(input: {
  actorId: number | null;
  actorLabel: string;
  action: string;
  target?: string | null;
  before?: unknown;
  after?: unknown;
}): void {
  getDb()
    .prepare(
      `INSERT INTO audit_log
         (actor_id, actor_label, action, target, before_json, after_json)
       VALUES
         (@actorId, @actorLabel, @action, @target, @before, @after)`,
    )
    .run({
      actorId: input.actorId,
      actorLabel: input.actorLabel,
      action: input.action,
      target: input.target ?? null,
      before: safeAuditJson(input.before),
      after: safeAuditJson(input.after),
    });
}
