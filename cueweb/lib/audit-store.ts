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
 * Append-only audit store for CueWeb — the persistence layer of the "CueWeb
 * Audit" web system (Admin -> CueWeb Audit). It records who performed which
 * action, at what time, against which target, and whether it succeeded.
 *
 * The design deliberately mirrors `lib/facility-store.ts`: a single JSONL file
 * (one JSON record per line, newest appended last) under a configurable path.
 * This keeps CueWeb dependency-free and true to its otherwise-stateless design
 * — no database, no ORM, no new infrastructure. For a deployment where the
 * trail must survive container restarts, point `CUEWEB_AUDIT_STORE` at a
 * mounted volume.
 *
 *   CUEWEB_AUDIT_STORE        path to the JSONL audit file
 *                             (default: <os tmp>/cueweb-audit.jsonl)
 *   CUEWEB_AUDIT_MAX_RECORDS  hard cap on records kept in the file; older lines
 *                             are dropped on write (default: 50000, 0 = no cap)
 *
 * SERVER-ONLY: this module imports `node:fs` and must never reach the client
 * bundle. Only Route Handlers, Server Components and server-side auth callbacks
 * import from here (always dynamically from the gateway proxy path).
 */

import { promises as fs } from "fs";
import os from "os";
import path from "path";

/** High-level bucket an audited event belongs to. */
export type AuditCategory =
  | "job"
  | "frame"
  | "layer"
  | "group"
  | "host"
  | "proc"
  | "show"
  | "allocation"
  | "subscription"
  | "limit"
  | "service"
  | "filter"
  | "depend"
  | "owner"
  | "facility"
  | "auth"
  | "other";

/** Outcome of an audited event. */
export type AuditResult = "success" | "error";

/** A single audit record (one JSONL line). */
export interface AuditRecord {
  /** ISO-8601 timestamp of when the action was handled. */
  at: string;
  /** Who performed it (user email/name, or "anonymous" when auth is off). */
  actor: string;
  /** High-level category (job, host, auth, ...). */
  category: AuditCategory;
  /** Human-friendly action name, e.g. "Kill Job", "Pause", "Sign in". */
  action: string;
  /** Best-effort target identifier, e.g. "job:comp_v2" or "host:render01". */
  target?: string;
  /** Cuebot facility the action was routed to (when applicable). */
  facility?: string;
  /** Outcome. */
  result: AuditResult;
  /** Error message when result === "error". */
  error?: string;
  /** Sanitized, size-capped request parameters (no secrets, no large blobs). */
  details?: Record<string, unknown>;
  /** Underlying gRPC/REST endpoint, e.g. "/job.JobInterface/Kill". */
  endpoint?: string;
  /** HTTP method used against the gateway. */
  method?: string;
}

const STORE_PATH =
  process.env.CUEWEB_AUDIT_STORE || path.join(os.tmpdir(), "cueweb-audit.jsonl");

/** Hard cap on retained records (0 disables the cap). */
function maxRecords(): number {
  const raw = Number(process.env.CUEWEB_AUDIT_MAX_RECORDS);
  if (!Number.isFinite(raw) || raw < 0) return 50000;
  return Math.floor(raw);
}

// Serialize writes within this process so concurrent appends (Next.js does not
// serialize Route Handler invocations) can't interleave or lose the trim. A
// single CueWeb instance is one Node process, so chaining each write onto the
// previous is sufficient. A multi-instance deployment sharing the file would
// additionally want a cross-process lock (same caveat as facility-store.ts).
let writeChain: Promise<unknown> = Promise.resolve();

/**
 * Append one audit record. Best-effort and non-throwing: auditing must never
 * break the action it is recording, so all failures are swallowed (logged to
 * the server console only).
 */
export function recordAudit(record: AuditRecord): Promise<void> {
  const run = writeChain.then(() => doRecordAudit(record));
  // Keep the chain alive even if this write rejects, so one failure doesn't
  // break serialization for subsequent writes.
  writeChain = run.catch(() => undefined);
  return run.catch((err) => {
    console.error("[audit] failed to record event:", err);
  });
}

