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
import { ChevronDown, ChevronRight } from "lucide-react";

import {
  Allocation,
  Group,
  RedirectHost,
  Show,
  findJobByName,
  getActiveShows,
  getAllocations,
  getJobs,
  getShowGroups,
  searchRedirect,
} from "@/app/utils/get_utils";
import { redirectHostToJob } from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

const KB_PER_GB = 1048576;

function fmtHHMMSS(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "00:00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
const gb = (kb: number) => `${(kb / KB_PER_GB).toFixed(2)}GB`;

function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  function toggle(value: string, checked: boolean) {
    onChange(checked ? [...selected, value] : selected.filter((v) => v !== value));
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          {label} ({selected.length})
          <ChevronDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-80 overflow-y-auto">
        {options.length === 0 ? (
          <div className="px-2 py-1.5 text-sm text-muted-foreground">None</div>
        ) : (
          options.map((o) => (
            <DropdownMenuCheckboxItem
              key={o}
              checked={selected.includes(o)}
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

function NumField({
  label,
  value,
  onChange,
  step,
  suffix,
  width = "w-20",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  step?: number;
  suffix?: string;
  width?: string;
}) {
  return (
    <label className="flex items-center gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <Input
        type="number"
        min={0}
        step={step ?? 1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`h-8 ${width}`}
        aria-label={label}
      />
      {suffix ? <span className="text-xs text-muted-foreground">{suffix}</span> : null}
    </label>
  );
}

export default function RedirectPage() {
  const [shows, setShows] = React.useState<Show[]>([]);
  const [allocations, setAllocations] = React.useState<Allocation[]>([]);
  const [groups, setGroups] = React.useState<Group[]>([]);
  const [jobNames, setJobNames] = React.useState<string[]>([]);

  const [show, setShow] = React.useState("");
  const [selectedAllocs, setSelectedAllocs] = React.useState<string[]>([]);
  const [includeGroups, setIncludeGroups] = React.useState<string[]>([]);
  const [requireService, setRequireService] = React.useState("");
  const [excludeRegex, setExcludeRegex] = React.useState("");
  const [minCores, setMinCores] = React.useState("1");
  const [maxCores, setMaxCores] = React.useState("32");
  const [minMemoryGb, setMinMemoryGb] = React.useState("4.0");
  const [limit, setLimit] = React.useState("10");
  const [cutoffPrcHrs, setCutoffPrcHrs] = React.useState("20.0");
  const [targetJob, setTargetJob] = React.useState("");

  const [hosts, setHosts] = React.useState<RedirectHost[] | null>(null);
  const [checked, setChecked] = React.useState<Set<string>>(new Set());
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());
  const [done, setDone] = React.useState<Set<string>>(new Set());
  const [searching, setSearching] = React.useState(false);
  const [redirecting, setRedirecting] = React.useState(false);
  const [confirm, setConfirm] = React.useState<{ message: string; run: () => Promise<void> } | null>(null);

  // Load shows / allocations / job names once.
  React.useEffect(() => {
    getActiveShows()
      .then((s) => {
        setShows(s);
        setShow((cur) => cur || s[0]?.name || "");
      })
      .catch((err) => handleError(err, "Could not load shows"));
    getAllocations().then(setAllocations).catch(() => setAllocations([]));
    getJobs(JSON.stringify({ r: { include_finished: false } }))
      .then((jobs) => setJobNames(jobs.map((j) => j.name)))
      .catch(() => setJobNames([]));
  }, []);

  // Reload the group list when the show changes.
  React.useEffect(() => {
    const showObj = shows.find((s) => s.name === show);
    if (!showObj) {
      setGroups([]);
      return;
    }
    getShowGroups(showObj.id).then(setGroups).catch(() => setGroups([]));
    setIncludeGroups([]);
  }, [show, shows]);

  // Auto-populate cores / memory / show from the target job's layers (CueGUI
  // detect()). Best-effort, fired when the target field loses focus.
  async function detectTarget() {
    const name = targetJob.trim();
    if (!name) return;
    try {
      const job = await findJobByName(name);
      if (!job) return;
      const jobShow = (job as any).show as string | undefined;
      if (jobShow && shows.some((s) => s.name === jobShow)) setShow(jobShow);
      const layers = await getJobs ? null : null; // placeholder to keep imports minimal
      void layers;
      const jobLayers = await import("@/app/utils/get_utils").then((m) =>
        m.getLayers(JSON.stringify({ job: { id: (job as any).id, name: job.name } })),
      );
      let minC = 1;
      let minMemKb = 0;
      for (const layer of jobLayers) {
        const lc = Number((layer as any).minCores ?? 0);
        const lm = Number((layer as any).minMemory ?? 0);
        if (lc > minC) minC = lc;
        if (lm > minMemKb) minMemKb = lm;
      }
      setMinCores(String(Math.round(minC)));
      if (minMemKb > 0) setMinMemoryGb((minMemKb / KB_PER_GB).toFixed(1));
    } catch {
      /* best-effort */
    }
  }

  const allocNames = React.useMemo(
    () => allocations.map((a) => a.name).sort((a, b) => a.localeCompare(b)),
    [allocations],
  );
  const groupNames = React.useMemo(
    () => groups.map((g) => g.name).sort((a, b) => a.localeCompare(b)),
    [groups],
  );

  async function onSearch() {
    if (!show) {
      toastWarning("Select a show first.");
      return;
    }
    setSearching(true);
    try {
      const result = await searchRedirect({
        show,
        allocs: selectedAllocs,
        targetJob: targetJob.trim(),
        minCores: Number(minCores),
        maxCores: Number(maxCores),
        minMemoryKb: Math.round(parseFloat(minMemoryGb || "0") * KB_PER_GB),
        limit: Number(limit),
        cutoffSeconds: Math.round(parseFloat(cutoffPrcHrs || "0") * 3600),
        requireService: requireService.trim(),
        includeGroups,
        excludeRegex: excludeRegex.trim(),
      });
      setHosts(result);
      setChecked(new Set());
      setDone(new Set());
      setExpanded(new Set());
    } catch (err) {
      handleError(err, "Redirect search failed");
      setHosts([]);
    } finally {
      setSearching(false);
    }
  }

  function toggleHost(name: string, isChecked: boolean) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (isChecked) next.add(name);
      else next.delete(name);
      return next;
    });
  }
  function toggleExpand(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }
  function selectAll() {
    if (!hosts) return;
    setChecked(new Set(hosts.filter((h) => !done.has(h.name)).map((h) => h.name)));
  }

  async function doRedirect(jobId: string, jobName: string, selected: RedirectHost[]) {
    setRedirecting(true);
    try {
      const outcomes = await Promise.all(
        // RedirectToJob resolves procs by id (pk_proc), matching pycue's
        // `proc_names=[proc.data.id ...]` - sending the display name 404s.
        selected.map((h) => redirectHostToJob(h.host, h.procs.map((p) => p.id), jobId)),
      );
      const okHosts = selected.filter((_, i) => outcomes[i]).map((h) => h.name);
      const failed = selected.length - okHosts.length;
      setDone((prev) => {
        const next = new Set(prev);
        okHosts.forEach((n) => next.add(n));
        return next;
      });
      if (failed === 0) toastSuccess(`Redirect request sent for ${jobName} (${okHosts.length} host(s)).`);
      else toastWarning(`${okHosts.length} host(s) redirected; ${failed} failed.`);
    } finally {
      setRedirecting(false);
    }
  }

  async function onRedirect() {
    const selected = (hosts ?? []).filter((h) => checked.has(h.name) && !done.has(h.name));
    if (selected.length === 0) {
      toastWarning("You have not selected anything to redirect.");
      return;
    }
    const name = targetJob.trim();
    if (!name) {
      toastWarning("You must have a job name selected.");
      return;
    }
    let job;
    try {
      job = await findJobByName(name);
    } catch (err) {
      handleError(err, "Could not verify the target job");
      return;
    }
    if (!job) {
      toastWarning("The job you're trying to redirect to appears to be no longer in the cue!");
      return;
    }
    const stats = (job as any).jobStats ?? {};
    const waiting = Number(stats.waitingFrames ?? 0);
    if (waiting <= 0) {
      toastWarning(`Target job ${job.name} has no waiting frames.`);
      return;
    }
    const reserved = Number(stats.reservedCores ?? 0);
    const maxC = Number((job as any).maxCores ?? 0);
    if (maxC > 0 && reserved >= maxC) {
      toastWarning(`Target job ${job.name} has reached its max cores (${maxC}).`);
      return;
    }

    // Soft warnings: paused target, cross-show redirect.
    const warnings: string[] = [];
    if ((job as any).isPaused) warnings.push("The target job is paused.");
    const jobShow = (job as any).show as string | undefined;
    const crossShow = selected.some((h) => h.procs.some((p) => p.showName && jobShow && p.showName !== jobShow));
    if (crossShow) {
      warnings.push("Some selected procs belong to a different show - redirecting will kill frames on other shows.");
    }

    const run = () => doRedirect((job as any).id, job.name, selected);
    if (warnings.length) {
      setConfirm({ message: `${warnings.join("\n")}\n\nRedirect anyway?`, run });
    } else {
      await run();
    }
  }

  const totalProcs = (hosts ?? []).reduce((n, h) => n + h.procs.length, 0);

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Redirect</h1>

      {/* Job Filters */}
      <fieldset className="mb-3 rounded-md border p-3">
        <legend className="px-1 text-xs font-medium text-muted-foreground">Job Filters</legend>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Show:</span>
            <select
              value={show}
              onChange={(e) => setShow(e.target.value)}
              className="h-8 rounded-md border border-input bg-background px-2 text-sm"
              aria-label="Show"
            >
              {shows.map((s) => (
                <option key={s.id} value={s.name}>{s.name}</option>
              ))}
            </select>
          </label>
          <MultiSelect label="Include Groups" options={groupNames} selected={includeGroups} onChange={setIncludeGroups} />
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Require Services</span>
            <Input value={requireService} onChange={(e) => setRequireService(e.target.value)} className="h-8 w-40" aria-label="Require Services" />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Exclude Regex</span>
            <Input value={excludeRegex} onChange={(e) => setExcludeRegex(e.target.value)} className="h-8 w-40" aria-label="Exclude Regex" />
          </label>
        </div>
      </fieldset>

      {/* Resource Filters */}
      <fieldset className="mb-3 rounded-md border p-3">
        <legend className="px-1 text-xs font-medium text-muted-foreground">Resource Filters</legend>
        <div className="flex flex-wrap items-center gap-4">
          <MultiSelect label="Allocations" options={allocNames} selected={selectedAllocs} onChange={setSelectedAllocs} />
          <NumField label="Minimum Cores:" value={minCores} onChange={setMinCores} />
          <NumField label="Max Cores:" value={maxCores} onChange={setMaxCores} />
          <NumField label="Minimum Memory:" value={minMemoryGb} onChange={setMinMemoryGb} step={0.1} suffix="GB" width="w-24" />
          <NumField label="Result Limit:" value={limit} onChange={setLimit} />
          <NumField label="Proc Hour Cutoff:" value={cutoffPrcHrs} onChange={setCutoffPrcHrs} step={0.1} suffix="PrcHrs" width="w-24" />
        </div>
      </fieldset>

      {/* Actions + target */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button type="button" size="sm" onClick={onSearch} disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={onRedirect} disabled={redirecting}>
          {redirecting ? "Redirecting…" : "Redirect"}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={selectAll}>Select All</Button>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Target:</span>
          <Input
            value={targetJob}
            onChange={(e) => setTargetJob(e.target.value)}
            onBlur={detectTarget}
            list="redirect-job-names"
            className="h-8 w-80"
            placeholder="target job name"
            aria-label="Target job"
          />
          <datalist id="redirect-job-names">
            {jobNames.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
        </label>
        <Button type="button" size="sm" variant="ghost" onClick={() => setTargetJob("")}>Clr</Button>
      </div>

      {/* Results */}
      {hosts === null ? (
        <p className="text-sm text-muted-foreground">
          Set your filters and a target job, then click Search to find procs to redirect.
        </p>
      ) : hosts.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hosts matched the current filters.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left">
              <tr>
                <th className="w-8 p-2" />
                <th className="p-2 font-medium">Name</th>
                <th className="p-2 font-medium">Cores</th>
                <th className="p-2 font-medium">Memory</th>
                <th className="p-2 font-medium">PrcTime</th>
                <th className="p-2 font-medium">Group</th>
                <th className="p-2 font-medium">Service</th>
                <th className="p-2 font-medium">Job Cores</th>
                <th className="p-2 font-medium">Waiting Frames</th>
                <th className="p-2 font-medium">LLU</th>
                <th className="p-2 font-medium">Log</th>
              </tr>
            </thead>
            <tbody>
              {hosts.map((h) => {
                const isDone = done.has(h.name);
                const isOpen = expanded.has(h.name);
                return (
                  <React.Fragment key={h.name}>
                    <tr className={`border-b ${isDone ? "opacity-50" : ""}`}>
                      <td className="p-2 align-middle">
                        <Checkbox
                          checked={checked.has(h.name)}
                          disabled={isDone}
                          onCheckedChange={(c) => toggleHost(h.name, !!c)}
                          aria-label={`Select ${h.name}`}
                        />
                      </td>
                      <td className="p-2 font-medium">
                        <button className="flex items-center gap-1" onClick={() => toggleExpand(h.name)}>
                          {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                          {h.name}
                        </button>
                      </td>
                      <td className="p-2 tabular-nums">{h.cores}</td>
                      <td className="p-2 tabular-nums">{gb(h.memoryKb)}</td>
                      <td className="p-2 tabular-nums">{fmtHHMMSS(h.timeSeconds)}</td>
                      <td className="p-2" colSpan={6} />
                    </tr>
                    {isOpen
                      ? h.procs.map((p) => (
                          <tr key={p.name} className="border-b bg-muted/10 text-muted-foreground">
                            <td className="p-2" />
                            <td className="truncate p-2 pl-6" title={p.jobName}>{p.jobName}</td>
                            <td className="p-2 tabular-nums">{p.reservedCores}</td>
                            <td className="p-2 tabular-nums">{gb(p.reservedMemoryKb)}</td>
                            <td className="p-2 tabular-nums">{fmtHHMMSS(p.runtimeSeconds)}</td>
                            <td className="p-2">{p.groupName}</td>
                            <td className="p-2">{p.services.join(",")}</td>
                            <td className="p-2 tabular-nums">{h.jobCores}</td>
                            <td className="p-2 tabular-nums">{h.waitingFrames}</td>
                            <td className="p-2" />
                            <td className="p-2" />
                          </tr>
                        ))
                      : null}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {hosts && hosts.length > 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          {hosts.length} host(s), {totalProcs} proc(s). LLU and Log are blank when the log filesystem isn&apos;t mounted.
        </p>
      ) : null}

      <ConfirmDialog
        open={confirm !== null}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Confirm Redirect"
        description={<span className="whitespace-pre-line">{confirm?.message}</span>}
        confirmLabel="Redirect"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={async () => {
          const run = confirm?.run;
          setConfirm(null);
          if (run) await run();
        }}
      />
    </div>
  );
}
