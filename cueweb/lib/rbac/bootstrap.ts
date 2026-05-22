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

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import argon2 from "argon2";

import { getDb } from "./db";
import {
  addAdmin,
  adminCount,
  appendAudit,
  attachRoleToUser,
  findRoleByName,
  findUserByUsername,
  upsertUser,
} from "./db/dal";
import { BUILTIN_ROLES } from "./roles";

const BOOTSTRAP_USERNAME = "admin";
const BOOTSTRAP_PASSWORD_BYTES = 18; // 24 base64url chars

function defaultBootstrapPath(): string {
  const dbPath = process.env.CUEWEB_RBAC_DB || "/data/cueweb-rbac.db";
  if (dbPath === ":memory:") {
    return path.join(process.cwd(), ".cueweb-bootstrap");
  }
  return path.join(path.dirname(dbPath), ".cueweb-bootstrap");
}

function generatePassword(): string {
  return crypto.randomBytes(BOOTSTRAP_PASSWORD_BYTES).toString("base64url");
}

function writeBootstrapFile(filePath: string, password: string): void {
  const body =
    `# CueWeb bootstrap admin credentials\n` +
    `# Generated automatically on first launch. Delete this file once you've\n` +
    `# copied the password somewhere safe; the credentials are also printed\n` +
    `# once to the server log.\n` +
    `username=${BOOTSTRAP_USERNAME}\n` +
    `password=${password}\n`;
  fs.writeFileSync(filePath, body, { mode: 0o600 });
  try {
    fs.chmodSync(filePath, 0o600);
  } catch {
    // best effort on filesystems that don't support unix perms
  }
}

function printBootstrapBanner(password: string, filePath: string): void {
  const line = "=".repeat(72);
  // eslint-disable-next-line no-console
  console.log(
    `\n${line}\n` +
      `CueWeb bootstrap admin created (first-launch flow).\n` +
      `\n` +
      `  username : ${BOOTSTRAP_USERNAME}\n` +
      `  password : ${password}\n` +
      `\n` +
      `Credentials were also written to ${filePath} (mode 0600). The\n` +
      `password will be required to change on first login. Delete the file\n` +
      `once you have a working admin password set.\n` +
      `${line}\n`,
  );
}

/**
 * Runs once per process on startup. If the admins table is empty (i.e.
 * this is a freshly-provisioned DB), creates a `admin` local user, gives
 * it the `site-admin` role + admin access, generates a random password,
 * writes it to /data/.cueweb-bootstrap (0600) and prints a one-time
 * banner to stdout. The user is marked `must_change_password=1` so the
 * first login forces a change.
 *
 * Idempotent: if any admins row already exists, this is a no-op.
 */
export async function ensureBootstrapAdmin(): Promise<void> {
  // Force DB init so migrations run before we read counts.
  getDb();

  if (adminCount() > 0) return;

  const password = generatePassword();
  const hash = await argon2.hash(password, { type: argon2.argon2id });

  const userId = upsertUser({
    externalId: `local:${BOOTSTRAP_USERNAME}`,
    username: BOOTSTRAP_USERNAME,
    email: null,
    displayName: "Bootstrap admin",
    source: "local",
    passwordHash: hash,
    mustChangePassword: true,
  });

  const siteAdmin = findRoleByName(BUILTIN_ROLES.SITE_ADMIN);
  if (siteAdmin) {
    attachRoleToUser(userId, siteAdmin.id);
  }
  addAdmin(userId);

  appendAudit({
    actorId: null,
    actorLabel: "system",
    action: "bootstrap.admin_created",
    target: `user:${userId}`,
    after: { username: BOOTSTRAP_USERNAME, source: "local" },
  });

  const filePath = defaultBootstrapPath();
  try {
    writeBootstrapFile(filePath, password);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error(
      `CueWeb: failed to write bootstrap credentials to ${filePath}: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }
  printBootstrapBanner(password, filePath);
}

/**
 * Used by the local Credentials provider in NextAuth to authenticate
 * `admin` and any other local users created in the Admin UI. Returns
 * the user row on success, or `null` on failure (no logged error - the
 * caller decides what to surface).
 */
export async function verifyLocalLogin(
  username: string,
  password: string,
): Promise<{ user: ReturnType<typeof findUserByUsername> } | null> {
  const user = findUserByUsername(username);
  if (!user || user.active !== 1 || user.source !== "local" || !user.password_hash) {
    return null;
  }
  try {
    const ok = await argon2.verify(user.password_hash, password);
    if (!ok) return null;
  } catch {
    return null;
  }
  return { user };
}
