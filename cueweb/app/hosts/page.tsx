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
import { ChevronDown } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Host, getHosts } from "@/app/utils/get_utils";
import { setAttributeSelection } from "@/app/utils/use_attribute_selection";
import { hostColumns, hostRowClassName } from "@/app/hosts/columns";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { HostLockDialog } from "@/components/ui/host-lock-dialog";
import { HostRebootDialog } from "@/components/ui/host-reboot-dialog";
import { EditHostTagsDialog } from "@/components/ui/edit-host-tags-dialog";
import { HostMonitorDialogs } from "@/components/ui/host-monitor-dialogs";
import { ProcMonitorPanel } from "@/components/ui/proc-monitor-panel";
import { HOSTS_CHANGED_EVENT, type HostsChangedDetail } from "@/components/ui/host-action-events";

const REFRESH_MS = 30000;
const HARDWARE_STATES = ["UP", "DOWN", "REBOOTING", "REBOOT_WHEN_IDLE", "REPAIR"];
const LOCK_STATES = ["OPEN", "LOCKED", "NIMBY_LOCKED"];

function FilterMenu({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  function toggle(value: string, checked: boolean) {
    const next = new Set(selected);
    if (checked) next.add(value);
    else next.delete(value);
    onChange(next);
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          {label}
          {selected.size ? ` (${selected.size})` : ""}
          <ChevronDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-80 overflow-y-auto">
        <DropdownMenuItem onSelect={() => onChange(new Set())}>Clear</DropdownMenuItem>
        <DropdownMenuSeparator />
        {options.length === 0 ? (
          <div className="px-2 py-1.5 text-sm text-muted-foreground">None</div>
        ) : (
          options.map((o) => (
            <DropdownMenuCheckboxItem
              key={o}
              checked={selected.has(o)}
              onCheckedChange={(c) => toggle(o, !!c)}
              onSelect={(e) => e.preventDefault()}
            >
              {o}
            </DropdownMenuCheckboxItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Filter state is mirrored in the URL query string (CueGUI keeps it in the
// plugin session; the web equivalent is a shareable/bookmarkable URL):
//   ?q=<regex>&alloc=a,b&hw=UP,DOWN&lock=OPEN&os=rhel9
function parseSetParam(params: URLSearchParams, key: string): Set<string> {
  return new Set(
    (params.get(key) ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
}

function HostsPageInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [hosts, setHosts] = React.useState<Host[] | null>(null);
  // Host row clicked into the Attributes panel (CueGUI parity).
  const [selectedHostId, setSelectedHostId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = React.useState(true);

  // Seed filters from the URL once on mount (initializers run a single time).
  const [search, setSearch] = React.useState(() => searchParams.get("q") ?? "");
  const [allocFilter, setAllocFilter] = React.useState<Set<string>>(() => parseSetParam(searchParams, "alloc"));
  const [hwFilter, setHwFilter] = React.useState<Set<string>>(() => parseSetParam(searchParams, "hw"));
  const [lockFilter, setLockFilter] = React.useState<Set<string>>(() => parseSetParam(searchParams, "lock"));
  const [osFilter, setOsFilter] = React.useState<Set<string>>(() => parseSetParam(searchParams, "os"));

  // Keep the URL in sync as filters change (replace, so we don't spam history).
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (search.trim()) params.set("q", search.trim());
    if (allocFilter.size) params.set("alloc", Array.from(allocFilter).join(","));
    if (hwFilter.size) params.set("hw", Array.from(hwFilter).join(","));
    if (lockFilter.size) params.set("lock", Array.from(lockFilter).join(","));
    if (osFilter.size) params.set("os", Array.from(osFilter).join(","));
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [search, allocFilter, hwFilter, lockFilter, osFilter, pathname, router]);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getHosts();
      if (isCancelled?.()) return;
      setHosts(data);
      setError(null);
    } catch (err) {
      if (isCancelled?.()) return;
      setError(err instanceof Error ? err.message : String(err));
      setHosts((prev) => prev ?? []);
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;
    load(isCancelled);
    if (!autoRefresh) return () => { cancelled = true; };
    const interval = setInterval(() => load(isCancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [load, autoRefresh]);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<HostsChangedDetail>).detail;
      if (!detail?.hostIds?.length || !detail.patch) return;
      const ids = new Set(detail.hostIds);
      setHosts((prev) => (prev ? prev.map((h) => (ids.has(h.id) ? { ...h, ...detail.patch } : h)) : prev));
      load();
    }
    window.addEventListener(HOSTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(HOSTS_CHANGED_EVENT, handler);
  }, [load]);

  const allocOptions = React.useMemo(
    () => Array.from(new Set((hosts ?? []).map((h) => h.allocName).filter(Boolean) as string[])).sort(),
    [hosts],
  );
  const osOptions = React.useMemo(
    () => Array.from(new Set((hosts ?? []).map((h) => h.os).filter(Boolean) as string[])).sort(),
    [hosts],
  );

  const filtered = React.useMemo(() => {
    if (!hosts) return null;
    let nameRe: RegExp | null = null;
    if (search.trim()) {
      try {
        nameRe = new RegExp(search.trim(), "i");
      } catch {
        nameRe = null;
      }
    }
    const term = search.trim().toLowerCase();
    return hosts.filter((h) => {
      if (search.trim()) {
        const ok = nameRe ? nameRe.test(h.name) : h.name.toLowerCase().includes(term);
        if (!ok) return false;
      }
      if (allocFilter.size && !(h.allocName && allocFilter.has(h.allocName))) return false;
      if (hwFilter.size && !hwFilter.has(h.state)) return false;
      if (lockFilter.size && !lockFilter.has(h.lockState)) return false;
      if (osFilter.size && !(h.os && osFilter.has(h.os))) return false;
      return true;
    });
  }, [hosts, search, allocFilter, hwFilter, lockFilter, osFilter]);

  function clearFilters() {
    setSearch("");
    setAllocFilter(new Set());
    setHwFilter(new Set());
    setLockFilter(new Set());
    setOsFilter(new Set());
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Monitor Hosts</h1>

      {/* Filter bar (CueGUI parity). */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter hosts (name / regex)"
          className="h-8 w-64"
          aria-label="Filter hosts"
        />
        <Button variant="outline" size="sm" className="h-8" onClick={() => setSearch("")}>Clr</Button>
        <FilterMenu label="Filter Allocation" options={allocOptions} selected={allocFilter} onChange={setAllocFilter} />
        <FilterMenu label="Filter HardwareState" options={HARDWARE_STATES} selected={hwFilter} onChange={setHwFilter} />
        <FilterMenu label="Filter LockState" options={LOCK_STATES} selected={lockFilter} onChange={setLockFilter} />
        <FilterMenu label="Filter OS" options={osOptions} selected={osFilter} onChange={setOsFilter} />
        <div className="ml-auto flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={autoRefresh} onCheckedChange={(c) => setAutoRefresh(!!c)} aria-label="Auto-refresh" />
            Auto-refresh
          </label>
          <Button size="sm" className="h-8" onClick={() => load()}>Refresh</Button>
          <Button variant="outline" size="sm" className="h-8" onClick={clearFilters}>Clear</Button>
        </div>
      </div>

      {filtered === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <>
          {error && hosts && hosts.length === 0 ? (
            <div className="mb-3 flex items-center gap-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
              <span>Could not load hosts from Cuebot.</span>
              <Button size="sm" variant="outline" onClick={() => load()}>Retry</Button>
            </div>
          ) : null}
          <SimpleDataTable
            columns={hostColumns}
            data={filtered}
            username=""
            isHostsTable
            getRowClassName={hostRowClassName}
            columnVisibilityStorageKey="cueweb.hosts.columnVisibility"
            // Click a host row to load it into the Attributes panel.
            onRowClick={(host) => {
              const h = host as Host;
              setSelectedHostId(h.id);
              setAttributeSelection({
                type: "host",
                id: h.id,
                name: h.name,
                data: h as unknown as Record<string, unknown>,
              });
            }}
            selectedRowId={selectedHostId}
          />
        </>
      )}

      {/* Bottom proc panel (View Procs). */}
      <ProcMonitorPanel />

      {/* Dialogs opened by the host row context menu. */}
      <HostLockDialog />
      <HostRebootDialog />
      <EditHostTagsDialog />
      <HostMonitorDialogs />
    </div>
  );
}

// useSearchParams() requires a Suspense boundary for this client route.
export default function HostsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="space-y-2 p-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      }
    >
      <HostsPageInner />
    </React.Suspense>
  );
}
