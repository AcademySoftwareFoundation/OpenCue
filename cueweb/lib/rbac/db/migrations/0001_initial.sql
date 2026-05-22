-- Copyright Contributors to the OpenCue Project
-- SPDX-License-Identifier: Apache-2.0

PRAGMA foreign_keys = ON;

-- A signed-in user. `source` tells the Admin UI whether the row was
-- created locally (admin UI / bootstrap), came from Okta, came from
-- LDAP, or was imported from a legacy YAML policy.
CREATE TABLE IF NOT EXISTS users (
  id                     INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id            TEXT    NOT NULL UNIQUE,         -- Okta sub, LDAP DN, or "local:<name>"
  username               TEXT    NOT NULL UNIQUE,
  email                  TEXT,
  display_name           TEXT,
  source                 TEXT    NOT NULL CHECK (source IN ('local', 'okta', 'ldap', 'imported')),
  active                 INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  password_hash          TEXT,                            -- only set for source='local'
  must_change_password   INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
  created_at             INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  updated_at             INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  last_login_at          INTEGER
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_source ON users(source);

-- A directory group (Okta group, LDAP group, or a local group created
-- in the Admin UI).
CREATE TABLE IF NOT EXISTS groups (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT    NOT NULL UNIQUE,
  description  TEXT,
  source       TEXT    NOT NULL CHECK (source IN ('local', 'okta', 'ldap', 'imported')),
  created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  updated_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_groups_source ON groups(source);

-- Group membership. `source` records who put the user in the group:
-- a resolver sync, a local admin, etc.
CREATE TABLE IF NOT EXISTS user_groups (
  user_id     INTEGER NOT NULL,
  group_id    INTEGER NOT NULL,
  source      TEXT    NOT NULL CHECK (source IN ('local', 'okta', 'ldap', 'imported')),
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  PRIMARY KEY (user_id, group_id),
  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_groups_group_id ON user_groups(group_id);

-- A role (built-in or custom). Built-in rows have `builtin=1` and are
-- protected from deletion by the API layer.
CREATE TABLE IF NOT EXISTS roles (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT    NOT NULL UNIQUE,
  description  TEXT,
  builtin      INTEGER NOT NULL DEFAULT 0 CHECK (builtin IN (0, 1)),
  created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  updated_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- Many-to-many: each role holds a set of permission strings.
CREATE TABLE IF NOT EXISTS role_permissions (
  role_id     INTEGER NOT NULL,
  permission  TEXT    NOT NULL,
  PRIMARY KEY (role_id, permission),
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Groups grant roles to all members.
CREATE TABLE IF NOT EXISTS group_roles (
  group_id    INTEGER NOT NULL,
  role_id     INTEGER NOT NULL,
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  PRIMARY KEY (group_id, role_id),
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id)  REFERENCES roles(id)  ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_group_roles_role_id ON group_roles(role_id);

-- Direct role grants on a user. Survive resolver syncs so an admin
-- promotion does not silently disappear the next time a user logs in.
CREATE TABLE IF NOT EXISTS user_roles (
  user_id     INTEGER NOT NULL,
  role_id     INTEGER NOT NULL,
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- Whitelist of users that may access the /admin UI and /api/admin/*
-- endpoints. The bootstrap admin lands here on first launch.
CREATE TABLE IF NOT EXISTS admins (
  user_id     INTEGER PRIMARY KEY,
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Append-only audit trail of every mutating action through /api/admin/*.
CREATE TABLE IF NOT EXISTS audit_log (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  actor_id     INTEGER,                                   -- nullable: bootstrap actions
  actor_label  TEXT    NOT NULL,                          -- "admin", okta sub, "system", etc.
  action       TEXT    NOT NULL,                          -- e.g. "user.create", "role.update"
  target       TEXT,                                      -- free-form (entity + id)
  before_json  TEXT,
  after_json   TEXT,
  FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_id ON audit_log(actor_id);

-- Schema version table, used by the migration runner. The runner
-- inserts a row per applied migration filename.
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename    TEXT    PRIMARY KEY,
  applied_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
