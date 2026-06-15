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
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { MessageSquare } from "lucide-react";

import type { Frame } from "@/app/frames/frame-columns";
import { StuckFrame, getStuckFrames, getStuckFrameLastLine } from "@/app/utils/get_utils";
import { eatFrames, killFrames, retryFrames, setLayerMinCores } from "@/app/utils/action_utils";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DEFAULT_FILTER,
  StuckFrameFilters,
  type StuckFilter,
} from "@/components/ui/stuck-frame-filters";

const AUTO_REFRESH_MS = 60000;
const FILTERS_KEY = "cueweb.stuck-frames.filters";

// --- formatting -----------------------------------------------------------
function fmtDur(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
const hostOf = (lastResource: string) => (lastResource || "").split("/")[0] || "";

// --- detection (CueGUI StuckFramePlugin parity) ---------------------------
type Metrics = { runtime: number; llu: number; percentStuck: number; avg: number };

function metricsOf(f: StuckFrame, now: number): Metrics {
  const runtime = f.startTime ? now - f.startTime : 0;
  const llu = f.state === "RUNNING" && f.lluTime ? now - f.lluTime : 0;
  const percentStuck = runtime > 0 ? llu / runtime : 0;
  return { runtime, llu, percentStuck, avg: f.avgFrameSec };
}

// The catch-all filter (index 0) applies unless a later, service-specific
// filter matches the frame's service.
function pickFilter(f: StuckFrame, filters: StuckFilter[]): StuckFilter | undefined {
  const specific = filters.find((flt, i) => i > 0 && flt.service && flt.service === f.service);
  return specific ?? filters[0];
}

function isExcluded(f: StuckFrame, filter: StuckFilter): boolean {
  const keywords = filter.regex.split(",").map((s) => s.trim()).filter(Boolean);
  return keywords.some((kw) => {
    try {
      const re = new RegExp(kw, "i");
      return re.test(f.jobName) || re.test(f.layerName);
    } catch {
      const k = kw.toLowerCase();
      return f.jobName.toLowerCase().includes(k) || f.layerName.toLowerCase().includes(k);
    }
  });
}

// Mirrors CueGUI: lluTime > minLLU AND %stuck > threshold AND runtime >
// avg*avgComp% AND %stuck < 1.1 AND runtime > 500s.
function isStuck(f: StuckFrame, filter: StuckFilter | undefined, now: number): boolean {
  if (!filter || !filter.enabled) return false;
  if (isExcluded(f, filter)) return false;
  const { runtime, llu, percentStuck, avg } = metricsOf(f, now);
  return (
    llu > filter.minLlu * 60 &&
    percentStuck * 100 > filter.percentStuck &&
    runtime > (avg * filter.avgComp) / 100 &&
    percentStuck < 1.1 &&
    runtime > 500
  );
}

type MenuState =
  | { kind: "frame"; x: number; y: number; frame: StuckFrame }
  | { kind: "job"; x: number; y: number; jobId: string; jobName: string };

export default function StuckFramesPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email ?? "cueweb";

  const [raw, setRaw] = React.useState<StuckFrame[] | null>(null);
  const [now, setNow] = React.useState(() => Date.now() / 1000);
  const [filters, setFilters] = React.useState<StuckFilter[]>([{ ...DEFAULT_FILTER }]);
  const [autoRefresh, setAutoRefresh] = React.useState(false);
  const [notify, setNotify] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  // Client-side removals: "Frame/Job Not Stuck".
  const [hiddenFrames, setHiddenFrames] = React.useState<Set<string>>(new Set());
  const [hiddenJobs, setHiddenJobs] = React.useState<Set<string>>(new Set());

  const [lastLines, setLastLines] = React.useState<Record<string, string>>({});
  const [menu, setMenu] = React.useState<MenuState | null>(null);
  const [coreUp, setCoreUp] = React.useState<{ targets: { id: string; name: string }[]; cores: string } | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  // Restore persisted filters on mount.
  React.useEffect(() => {
    const stored = window.localStorage.getItem(FILTERS_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) setFilters(parsed);
      } catch {
        /* ignore corrupt value */
      }
    }
  }, []);

  function persistFilters(next: StuckFilter[]) {
    setFilters(next);
    window.localStorage.setItem(FILTERS_KEY, JSON.stringify(next));
  }

  // Returns the loaded frames (null on cancel/error) so callers can act on the
  // fresh data without waiting for the state/memo round-trip.
  const load = React.useCallback(async (isCancelled?: () => boolean): Promise<StuckFrame[] | null> => {
    setLoading(true);
    try {
      const data = await getStuckFrames();
      if (isCancelled?.()) return null;
      setRaw(data);
      setNow(Date.now() / 1000);
      return data;
    } catch (err) {
      if (isCancelled?.()) return null;
      handleError(err, "Could not load stuck frames");
      setRaw((prev) => prev ?? []);
      return null;
    } finally {
      if (!isCancelled?.()) setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    load(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load]);

  // Auto-refresh. CueGUI refreshes ~every 30 min; a web monitor wants fresher
  // data, so this polls every 60s while enabled. Fires a desktop notification
  // on completion when armed and stuck frames are actually present.
  React.useEffect(() => {
    if (!autoRefresh) return;
    let cancelled = false;
    // Skip a tick if the previous scan is still running, so a slow/degraded
    // backend can't pile up overlapping, out-of-order refreshes.
    let inFlight = false;
    const id = setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const data = await load(() => cancelled);
        if (cancelled || !data) return;
        if (notify && typeof Notification !== "undefined" && Notification.permission === "granted") {
          // Apply the same detection + hidden filters as the table so we only
          // notify when a stuck frame would actually be shown.
          const scanNow = Date.now() / 1000;
          const stuckCount = data.filter(
            (f) =>
              !hiddenFrames.has(f.id) &&
              !hiddenJobs.has(f.jobId) &&
              isStuck(f, pickFilter(f, filters), scanNow),
          ).length;
          if (stuckCount > 0) {
            new Notification(`CueWeb: ${stuckCount} stuck frame(s) detected`);
          }
        }
      } finally {
        inFlight = false;
      }
    }, AUTO_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [autoRefresh, notify, load, filters, hiddenFrames, hiddenJobs]);

  function toggleNotify(checked: boolean) {
    setNotify(checked);
    if (checked && typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }

  // Services present in the data, for the add-filter service dropdown.
  const availableServices = React.useMemo(() => {
    const set = new Set<string>();
    (raw ?? []).forEach((f) => f.service && set.add(f.service));
    return Array.from(set).sort();
  }, [raw]);

  // Apply detection + client-side removals, group by job. Identity is jobId,
  // not jobName, so two jobs sharing a name aren't merged or acted on together.
  const groups = React.useMemo(() => {
    if (!raw) return null;
    const stuck = raw.filter(
      (f) =>
        !hiddenFrames.has(f.id) &&
        !hiddenJobs.has(f.jobId) &&
        isStuck(f, pickFilter(f, filters), now),
    );
    const byJob = new Map<string, { jobName: string; frames: StuckFrame[] }>();
    for (const f of stuck) {
      const entry = byJob.get(f.jobId) ?? { jobName: f.jobName, frames: [] };
      entry.frames.push(f);
      byJob.set(f.jobId, entry);
    }
    return Array.from(byJob.entries())
      .sort((a, b) => a[1].jobName.localeCompare(b[1].jobName))
      .map(([jobId, { jobName, frames }]) => ({
        jobId,
        jobName,
        frames: frames.sort((a, b) => metricsOf(b, now).runtime - metricsOf(a, now).runtime),
      }));
  }, [raw, filters, now, hiddenFrames, hiddenJobs]);

  const totalStuck = groups?.reduce((n, g) => n + g.frames.length, 0) ?? 0;

  // Lazily fetch the last log line for visible stuck frames.
  React.useEffect(() => {
    if (!groups) return;
    const pending = groups
      .flatMap((g) => g.frames)
      .filter((f) => f.jobLogDir && lastLines[f.id] === undefined)
      .slice(0, 50); // bound per pass
    if (pending.length === 0) return;
    let cancelled = false;
    (async () => {
      const entries = await Promise.all(
        pending.map(async (f) => {
          const logPath = `${f.jobLogDir}/${f.jobName}.${f.name}.rqlog`;
          const line = await getStuckFrameLastLine(logPath);
          return [f.id, line] as const;
        }),
      );
      if (cancelled) return;
      setLastLines((prev) => {
        const next = { ...prev };
        for (const [id, line] of entries) next[id] = line;
        return next;
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [groups, lastLines]);

  // Close the context menu on any outside interaction.
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

  // --- helpers -------------------------------------------------------------
  function toFrame(sf: StuckFrame): Frame {
    const {
      jobId: _a, jobName: _b, jobLogDir: _c, jobHasComment: _d,
      service: _e, avgFrameSec: _f, layerId: _g, layerMinCores: _h,
      ...frame
    } = sf;
    return frame as Frame;
  }

  function openLog(f: StuckFrame) {
    const logDir = `${f.jobLogDir}/${f.jobName}.${f.name}.rqlog`;
    const params = new URLSearchParams({ frameId: f.id, frameLogDir: logDir, username });
    window.open(`/frames/${encodeURIComponent(f.name)}?${params.toString()}`, "_blank", "noopener,noreferrer");
  }

  function exportLog(frames: StuckFrame[]) {
    // Web adaptation of CueGUI's YAML "stuck_frames_db" file: a JSON download
    // (the browser can't write to a fileshare).
    const db: Record<string, Record<string, unknown>> = {};
    for (const f of frames) {
      const { runtime, llu, avg } = metricsOf(f, now);
      const byJob = db[f.jobName] ?? (db[f.jobName] = {});
      byJob[`${f.number}-${Math.floor(now)}`] = {
        layer: f.layerName,
        host: f.lastResource,
        llu,
        runtime,
        average: avg,
        log: lastLines[f.id] ?? "",
      };
    }
    const blob = new Blob([JSON.stringify(db, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "stuck_frames.json";
    a.click();
    URL.revokeObjectURL(url);
    toastSuccess(`Logged ${frames.length} stuck frame(s)`);
  }

  function hideFrame(f: StuckFrame) {
    setHiddenFrames((prev) => new Set(prev).add(f.id));
  }
  function hideJob(jobId: string) {
    setHiddenJobs((prev) => new Set(prev).add(jobId));
  }
  function addJobToExcludes(jobName: string) {
    // Append the job name to the catch-all filter's exclude keywords.
    persistFilters(
      filters.map((flt, i) =>
        i === 0
          ? { ...flt, regex: flt.regex ? `${flt.regex}, ${jobName}` : jobName }
          : flt,
      ),
    );
    toastSuccess(`Excluded ${jobName}`);
  }

  async function act(f: StuckFrame, fn: () => Promise<boolean>) {
    setBusyId(f.id);
    setMenu(null);
    try {
      // Only remove the frame from view when the backend action succeeded;
      // performAction resolves false (without throwing) on failure.
      const ok = await fn();
      if (ok) {
        hideFrame(f);
        await load();
      }
    } finally {
      setBusyId(null);
    }
  }

  const retry = (f: StuckFrame) => act(f, () => retryFrames([toFrame(f)]));
  const eat = (f: StuckFrame) => act(f, () => eatFrames([toFrame(f)]));
  const kill = (f: StuckFrame) =>
    act(f, () => killFrames([toFrame(f)], username, `Manual frame kill from CueWeb Stuck Frames by ${username}`));

  function openCoreUpForFrame(f: StuckFrame) {
    setMenu(null);
    if (!f.layerId) return;
    setCoreUp({ targets: [{ id: f.layerId, name: f.layerName }], cores: String(Math.max(1, f.layerMinCores || 1)) });
  }
  function openCoreUpForJob(jobId: string) {
    setMenu(null);
    const frames = (raw ?? []).filter((f) => f.jobId === jobId && f.layerId);
    const seen = new Map<string, string>();
    frames.forEach((f) => seen.set(f.layerId, f.layerName));
    if (seen.size === 0) return;
    setCoreUp({ targets: Array.from(seen.entries()).map(([id, name]) => ({ id, name })), cores: "1" });
  }
  async function applyCoreUp() {
    if (!coreUp) return;
    const cores = Number(coreUp.cores);
    if (!Number.isFinite(cores) || cores < 0) return;
    await Promise.all(coreUp.targets.map((t) => setLayerMinCores(t, cores)));
    setCoreUp(null);
    await load();
  }

  // --- render --------------------------------------------------------------
  const menuItemCls = "block w-full rounded px-2 py-1.5 text-left hover:bg-accent disabled:opacity-50";

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">Stuck Frames</h1>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={autoRefresh} onCheckedChange={(c) => setAutoRefresh(!!c)} aria-label="Auto-refresh" />
            Auto-refresh
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={notify} onCheckedChange={(c) => toggleNotify(!!c)} aria-label="Notification" />
            Notification
          </label>
          <Button type="button" variant="outline" size="sm" onClick={() => { setHiddenFrames(new Set()); setHiddenJobs(new Set()); setRaw([]); }}>
            Clear
          </Button>
          <Button type="button" size="sm" onClick={() => load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      <div className="mb-4">
        <StuckFrameFilters filters={filters} onChange={persistFilters} availableServices={availableServices} />
      </div>

      {groups === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : totalStuck === 0 ? (
        <p className="text-sm text-muted-foreground">
          No stuck frames detected with the current filters.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left">
              <tr>
                <th className="p-2 font-medium">Name</th>
                <th className="p-2 font-medium" title="Comment">{/* comment icon col */}</th>
                <th className="p-2 font-medium">Frame</th>
                <th className="p-2 font-medium">Host</th>
                <th className="p-2 font-medium">LLU</th>
                <th className="p-2 font-medium">Runtime</th>
                <th className="p-2 font-medium">% Stuck</th>
                <th className="p-2 font-medium">Average</th>
                <th className="p-2 font-medium">Last Line</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <React.Fragment key={g.jobId}>
                  <tr
                    className="cursor-context-menu border-b bg-muted/30"
                    onContextMenu={(e) => {
                      e.preventDefault();
                      setMenu({ kind: "job", x: e.clientX, y: e.clientY, jobId: g.jobId, jobName: g.jobName });
                    }}
                  >
                    <td className="p-2 font-medium" colSpan={1} title={g.jobName}>{g.jobName}</td>
                    <td className="p-2">
                      {g.frames[0]?.jobHasComment ? (
                        <button
                          title="View comments"
                          aria-label={`View comments for ${g.jobName}`}
                          onClick={() =>
                            window.open(
                              `/jobs/${encodeURIComponent(g.jobName)}/comments?jobId=${encodeURIComponent(g.jobId)}`,
                              "_blank",
                              "noopener,noreferrer",
                            )
                          }
                        >
                          <MessageSquare className="h-4 w-4 text-primary" />
                        </button>
                      ) : null}
                    </td>
                    <td className="p-2" colSpan={7} />
                  </tr>
                  {g.frames.map((f) => {
                    const m = metricsOf(f, now);
                    return (
                      <tr
                        key={`${f.jobId}:${f.id}`}
                        className="cursor-context-menu border-b last:border-0 hover:bg-muted/20"
                        onContextMenu={(e) => {
                          e.preventDefault();
                          setMenu({ kind: "frame", x: e.clientX, y: e.clientY, frame: f });
                        }}
                      >
                        <td className="p-2 pl-6 text-muted-foreground">{f.layerName}</td>
                        <td className="p-2" />
                        <td className="p-2 tabular-nums">{f.number}</td>
                        <td className="p-2">{hostOf(f.lastResource)}</td>
                        <td className="p-2 tabular-nums">{fmtDur(m.llu)}</td>
                        <td className="p-2 tabular-nums">{fmtDur(m.runtime)}</td>
                        <td className="p-2 tabular-nums">{(m.percentStuck * 100).toFixed(2)}</td>
                        <td className="p-2 tabular-nums">{fmtDur(m.avg)}</td>
                        <td className="max-w-[24rem] truncate p-2 font-mono text-xs" title={lastLines[f.id] ?? ""}>
                          {lastLines[f.id] ?? ""}
                          {busyId === f.id ? " …" : ""}
                        </td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && groups !== null ? (
        <p className="mt-2 text-xs text-muted-foreground">
          {totalStuck} stuck frame(s) across {groups.length} job(s).
        </p>
      ) : null}

      {/* Context menu */}
      {menu ? (
        <div
          className="fixed z-50 min-w-56 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {menu.kind === "frame" ? (
            <>
              <button className={menuItemCls} onClick={() => { openLog(menu.frame); setMenu(null); }}>Tail Log</button>
              <button className={menuItemCls} onClick={() => { openLog(menu.frame); setMenu(null); }}>View Log</button>
              {menu.frame.retryCount >= 1 ? (
                <button className={menuItemCls} onClick={() => { openLog(menu.frame); setMenu(null); }}>View Last Log</button>
              ) : null}
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} onClick={() => retry(menu.frame)}>Retry</button>
              <button className={menuItemCls} onClick={() => eat(menu.frame)}>Eat</button>
              <button className={menuItemCls} onClick={() => kill(menu.frame)}>Kill</button>
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} onClick={() => { exportLog([menu.frame]); setMenu(null); }}>Log Stuck Frame</button>
              <button className={menuItemCls} onClick={() => { exportLog([menu.frame]); retry(menu.frame); }}>Log and Retry</button>
              <button className={menuItemCls} onClick={() => { exportLog([menu.frame]); eat(menu.frame); }}>Log and Eat</button>
              <button className={menuItemCls} onClick={() => { exportLog([menu.frame]); kill(menu.frame); }}>Log and Kill</button>
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} onClick={() => { hideFrame(menu.frame); setMenu(null); }}>Frame Not Stuck</button>
              <button className={menuItemCls} onClick={() => { addJobToExcludes(menu.frame.jobName); setMenu(null); }}>Add Job to Excludes</button>
              <button className={menuItemCls} onClick={() => { addJobToExcludes(menu.frame.jobName); hideJob(menu.frame.jobId); setMenu(null); }}>Exclude and Remove Job</button>
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} disabled={!menu.frame.layerId} onClick={() => openCoreUpForFrame(menu.frame)}>Core Up</button>
              <button className={menuItemCls} onClick={() => { const h = hostOf(menu.frame.lastResource); if (h) window.open(`/hosts/${encodeURIComponent(h)}`, "_blank", "noopener,noreferrer"); setMenu(null); }}>View Host</button>
            </>
          ) : (
            <>
              <button className={menuItemCls} onClick={() => { window.open(`/jobs/${encodeURIComponent(menu.jobName)}/comments?jobId=${encodeURIComponent(menu.jobId)}`, "_blank", "noopener,noreferrer"); setMenu(null); }}>View Comments</button>
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} onClick={() => { hideJob(menu.jobId); setMenu(null); }}>Job Not Stuck</button>
              <button className={menuItemCls} onClick={() => { addJobToExcludes(menu.jobName); setMenu(null); }}>Add Job to Excludes</button>
              <button className={menuItemCls} onClick={() => { addJobToExcludes(menu.jobName); hideJob(menu.jobId); setMenu(null); }}>Exclude and Remove Job</button>
              <div className="my-1 h-px bg-border" />
              <button className={menuItemCls} onClick={() => openCoreUpForJob(menu.jobId)}>Core Up</button>
            </>
          )}
        </div>
      ) : null}

      {/* Core Up dialog */}
      <Dialog open={coreUp !== null} onOpenChange={(o) => !o && setCoreUp(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Core Up</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2 text-sm">
            <p className="text-muted-foreground">
              Set minimum cores for {coreUp?.targets.length === 1 ? `layer "${coreUp.targets[0].name}"` : `${coreUp?.targets.length ?? 0} layer(s)`}.
            </p>
            <Input
              type="number"
              min={0}
              step={1}
              value={coreUp?.cores ?? ""}
              onChange={(e) => setCoreUp((c) => (c ? { ...c, cores: e.target.value } : c))}
              aria-label="Minimum cores"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setCoreUp(null)}>Cancel</Button>
            <Button type="button" onClick={applyCoreUp}>Apply</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
