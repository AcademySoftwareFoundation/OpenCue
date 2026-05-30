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
 * NOTE: this hook persists and broadcasts the selection. Actually routing
 * REST-gateway calls per-facility is a separate task. Until that lands, the value is informational.
 */

export const STORAGE_KEY = "cueweb.facility.selected";
const CHANGE_EVENT = "cueweb:facility-changed";

const DEFAULT_FACILITIES = ["local", "dev", "cloud", "external"] as const;

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
    setFacilityState(readSelected(facilities));

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
      writeSelected(next);
      setFacilityState(next);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
      }
    },
    [facilities],
  );

  return { facility, facilities, setFacility };
}