async function doRecordAudit(record: AuditRecord): Promise<void> {
  await fs.mkdir(path.dirname(STORE_PATH), { recursive: true });
  await fs.appendFile(STORE_PATH, JSON.stringify(record) + "\n", { mode: 0o600 });
  await trimIfNeeded();
}

// Drop the oldest lines once the file exceeds the cap. Cheap rewrite: the file
// is bounded (default 50k lines) so reading it fully on overflow is fine.
async function trimIfNeeded(): Promise<void> {
  const cap = maxRecords();
  if (cap === 0) return;
  let lines: string[];
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    lines = raw.split("\n").filter((l) => l.trim().length > 0);
  } catch {
    return;
  }
  if (lines.length <= cap) return;
  const kept = lines.slice(lines.length - cap);
  await fs.writeFile(STORE_PATH, kept.join("\n") + "\n", { mode: 0o600 });
}

/** Filters accepted by {@link readAudit}. All optional; combined with AND. */
export interface AuditQuery {
  /** Max records to return after filtering (default 200). */
  limit?: number;
  /** Skip this many matching records (for pagination). */
  offset?: number;
  /** Case-insensitive substring match on the actor. */
  actor?: string;
  /** Exact category match. */
  category?: string;
  /** Exact result match. */
  result?: AuditResult;
  /** Only records at/after this ISO timestamp. */
  since?: string;
  /** Only records at/before this ISO timestamp. */
  until?: string;
  /** Case-insensitive substring match across actor/action/target/error. */
  search?: string;
}

export interface AuditPage {
  /** Matching records, newest first. */
  records: AuditRecord[];
  /** Total number of records matching the filters (before limit/offset). */
  total: number;
}

/** Read the audit trail, newest first, applying the given filters. */
export async function readAudit(query: AuditQuery = {}): Promise<AuditPage> {
  let all: AuditRecord[];
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    all = raw
      .split("\n")
      .filter((l) => l.trim().length > 0)
      .map((l) => {
        try {
          return JSON.parse(l) as AuditRecord;
        } catch {
          return null;
        }
      })
      .filter((e): e is AuditRecord => e !== null);
  } catch {
    return { records: [], total: 0 };
  }

  // Newest first.
  all.reverse();

  const actor = query.actor?.trim().toLowerCase();
  const search = query.search?.trim().toLowerCase();
  const sinceMs = query.since ? Date.parse(query.since) : NaN;
  const untilMs = query.until ? Date.parse(query.until) : NaN;

  const filtered = all.filter((r) => {
    if (actor && !r.actor.toLowerCase().includes(actor)) return false;
    if (query.category && r.category !== query.category) return false;
    if (query.result && r.result !== query.result) return false;
    if (!Number.isNaN(sinceMs) && Date.parse(r.at) < sinceMs) return false;
    if (!Number.isNaN(untilMs) && Date.parse(r.at) > untilMs) return false;
    if (search) {
      const hay = `${r.actor} ${r.action} ${r.target ?? ""} ${r.error ?? ""}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  const offset = Math.max(0, query.offset ?? 0);
  const limit = Math.max(1, Math.min(query.limit ?? 200, 5000));
  return {
    records: filtered.slice(offset, offset + limit),
    total: filtered.length,
  };
}

/** Distinct actors and categories present in the trail (for filter dropdowns). */
export async function readAuditFacets(): Promise<{
  actors: string[];
  categories: string[];
}> {
  const { records } = await readAudit({ limit: 5000 });
  const actors = new Set<string>();
  const categories = new Set<string>();
  for (const r of records) {
    if (r.actor) actors.add(r.actor);
    if (r.category) categories.add(r.category);
  }
  return {
    actors: Array.from(actors).sort(),
    categories: Array.from(categories).sort(),
  };
}

/** Where the trail lives (shown to operators on the audit screen). */
export function auditStorePath(): string {
  return STORE_PATH;
}
