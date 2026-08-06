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
 * Runtime store for per-facility connection overrides (the J2 "edit URLs /
 * credentials without redeploy" feature). Overrides are layered ON TOP of the
 * env-var defaults by `lib/facility.ts`, so an empty store reproduces the
 * env-only behavior exactly.
 *
 * Persistence is a single JSON file plus an append-only JSONL audit log, both
 * under `CUEWEB_FACILITY_STORE` (defaults to a file in the OS temp dir). For a
 * deployment where edits must survive a container restart, point that var at a
 * mounted volume. The file is written 0600 because it can contain a per-facility
 * JWT secret.
 *
 * SERVER-ONLY: this module imports `node:fs` and must never reach the client
 * bundle. `lib/facility.ts` only ever imports it dynamically.
 */

import { promises as fs } from "fs";
import os from "os";
import path from "path";

export interface FacilityOverride {
  /** Override REST gateway base URL (absent = use the env/default). */
  gatewayUrl?: string;
  /** Override JWT secret (absent = use the env/default). Never sent to clients. */
  jwtSecret?: string;
}

export type FacilityOverrideMap = Record<string, FacilityOverride>;

export interface AuditEntry {
  /** ISO-8601 timestamp. */
  at: string;
  /** Who made the change (best-effort; "unknown" when auth is disabled). */
  actor: string;
  /** Facility name affected. */
  facility: string;
  /** Which fields changed (secret values are NEVER recorded). */
  changes: string[];
}

const STORE_PATH =
  process.env.CUEWEB_FACILITY_STORE || path.join(os.tmpdir(), "cueweb-facilities.json");
const AUDIT_PATH = STORE_PATH.replace(/\.json$/, "") + ".audit.jsonl";

// Small in-process cache so the per-request resolver (called by every gateway
// proxy route) doesn't hit the filesystem on every call. Short TTL keeps "edit
// without redeploy" feeling immediate; writes bust the cache outright.
const CACHE_TTL_MS = 3000;
let cache: { at: number; map: FacilityOverrideMap } | null = null;

function nowMs(): number {
  return Date.now();
}

/** Read the override map (cached). Returns {} on any read/parse failure. */
export async function readFacilityOverrides(): Promise<FacilityOverrideMap> {
  if (cache && nowMs() - cache.at < CACHE_TTL_MS) return cache.map;
  let map: FacilityOverrideMap = {};
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && parsed.facilities && typeof parsed.facilities === "object") {
      map = parsed.facilities as FacilityOverrideMap;
    }
  } catch {
    // Missing / unreadable / malformed: treat as no overrides.
  }
  cache = { at: nowMs(), map };
  return map;
}

// Serialize writes within this process so concurrent saves can't lose updates:
// the read-modify-write below interleaves at its await points, and Next.js does
// not serialize Server Action invocations. A single CueWeb instance is one Node
// process, so chaining each write onto the previous one is sufficient. (A
// multi-instance deployment sharing the store file would additionally need a
// cross-process file lock.)
let writeChain: Promise<unknown> = Promise.resolve();

/**
 * Apply a partial override for one facility and append an audit entry. Passing
 * an empty string for a field clears that override (falls back to env/default).
 * Serialized so concurrent calls apply one-at-a-time (no lost updates).
 */
export async function writeFacilityOverride(
  facility: string,
  override: FacilityOverride,
  actor: string,
): Promise<void> {
  const run = writeChain.then(() => doWriteFacilityOverride(facility, override, actor));
  // Keep the chain alive even if this write rejects, so one failure doesn't
  // break serialization for subsequent writes.
  writeChain = run.catch(() => undefined);
  return run;
}

async function doWriteFacilityOverride(
  facility: string,
  override: FacilityOverride,
  actor: string,
): Promise<void> {
  const current = await readFacilityOverrides();
  const prev = current[facility] ?? {};
  const next: FacilityOverride = { ...prev };
  const changes: string[] = [];

  if (override.gatewayUrl !== undefined) {
    const v = override.gatewayUrl.trim();
    if (v === "") {
      if (next.gatewayUrl !== undefined) changes.push("gatewayUrl cleared");
      delete next.gatewayUrl;
    } else if (v !== next.gatewayUrl) {
      changes.push("gatewayUrl updated");
      next.gatewayUrl = v;
    }
  }
  if (override.jwtSecret !== undefined) {
    const v = override.jwtSecret;
    if (v === "") {
      if (next.jwtSecret !== undefined) changes.push("jwtSecret cleared");
      delete next.jwtSecret;
    } else if (v !== next.jwtSecret) {
      // Record THAT it changed, never the value.
      changes.push("jwtSecret updated");
      next.jwtSecret = v;
    }
  }

  if (changes.length === 0) return; // nothing actually changed

  const map: FacilityOverrideMap = { ...current };
  if (next.gatewayUrl === undefined && next.jwtSecret === undefined) {
    delete map[facility];
  } else {
    map[facility] = next;
  }

  await fs.mkdir(path.dirname(STORE_PATH), { recursive: true });
  await fs.writeFile(STORE_PATH, JSON.stringify({ facilities: map }, null, 2), { mode: 0o600 });
  cache = null; // bust cache so the change takes effect immediately

  const entry: AuditEntry = {
    at: new Date().toISOString(),
    actor: actor || "unknown",
    facility,
    changes,
  };
  await fs.appendFile(AUDIT_PATH, JSON.stringify(entry) + "\n", { mode: 0o600 }).catch(() => undefined);
}

/** Read the audit log, newest first. Returns [] when none exists. */
export async function readFacilityAudit(limit = 50): Promise<AuditEntry[]> {
  try {
    const raw = await fs.readFile(AUDIT_PATH, "utf8");
    const entries = raw
      .split("\n")
      .filter((l) => l.trim().length > 0)
      .map((l) => {
        try {
          return JSON.parse(l) as AuditEntry;
        } catch {
          return null;
        }
      })
      .filter((e): e is AuditEntry => e !== null);
    return entries.reverse().slice(0, limit);
  } catch {
    return [];
  }
}

/** Where the store lives (shown on the settings screen for operators). */
export function facilityStorePath(): string {
  return STORE_PATH;
}
