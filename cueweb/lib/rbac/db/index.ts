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

// Server-only: better-sqlite3 is a native module. Importing this file
// from a client component would fail at build time, which is the point.
import "server-only";

import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

import { runMigrations } from "./migrations";
import { seedBuiltinRoles } from "../seed";

// Default DB location. Override with CUEWEB_RBAC_DB to point at a
// different path (e.g. an in-memory ":memory:" DB in tests).
const DEFAULT_DB_PATH = "/data/cueweb-rbac.db";

let _db: Database.Database | null = null;
let _initialized = false;

function resolveDbPath(): string {
  const override = process.env.CUEWEB_RBAC_DB;
  if (override && override.length > 0) return override;
  return DEFAULT_DB_PATH;
}

function ensureParentDir(filePath: string) {
  if (filePath === ":memory:") return;
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

/**
 * Returns the process-wide better-sqlite3 handle. Lazy-creates the DB,
 * runs forward migrations, and seeds built-in roles on first call. All
 * other RBAC modules should obtain the handle through this function so
 * the initialization only happens once per process.
 */
export function getDb(): Database.Database {
  // Only return a cached handle if it has finished initialization;
  // otherwise a failure in migrations or seeding on the first call
  // would leave subsequent callers with a half-built DB.
  if (_db && _initialized) return _db;

  const dbPath = resolveDbPath();
  ensureParentDir(dbPath);

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.pragma("synchronous = NORMAL");

  try {
    runMigrations(db);
    seedBuiltinRoles(db);
    _initialized = true;
    _db = db;
  } catch (err) {
    try {
      db.close();
    } catch {
      // ignore - the bad handle is being discarded anyway
    }
    _db = null;
    _initialized = false;
    throw err;
  }

  return db;
}

/**
 * Test-only: close the current DB handle and clear the cached state.
 * Production code never calls this; the DB lives for the process
 * lifetime.
 */
export function _resetForTests(): void {
  if (_db) {
    try {
      _db.close();
    } catch {
      // ignore
    }
  }
  _db = null;
  _initialized = false;
}
