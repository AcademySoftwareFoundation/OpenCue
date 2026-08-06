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
 * SERVER-ONLY facility resolution that layers the runtime override store
 * (lib/facility-store.ts, filesystem-backed) on top of the env/cookie defaults
 * resolved by lib/facility.ts. Kept separate from lib/facility.ts because that
 * module is part of the client bundle (via api_utils) and must not import
 * node:fs. Only server code (gateway_server.ts, the health route, the settings
 * page/action) imports from here.
 */

import {
  envKey,
  getConfiguredFacilities,
  getRequestFacilityTarget,
  resolveFacilityTarget,
  type FacilityConfigView,
  type FacilityTarget,
} from "./facility";
import { readFacilityOverrides, type FacilityOverride } from "./facility-store";

/** Layer a runtime override on top of an env-resolved target. */
function applyOverride(target: FacilityTarget, override: FacilityOverride | undefined): FacilityTarget {
  if (!override) return target;
  return {
    name: target.name,
    gatewayUrl: override.gatewayUrl?.trim() || target.gatewayUrl,
    jwtSecret: override.jwtSecret || target.jwtSecret,
  };
}

/**
 * Resolve the current request's facility target with any runtime override
 * applied. Used by the gateway proxy path so admin edits to a facility's URL /
 * secret take effect without a redeploy.
 */
export async function getRequestFacilityTargetWithOverrides(): Promise<FacilityTarget> {
  const base = await getRequestFacilityTarget();
  const overrides = await readFacilityOverrides();
  return applyOverride(base, overrides[base.name]);
}

/**
 * Resolve every configured facility's target (override-layered), including the
 * JWT secret. Used by the per-facility health probe. Never return this to a
 * client; use getFacilityConfigViews() for the settings screen.
 */
export async function getAllFacilityTargets(): Promise<FacilityTarget[]> {
  const overrides = await readFacilityOverrides();
  return getConfiguredFacilities().map((name) =>
    applyOverride(resolveFacilityTarget(name), overrides[name]),
  );
}

/**
 * Per-facility effective configuration WITHOUT secrets, for the admin settings
 * screen.
 */
export async function getFacilityConfigViews(): Promise<FacilityConfigView[]> {
  const overrides = await readFacilityOverrides();
  return getConfiguredFacilities().map((name) => {
    const override = overrides[name];
    const envUrl = process.env[envKey(name, "REST_GATEWAY_URL")];
    const legacyUrl = process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT;
    const effectiveUrl = override?.gatewayUrl?.trim() || envUrl || legacyUrl || "";
    const source: FacilityConfigView["source"] = override?.gatewayUrl?.trim()
      ? "override"
      : envUrl
        ? "env"
        : legacyUrl
          ? "default"
          : "unset";
    const envSecret = process.env[envKey(name, "JWT_SECRET")];
    const legacySecret = process.env.NEXT_JWT_SECRET;
    return {
      name,
      gatewayUrl: effectiveUrl,
      source,
      hasOverride: !!override?.gatewayUrl?.trim(),
      hasJwtSecret: !!(override?.jwtSecret || envSecret || legacySecret),
      secretFromOverride: !!override?.jwtSecret,
    };
  });
}
