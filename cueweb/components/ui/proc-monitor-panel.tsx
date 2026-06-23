"use client";

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

import * as React from "react";
import { useRouter } from "next/navigation";

import type { Proc } from "@/app/utils/get_utils";
import { getProcsByHosts } from "@/app/utils/get_utils";
import { killProcs, unbookProcs } from "@/app/utils/action_utils";
import { handleError } from "@/app/utils/notify_utils";
import { kbStringToHuman } from "@/app/hosts/host_format_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { VIEW_HOST_PROCS_EVENT, type ViewHostProcsDetail } from "@/components/ui/host-action-events";

const REFRESH_MS = 30000;

function fmtAge(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

type MenuState = { x: number; y: number; proc: Proc };

// The bottom "Proc monitor" panel of CueGUI's Monitor Hosts. Populated by the
// host panel's "View Procs" action (or by typing host names here), with a
// right-click menu mirroring CueGUI's ProcActions (View Job / Unbook / Kill /
// Unbook and Kill).
export function ProcMonitorPanel() {
  const router = useRouter();
  const [hostNames, setHostNames] = React.useState<string[]>([]);
  const [hostInput, setHostInput] = React.useState("");
  const [procs, setProcs] = React.useState<Proc[] | null>(null);
  const [autoRefresh, setAutoRefresh] = React.useState(true);
  const [now, setNow] = React.useState(() => Date.now() / 1000);
  const [menu, setMenu] = React.useState<MenuState | null>(null);
  const [busy, setBusy] = React.useState(false);

  // Monotonic token so out-of-order responses can't clobber a newer scope:
  // a quick A -> B switch must not let A's slower response land after B's.
  const loadSeq = React.useRef(0);
  const load = React.useCallback(async (names: string[], isCancelled?: () => boolean) => {
    const seq = ++loadSeq.current;
    if (names.length === 0) {
      setProcs(null);
      return;
    }
    try {
      const data = await getProcsByHosts(names);
      if (isCancelled?.() || seq !== loadSeq.current) return;
      setProcs(data);
      setNow(Date.now() / 1000);
    } catch (err) {
      if (isCancelled?.() || seq !== loadSeq.current) return;
      handleError(err, "Could not load procs");
      setProcs((prev) => prev ?? []);
    }
  }, []);

  // "View Procs" from the host panel sets the host scope.
  React.useEffect(() => {
    function handler(e: Event) {
      const names = (e as CustomEvent<ViewHostProcsDetail>).detail.hostNames;
      setHostNames(names);
      setHostInput(names.join(" "));
      load(names);
    }
    window.addEventListener(VIEW_HOST_PROCS_EVENT, handler);
    return () => window.removeEventListener(VIEW_HOST_PROCS_EVENT, handler);
  }, [load]);

  React.useEffect(() => {
    if (!autoRefresh || hostNames.length === 0) return;
    let cancelled = false;
    const id = setInterval(() => load(hostNames, () => cancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [autoRefresh, hostNames, load]);

  React.useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  function applyHostInput() {
    const names = hostInput.split(/[\s,]+/).filter(Boolean);
    setHostNames(names);
    load(names);
  }
  function clearAll() {
    setHostInput("");
    setHostNames([]);
    setProcs(null);
  }

  async function act(proc: Proc, fn: () => Promise<unknown>) {
    setBusy(true);
    setMenu(null);
    try {
      await fn();
      await load(hostNames);
    } finally {
      setBusy(false);
    }
  }

  const menuItemCls = "block w-full rounded px-2 py-1.5 text-left hover:bg-accent disabled:opacity-50";

  return (
    <div className="mt-6">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">Procs</span>
        <Input
          value={hostInput}
          onChange={(e) => setHostInput(e.target.value)}
          onBlur={applyHostInput}
          onKeyDown={(e) => e.key === "Enter" && applyHostInput()}
          placeholder="host names (space-separated)"
          className="h-8 w-72"
          aria-label="Proc host filter"
        />
        <Button variant="outline" size="sm" onClick={clearAll}>Clr</Button>
        <div className="ml-auto flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={autoRefresh} onCheckedChange={(c) => setAutoRefresh(!!c)} aria-label="Auto-refresh procs" />
            Auto-refresh
          </label>
          <Button size="sm" onClick={() => load(hostNames)} disabled={hostNames.length === 0}>Refresh</Button>
        </div>
      </div>

      {procs === null ? (
        <p className="text-sm text-muted-foreground">Right-click a host and choose &quot;View Procs&quot; to list its running procs here.</p>
      ) : procs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No procs running on the selected host(s).</p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left">
              <tr>
                <th className="p-2 font-medium">Name</th>
                <th className="p-2 font-medium">Cores</th>
                <th className="p-2 font-medium">Mem Reserved</th>
                <th className="p-2 font-medium">Mem Used</th>
                <th className="p-2 font-medium">GPU Used</th>
                <th className="p-2 font-medium">Age</th>
                <th className="p-2 font-medium">Unbooked</th>
                <th className="p-2 font-medium">Frame</th>
                <th className="p-2 font-medium">Job</th>
              </tr>
            </thead>
            <tbody>
              {procs.map((p) => (
                <tr
                  key={p.id || p.name}
                  className="cursor-context-menu border-b last:border-0 hover:bg-muted/20"
                  onContextMenu={(e) => {
                    e.preventDefault();
                    setMenu({ x: e.clientX, y: e.clientY, proc: p });
                  }}
                >
                  <td className="p-2">{p.name}</td>
                  <td className="p-2 tabular-nums">{(p.reservedCores ?? 0).toFixed(2)}</td>
                  <td className="p-2 tabular-nums">{kbStringToHuman(p.reservedMemory)}</td>
                  <td className="p-2 tabular-nums">{kbStringToHuman(p.usedMemory)}</td>
                  <td className="p-2 tabular-nums">{kbStringToHuman(p.reservedGpuMemory ?? "")}</td>
                  <td className="p-2 tabular-nums">{fmtAge(now - (p.dispatchTime ?? now))}</td>
                  <td className="p-2">{p.unbooked ? "Yes" : "No"}</td>
                  <td className="max-w-[20rem] truncate p-2" title={p.frameName}>{p.frameName}</td>
                  <td className="max-w-[16rem] truncate p-2" title={p.jobName}>{p.jobName}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {menu ? (
        <div
          className="fixed z-50 min-w-48 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={menuItemCls}
            onClick={() => {
              router.push(`/jobs/${encodeURIComponent(menu.proc.jobName)}?tab=overview`);
              setMenu(null);
            }}
          >
            View Job
          </button>
          <div className="my-1 h-px bg-border" />
          <button className={menuItemCls} disabled={busy} onClick={() => act(menu.proc, () => unbookProcs([menu.proc], false))}>
            Unbook
          </button>
          <button className={menuItemCls} disabled={busy} onClick={() => act(menu.proc, () => killProcs([menu.proc]))}>
            Kill
          </button>
          <button className={menuItemCls} disabled={busy} onClick={() => act(menu.proc, () => unbookProcs([menu.proc], true))}>
            Unbook and Kill
          </button>
        </div>
      ) : null}
    </div>
  );
}
