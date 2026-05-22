"use client";

/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import { Button } from "@/components/ui/button";

type AuditEntry = {
  id: number;
  ts: number;
  actor_id: number | null;
  actor_label: string;
  action: string;
  target: string | null;
  before_json: string | null;
  after_json: string | null;
};

export default function AuditPage() {
  const [entries, setEntries] = React.useState<AuditEntry[]>([]);
  const [action, setAction] = React.useState("");
  const [actor, setActor] = React.useState("");

  const refresh = React.useCallback(async () => {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (actor) params.set("actor", actor);
    const r = await fetch(`/api/admin/audit?${params}`).then((r) => r.json());
    setEntries(r.entries ?? []);
  }, [action, actor]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function loadMore() {
    if (entries.length === 0) return;
    const oldestId = entries[entries.length - 1].id;
    const params = new URLSearchParams({ beforeId: String(oldestId) });
    if (action) params.set("action", action);
    if (actor) params.set("actor", actor);
    const r = await fetch(`/api/admin/audit?${params}`).then((r) => r.json());
    setEntries((prev) => [...prev, ...(r.entries ?? [])]);
  }

  function exportCsv() {
    const header = "id,ts,actor_id,actor_label,action,target,before,after";
    const escape = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const rows = entries.map((e) =>
      [
        e.id,
        new Date(e.ts * 1000).toISOString(),
        e.actor_id ?? "",
        escape(e.actor_label),
        escape(e.action),
        escape(e.target ?? ""),
        escape(e.before_json ?? ""),
        escape(e.after_json ?? ""),
      ].join(","),
    );
    const blob = new Blob([`${header}\n${rows.join("\n")}`], {
      type: "text/csv",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cueweb-audit-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm space-y-1">
          <span className="font-medium">Action</span>
          <input
            value={action}
            onChange={(e) => setAction(e.target.value)}
            placeholder="user.create"
            className="block rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm space-y-1">
          <span className="font-medium">Actor</span>
          <input
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            placeholder="username, sub..."
            className="block rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <Button variant="outline" onClick={refresh}>
          Apply filters
        </Button>
        <Button variant="outline" onClick={exportCsv} className="ml-auto">
          Export current view to CSV
        </Button>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-foreground/5">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                When
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Actor
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Action
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Target
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Details
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="px-3 py-2 align-top whitespace-nowrap">
                  {new Date(e.ts * 1000).toISOString().replace("T", " ").slice(0, 19)}
                </td>
                <td className="px-3 py-2 align-top">{e.actor_label}</td>
                <td className="px-3 py-2 align-top font-mono text-xs">{e.action}</td>
                <td className="px-3 py-2 align-top">{e.target ?? ""}</td>
                <td className="px-3 py-2 align-top">
                  {(e.before_json || e.after_json) && (
                    <details>
                      <summary className="cursor-pointer text-xs text-foreground/70">
                        before/after
                      </summary>
                      <pre className="text-xs whitespace-pre-wrap break-all">
                        {[e.before_json && `before: ${e.before_json}`, e.after_json && `after: ${e.after_json}`]
                          .filter(Boolean)
                          .join("\n")}
                      </pre>
                    </details>
                  )}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-center text-foreground/60">
                  No audit entries.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {entries.length > 0 && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadMore}>
            Load older
          </Button>
        </div>
      )}
    </div>
  );
}
