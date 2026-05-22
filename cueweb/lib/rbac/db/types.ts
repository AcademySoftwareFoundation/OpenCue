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

// Row shapes for the SQLite RBAC store. Mirrors migrations/0001_initial.sql.

export type Source = "local" | "okta" | "ldap" | "imported";

export type UserRow = {
  id: number;
  external_id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  source: Source;
  active: 0 | 1;
  password_hash: string | null;
  must_change_password: 0 | 1;
  created_at: number;
  updated_at: number;
  last_login_at: number | null;
};

export type GroupRow = {
  id: number;
  name: string;
  description: string | null;
  source: Source;
  created_at: number;
  updated_at: number;
};

export type RoleRow = {
  id: number;
  name: string;
  description: string | null;
  builtin: 0 | 1;
  created_at: number;
  updated_at: number;
};

export type AuditLogRow = {
  id: number;
  ts: number;
  actor_id: number | null;
  actor_label: string;
  action: string;
  target: string | null;
  before_json: string | null;
  after_json: string | null;
};
