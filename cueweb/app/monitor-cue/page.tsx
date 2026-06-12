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
import Link from "next/link";
import { useSession } from "next-auth/react";
import type { Row } from "@tanstack/react-table";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

import type { Job } from "@/app/jobs/columns";
import { Show, getActiveShows, getJobs } from "@/app/utils/get_utils";
import {
  eatJobsDeadFrames,
  killJobs,
  pauseJobs,
  retryJobsDeadFrames,
  unpauseJobs,
} from "@/app/utils/action_utils";
import { handleError, toastWarning } from "@/app/utils/notify_utils";
import { convertMemoryToString, secondsToHHHMM } from "@/app/utils/layers_frames_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { JobProgressBar } from "@/components/ui/job-progress-bar";
import { JobContextMenu } from "@/components/ui/context_menus/action-context-menu";
import { useContextMenu } from "@/components/ui/context_menus/useContextMenu";
// Job action dialogs the JobContextMenu opens via CustomEvents.
import { DependencyWizardDialog } from "@/components/ui/dependency-wizard-dialog";
import { EmailArtistDialog } from "@/components/ui/email-artist-dialog";
import { RequestCoresDialog } from "@/components/ui/request-cores-dialog";
import { SetCoresDialog } from "@/components/ui/set-cores-dialog";
import { SetPriorityDialog } from "@/components/ui/set-priority-dialog";
import { SubscribeToJobDialog } from "@/components/ui/subscribe-to-job-dialog";
import { UnbookDialog } from "@/components/ui/unbook-dialog";
import { ViewDependenciesDialog } from "@/components/ui/view-dependencies-dialog";

const REFRESH_MS = 5000;
const SELECTED_SHOWS_KEY = "cueweb.monitor-cue.shows";

const mem = (kb?: string) => {
  const n = Number(kb ?? 0);
  return Number.isFinite(n) && n > 0 ? convertMemoryToString(n, "job") : "0K";
};

// CueGUI JobWidgetItem row tint.
function jobRowClass(j: Job): string {
  const s = j.jobStats;
  if (j.isPaused) return "bg-blue-950/40";
  if ((s?.deadFrames ?? 0) > 0) return "bg-red-950/40";
  if ((s?.runningFrames ?? 0) === 0) {
    if ((s?.waitingFrames ?? 0) === 0 && (s?.dependFrames ?? 0) > 0) return "bg-purple-950/40";
    if ((s?.waitingFrames ?? 0) > 0) return "bg-green-950/30";
  }
  return "";
}

const NUM_COLS: { key: string; label: string; get: (j: Job) => React.ReactNode; title: string }[] = [
  { key: "run", label: "Run", get: (j) => j.jobStats?.runningFrames ?? 0, title: "Running frames" },
  { key: "cores", label: "Cores", get: (j) => (j.jobStats?.reservedCores ?? 0).toFixed(2), title: "Reserved cores" },
  { key: "gpus", label: "Gpus", get: (j) => j.jobStats?.reservedGpus ?? 0, title: "Reserved GPUs" },
  { key: "wait", label: "Wait", get: (j) => j.jobStats?.waitingFrames ?? 0, title: "Waiting frames" },
  { key: "depend", label: "Depend", get: (j) => j.jobStats?.dependFrames ?? 0, title: "Dependent frames" },
  { key: "total", label: "Total", get: (j) => j.jobStats?.totalFrames ?? 0, title: "Total frames" },
  { key: "min", label: "Min", get: (j) => Math.round(j.minCores ?? 0), title: "Minimum cores" },
  { key: "max", label: "Max", get: (j) => Math.round(j.maxCores ?? 0), title: "Maximum cores" },
  { key: "ming", label: "Min G", get: (j) => j.minGpus ?? 0, title: "Minimum GPUs" },
  { key: "maxg", label: "Max G", get: (j) => j.maxGpus ?? 0, title: "Maximum GPUs" },
  { key: "pri", label: "Pri", get: (j) => j.priority ?? 0, title: "Priority" },
  { key: "eta", label: "ETA", get: () => "", title: "ETA (disabled, as in CueGUI)" },
  { key: "maxrss", label: "MaxRss", get: (j) => mem(j.jobStats?.maxRss), title: "Peak memory of any single frame" },
  { key: "maxgpu", label: "MaxGpuMem", get: (j) => mem(j.jobStats?.maxGpuMemory), title: "Peak GPU memory of any single frame" },
];

