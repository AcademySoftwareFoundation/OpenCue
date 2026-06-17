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

"use client";

import * as React from "react";

/**
 * Cuebot Facility selector - CueGUI parity (the "Cuebot Facility" menu in
 * `cuegui/cuegui/MainWindow.py`). Lets users switch between facilities
 * (local / dev / cloud / external by default).
 *
 * The set of available facilities can be overridden at build time via
 * `NEXT_PUBLIC_CUEBOT_FACILITIES` (comma-separated). The selected facility
 * is persisted to `localStorage["cueweb.facility.selected"]` and synced
 * across components via a CustomEvent (same tab) + the browser `storage`
 * event (cross-tab).
 *
 * The selection is ALSO written to a cookie (`cueweb.facility`) so server-side
 * API routes can resolve the per-facility REST gateway for each request (see
 * `lib/facility.ts`). Selecting a facility reloads the page so every view
 * re-fetches against the newly selected gateway — mirroring CueGUI, which
 * clears and re-fetches all data on a facility switch.
 */

export const STORAGE_KEY = "cueweb.facility.selected";
const CHANGE_EVENT = "cueweb:facility-changed";
// Cookie read server-side by lib/facility.ts (FACILITY_COOKIE). Keep in sync.
const COOKIE_KEY = "cueweb.facility";

const DEFAULT_FACILITIES = ["local", "dev", "cloud", "external"] as const;

/** Mirror the selection into a cookie the server reads on every request. */
function writeCookie(value: string): void {
  if (typeof document === "undefined") return;
  // Not HttpOnly: the client sets it for instant routing, and the server
  // re-validates the value against the configured facility list, so a tampered
  // cookie can only ever select another already-configured facility.
  const oneYear = 60 * 60 * 24 * 365;
  document.cookie = `${COOKIE_KEY}=${encodeURIComponent(value)}; path=/; max-age=${oneYear}; samesite=lax`;
}

/** Read the facility cookie (returns null when absent). */
function readCookie(): string | null {
  if (typeof document === "undefined") return null;
  const row = document.cookie
    .split("; ")
    .find((r) => r.startsWith(`${COOKIE_KEY}=`));
  return row ? decodeURIComponent(row.slice(COOKIE_KEY.length + 1)) : null;
}

/** Parse the build-time env var; falls back to the CueGUI defaults. */
function readFacilitiesFromEnv(): string[] {
  const raw = process.env.NEXT_PUBLIC_CUEBOT_FACILITIES ?? "";
  const parsed = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  return parsed.length > 0 ? parsed : [...DEFAULT_FACILITIES];
}

function readSelected(facilities: string[]): string {
  if (typeof window === "undefined") return facilities[0] ?? "local";
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw && facilities.includes(raw)) return raw;
  } catch {
    // ignore
  }
  return facilities[0] ?? "local";
}

function writeSelected(value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // ignore
  }
}

export function useCuebotFacility(): {
  facility: string;
  facilities: string[];
  setFacility: (next: string) => void;
} {
  // The list is static for the lifetime of the page (it's a build-time env);
  // memoize to keep referential equality stable.
  const facilities = React.useMemo(readFacilitiesFromEnv, []);

  // SSR-safe: render the first facility on the server / initial client
  // render to avoid hydration mismatches, then reconcile from localStorage.
  const [facility, setFacilityState] = React.useState<string>(
    () => facilities[0] ?? "local",
  );

  React.useEffect(() => {
    const current = readSelected(facilities);
    setFacilityState(current);
    // Propagate a pre-existing localStorage selection (set before the cookie
    // existed) to the cookie so server routes pick it up without a reselect.
    if (readCookie() !== current) writeCookie(current);

    const customHandler = () => setFacilityState(readSelected(facilities));
    const storageHandler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setFacilityState(readSelected(facilities));
    };

    window.addEventListener(CHANGE_EVENT, customHandler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, customHandler);
      window.removeEventListener("storage", storageHandler);
    };
  }, [facilities]);

  const setFacility = React.useCallback(
    (next: string) => {
      if (!facilities.includes(next)) return;
      const previous = readSelected(facilities);
      writeSelected(next);
      writeCookie(next);
      setFacilityState(next);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
        // Re-fetch everything against the newly selected gateway. CueGUI clears
        // and reloads all data on a facility switch; a full reload is the
        // simplest equivalent and guarantees no stale cross-facility data.
        if (next !== previous) window.location.reload();
      }
    },
    [facilities],
  );

  return { facility, facilities, setFacility };
}
