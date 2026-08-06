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
 * Pure helpers for the multi-pane split workspace (CueGUI "Add new window"
 * equivalent - see `cuegui/cuegui/MainWindow.py`). Kept free of React /
 * `window` so they can be unit-tested directly; the thin localStorage
 * wrappers below are the only browser-touching exports.
 *
 * The split route is driven entirely by the URL:
 *   /split?left=/jobs&right=/hosts/server-01
 * so each pane carries its own URL and the whole workspace survives a reload.
 * The only piece of state that lives outside the URL is the divider ratio,
 * persisted under SPLIT_RATIO_KEY.
 */

export const SPLIT_RATIO_KEY = "cueweb.split.ratio";

/** Divider position bounds (percent of the workspace width given to the
 *  left pane). Clamped so neither pane can be dragged shut. */
export const MIN_RATIO = 15;
export const MAX_RATIO = 85;
export const DEFAULT_RATIO = 50;

/** Default pane targets when the URL omits one (Jobs left, Hosts right). */
export const DEFAULT_LEFT = "/";
export const DEFAULT_RIGHT = "/hosts";

export type PaneSide = "left" | "right";

// ASCII control characters (NUL..US) have no place in a path; reject them.
// Checked by code point so no control bytes need to live in this source file.
function hasControlChar(s: string): boolean {
  for (let i = 0; i < s.length; i++) {
    if (s.charCodeAt(i) < 0x20) return true;
  }
  return false;
}

/**
 * Validate / normalize a pane target so a pane can only ever point at an
 * internal CueWeb path. Rejects (returning `fallback`):
 *   - empty / missing values
 *   - anything that isn't an absolute path ("/...")
 *   - protocol-relative ("//evil.com") and backslash tricks
 *   - control characters
 *   - the `/split` route itself (would recursively embed the workspace)
 */
export function sanitizePanePath(
  raw: string | null | undefined,
  fallback: string,
): string {
  if (raw == null) return fallback;
  const v = raw.trim();
  if (v.length === 0) return fallback;
  if (!v.startsWith("/")) return fallback;
  if (v.startsWith("//")) return fallback;
  if (v.includes("\\")) return fallback;
  if (hasControlChar(v)) return fallback;

  const pathOnly = (v.split(/[?#]/)[0] || "/").replace(/\/+$/, "") || "/";
  if (pathOnly === "/split" || pathOnly.startsWith("/split/")) return fallback;
  return v;
}

/** Clamp a raw percentage into the allowed divider range. */
export function clampRatio(n: number): number {
  if (!Number.isFinite(n)) return DEFAULT_RATIO;
  return Math.min(MAX_RATIO, Math.max(MIN_RATIO, n));
}

/** Parse a stored ratio string into a clamped number (DEFAULT on garbage). */
export function parseRatio(raw: string | null | undefined): number {
  if (raw == null) return DEFAULT_RATIO;
  const n = Number.parseFloat(raw);
  if (!Number.isFinite(n)) return DEFAULT_RATIO;
  return clampRatio(n);
}

/** Build the canonical `/split?left=...&right=...` URL (values encoded). */
export function buildSplitUrl(left: string, right: string): string {
  const params = new URLSearchParams();
  params.set("left", left);
  params.set("right", right);
  return `/split?${params.toString()}`;
}

/** Read the persisted divider ratio (browser-only; DEFAULT off the server). */
export function readRatio(): number {
  if (typeof window === "undefined") return DEFAULT_RATIO;
  try {
    return parseRatio(window.localStorage.getItem(SPLIT_RATIO_KEY));
  } catch {
    return DEFAULT_RATIO;
  }
}

/** Persist the divider ratio (clamped). No-op on the server / in private mode. */
export function writeRatio(n: number): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SPLIT_RATIO_KEY, String(clampRatio(n)));
  } catch {
    // quota / private mode; ignore.
  }
}
