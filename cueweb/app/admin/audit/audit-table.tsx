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
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

import type { AuditRecord } from "@/lib/audit-store";
import { cn } from "@/lib/utils";

interface Facets {
  actors: string[];
  categories: string[];
}

interface Props {
  initialRecords: AuditRecord[];
  initialTotal: number;
  facets: Facets;
}

// Selectable page sizes for the paginated table. Mirrors Monitor Jobs
// (app/jobs/data-table.tsx), minus 10000: readAudit() in lib/audit-store.ts
// hard-caps a single read at 5000, so a larger page would silently hide rows
// (the client would compute too few pages while the server returns only 5000).
const PAGE_SIZE_OPTIONS = [
  5, 10, 15, 20, 25, 50, 100, 200, 300, 400, 500, 1000, 2000, 3000, 4000, 5000,
];
// Default to 10, the same first-visit page size Monitor Jobs uses.
const DEFAULT_PAGE_SIZE = 10;

interface Filters {
  search: string;
  actor: string;
  category: string;
  result: "" | "success" | "error";
  since: string;
  until: string;
}

const EMPTY_FILTERS: Filters = {
  search: "",
  actor: "",
  category: "",
  result: "",
  since: "",
  until: "",
};

function fmtWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // Local, human-readable, second precision.
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// datetime-local value (YYYY-MM-DDTHH:mm) → ISO for the query string.
function localToIso(local: string): string {
  if (!local) return "";
  const d = new Date(local);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

function buildQuery(filters: Filters, limit: number, offset: number): string {
  const p = new URLSearchParams();
  p.set("limit", String(limit));
  p.set("offset", String(offset));
  if (filters.search) p.set("search", filters.search);
  if (filters.actor) p.set("actor", filters.actor);
  if (filters.category) p.set("category", filters.category);
  if (filters.result) p.set("result", filters.result);
  const since = localToIso(filters.since);
  const until = localToIso(filters.until);
  if (since) p.set("since", since);
  if (until) p.set("until", until);
  return p.toString();
}

function toCsv(records: AuditRecord[]): string {
  const header = [
    "at",
    "actor",
    "category",
    "action",
    "target",
    "facility",
    "result",
    "error",
    "endpoint",
  ];
  const esc = (v: unknown) => {
    const s = v === undefined || v === null ? "" : String(v);
    // Neutralize spreadsheet formula injection (CWE-1236): a cell beginning
    // with = + - @ (or a leading tab/CR that some apps strip) can execute as a
    // formula in Excel/Sheets. Prefix with a single quote so it's treated as
    // literal text. Audit values (actor/target/action/error) are attacker-
    // influenced, so this runs before CSV quoting.
    const neutralized = /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
    return /[",\n]/.test(neutralized)
      ? `"${neutralized.replace(/"/g, '""')}"`
      : neutralized;
  };
  const rows = records.map((r) =>
    [r.at, r.actor, r.category, r.action, r.target, r.facility, r.result, r.error, r.endpoint]
      .map(esc)
      .join(","),
  );
  return [header.join(","), ...rows].join("\n");
}

export function AuditTable({ initialRecords, initialTotal, facets }: Props) {
  const [filters, setFilters] = React.useState<Filters>(EMPTY_FILTERS);
  const [records, setRecords] = React.useState<AuditRecord[]>(initialRecords);
  const [total, setTotal] = React.useState<number>(initialTotal);
  const [facetState, setFacetState] = React.useState<Facets>(facets);
  const [page, setPage] = React.useState<number>(0); // 0-based page index
  const [pageSize, setPageSize] = React.useState<number>(DEFAULT_PAGE_SIZE);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [expanded, setExpanded] = React.useState<Set<number>>(new Set());
  const [autoRefresh, setAutoRefresh] = React.useState<boolean>(false);

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Track the latest request so a slow earlier fetch can't overwrite a newer
  // one (last-write-wins by sequence number).
  const seq = React.useRef(0);

  const fetchPage = React.useCallback(
    async (nextPage: number) => {
      const mySeq = ++seq.current;
      setLoading(true);
      setError(null);
      try {
        const qs = buildQuery(filters, pageSize, nextPage * pageSize);
        const res = await fetch(`/api/admin/audit?${qs}`, { cache: "no-store" });
        const data = await res.json();
        if (mySeq !== seq.current) return; // a newer request superseded this one
        if (!res.ok) {
          setError(data?.error ?? "Failed to load audit trail.");
          return;
        }
        setTotal(data.total ?? 0);
        if (data.facets) setFacetState(data.facets);
        setRecords(data.records ?? []);
        setExpanded(new Set());
        setPage(nextPage);
      } catch {
        if (mySeq === seq.current) setError("Failed to load audit trail.");
      } finally {
        if (mySeq === seq.current) setLoading(false);
      }
    },
    [filters, pageSize],
  );

  // Re-query the first page whenever the filters or page size change, debounced
  // so typing in the search box doesn't fire a request per keystroke.
  React.useEffect(() => {
    const t = setTimeout(() => {
      fetchPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [fetchPage]);

  // Optional polling so a live ops view stays current. Refresh the page the
  // user is currently viewing rather than jumping back to the top.
  React.useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchPage(page), 10000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchPage, page]);

  const hasFilters = React.useMemo(
    () => JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS),
    [filters],
  );

  const setField = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setFilters((f) => ({ ...f, [key]: value }));

  const exportCsv = () => {
    const blob = new Blob([toCsv(records)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cueweb-audit-${new Date().toISOString().slice(0, 19)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleExpand = (i: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  return (
    <div>
      {/* Filter bar */}
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <div className="relative w-full sm:w-auto">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={filters.search}
            onChange={(e) => setField("search", e.target.value)}
            placeholder="Search actor / action / target"
            aria-label="Search audit trail"
            className="h-8 w-full rounded-md border border-border bg-background pl-7 pr-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring sm:w-64"
          />
        </div>

        <select
          value={filters.actor}
          onChange={(e) => setField("actor", e.target.value)}
          aria-label="Filter by actor"
          className="h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All actors</option>
          {facetState.actors.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        <select
          value={filters.category}
          onChange={(e) => setField("category", e.target.value)}
          aria-label="Filter by category"
          className="h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All categories</option>
          {facetState.categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          value={filters.result}
          onChange={(e) => setField("result", e.target.value as Filters["result"])}
          aria-label="Filter by result"
          className="h-8 rounded-md border border-border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">Any result</option>
          <option value="success">Success</option>
          <option value="error">Error</option>
        </select>

        <label className="flex items-center gap-1 text-[11px] text-muted-foreground">
          From
          <input
            type="datetime-local"
            value={filters.since}
            onChange={(e) => setField("since", e.target.value)}
            aria-label="From date"
            className="h-8 rounded-md border border-border bg-background px-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </label>
        <label className="flex items-center gap-1 text-[11px] text-muted-foreground">
          To
          <input
            type="datetime-local"
            value={filters.until}
            onChange={(e) => setField("until", e.target.value)}
            aria-label="To date"
            className="h-8 rounded-md border border-border bg-background px-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </label>

        {hasFilters && (
          <button
            type="button"
            onClick={() => setFilters(EMPTY_FILTERS)}
            className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2 text-xs text-muted-foreground hover:bg-foreground/5"
          >
            <X className="h-3.5 w-3.5" /> Clear
          </button>
        )}

        <div className="ml-auto flex items-center gap-2">
          <label className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button
            type="button"
            onClick={() => fetchPage(page)}
            disabled={loading}
            className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2 text-xs hover:bg-foreground/5 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            type="button"
            onClick={exportCsv}
            disabled={records.length === 0}
            className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2 text-xs hover:bg-foreground/5 disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-3 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">When</th>
              <th className="px-3 py-2 font-medium">Actor</th>
              <th className="px-3 py-2 font-medium">Category</th>
              <th className="px-3 py-2 font-medium">Action</th>
              <th className="px-3 py-2 font-medium">Target</th>
              <th className="px-3 py-2 font-medium">Facility</th>
              <th className="px-3 py-2 font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-muted-foreground">
                  {loading ? "Loading…" : "No audit records match the current filters."}
                </td>
              </tr>
            ) : (
              records.map((r, i) => {
                const isOpen = expanded.has(i);
                const hasDetails = r.details && Object.keys(r.details).length > 0;
                return (
                  <React.Fragment key={`${r.at}-${i}`}>
                    <tr
                      className={cn(
                        "border-t border-border align-top",
                        (hasDetails || r.error) && "cursor-pointer hover:bg-foreground/5",
                      )}
                      onClick={() => (hasDetails || r.error) && toggleExpand(i)}
                    >
                      <td className="whitespace-nowrap px-3 py-1.5 font-mono">{fmtWhen(r.at)}</td>
                      <td className="px-3 py-1.5">{r.actor}</td>
                      <td className="px-3 py-1.5">
                        <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                          {r.category}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 font-medium">{r.action}</td>
                      <td className="px-3 py-1.5 font-mono text-muted-foreground">
                        {r.target ?? "—"}
                      </td>
                      <td className="px-3 py-1.5">{r.facility ?? "—"}</td>
                      <td className="px-3 py-1.5">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase",
                            r.result === "success"
                              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                              : "bg-red-500/15 text-red-700 dark:text-red-300",
                          )}
                        >
                          {r.result}
                        </span>
                      </td>
                    </tr>
                    {isOpen && (hasDetails || r.error) && (
                      <tr className="border-t border-border bg-muted/20">
                        <td colSpan={7} className="px-3 py-2">
                          {r.error && (
                            <div className="mb-1 text-red-600 dark:text-red-400">
                              <span className="font-semibold">Error:</span> {r.error}
                            </div>
                          )}
                          {hasDetails && (
                            <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] text-muted-foreground">
                              {JSON.stringify(r.details, null, 2)}
                            </pre>
                          )}
                          {r.endpoint && (
                            <div className="mt-1 text-[10px] text-muted-foreground">
                              {r.method} {r.endpoint}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-3">
          <span>
            {total === 0
              ? "No records"
              : `Showing ${page * pageSize + 1}–${Math.min(
                  total,
                  (page + 1) * pageSize,
                )} of ${total} record${total === 1 ? "" : "s"}`}
          </span>
          <label className="flex items-center gap-1">
            Rows per page
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              aria-label="Rows per page"
              className="h-7 rounded-md border border-border bg-background px-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex items-center gap-2">
          <span>
            Page {page + 1} of {pageCount}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => fetchPage(0)}
              disabled={loading || page === 0}
              aria-label="First page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border hover:bg-foreground/5 disabled:opacity-40"
            >
              <ChevronsLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => fetchPage(page - 1)}
              disabled={loading || page === 0}
              aria-label="Previous page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border hover:bg-foreground/5 disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => fetchPage(page + 1)}
              disabled={loading || page >= pageCount - 1}
              aria-label="Next page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border hover:bg-foreground/5 disabled:opacity-40"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => fetchPage(pageCount - 1)}
              disabled={loading || page >= pageCount - 1}
              aria-label="Last page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border hover:bg-foreground/5 disabled:opacity-40"
            >
              <ChevronsRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
