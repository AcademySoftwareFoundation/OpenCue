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

import type Database from "better-sqlite3";

import { MIGRATIONS } from "./migrations_data";

/**
 * Applies any inlined migrations from `migrations_data.ts` that haven't
 * already been recorded in `schema_migrations`. Migrations run in array
 * order and each runs inside its own transaction so a partial failure
 * rolls back cleanly. Forward-only; reversals are new forward migrations.
 *
 * The SQL is bundled as TypeScript constants rather than read from
 * `*.sql` sidecars so Next.js's standalone build output ships it
 * without needing custom `outputFileTracingIncludes` config.
 */
export function runMigrations(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename    TEXT    PRIMARY KEY,
      applied_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    );
  `);

  const applied = new Set<string>(
    (
      db
        .prepare("SELECT filename FROM schema_migrations")
        .all() as Array<{ filename: string }>
    ).map((r) => r.filename),
  );

  const recordStmt = db.prepare(
    "INSERT INTO schema_migrations (filename) VALUES (?)",
  );

  for (const migration of MIGRATIONS) {
    if (applied.has(migration.filename)) continue;
    const apply = db.transaction(() => {
      db.exec(migration.sql);
      recordStmt.run(migration.filename);
    });
    apply();
  }
}
