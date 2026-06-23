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
 * SERVER-ONLY capture layer for the CueWeb Audit web system.
 *
 * The single integration point is the gateway proxy (`app/utils/gateway_server.ts`
 * → `handleRoute`), which every state-changing CueWeb action funnels through.
 * For each call this module:
 *   1. decides whether the endpoint is a mutation worth auditing (reads such as
 *      GetJob / FindHost are skipped),
 *   2. resolves WHO (the signed-in user), WHEN (now), WHAT (a friendly action
 *      name + category), the TARGET (best-effort entity id), and the FACILITY,
 *   3. writes one record to the append-only store (`lib/audit-store.ts`).
 *
 * Auditing is best-effort: a failure here must never break the underlying
 * action, so `auditGatewayCall` never throws.
 */

import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import { getRequestFacilityTarget } from "@/lib/facility";
import {
  recordAudit,
  type AuditCategory,
  type AuditResult,
} from "@/lib/audit-store";

// Map a gRPC service interface (the part before "Interface") to a category.
const SERVICE_CATEGORY: Record<string, AuditCategory> = {
  job: "job",
  frame: "frame",
  layer: "layer",
  group: "group",
  host: "host",
  proc: "proc",
  show: "show",
  allocation: "allocation",
  subscription: "subscription",
  limit: "limit",
  service: "service",
  serviceoverride: "service",
  filter: "filter",
  action: "filter",
  matcher: "filter",
  depend: "depend",
  owner: "owner",
  deed: "owner",
  facility: "facility",
  department: "show",
  task: "show",
};

// Entity keys we look for in a request body to identify the action's target,
// in priority order (the first present wins).
const TARGET_KEYS = [
  "job",
  "frame",
  "layer",
  "group",
  "host",
  "proc",
  "show",
  "allocation",
  "subscription",
  "limit",
  "service",
  "filter",
  "depend",
  "owner",
  "deed",
  "facility",
  "department",
  "task",
] as const;

// Method-name prefixes that denote a read; calls matching these are not audited.
const READ_PREFIXES = ["get", "find", "lookup", "is", "status", "list", "query"];

// Keys never copied into the sanitized `details` snapshot.
const SECRET_KEY = /(pass|secret|token|credential|authorization)/i;

const MAX_DETAILS_CHARS = 1500;

/** Parse "/job.JobInterface/Kill" → { service: "job", method: "Kill" }. */
function parseEndpoint(endpoint: string): { service: string; method: string } | null {
  // Strip a leading slash, then split "<pkg>.<Interface>/<Method>".
  const m = endpoint.replace(/^\//, "").match(/^([a-zA-Z]+)\.[A-Za-z]+\/([A-Za-z0-9_]+)$/);
  if (!m) return null;
  return { service: m[1].toLowerCase(), method: m[2] };
}

/** True when the endpoint is a read-only query that should not be audited. */
function isReadMethod(method: string): boolean {
  const lower = method.toLowerCase();
  return READ_PREFIXES.some((p) => lower.startsWith(p));
}

// Friendlier labels for a few common methods; everything else is humanized
// from camelCase (e.g. "SetMaxCores" → "Set Max Cores").
const ACTION_LABELS: Record<string, string> = {
  Kill: "Kill",
  Pause: "Pause",
  Resume: "Resume",
  EatFrames: "Eat Frames",
  KillFrames: "Kill Frames",
  RetryFrames: "Retry Frames",
  MarkDoneFrames: "Mark Frames Done",
  StaggerFrames: "Stagger Frames",
  ReorderFrames: "Reorder Frames",
  SetMaxCores: "Set Max Cores",
  SetMinCores: "Set Min Cores",
  SetMaxGpus: "Set Max GPUs",
  SetMinGpus: "Set Min GPUs",
  SetMaxRetries: "Set Max Retries",
  SetPriority: "Set Priority",
  SetAutoEat: "Set Auto-Eat",
  AddComment: "Add Comment",
  AddRenderPartition: "Add Local Booking",
  LaunchSpecAndWait: "Submit Job",
  Lock: "Lock Host",
  Unlock: "Unlock Host",
  Reboot: "Reboot Host",
  RebootWhenIdle: "Reboot When Idle",
  SetHardwareState: "Set Hardware State",
  SetAllocation: "Set Allocation",
  TakeOwnership: "Take Ownership",
  AddTags: "Add Tags",
  RemoveTags: "Remove Tags",
  RenameTag: "Rename Tag",
  Delete: "Delete",
  RedirectToJob: "Redirect To Job",
};

function humanizeMethod(method: string): string {
  if (ACTION_LABELS[method]) return ACTION_LABELS[method];
  return method
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
}

/** Best-effort target string ("job:comp_v2") from a parsed request body. */
function extractTarget(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const obj = body as Record<string, unknown>;
  for (const key of TARGET_KEYS) {
    if (!(key in obj)) continue;
    const v = obj[key];
    if (typeof v === "string" && v.trim()) return `${key}:${v.trim()}`;
    if (v && typeof v === "object") {
      const e = v as Record<string, unknown>;
      const name = (e.name ?? e.id) as unknown;
      if (typeof name === "string" && name.trim()) return `${key}:${name.trim()}`;
    }
  }
  return undefined;
}

/**
 * Build a small, safe snapshot of the request parameters: entity objects are
 * collapsed to their name/id, secrets are dropped, nested objects keep only
 * their primitive fields, and the whole thing is size-capped.
 */
function sanitizeDetails(body: unknown): Record<string, unknown> | undefined {
  if (!body || typeof body !== "object") return undefined;
  const obj = body as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (SECRET_KEY.test(key)) continue;
    if (value === null || value === undefined) continue;
    if (typeof value !== "object") {
      out[key] = value;
      continue;
    }
    if ((TARGET_KEYS as readonly string[]).includes(key)) {
      const e = value as Record<string, unknown>;
      const id = e.name ?? e.id;
      if (id !== undefined) out[key] = id;
      continue;
    }
    // Generic nested object: keep only primitive sub-fields (e.g. req: {...}).
    const nested: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (SECRET_KEY.test(k)) continue;
      if (v !== null && typeof v !== "object") nested[k] = v;
    }
    if (Object.keys(nested).length) out[key] = nested;
  }
  if (!Object.keys(out).length) return undefined;
  // Size cap: if the snapshot is too big, drop it rather than bloat the log.
  if (JSON.stringify(out).length > MAX_DETAILS_CHARS) {
    return { note: "parameters omitted (too large)" };
  }
  return out;
}