export default function MonitorCuePage() {
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email?.split("@")[0] ?? "";

  const [shows, setShows] = React.useState<Show[]>([]);
  const [selectedShows, setSelectedShows] = React.useState<string[]>([]);
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [now, setNow] = React.useState(() => Date.now() / 1000);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());
  const [selectText, setSelectText] = React.useState("");
  const [autoRefresh, setAutoRefresh] = React.useState(true);
  const [killConfirm, setKillConfirm] = React.useState(false);

  const tableRef = React.useRef<HTMLDivElement>(null);
  const { contextMenuState, contextMenuHandleOpen, contextMenuHandleClose, contextMenuRef, contextMenuTargetAreaRef } =
    useContextMenu(tableRef);

  // Active shows for the "Shows" menu; restore the prior selection.
  React.useEffect(() => {
    getActiveShows()
      .then((data) => {
        setShows(data);
        const stored = window.localStorage.getItem(SELECTED_SHOWS_KEY);
        if (stored) {
          try {
            const names: string[] = JSON.parse(stored);
            setSelectedShows(names.filter((n) => data.some((s) => s.name === n)));
          } catch {
            /* ignore */
          }
        }
      })
      .catch((err) => handleError(err, "Could not load shows"));
  }, []);

  const persistShows = React.useCallback((names: string[]) => {
    setSelectedShows(names);
    window.localStorage.setItem(SELECTED_SHOWS_KEY, JSON.stringify(names));
  }, []);

  const load = React.useCallback(
    async (showNames: string[], isCancelled?: () => boolean) => {
      if (showNames.length === 0) {
        setJobs(null);
        return;
      }
      try {
        const data = await getJobs(JSON.stringify({ r: { shows: showNames, include_finished: false } }));
        if (isCancelled?.()) return;
        setJobs(data);
        setNow(Date.now() / 1000);
      } catch (err) {
        if (isCancelled?.()) return;
        handleError(err, "Could not load jobs");
        setJobs((prev) => prev ?? []);
      }
    },
    [],
  );

  React.useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;
    load(selectedShows, isCancelled);
    if (!autoRefresh) return () => { cancelled = true; };
    const id = setInterval(() => load(selectedShows, isCancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedShows, autoRefresh, load]);

  // Group jobs by show, sorted; jobs sorted by name within each show.
  const groups = React.useMemo(() => {
    if (!jobs) return null;
    const byShow = new Map<string, Job[]>();
    for (const j of jobs) {
      const arr = byShow.get(j.show) ?? [];
      arr.push(j);
      byShow.set(j.show, arr);
    }
    return Array.from(byShow.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([show, js]) => ({ show, jobs: js.sort((a, b) => a.name.localeCompare(b.name)) }));
  }, [jobs]);

  const selectedJobs = React.useMemo(
    () => (jobs ?? []).filter((j) => selected.has(j.id)),
    [jobs, selected],
  );

  function toggleJob(id: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }
  function toggleShowCollapse(show: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(show)) next.delete(show);
      else next.add(show);
      return next;
    });
  }

  function toggleShowFilter(name: string, checked: boolean) {
    persistShows(checked ? [...selectedShows, name] : selectedShows.filter((n) => n !== name));
  }

  // "Select:" search selects matching rows; "selectMine" selects the user's jobs.
  function applySelect(text: string) {
    if (!jobs) return;
    let re: RegExp | null = null;
    try {
      re = text ? new RegExp(text, "i") : null;
    } catch {
      re = null;
    }
    const term = text.toLowerCase();
    const match = (j: Job) => (re ? re.test(j.name) : j.name.toLowerCase().includes(term));
    setSelected(new Set(jobs.filter((j) => text && match(j)).map((j) => j.id)));
  }
  function selectMine() {
    if (!jobs || !username) return;
    setSelected(new Set(jobs.filter((j) => j.user === username || j.name.includes(`-${username}_`)).map((j) => j.id)));
  }

  function requireSelection(): Job[] | null {
    if (selectedJobs.length === 0) {
      toastWarning("Select one or more jobs first.");
      return null;
    }
    return selectedJobs;
  }

  async function refresh() {
    await load(selectedShows);
  }
  async function doEat() {
    const js = requireSelection();
    if (js) {
      await eatJobsDeadFrames(js);
      refresh();
    }
  }
  async function doRetry() {
    const js = requireSelection();
    if (js) {
      await retryJobsDeadFrames(js);
      refresh();
    }
  }
  async function doPause() {
    const js = requireSelection();
    if (js) {
      await pauseJobs(js);
      refresh();
    }
  }
  async function doUnpause() {
    const js = requireSelection();
    if (js) {
      await unpauseJobs(js);
      refresh();
    }
  }
  function doKill() {
    if (requireSelection()) setKillConfirm(true);
  }

  const sortedShowNames = React.useMemo(
    () => shows.map((s) => s.name).sort((a, b) => a.localeCompare(b)),
    [shows],
  );

  // Setter passed to JobContextMenu (its Unmonitor/Kill actions update the list).
  const setTableDataProp = React.useCallback(((updater: any) => {
    setJobs((prev) => {
      const cur = prev ?? [];
      return typeof updater === "function" ? updater(cur) : updater;
    });
  }) as React.Dispatch<React.SetStateAction<Job[]>>, []);

  const totalJobs = jobs?.length ?? 0;

  return (
    <div className="p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h1 className="mr-2 text-lg font-semibold">Monitor Cue</h1>

        {/* Shows multi-select */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              Shows{selectedShows.length ? ` (${selectedShows.length})` : ""}
              <ChevronDown className="ml-1 h-3 w-3 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-96 overflow-y-auto">
            <DropdownMenuItem onSelect={() => persistShows(sortedShowNames)}>All Shows</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => persistShows([])}>Clear</DropdownMenuItem>
            <DropdownMenuSeparator />
            {sortedShowNames.map((name) => (
              <DropdownMenuCheckboxItem
                key={name}
                checked={selectedShows.includes(name)}
                onCheckedChange={(c) => toggleShowFilter(name, !!c)}
                onSelect={(e) => e.preventDefault()}
              >
                {name}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="outline" size="sm" className="h-8" onClick={() => setCollapsed(new Set())}>Expand All</Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8"
          onClick={() => setCollapsed(new Set((groups ?? []).map((g) => g.show)))}
        >
          Collapse All
        </Button>

        {/* Bulk actions on selected jobs */}
        <span className="mx-1 h-5 w-px bg-border" />
        <Button variant="outline" size="sm" className="h-8" onClick={doEat} title="Eat dead frames">Eat</Button>
        <Button variant="outline" size="sm" className="h-8" onClick={doRetry} title="Retry dead frames">Retry</Button>
        <Button variant="outline" size="sm" className="h-8" onClick={doPause} title="Pause">Pause</Button>
        <Button variant="outline" size="sm" className="h-8" onClick={doUnpause} title="Unpause">Unpause</Button>
        <Button variant="destructive" size="sm" className="h-8" onClick={doKill} title="Kill">Kill</Button>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Select:</span>
          <Input
            value={selectText}
            onChange={(e) => setSelectText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applySelect(selectText)}
            placeholder="name / regex"
            className="h-8 w-48"
            aria-label="Select jobs"
          />
          <Button variant="outline" size="sm" className="h-8" onClick={() => { setSelectText(""); setSelected(new Set()); }}>Clr</Button>
          <Button variant="outline" size="sm" className="h-8" onClick={selectMine}>selectMine</Button>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={autoRefresh} onCheckedChange={(c) => setAutoRefresh(!!c)} aria-label="Auto-refresh" />
            Auto-refresh
          </label>
          <Button size="sm" className="h-8" onClick={refresh} title="Refresh"><RefreshCw className="h-4 w-4" /></Button>
        </div>
      </div>

      {groups === null ? (
        <p className="text-sm text-muted-foreground">Select one or more shows from the Shows menu to monitor their jobs.</p>
      ) : (
        <div ref={contextMenuTargetAreaRef}>
          <div ref={tableRef} className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40 text-left">
                <tr>
                  <th className="w-8 p-2" />
                  <th className="p-2 font-medium">Job</th>
                  {NUM_COLS.map((c) => (
                    <th key={c.key} className="p-2 text-right font-medium" title={c.title}>{c.label}</th>
                  ))}
                  <th className="p-2 font-medium">Age</th>
                  <th className="min-w-[12rem] p-2 font-medium">Progress</th>
                </tr>
              </thead>
              <tbody>
                {groups.length === 0 ? (
                  <tr>
                    <td colSpan={NUM_COLS.length + 4} className="p-3 text-sm text-muted-foreground">
                      No jobs for the selected show(s).
                    </td>
                  </tr>
                ) : (
                  groups.map((g) => {
                    const isOpen = !collapsed.has(g.show);
                    return (
                      <React.Fragment key={g.show}>
                        <tr className="border-b bg-muted/30">
                          <td className="p-2" />
                          <td className="p-2 font-semibold" colSpan={NUM_COLS.length + 3}>
                            <button className="flex items-center gap-1" onClick={() => toggleShowCollapse(g.show)}>
                              {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                              {g.show}
                              <span className="ml-2 text-xs font-normal text-muted-foreground">({g.jobs.length})</span>
                            </button>
                          </td>
                        </tr>
                        {isOpen
                          ? g.jobs.map((j) => (
                              <tr
                                key={j.id}
                                className={`cursor-context-menu border-b last:border-0 hover:bg-muted/20 ${jobRowClass(j)}`}
                                onContextMenu={(e) => contextMenuHandleOpen(e, { original: j } as unknown as Row<Job>)}
                              >
                                <td className="p-2 align-middle">
                                  <Checkbox
                                    checked={selected.has(j.id)}
                                    onCheckedChange={(c) => toggleJob(j.id, !!c)}
                                    aria-label={`Select ${j.name}`}
                                  />
                                </td>
                                <td className="max-w-[34rem] truncate p-2 pl-4" title={j.name}>
                                  <Link
                                    href={`/jobs/${encodeURIComponent(j.name)}?tab=overview`}
                                    className="text-primary underline-offset-2 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {j.name}
                                  </Link>
                                </td>
                                {NUM_COLS.map((c) => (
                                  <td key={c.key} className="p-2 text-right tabular-nums">{c.get(j)}</td>
                                ))}
                                <td className="p-2 tabular-nums">{secondsToHHHMM(now - (j.startTime ?? now))}</td>
                                <td className="p-2"><JobProgressBar job={j} /></td>
                              </tr>
                            ))
                          : null}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {jobs ? (
        <p className="mt-2 text-xs text-muted-foreground">
          {totalJobs} job(s){selected.size ? `, ${selected.size} selected` : ""}.
        </p>
      ) : null}

      {/* Right-click job menu (reused from Monitor Jobs) + the dialogs it opens. */}
      <JobContextMenu
        username={username}
        contextMenuState={contextMenuState}
        contextMenuHandleClose={contextMenuHandleClose}
        contextMenuRef={contextMenuRef}
        contextMenuTargetAreaRef={contextMenuTargetAreaRef}
        tableData={jobs ?? []}
        tableDataUnfiltered={jobs ?? []}
        rowSelection={{}}
        setTableData={setTableDataProp}
        setTableDataUnfiltered={setTableDataProp}
        setRowSelection={() => {}}
        tableStorageName="cueweb.monitor-cue.jobs"
        unfilteredTableStorageName="cueweb.monitor-cue.jobsUnfiltered"
      />
      <SetPriorityDialog />
      <SetCoresDialog />
      <EmailArtistDialog />
      <RequestCoresDialog />
      <SubscribeToJobDialog />
      <ViewDependenciesDialog />
      <DependencyWizardDialog />
      <UnbookDialog />

      <ConfirmDialog
        open={killConfirm}
        onOpenChange={setKillConfirm}
        title="Kill selected jobs?"
        description={`Kill ${selectedJobs.length} selected job(s)? Running frames will be killed.`}
        confirmLabel="Kill"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={async () => {
          await killJobs(selectedJobs, username, `Killed from CueWeb Monitor Cue by ${username}`);
          setKillConfirm(false);
          refresh();
        }}
      />
    </div>
  );
}
