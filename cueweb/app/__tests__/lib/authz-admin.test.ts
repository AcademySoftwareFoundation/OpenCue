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

import {
  isAdminPath,
  isEffectiveAdmin,
  isGateActive,
} from "@/lib/authz";

// authz reads the env at call time, so each test just sets the vars it needs.
const ENV_KEYS = [
  "NEXT_PUBLIC_AUTH_PROVIDER",
  "CUEWEB_AUTHZ_ENABLED",
  "CUEWEB_ADMIN_GROUPS",
] as const;
const ORIGINAL: Record<string, string | undefined> = {};
beforeAll(() => ENV_KEYS.forEach((k) => (ORIGINAL[k] = process.env[k])));
afterEach(() => {
  ENV_KEYS.forEach((k) => {
    if (ORIGINAL[k] === undefined) delete process.env[k];
    else process.env[k] = ORIGINAL[k];
  });
});

function setEnv(env: Partial<Record<(typeof ENV_KEYS)[number], string>>) {
  ENV_KEYS.forEach((k) => delete process.env[k]);
  Object.entries(env).forEach(([k, v]) => (process.env[k] = v));
}

describe("authz admin helpers", () => {
  it("treats /admin and /api/admin as admin-only paths", () => {
    expect(isAdminPath("/admin/audit")).toBe(true);
    expect(isAdminPath("/api/admin/audit")).toBe(true);
    // The whole CueCommander section is gated
    expect(isAdminPath("/monitor-cue")).toBe(true);
    expect(isAdminPath("/hosts")).toBe(true);
    expect(isAdminPath("/hosts/some-host")).toBe(true);
    expect(isAdminPath("/stuck-frames")).toBe(true);
    // Manage facilities… (per-facility gateway settings) is admin-only.
    expect(isAdminPath("/settings/facilities")).toBe(true);
  });

  it("gate is inactive without an auth provider", () => {
    setEnv({ CUEWEB_AUTHZ_ENABLED: "true", CUEWEB_ADMIN_GROUPS: "admins" });
    expect(isGateActive()).toBe(false);
    // Inactive gate => everyone is effectively admin (show to everyone).
    expect(isEffectiveAdmin([])).toBe(true);
  });

  it("gate is inactive when CUEWEB_AUTHZ_ENABLED is off", () => {
    setEnv({ NEXT_PUBLIC_AUTH_PROVIDER: "okta", CUEWEB_AUTHZ_ENABLED: "false" });
    expect(isGateActive()).toBe(false);
    expect(isEffectiveAdmin([])).toBe(true);
  });

  it("active gate with no admin groups configured => everyone is admin", () => {
    setEnv({ NEXT_PUBLIC_AUTH_PROVIDER: "okta", CUEWEB_AUTHZ_ENABLED: "true" });
    expect(isGateActive()).toBe(true);
    expect(isEffectiveAdmin([])).toBe(true);
    expect(isEffectiveAdmin(["anything"])).toBe(true);
  });

  it("active gate with admin groups restricts to members", () => {
    setEnv({
      NEXT_PUBLIC_AUTH_PROVIDER: "okta",
      CUEWEB_AUTHZ_ENABLED: "true",
      CUEWEB_ADMIN_GROUPS: "cue-admins",
    });
    expect(isGateActive()).toBe(true);
    expect(isEffectiveAdmin(["cue-admins"])).toBe(true);
    expect(isEffectiveAdmin(["CUE-ADMINS"])).toBe(true); // case-insensitive
    expect(isEffectiveAdmin(["renderers"])).toBe(false);
    expect(isEffectiveAdmin([])).toBe(false);
  });
});