async function resolveActor(): Promise<string> {
  try {
    const session = await getServerSession(authOptions);
    return session?.user?.email || session?.user?.name || "anonymous";
  } catch {
    return "anonymous";
  }
}

async function resolveFacility(): Promise<string | undefined> {
  try {
    const { name } = await getRequestFacilityTarget();
    return name || undefined;
  } catch {
    return undefined;
  }
}

/**
 * Audit one gateway call. Called from `handleRoute` for every proxied request;
 * returns immediately (no record) for reads and unparseable endpoints.
 *
 * @param endpoint gRPC/REST endpoint, e.g. "/job.JobInterface/Kill"
 * @param method   HTTP method used against the gateway
 * @param rawBody  the request body string forwarded to the gateway
 * @param ok       whether the gateway call succeeded
 * @param error    error message when ok === false
 */
export async function auditGatewayCall(
  endpoint: string,
  method: string,
  rawBody: string,
  ok: boolean,
  error?: string,
): Promise<void> {
  try {
    const parsed = parseEndpoint(endpoint);
    if (!parsed) return;
    if (isReadMethod(parsed.method)) return; // reads are not audited

    let body: unknown = undefined;
    try {
      body = rawBody ? JSON.parse(rawBody) : undefined;
    } catch {
      // Non-JSON body: still audit the action, just without details/target.
    }

    const category = SERVICE_CATEGORY[parsed.service] ?? "other";
    const [actor, facility] = await Promise.all([resolveActor(), resolveFacility()]);

    await recordAudit({
      at: new Date().toISOString(),
      actor,
      category,
      action: humanizeMethod(parsed.method),
      target: extractTarget(body),
      facility,
      result: (ok ? "success" : "error") as AuditResult,
      error: ok ? undefined : error,
      details: sanitizeDetails(body),
      endpoint,
      method,
    });
  } catch (err) {
    // Auditing must never break the action it records.
    console.error("[audit] auditGatewayCall failed:", err);
  }
}

/** Record an authentication event (sign-in / sign-out) from NextAuth callbacks. */
export async function auditAuthEvent(
  action: "Sign in" | "Sign out",
  actor: string,
): Promise<void> {
  try {
    await recordAudit({
      at: new Date().toISOString(),
      actor: actor || "anonymous",
      category: "auth",
      action,
      result: "success",
    });
  } catch (err) {
    console.error("[audit] auditAuthEvent failed:", err);
  }
}
