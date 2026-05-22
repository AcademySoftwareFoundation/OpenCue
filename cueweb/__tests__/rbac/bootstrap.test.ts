/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

process.env.CUEWEB_RBAC_DB = ":memory:";
process.env.NEXT_PUBLIC_AUTH_PROVIDER = "local";

import fs from "node:fs";
import path from "node:path";
import argon2 from "argon2";

import { _resetForTests } from "@/lib/rbac/db";
import {
  ensureBootstrapAdmin,
  verifyLocalLogin,
} from "@/lib/rbac/bootstrap";
import {
  adminCount,
  findUserByUsername,
  setUserPassword,
} from "@/lib/rbac/db/dal";

const BOOTSTRAP_FILE = path.join(process.cwd(), ".cueweb-bootstrap");

beforeEach(() => {
  _resetForTests();
  if (fs.existsSync(BOOTSTRAP_FILE)) fs.unlinkSync(BOOTSTRAP_FILE);
});

afterAll(() => {
  if (fs.existsSync(BOOTSTRAP_FILE)) fs.unlinkSync(BOOTSTRAP_FILE);
});

describe("bootstrap admin", () => {
  test("creates admin user, sets must_change_password, writes 0600 file", async () => {
    await ensureBootstrapAdmin();
    const user = findUserByUsername("admin");
    expect(user).not.toBeNull();
    expect(user!.source).toBe("local");
    expect(user!.password_hash).toBeTruthy();
    expect(user!.must_change_password).toBe(1);
    expect(adminCount()).toBe(1);

    expect(fs.existsSync(BOOTSTRAP_FILE)).toBe(true);
    const body = fs.readFileSync(BOOTSTRAP_FILE, "utf8");
    expect(body).toContain("username=admin");
    expect(body).toContain("password=");
    // On filesystems that support unix perms the mode must be 0600.
    if (process.platform !== "win32") {
      const mode = fs.statSync(BOOTSTRAP_FILE).mode & 0o777;
      expect(mode).toBe(0o600);
    }
  });

  test("is idempotent: second call does not create a second admin", async () => {
    await ensureBootstrapAdmin();
    await ensureBootstrapAdmin();
    expect(adminCount()).toBe(1);
  });

  test("local login verifies the generated password", async () => {
    await ensureBootstrapAdmin();
    const body = fs.readFileSync(BOOTSTRAP_FILE, "utf8");
    const password = body
      .split("\n")
      .find((l) => l.startsWith("password="))!
      .slice("password=".length);
    expect(password.length).toBeGreaterThan(0);

    const ok = await verifyLocalLogin("admin", password);
    expect(ok).not.toBeNull();

    const bad = await verifyLocalLogin("admin", "definitely-not-it");
    expect(bad).toBeNull();
  });

  test("clearing must_change_password lets a new password verify", async () => {
    await ensureBootstrapAdmin();
    const user = findUserByUsername("admin")!;
    const hash = await argon2.hash("brand-new-password", {
      type: argon2.argon2id,
    });
    setUserPassword(user.id, hash, false);

    const ok = await verifyLocalLogin("admin", "brand-new-password");
    expect(ok).not.toBeNull();
    expect(findUserByUsername("admin")!.must_change_password).toBe(0);
  });
});
