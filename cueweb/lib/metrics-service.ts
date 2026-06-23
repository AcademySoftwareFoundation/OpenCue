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

// lib/metrics-service.ts
//
// Prometheus usage metrics for CueWeb. Singleton over a single prom-client
// Registry exposed at GET /api/metrics. Tracks WHO uses WHAT, how often, and
// how fast - per user, per page/module, per action - with bounded cardinality
// (page/action label values are validated against allow-lists; the API
// counters carry no user label). Mirrors the asset-search approach.
import { Counter, Histogram, Registry } from "prom-client";

// Sentinel user when the caller is unauthenticated (auth disabled / no session).
export const ANONYMOUS_USER = "anonymous";

// Allow-lists keep `page` / `action` cardinality bounded: unknown values map to
// "other" so a buggy/hostile client can't explode the series count.
export const ALLOWED_PAGES = [
  "dashboard", "monitor-jobs", "job-graph", "job-details", "frame-log",
  "monitor-cue", "monitor-hosts", "host-details", "allocations", "limits",
  "redirect", "services", "shows", "stuck-frames", "subscriptions",
  "subscription-graphs", "cuesubmit", "plugins", "settings", "login", "other",
] as const;

// The action keys correspond to the gateway-proxy action routes
// (/api/<entity>/action/<verb> -> "<entity>-<verb>"), so cardinality is bounded
// by the fixed set of routes. A few client-only keys (submit, view presets) are
// appended; anything else maps to "other".
export const ALLOWED_ACTIONS = [
  "comment-delete", "comment-save",
  "frame-createdependonframe", "frame-createdependonjob",
  "frame-createdependonlayer", "frame-dropdepends", "frame-eat",
  "frame-getdepends", "frame-kill", "frame-markaswaiting", "frame-retry",
  "group-createsubgroup", "group-delete", "group-reparentgroups",
  "group-reparentjobs", "group-update",
  "host-addcomment", "host-addtags", "host-delete", "host-lock", "host-reboot",
  "host-rebootwhenidle", "host-redirecttojob", "host-removetags",
  "host-renametag", "host-setallocation", "host-sethardwarestate",
  "host-takeownership", "host-unlock",
  "job-addcomment", "job-addrenderpart", "job-addsubscriber",
  "job-createdependonframe", "job-createdependonjob", "job-createdependonlayer",
  "job-dropdepends", "job-eatframes", "job-getdepends",
  "job-getwhatdependsonthis", "job-kill", "job-killframes",
  "job-markdoneframes", "job-pause", "job-reorderframes", "job-retryframes",
  "job-setautoeat", "job-setmaxcores", "job-setmaxgpus", "job-setmaxretries",
  "job-setmincores", "job-setmingpus", "job-setpriority", "job-staggerframes",
  "job-unpause",
  "layer-createdependonframe", "layer-createdependonjob",
  "layer-createdependonlayer", "layer-createframebyframedepend",
  "layer-eatframes", "layer-getdepends", "layer-getoutputpaths", "layer-kill",
  "layer-markdone", "layer-reorderframes", "layer-retryframes",
  "layer-setmincores", "layer-setmingpumemory", "layer-setminmemory",
  "layer-settags", "layer-setthreadable", "layer-staggerframes",
  "limit-create", "limit-delete", "limit-rename", "limit-setmaxvalue",
  "proc-kill", "proc-unbook", "proc-unbookone",
  "show-createsubscription", "show-enablebooking", "show-enabledispatching",
  "show-setcommentemail", "show-setdefaultmaxcores", "show-setdefaultmincores",
  // client-only actions (not gateway action routes)
  "job-submit", "view-save", "view-apply", "redirect", "other",
] as const;

type Page = (typeof ALLOWED_PAGES)[number];
type Action = (typeof ALLOWED_ACTIONS)[number];

