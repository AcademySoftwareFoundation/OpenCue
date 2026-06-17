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

/**
 * Group-based authorization for CueWeb.
 *
 * A deployment can restrict who may use CueWeb, and who may reach the
 * CueCommander administration pages, by listing the groups that are allowed.
 * The policy is entirely environment-driven so a single image behaves
 * differently per deployment (see middleware.ts):
 *
 *   CUEWEB_AUTHZ_ENABLED   master switch for the gate (default off; "true" on)
 *   CUEWEB_ALLOWED_GROUPS  groups allowed to use CueWeb at all
 *   CUEWEB_ADMIN_GROUPS    groups allowed to use the CueCommander admin pages
 *   CUEWEB_GROUPS_CLAIM    JWT/OIDC claim that carries the user's groups
 *
 * The gate is opt-in: it stays off until CUEWEB_AUTHZ_ENABLED is set to a
 * truthy value, so the default behavior is a pure pass-through. This keeps the
 * seam for the planned OpenCue-wide authentication/authorization layer - a
 * deployment enables CueWeb's gate only if it wants CueWeb to own access
 * control, and leaves it off to defer to that layer.
 *
 * Empty lists mean "no restriction": with nothing configured every signed-in
 * user is allowed and is treated as an admin, so the default behavior is
 * unchanged. Group resolution happens once at sign-in (lib/auth.ts, which has
 * Node access to the identity provider); this module only reads the groups
 * already stamped on the token, so it stays Edge-safe for use in middleware.
 *
 * Sites that resolve group membership from a directory or service the OIDC
 * token does not expose can replace the sign-in resolution (extractGroups
 * below, wired through the jwt callback) without changing the enforcement
 * here.
 */

// Admin-only pages: the CueCommander administration pages plus job submission
// (CueSubmit). A request whose path starts with one of these prefixes
// additionally requires CUEWEB_ADMIN_GROUPS membership. Monitoring-only routes
// (Monitor Cue, Monitor Hosts) are intentionally not listed, so read-only
// monitoring stays available to non-admin users.
export const ADMIN_PATH_PREFIXES = [
  "/allocations",
  "/shows",
  "/services",
  "/subscriptions",
  "/subscription-graphs",
  "/limits",
  "/redirect",
  "/stuck-frame",
  "/cuesubmit",
  // Guard the submit API too, so the restriction can't be bypassed by POSTing
  // directly past the CueSubmit UI.
  "/api/job/submit",
];

/** Parse a comma-separated env list into a normalized (lowercased) set of names. */
function parseGroupList(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((g) => g.trim().toLowerCase())
    .filter(Boolean);
}

/**
 * Master switch for the authorization gate. Defaults to off (opt-in); enable it
 * with an explicit truthy value ("true", "1", "yes", "on"). Unset or empty
 * keeps it off, so the gate never changes behavior until a deployment turns it
 * on.
 */
export function isAuthzEnabled(): boolean {
  const raw = process.env.CUEWEB_AUTHZ_ENABLED;
  if (raw === undefined || raw.trim() === "") return false;
  return ["true", "1", "yes", "on"].includes(raw.trim().toLowerCase());
}

/** The JWT/OIDC claim that holds the user's group memberships. */
export function getGroupsClaim(): string {
  return process.env.CUEWEB_GROUPS_CLAIM || "groups";
}

/** Normalize a claim value (string, array, or space/comma-delimited string) to a list. */
function normalizeGroups(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map((g) => String(g)).filter(Boolean);
  }
  if (typeof raw === "string") {
    return raw.split(/[\s,]+/).filter(Boolean);
  }
  return [];
}

/**
 * Resolve a user's groups at sign-in from the OIDC profile claim or from a
 * `groups` field that a credentials/LDAP provider attached to the user object.
 * Wired through the jwt callback in lib/auth.ts.
 */
export function extractGroups(
  profile: Record<string, unknown> | undefined | null,
  user: Record<string, unknown> | undefined | null,
): string[] {
  const claim = getGroupsClaim();
  const fromProfile = profile ? normalizeGroups(profile[claim]) : [];
  const fromUser = user ? normalizeGroups((user as { groups?: unknown }).groups) : [];
  // De-duplicate while preserving the original casing for display/debugging.
  return Array.from(new Set([...fromProfile, ...fromUser]));
}

/** Read the groups previously stamped on the NextAuth token. */
export function getUserGroups(token: { groups?: unknown } | null | undefined): string[] {
  return normalizeGroups(token?.groups);
}

/** True when `userGroups` intersects `required` (both compared case-insensitively). */
function intersects(userGroups: string[], required: string[]): boolean {
  if (required.length === 0) return true;
  const have = new Set(userGroups.map((g) => g.toLowerCase()));
  return required.some((g) => have.has(g));
}

/** May this user use CueWeb at all? Empty CUEWEB_ALLOWED_GROUPS ⇒ everyone. */
export function isUserAllowed(userGroups: string[]): boolean {
  return intersects(userGroups, parseGroupList(process.env.CUEWEB_ALLOWED_GROUPS));
}

/** May this user use the CueCommander admin pages? Empty CUEWEB_ADMIN_GROUPS ⇒ everyone. */
export function isUserAdmin(userGroups: string[]): boolean {
  return intersects(userGroups, parseGroupList(process.env.CUEWEB_ADMIN_GROUPS));
}

/** Does this path target a CueCommander administration page? */
export function isAdminPath(pathname: string): boolean {
  return ADMIN_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
