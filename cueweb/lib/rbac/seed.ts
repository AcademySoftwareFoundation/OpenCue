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
import type Database from "better-sqlite3";

import { BUILTIN_ROLE_SEEDS } from "./roles";

/**
 * Idempotently upserts the built-in roles and their permission sets.
 * Runs after migrations on every process start so that adding a new
 * permission to a built-in role in code is reflected in the DB on the
 * next start without any manual migration.
 *
 * Custom roles created via the Admin UI are untouched.
 */
export function seedBuiltinRoles(db: Database.Database): void {
  const upsertRole = db.prepare(`
    INSERT INTO roles (name, description, builtin)
    VALUES (?, ?, 1)
    ON CONFLICT(name) DO UPDATE SET
      description = excluded.description,
      builtin     = 1,
      updated_at  = strftime('%s','now')
  `);
  const selectRoleId = db.prepare(
    "SELECT id FROM roles WHERE name = @name",
  );
  const deletePerms = db.prepare(
    "DELETE FROM role_permissions WHERE role_id = ?",
  );
  const insertPerm = db.prepare(
    "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
  );

  const seed = db.transaction(() => {
    for (const role of BUILTIN_ROLE_SEEDS) {
      upsertRole.run(role.name, role.description);
      const row = selectRoleId.get({ name: role.name }) as
        | { id: number }
        | undefined;
      if (!row) continue;
      deletePerms.run(row.id);
      for (const perm of role.permissions) {
        insertPerm.run(row.id, perm);
      }
    }
  });
  seed();
}
