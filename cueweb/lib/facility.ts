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
 * Server-side Cuebot facility resolver (CueGUI "Cuebot Facility" parity).
 *
 * CueGUI maps a facility name to a list of Cuebot host:port pairs
 * (`cuebot.facility` in opencue's config) and rewires the gRPC connection
 * when the user switches (`Cuebot.setHostWithFacility`). CueWeb talks to the
 * REST gateway rather than gRPC directly, so the CueWeb analog maps a facility
 * name to a REST-gateway base URL + the JWT secret that gateway trusts.
 *
 * The selected facility travels from the browser to the server in a cookie
 * (see `FACILITY_COOKIE`); every gateway-bound API route resolves the target
 * for the current request via `getRequestFacilityTarget()`.
 *
 * Configuration (all server-side, optional). Resolution layers, highest first:
 *   1. Runtime override store (lib/facility-store.ts) — edited at runtime from
 *      the /settings/facilities admin screen, no redeploy required.
 *   2. Env vars: CUEBOT_<NAME>_REST_GATEWAY_URL / CUEBOT_<NAME>_JWT_SECRET.
 *   3. Legacy single-gateway vars NEXT_PUBLIC_OPENCUE_ENDPOINT / NEXT_JWT_SECRET.
 *   NEXT_PUBLIC_CUEBOT_FACILITIES lists the facility names (the menu).
 *
 * When a facility has no override and no explicit *_REST_GATEWAY_URL /
 * *_JWT_SECRET, it falls back to the legacy vars, so the default deployment
 * keeps working with zero new config and only the `local` facility wired up.
 *
 * NOTE: `getRequestFacilityTarget()` reads `next/headers` and only runs
 * server-side. It uses a *dynamic* import so this module stays free of a
 * static `next/headers` dependency — `api_utils.ts` (which imports this
 * module) is also part of the client bundle, and Next.js forbids a static
 * `next/headers` import anywhere in the client graph. The pure helpers below
 * are safe to import from anywhere. Client components that need the cookie
 * name use the literal in `use_cuebot_facility.ts`, kept in sync with
 * `FACILITY_COOKIE`.
 */

/** Cookie carrying the selected facility name. Mirrors the localStorage value
 *  written by `useCuebotFacility`; must match the literal there. */
export const FACILITY_COOKIE = "cueweb.facility";

/** Default facility list — matches CueGUI's example `cuebot.facility` keys. */
const DEFAULT_FACILITIES = ["local", "dev", "cloud", "external"] as const;

export interface FacilityTarget {
  /** The resolved (validated) facility name. */
  name: string;
  /** REST gateway base URL to send this request to. */
  gatewayUrl: string;
  /** JWT secret the target gateway trusts. */
  jwtSecret: string;
}

/** The configured facility names (the menu). Falls back to the CueGUI defaults. */
export function getConfiguredFacilities(): string[] {
  const raw = process.env.NEXT_PUBLIC_CUEBOT_FACILITIES ?? "";
  const parsed = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  return parsed.length > 0 ? parsed : [...DEFAULT_FACILITIES];
}

/** "dev" -> "CUEBOT_DEV_REST_GATEWAY_URL". Non-alphanumerics become "_". */
export function envKey(facility: string, suffix: string): string {
  const norm = facility.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
  return `CUEBOT_${norm}_${suffix}`;
}

/**
 * Resolve a facility name to its gateway target. Unknown / unconfigured names
 * fall back to the first configured facility (the default), mirroring CueGUI's
 * `setHostWithFacility` which falls back to `cuebot.facility_default`.
 */
export function resolveFacilityTarget(name: string | undefined): FacilityTarget {
  const facilities = getConfiguredFacilities();
  const fallbackName = facilities[0] ?? "local";
  const facility = name && facilities.includes(name) ? name : fallbackName;

  const gatewayUrl =
    process.env[envKey(facility, "REST_GATEWAY_URL")] ??
    process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT ??
    "";
  const jwtSecret =
    process.env[envKey(facility, "JWT_SECRET")] ??
    process.env.NEXT_JWT_SECRET ??
    "";

  return { name: facility, gatewayUrl, jwtSecret };
}

/**
 * Resolve the facility target for the current request, reading the selection
 * from the request cookie and validating it against the configured list.
 * Env-only (no runtime overrides); the override-aware variant lives in the
 * server-only `lib/facility-server.ts`. Safe to call outside a request scope.
 */
export async function getRequestFacilityTarget(): Promise<FacilityTarget> {
  let selected: string | undefined;
  try {
    // Dynamic import keeps next/headers out of the static client graph.
    const { cookies } = await import("next/headers");
    const store = await cookies();
    selected = store.get(FACILITY_COOKIE)?.value;
  } catch {
    // Not in a request scope (e.g. build-time): use the default.
  }
  return resolveFacilityTarget(selected);
}

/** Secret-free view of a facility's effective config, for the settings screen. */
export interface FacilityConfigView {
  name: string;
  /** Effective gateway URL (override > env > legacy default). */
  gatewayUrl: string;
  /** Where the effective gateway URL came from. */
  source: "override" | "env" | "default" | "unset";
  /** Whether a runtime override is set for this facility. */
  hasOverride: boolean;
  /** Whether a JWT secret is configured (the value is never exposed). */
  hasJwtSecret: boolean;
  /** Whether the JWT secret specifically comes from a runtime override. */
  secretFromOverride: boolean;
}
