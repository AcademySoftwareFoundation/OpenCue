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

// Client-side usage beacons. Each call posts a tiny payload to /api/track,
// which resolves the USER server-side (from the session) and increments a
// Prometheus counter. Fire-and-forget; never throws; opt out at build time with
// NEXT_PUBLIC_USAGE_TRACKING=off.

const ENABLED =
  typeof window !== "undefined" &&
  (process.env.NEXT_PUBLIC_USAGE_TRACKING ?? "on").toLowerCase() !== "off";

function beacon(payload: { kind: string; name?: string }): void {
  if (!ENABLED) return;
  try {
    const body = JSON.stringify(payload);
    // sendBeacon survives navigation; fall back to keepalive fetch.
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/track", new Blob([body], { type: "application/json" }));
    } else {
      void fetch("/api/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      });
    }
  } catch {
    // ignore - usage tracking must never affect the UI
  }
}

// Map a Next.js pathname to a coarse, bounded page/module name (must match the
// ALLOWED_PAGES allow-list in lib/metrics-service.ts; anything else -> "other").
export function pageNameForPath(pathname: string): string {
  if (!pathname || pathname === "/") return "monitor-jobs";
  if (pathname.startsWith("/dashboard")) return "dashboard";
  if (pathname.startsWith("/monitor-cue")) return "monitor-cue";
  if (pathname.startsWith("/split")) return "monitor-jobs";
  if (pathname.startsWith("/hosts/")) return "host-details";
  if (pathname.startsWith("/hosts")) return "monitor-hosts";
  if (pathname.startsWith("/jobs/")) return "job-details";
  if (pathname.startsWith("/frames/")) return "frame-log";
  if (pathname.startsWith("/allocations")) return "allocations";
  if (pathname.startsWith("/limits")) return "limits";
  if (pathname.startsWith("/redirect")) return "redirect";
  if (pathname.startsWith("/services")) return "services";
  if (pathname.startsWith("/shows")) return "shows";
  if (pathname.startsWith("/stuck-frames")) return "stuck-frames";
  if (pathname.startsWith("/subscription-graphs")) return "subscription-graphs";
  if (pathname.startsWith("/subscriptions")) return "subscriptions";
  if (pathname.startsWith("/cuesubmit")) return "cuesubmit";
  if (pathname.startsWith("/plugins")) return "plugins";
  if (pathname.startsWith("/settings")) return "settings";
  if (pathname.startsWith("/login")) return "login";
  return "other";
}

export function trackPage(pathname: string): void {
  beacon({ kind: "page", name: pageNameForPath(pathname) });
}

export function trackAction(action: string): void {
  beacon({ kind: "action", name: action });
}

// Derive an action key from a gateway-proxy action endpoint
// ("/api/job/action/kill" -> "job-kill"). Returns "" for non-action routes.
export function actionKeyForEndpoint(endpoint: string): string {
  const m = endpoint.match(/\/api\/([a-z]+)\/action\/([a-z]+)/i);
  return m ? `${m[1].toLowerCase()}-${m[2].toLowerCase()}` : "";
}

// Track an action by its endpoint (used by the shared action dispatcher).
export function trackActionEndpoint(endpoint: string): void {
  const key = actionKeyForEndpoint(endpoint);
  if (key) trackAction(key);
}

export function trackFacility(facility: string): void {
  beacon({ kind: "facility", name: facility });
}

export function trackLogin(): void {
  beacon({ kind: "login" });
}