function normalize<T extends readonly string[]>(
  value: string,
  allowed: T,
): T[number] {
  return (allowed as readonly string[]).includes(value)
    ? (value as T[number])
    : ("other" as T[number]);
}

// HTTP status bucket so the API counter stays small (3 classes, not 1/status).
function statusClass(status: number): string {
  if (status >= 500) return "5xx";
  if (status >= 400) return "4xx";
  if (status >= 300) return "3xx";
  return "2xx";
}

class MetricsService {
  private static instance: MetricsService;
  private registry: Registry;

  // Generic counter store kept for backwards compatibility with the original
  // registerCounter/incrementCounter API (used by /api/increment).
  private counters: Map<string, Counter>;

  // Pre-registered usage metrics.
  private pageViews!: Counter;
  private actions!: Counter;
  private apiRequests!: Counter;
  private apiDuration!: Histogram;
  private logins!: Counter;
  private facilitySelected!: Counter;

  private constructor() {
    this.registry = new Registry();
    this.counters = new Map();

    this.pageViews = new Counter({
      name: "cueweb_page_views_total",
      help: "CueWeb page/module views, by user and page",
      labelNames: ["user", "page"],
      registers: [this.registry],
    });
    this.actions = new Counter({
      name: "cueweb_actions_total",
      help: "CueWeb user actions, by user and action",
      labelNames: ["user", "action"],
      registers: [this.registry],
    });
    this.apiRequests = new Counter({
      name: "cueweb_api_requests_total",
      help: "CueWeb gateway-proxy API calls, by endpoint and status class",
      labelNames: ["endpoint", "status"],
      registers: [this.registry],
    });
    this.apiDuration = new Histogram({
      name: "cueweb_api_request_duration_seconds",
      help: "CueWeb gateway-proxy API latency in seconds, by endpoint",
      labelNames: ["endpoint"],
      buckets: [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
      registers: [this.registry],
    });
    this.logins = new Counter({
      name: "cueweb_logins_total",
      help: "CueWeb session starts, by user",
      labelNames: ["user"],
      registers: [this.registry],
    });
    this.facilitySelected = new Counter({
      name: "cueweb_facility_selected_total",
      help: "Cuebot Facility switches, by user and facility",
      labelNames: ["user", "facility"],
      registers: [this.registry],
    });
  }

  public static getInstance(): MetricsService {
    if (!MetricsService.instance) {
      MetricsService.instance = new MetricsService();
    }
    return MetricsService.instance;
  }

  // --- Usage helpers --------------------------------------------------------

  public recordPageView(user: string, page: string): void {
    this.pageViews.inc({ user, page: normalize(page, ALLOWED_PAGES) });
  }

  public recordAction(user: string, action: string): void {
    this.actions.inc({ user, action: normalize(action, ALLOWED_ACTIONS) });
  }

  public recordApiRequest(endpoint: string, status: number, durationSeconds: number): void {
    this.apiRequests.inc({ endpoint, status: statusClass(status) });
    this.apiDuration.observe({ endpoint }, durationSeconds);
  }

  public recordLogin(user: string): void {
    this.logins.inc({ user });
  }

  public recordFacility(user: string, facility: string): void {
    this.facilitySelected.inc({ user, facility });
  }

  // --- Back-compat generic counter API (used by /api/increment) -------------

  public registerCounter(name: string, help: string): Counter | undefined {
    if (!this.counters.has(name)) {
      const counter = new Counter({
        name,
        help,
        registers: [this.registry],
        labelNames: ["user"],
      });
      this.counters.set(name, counter);
    }
    return this.counters.get(name);
  }

  public incrementCounter(name: string, username: string): void {
    const counter = this.counters.get(name);
    if (counter) {
      counter.inc({ user: username });
    } else {
      console.warn(`Counter ${name} not found`);
    }
  }

  public async getMetrics(): Promise<string> {
    return this.registry.metrics();
  }
}

export default MetricsService;
export type { Page, Action };
