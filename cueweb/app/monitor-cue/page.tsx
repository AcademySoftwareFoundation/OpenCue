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
import { ArrowUpDown, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Folder, RefreshCw, Search, StickyNote } from "lucide-react";
import { TbPacman, TbReload, TbPlayerPause, TbPlayerPlay } from "react-icons/tb";
import { MdOutlineCancel } from "react-icons/md";

import type { Job } from "@/app/jobs/columns";
import { UNKNOWN_USER } from "@/app/utils/constants";
import { Group, GroupStats, Show, getActiveShows, getGroupJobs, getShowGroups } from "@/app/utils/get_utils";
import { setAttributeSelection } from "@/app/utils/use_attribute_selection";
import { buildTreeFromGroups, type TreeNode } from "@/components/group-tree/build-tree";
import {
  deleteGroup,
  eatJobsDeadFrames,
  killJobs,
  pauseJobs,
  retryJobsDeadFrames,
  unpauseJobs,
} from "@/app/utils/action_utils";
import { handleError, toastWarning } from "@/app/utils/notify_utils";
import { convertMemoryToString, secondsToHHHMM, secondsToHumanAge } from "@/app/utils/layers_frames_utils";
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
import { JobBookingBar } from "@/components/ui/job-booking-bar";
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
import { JobExtraDialogs } from "@/components/ui/job-extra-dialogs";
import { JobCommentsDialog } from "@/components/ui/job-comments-dialog";
import { SendToGroupDialog } from "@/components/ui/send-to-group-dialog";
import { ShowPropertiesDialog } from "@/components/ui/show-properties-dialog";
import { GroupPropertiesDialog, OPEN_GROUP_PROPERTIES_EVENT } from "@/components/ui/group-properties-dialog";
import { CreateGroupDialog, GROUPS_CHANGED_EVENT, OPEN_CREATE_GROUP_EVENT } from "@/components/ui/create-group-dialog";
import { ViewFiltersDialog } from "@/components/ui/view-filters-dialog";
import { TaskPropertiesDialog } from "@/components/ui/task-properties-dialog";
import { ServicePropertiesDialog } from "@/components/ui/service-properties-dialog";
import { MonitorCueShowMenu, type ShowMenuState } from "@/components/ui/monitor-cue-show-menu";

const REFRESH_MS = 5000;
const SELECTED_SHOWS_KEY = "cueweb.monitor-cue.shows";

const mem = (kb?: string) => {
  const n = Number(kb ?? 0);
  return Number.isFinite(n) && n > 0 ? convertMemoryToString(n, "job") : "0K";
};

// memory_warning_level (Kb) from cuegui.yaml: jobs whose peak frame memory
// exceeds this get the yellow row tint, matching CueGUI.
const MEMORY_WARNING_LEVEL = 5242880;

// CueGUI JobWidgetTree row tint: blue=paused, red=dead frames, yellow=maxRss
// over the warning level, green=no running frames but frames waiting,
// purple=all remaining frames depend on something.
function jobRowClass(j: Job): string {
  const s = j.jobStats;
  if (j.isPaused) return "bg-blue-950/50";
  if ((s?.deadFrames ?? 0) > 0) return "bg-red-950/50";
  if (Number.parseInt(s?.maxRss ?? "0") > MEMORY_WARNING_LEVEL) return "bg-yellow-900/40";
  if ((s?.runningFrames ?? 0) === 0) {
    if ((s?.waitingFrames ?? 0) === 0 && (s?.dependFrames ?? 0) > 0) return "bg-purple-950/50";
    if ((s?.waitingFrames ?? 0) > 0) return "bg-green-950/40";
  }
  return "";
}

// A flattened Monitor Cue tree row: either a group folder or a job, with the
// indentation depth.
type TreeRow =
  | { kind: "group"; group: Group; depth: number; stats: GroupStats }
  | { kind: "job"; job: Job; depth: number };

// Flatten a group node's *contents* (its direct jobs, then each child folder and
// that folder's contents) into render rows, honoring the per-folder collapse,
// the job sort, and the substring filter. The node's own folder row is rendered
// by the caller (the show header for the root, the folder row for subgroups).
function flattenGroup(
  node: TreeNode,
  depth: number,
  jobsByGroup: Record<string, Job[]>,
  collapsedGroups: Set<string>,
  cmp: (a: Job, b: Job) => number,
  needle: string,
): TreeRow[] {
  const rows: TreeRow[] = [];
  const jobs = (jobsByGroup[node.group.id] ?? [])
    .filter((j) => !needle || j.name.toLowerCase().includes(needle))
    .sort(cmp);
  for (const j of jobs) rows.push({ kind: "job", job: j, depth });
  const children = [...node.children].sort((a, b) => a.group.name.localeCompare(b.group.name));
  for (const child of children) {
    rows.push({ kind: "group", group: child.group, depth, stats: child.rolledUpStats });
    if (!collapsedGroups.has(child.group.id)) {
      rows.push(...flattenGroup(child, depth + 1, jobsByGroup, collapsedGroups, cmp, needle));
    }
  }
  return rows;
}

// Which Monitor Cue columns a group folder row populates (from its rolled-up
// GroupStats); other columns are blank on group rows.
const GROUP_STAT_COL: Record<string, (s: GroupStats) => React.ReactNode> = {
  run: (s) => s.runningFrames,
  cores: (s) => s.reservedCores.toFixed(2),
  gpus: (s) => s.reservedGpus,
  wait: (s) => s.waitingFrames,
  depend: (s) => s.dependFrames,
};

// Unified, ordered, hideable, sortable column model for the Monitor Cue table.
// `cell` renders the body content; `sort` (when present) makes the header
// sortable; `header` overrides the header text with an icon. The checkbox
// column is fixed (not in this list).
type CueCol = {
  key: string;
  label: string;
  title?: string;
  align?: "left" | "right" | "center";
  minW?: string;
  sort?: (j: Job) => number | string;
  header?: React.ReactNode;
  cell: (j: Job, now: number) => React.ReactNode;
};

const ALL_COLUMNS: CueCol[] = [
  {
    key: "job", label: "Job", align: "left", minW: "min-w-[18rem]", sort: (j) => j.name.toLowerCase(),
    cell: (j) => (
      <Link
        href={`/jobs/${encodeURIComponent(j.name)}?tab=overview`}
        className="text-primary underline-offset-2 hover:underline"
        onClick={(e) => e.stopPropagation()}
      >
        {j.name}
      </Link>
    ),
  },
  {
    key: "comment", label: "", title: "Has comments", align: "center",
    header: <StickyNote className="mx-auto h-3.5 w-3.5" aria-hidden="true" />,
    sort: (j) => (j.hasComment ? 1 : 0),
    cell: (j) =>
      j.hasComment ? (
        <button
          type="button"
          title="Has comments — click to view"
          aria-label="View comments"
          className="inline-flex items-center justify-center text-amber-500 hover:text-amber-400"
          onClick={(e) => {
            e.stopPropagation();
            window.dispatchEvent(new CustomEvent("cueweb:open-job-comments", { detail: { job: j } }));
          }}
        >
          <StickyNote className="h-4 w-4" />
        </button>
      ) : null,
  },
  {
    key: "autoeat", label: "", title: "Auto-eating", align: "center",
    header: <TbPacman className="mx-auto h-3.5 w-3.5" aria-hidden="true" />,
    sort: (j) => (j.autoEat ? 1 : 0),
    cell: (j) =>
      j.autoEat ? (
        <span title="Auto-eating enabled" className="inline-flex items-center justify-center text-yellow-500">
          <TbPacman className="h-4 w-4" aria-hidden="true" />
        </span>
      ) : null,
  },
  { key: "run", label: "Run", align: "right", title: "Running frames", sort: (j) => j.jobStats?.runningFrames ?? 0, cell: (j) => j.jobStats?.runningFrames ?? 0 },
  { key: "cores", label: "Cores", align: "right", title: "Reserved cores", sort: (j) => j.jobStats?.reservedCores ?? 0, cell: (j) => (j.jobStats?.reservedCores ?? 0).toFixed(2) },
  { key: "gpus", label: "Gpus", align: "right", title: "Reserved GPUs", sort: (j) => j.jobStats?.reservedGpus ?? 0, cell: (j) => j.jobStats?.reservedGpus ?? 0 },
  { key: "wait", label: "Wait", align: "right", title: "Waiting frames", sort: (j) => j.jobStats?.waitingFrames ?? 0, cell: (j) => j.jobStats?.waitingFrames ?? 0 },
  { key: "depend", label: "Depend", align: "right", title: "Dependent frames", sort: (j) => j.jobStats?.dependFrames ?? 0, cell: (j) => j.jobStats?.dependFrames ?? 0 },
  { key: "total", label: "Total", align: "right", title: "Total frames", sort: (j) => j.jobStats?.totalFrames ?? 0, cell: (j) => j.jobStats?.totalFrames ?? 0 },
  { key: "bookingbar", label: "Booking", minW: "min-w-[8rem]", title: "Booking bar (running/waiting; min & max core markers)", cell: (j) => <JobBookingBar job={j} /> },
  { key: "min", label: "Min", align: "right", title: "Minimum cores", sort: (j) => j.minCores ?? 0, cell: (j) => Math.round(j.minCores ?? 0) },
  { key: "max", label: "Max", align: "right", title: "Maximum cores", sort: (j) => j.maxCores ?? 0, cell: (j) => Math.round(j.maxCores ?? 0) },
  { key: "ming", label: "Min G", align: "right", title: "Minimum GPUs", sort: (j) => j.minGpus ?? 0, cell: (j) => j.minGpus ?? 0 },
  { key: "maxg", label: "Max G", align: "right", title: "Maximum GPUs", sort: (j) => j.maxGpus ?? 0, cell: (j) => j.maxGpus ?? 0 },
  { key: "pri", label: "Pri", align: "right", title: "Priority", sort: (j) => j.priority ?? 0, cell: (j) => j.priority ?? 0 },
  { key: "eta", label: "ETA", align: "right", title: "ETA (disabled, as in CueGUI)", cell: () => "" },
  { key: "maxrss", label: "MaxRss", align: "right", title: "Peak memory of any single frame", sort: (j) => Number.parseInt(j.jobStats?.maxRss ?? "0") || 0, cell: (j) => mem(j.jobStats?.maxRss) },
  { key: "maxgpu", label: "MaxGpuMem", align: "right", title: "Peak GPU memory of any single frame", sort: (j) => Number.parseInt(j.jobStats?.maxGpuMemory ?? "0") || 0, cell: (j) => mem(j.jobStats?.maxGpuMemory) },
  { key: "age", label: "Age", title: "Age (HHH:MM)", sort: (j) => j.startTime ?? 0, cell: (j, now) => secondsToHHHMM(now - (j.startTime ?? now)) },
  { key: "readableage", label: "Readable Age", title: "Human-readable age", sort: (j) => j.startTime ?? 0, cell: (j, now) => secondsToHumanAge(now - (j.startTime ?? now)) },
  { key: "progress", label: "Progress", minW: "min-w-[12rem]", cell: (j) => <JobProgressBar job={j} /> },
];

const ALL_COLUMN_KEYS = ALL_COLUMNS.map((c) => c.key);
const COLUMN_ORDER_KEY = "cueweb.monitor-cue.columnOrder";
const COLUMN_HIDDEN_KEY = "cueweb.monitor-cue.columnHidden";

export default function MonitorCuePage() {
  const { data: session } = useSession();
  // Fall back to UNKNOWN_USER (not "") so username-required actions like Kill
  // still work in sandbox/no-auth mode - the kill route rejects an empty user.
  const username = session?.user?.name ?? session?.user?.email?.split("@")[0] ?? UNKNOWN_USER;

  const [shows, setShows] = React.useState<Show[]>([]);
  const [selectedShows, setSelectedShows] = React.useState<string[]>([]);
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  // Per show: the group tree (show root + nested folders) and each group's
  // direct jobs, keyed by group id (CueGUI Monitor Cue hierarchy). Jobs are
  // placed by group id since a job only carries its group *name*, which is not
  // unique (the root and a subgroup can share the show's name).
  const [treeByShow, setTreeByShow] = React.useState<
    Record<string, { tree: TreeNode | null; jobsByGroup: Record<string, Job[]> }>
  >({});
  const [now, setNow] = React.useState(() => Date.now() / 1000);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());
  // Collapsed group folders (by group id), independent of the per-show collapse.
  const [collapsedGroups, setCollapsedGroups] = React.useState<Set<string>>(new Set());
  const [selectText, setSelectText] = React.useState("");
  const [autoRefresh, setAutoRefresh] = React.useState(true);
  const [killConfirm, setKillConfirm] = React.useState(false);
  // Right-click menu on a show (group) header row.
  const [showMenu, setShowMenu] = React.useState<ShowMenuState | null>(null);
  // Right-click menu on a group folder row.
  const [groupMenu, setGroupMenu] = React.useState<{ x: number; y: number; show: Show; group: Group } | null>(null);
  const [deleteGroupTarget, setDeleteGroupTarget] = React.useState<Group | null>(null);

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
    // Persistence is best-effort: a full quota must not break selection.
    try { window.localStorage.setItem(SELECTED_SHOWS_KEY, JSON.stringify(names)); } catch { /* ignore */ }
  }, []);

  // --- Column order / visibility / sort (parity with Monitor Jobs) ---------
  const [columnOrder, setColumnOrder] = React.useState<string[]>(ALL_COLUMN_KEYS);
  const [hiddenColumns, setHiddenColumns] = React.useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = React.useState<string>("job");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc");
  // Client-side substring filter over the loaded jobs (parity with Monitor
  // Jobs' "Filter jobs..."). Hides non-matching rows; does not refetch.
  const [filterText, setFilterText] = React.useState("");

  // Hydrate persisted order/visibility once on mount.
  React.useEffect(() => {
    try {
      const rawOrder = window.localStorage.getItem(COLUMN_ORDER_KEY);
      if (rawOrder) {
        const parsed: string[] = JSON.parse(rawOrder);
        // Keep only known keys, then append any new columns not yet persisted.
        const known = parsed.filter((k) => ALL_COLUMN_KEYS.includes(k));
        const missing = ALL_COLUMN_KEYS.filter((k) => !known.includes(k));
        setColumnOrder([...known, ...missing]);
      }
      const rawHidden = window.localStorage.getItem(COLUMN_HIDDEN_KEY);
      if (rawHidden) setHiddenColumns(new Set(JSON.parse(rawHidden) as string[]));
    } catch {
      /* bad value in storage; keep defaults */
    }
  }, []);

  const persistColumnOrder = React.useCallback((next: string[]) => {
    setColumnOrder(next);
    try { window.localStorage.setItem(COLUMN_ORDER_KEY, JSON.stringify(next)); } catch { /* ignore */ }
  }, []);
  const persistHidden = React.useCallback((next: Set<string>) => {
    setHiddenColumns(next);
    try { window.localStorage.setItem(COLUMN_HIDDEN_KEY, JSON.stringify(Array.from(next))); } catch { /* ignore */ }
  }, []);

  const colByKey = React.useMemo(() => new Map(ALL_COLUMNS.map((c) => [c.key, c])), []);
  // Columns in display order, filtering hidden ones.
  const orderedCols = React.useMemo(
    () => columnOrder.map((k) => colByKey.get(k)).filter((c): c is CueCol => !!c && !hiddenColumns.has(c.key)),
    [columnOrder, hiddenColumns, colByKey],
  );

  function toggleColumn(key: string) {
    const next = new Set(hiddenColumns);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    persistHidden(next);
  }
  function moveColumn(key: string, dir: -1 | 1) {
    const idx = columnOrder.indexOf(key);
    const target = idx + dir;
    if (idx < 0 || target < 0 || target >= columnOrder.length) return;
    const next = [...columnOrder];
    [next[idx], next[target]] = [next[target], next[idx]];
    persistColumnOrder(next);
  }
  function resetColumns() {
    persistColumnOrder(ALL_COLUMN_KEYS);
    persistHidden(new Set());
  }
  function toggleSort(key: string) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  }

  // Monotonic token so a slower earlier load() (poller / manual Refresh /
  // post-action refresh run concurrently) can't commit after a newer one and
  // roll the table back to stale data.
  const loadRequestIdRef = React.useRef(0);
  const load = React.useCallback(
    async (showNames: string[], showList: Show[], isCancelled?: () => boolean) => {
      const requestId = ++loadRequestIdRef.current;
      if (showNames.length === 0) {
        setTreeByShow({});
        setJobs(null);
        return;
      }
      try {
        const result: Record<string, { tree: TreeNode | null; jobsByGroup: Record<string, Job[]> }> = {};
        const allJobs: Job[] = [];
        await Promise.all(
          showNames.map(async (name) => {
            const show = showList.find((s) => s.name === name);
            if (!show) return;
            const groups = await getShowGroups(show.id);
            const tree = buildTreeFromGroups(groups);
            // Load each group's direct jobs (parallel). Empty groups resolve to [].
            const jobsByGroup: Record<string, Job[]> = {};
            await Promise.all(
              groups.map(async (g) => {
                const js = await getGroupJobs(g.id);
                jobsByGroup[g.id] = js;
                allJobs.push(...js);
              }),
            );
            result[name] = { tree, jobsByGroup };
          }),
        );
        if (isCancelled?.() || requestId !== loadRequestIdRef.current) return;
        setTreeByShow(result);
        setJobs(allJobs);
        setNow(Date.now() / 1000);
      } catch (err) {
        if (isCancelled?.() || requestId !== loadRequestIdRef.current) return;
        handleError(err, "Could not load jobs");
        setJobs((prev) => prev ?? []);
      }
    },
    [],
  );

  React.useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;
    load(selectedShows, shows, isCancelled);
    // A group change (create / delete / properties) anywhere reloads the tree.
    const onGroupsChanged = () => load(selectedShows, shows, isCancelled);
    window.addEventListener(GROUPS_CHANGED_EVENT, onGroupsChanged);
    if (!autoRefresh) {
      return () => {
        cancelled = true;
        window.removeEventListener(GROUPS_CHANGED_EVENT, onGroupsChanged);
      };
    }
    const id = setInterval(() => load(selectedShows, shows, isCancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener(GROUPS_CHANGED_EVENT, onGroupsChanged);
    };
  }, [selectedShows, shows, autoRefresh, load]);

  // Close the group folder menu on any outside interaction.
  React.useEffect(() => {
    if (!groupMenu) return;
    const close = () => setGroupMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [groupMenu]);

  // Build the per-show group tree as flattened render rows (folders + jobs).
  // null until a show is selected (drives the "select a show" empty state).
  const showTrees = React.useMemo(() => {
    if (selectedShows.length === 0) return null;
    const sortCol = colByKey.get(sortKey);
    const accessor = (j: Job): number | string =>
      sortCol?.sort ? sortCol.sort(j) : j.name.toLowerCase();
    const cmp = (a: Job, b: Job) => {
      const va = accessor(a);
      const vb = accessor(b);
      let r: number;
      if (typeof va === "string" || typeof vb === "string") r = String(va).localeCompare(String(vb));
      else r = va - vb;
      return sortDir === "asc" ? r : -r;
    };
    const needle = filterText.trim().toLowerCase();
    return [...selectedShows]
      .sort((a, b) => a.localeCompare(b))
      .map((name) => {
        const entry = treeByShow[name];
        const root = entry?.tree ?? null;
        const rows = root ? flattenGroup(root, 1, entry.jobsByGroup, collapsedGroups, cmp, needle) : [];
        const jobCount = entry
          ? Object.values(entry.jobsByGroup).reduce((n, arr) => n + arr.length, 0)
          : 0;
        return { show: name, root: root?.group ?? null, rootStats: root?.rolledUpStats ?? null, rows, jobCount };
      });
  }, [treeByShow, selectedShows, collapsedGroups, sortKey, sortDir, colByKey, filterText]);

  const selectedJobs = React.useMemo(
    () => (jobs ?? []).filter((j) => selected.has(j.id)),
    [jobs, selected],
  );

  // Anchor for shift-click range selection, and the visible job ids in render
  // order (skipping collapsed shows / folders) so a range maps to what's shown.
  const lastSelectedRef = React.useRef<string | null>(null);
  const visibleJobIds = React.useMemo(
    () =>
      (showTrees ?? []).flatMap((st) =>
        collapsed.has(st.show)
          ? []
          : st.rows.filter((r): r is Extract<TreeRow, { kind: "job" }> => r.kind === "job").map((r) => r.job.id),
      ),
    [showTrees, collapsed],
  );

  function selectRange(toId: string) {
    const ids = visibleJobIds;
    const toIdx = ids.indexOf(toId);
    if (toIdx < 0) return;
    const anchorIdx = lastSelectedRef.current ? ids.indexOf(lastSelectedRef.current) : -1;
    if (anchorIdx < 0) {
      // The previous anchor is gone (refresh/filter/collapse). Select the
      // clicked row and re-anchor to it so the next Shift-click forms a range.
      lastSelectedRef.current = toId;
      setSelected((prev) => new Set(prev).add(toId));
      return;
    }
    const [lo, hi] = anchorIdx <= toIdx ? [anchorIdx, toIdx] : [toIdx, anchorIdx];
    setSelected((prev) => {
      const next = new Set(prev);
      for (let i = lo; i <= hi; i++) next.add(ids[i]);
      return next;
    });
  }

  // Row/checkbox selection: Shift+click extends a contiguous range from the
  // anchor; a plain (or Cmd/Ctrl) click toggles one job and sets the anchor.
  function handleSelect(id: string, e: React.MouseEvent) {
    if (e.shiftKey && lastSelectedRef.current) {
      e.preventDefault(); // suppress the browser's text-selection highlight
      selectRange(id);
      return;
    }
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    lastSelectedRef.current = id;
  }
  function toggleShowCollapse(show: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(show)) next.delete(show);
      else next.add(show);
      return next;
    });
  }

  function toggleGroupCollapse(groupId: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
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
    await load(selectedShows, shows);
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
  const allVisibleSelected = visibleJobIds.length > 0 && visibleJobIds.every((id) => selected.has(id));
  const someVisibleSelected = !allVisibleSelected && visibleJobIds.some((id) => selected.has(id));

  // Columns show/hide + reorder dropdown (parity with Monitor Jobs). Rendered
  // at the top-right of the table next to the filter box.
  const columnsDropdown = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          Columns
          <ChevronDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-[60vh] w-64 overflow-y-auto">
        <div className="sticky top-0 z-10 mb-1 border-b border-border bg-popover pb-1">
          <Button className="w-full justify-start px-2 py-1.5" variant="secondary" size="sm" onClick={resetColumns}>
            Reset to Default
          </Button>
        </div>
        {columnOrder.map((key, idx) => {
          const col = colByKey.get(key);
          if (!col) return null;
          const label = col.label || col.title || key;
          return (
            <DropdownMenuItem
              key={key}
              onSelect={(e) => e.preventDefault()}
              className="flex cursor-default items-center justify-between gap-2 px-2 py-1 focus:bg-accent/40"
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                <Checkbox
                  checked={!hiddenColumns.has(key)}
                  onCheckedChange={() => toggleColumn(key)}
                  aria-label={`Toggle ${label}`}
                />
                <span className="truncate">{label}</span>
              </label>
              <span className="inline-flex shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  aria-label={`Move ${label} left`}
                  title="Move left"
                  disabled={idx === 0}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); moveColumn(key, -1); }}
                  className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 disabled:opacity-30"
                >
                  <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={`Move ${label} right`}
                  title="Move right"
                  disabled={idx === columnOrder.length - 1}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); moveColumn(key, 1); }}
                  className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 disabled:opacity-30"
                >
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );

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
          onClick={() => setCollapsed(new Set((showTrees ?? []).map((st) => st.show)))}
        >
          Collapse All
        </Button>

        {/* Bulk actions on selected jobs. Icons mirror CueGUI's Monitor Cue
            toolbar (eat = Pacman, retry, pause, unpause, kill). */}
        <span className="mx-1 h-5 w-px bg-border" />
        <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={doEat} title="Eat dead frames">
          <TbPacman size={16} color="orange" /> Eat
        </Button>
        <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={doRetry} title="Retry dead frames">
          <TbReload size={16} className="text-green-600" /> Retry
        </Button>
        <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={doPause} title="Pause">
          <TbPlayerPause size={16} /> Pause
        </Button>
        <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={doUnpause} title="Unpause">
          <TbPlayerPlay size={16} className="text-green-600" /> Unpause
        </Button>
        <Button variant="destructive" size="sm" className="h-8 gap-1.5" onClick={doKill} title="Kill">
          <MdOutlineCancel size={16} /> Kill
        </Button>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Select:</span>
          <Input
            value={selectText}
            onChange={(e) => { setSelectText(e.target.value); applySelect(e.target.value); }}
            onKeyDown={(e) => e.key === "Enter" && applySelect(selectText)}
            placeholder="name / regex"
            className="h-8 w-48"
            aria-label="Select jobs"
            title="Type a name or regex to select (check) matching jobs"
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

      {showTrees === null ? (
        <p className="text-sm text-muted-foreground">Select one or more shows from the Shows menu to monitor their jobs.</p>
      ) : (
        <div ref={contextMenuTargetAreaRef}>
          {/* Top-right of the table: filter box + Columns dropdown (parity
              with Monitor Jobs). */}
          <div className="mb-2 flex items-center justify-end gap-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                placeholder="Filter jobs..."
                aria-label="Filter jobs"
                className="h-8 w-44 pl-7 text-xs"
              />
            </div>
            {columnsDropdown}
          </div>
          <div ref={tableRef} className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40 text-left">
                <tr>
                  <th className="w-8 p-2">
                    {/* Select all / none across the visible (expanded) jobs. */}
                    <Checkbox
                      checked={allVisibleSelected ? true : someVisibleSelected ? "indeterminate" : false}
                      onCheckedChange={(c) => setSelected(c ? new Set(visibleJobIds) : new Set())}
                      aria-label="Select all jobs"
                    />
                  </th>
                  {orderedCols.map((c) => {
                    const active = sortKey === c.key;
                    const alignClass = c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : "text-left";
                    return (
                      <th key={c.key} className={`p-2 font-medium ${c.minW ?? ""} ${alignClass}`} title={c.title}>
                        {c.sort ? (
                          <button
                            type="button"
                            onClick={() => toggleSort(c.key)}
                            className={`inline-flex items-center gap-1 ${c.align === "right" ? "flex-row-reverse" : ""} hover:text-foreground`}
                          >
                            {c.header ?? <span>{c.label}</span>}
                            {active ? (
                              sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ArrowUpDown className="h-3 w-3 opacity-40" />
                            )}
                          </button>
                        ) : (
                          c.header ?? c.label
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {showTrees.length === 0 ? (
                  <tr>
                    <td colSpan={orderedCols.length + 1} className="p-3 text-sm text-muted-foreground">
                      No jobs for the selected show(s).
                    </td>
                  </tr>
                ) : (
                  showTrees.map((st) => {
                    const isOpen = !collapsed.has(st.show);
                    const showObj = shows.find((s) => s.name === st.show);
                    return (
                      <React.Fragment key={st.show}>
                        {/* Show header = the root group; right-click opens the show menu. */}
                        <tr
                          className="border-b bg-muted/30"
                          onContextMenu={(e) => {
                            if (!showObj) return;
                            e.preventDefault();
                            setShowMenu({ x: e.clientX, y: e.clientY, show: showObj });
                          }}
                        >
                          <td className="px-2 py-1" />
                          <td className="px-2 py-1 font-semibold" colSpan={orderedCols.length}>
                            <button className="flex items-center gap-1" onClick={() => toggleShowCollapse(st.show)}>
                              {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                              {st.show}
                              <span className="ml-2 text-xs font-normal text-muted-foreground">({st.jobCount})</span>
                            </button>
                          </td>
                        </tr>
                        {isOpen
                          ? st.rows.map((r) =>
                              r.kind === "group" ? (
                                // Group folder row: stats from rolled-up GroupStats,
                                // folder name indented; right-click opens the group menu.
                                <tr
                                  key={`g-${r.group.id}`}
                                  className="border-b bg-muted/10"
                                  onContextMenu={(e) => {
                                    if (!showObj) return;
                                    e.preventDefault();
                                    setGroupMenu({ x: e.clientX, y: e.clientY, show: showObj, group: r.group });
                                  }}
                                >
                                  <td className="px-2 py-1" />
                                  {orderedCols.map((c) => {
                                    const alignClass =
                                      c.align === "right" ? "text-right tabular-nums" : c.align === "center" ? "text-center" : "";
                                    if (c.key === "job") {
                                      const folderOpen = !collapsedGroups.has(r.group.id);
                                      return (
                                        <td key={c.key} className="px-2 py-1 align-middle" style={{ paddingLeft: `${r.depth * 1.25 + 0.5}rem` }}>
                                          <button
                                            className="flex items-center gap-1 font-medium"
                                            onClick={() => toggleGroupCollapse(r.group.id)}
                                          >
                                            {folderOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                            <Folder className="h-3.5 w-3.5 text-muted-foreground" />
                                            {r.group.name}
                                          </button>
                                        </td>
                                      );
                                    }
                                    const stat = GROUP_STAT_COL[c.key];
                                    return (
                                      <td key={c.key} className={`px-2 py-1 align-middle ${alignClass}`}>
                                        {stat ? stat(r.stats) : ""}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ) : (
                                <tr
                                  key={r.job.id}
                                  className={`cursor-pointer select-none border-b last:border-0 ${jobRowClass(r.job)}`}
                                  onContextMenu={(e) => contextMenuHandleOpen(e, { original: r.job } as unknown as Row<Job>)}
                                  onClick={(e) => {
                                    handleSelect(r.job.id, e);
                                    // Load the job into the Attributes panel (CueGUI parity).
                                    setAttributeSelection({
                                      type: "job",
                                      id: r.job.id,
                                      name: r.job.name,
                                      data: r.job as unknown as Record<string, unknown>,
                                    });
                                  }}
                                >
                                  <td
                                    className="px-2 py-1 align-middle"
                                    onClick={(e) => { e.stopPropagation(); handleSelect(r.job.id, e); }}
                                  >
                                    <Checkbox
                                      checked={selected.has(r.job.id)}
                                      className="pointer-events-none"
                                      aria-label={`Select ${r.job.name}`}
                                    />
                                  </td>
                                  {orderedCols.map((c) => {
                                    const alignClass =
                                      c.align === "right" ? "text-right tabular-nums" : c.align === "center" ? "text-center" : "";
                                    const isJobCol = c.key === "job";
                                    const widthClass = isJobCol ? "max-w-[34rem] truncate" : c.minW ?? "";
                                    const style = isJobCol ? { paddingLeft: `${r.depth * 1.25 + 0.5}rem` } : undefined;
                                    return (
                                      <td
                                        key={c.key}
                                        className={`px-2 py-1 align-middle ${alignClass} ${widthClass}`}
                                        style={style}
                                        title={isJobCol ? r.job.name : undefined}
                                      >
                                        {c.cell(r.job, now)}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ),
                            )
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
      {/* Dialogs the job menu opens via CustomEvents: Set Min/Max Cores & GPUs,
          Max Retries, Reorder/Stagger Frames, Use Local Cores, Show Progress
          Bar (JobExtraDialogs), Comments (JobCommentsDialog), and Send To
          Group. Mounting them here makes every Monitor Cue menu item work. */}
      <JobExtraDialogs />
      <JobCommentsDialog />
      <SendToGroupDialog />

      {/* Show (group) right-click menu + the dialogs it opens (CueGUI Monitor
          Cue show menu parity). */}
      <MonitorCueShowMenu menu={showMenu} onClose={() => setShowMenu(null)} />
      <ShowPropertiesDialog />
      <GroupPropertiesDialog />
      <CreateGroupDialog />
      <ViewFiltersDialog />
      <TaskPropertiesDialog />
      <ServicePropertiesDialog />

      {/* Group folder right-click menu (CueGUI Monitor Cue group menu). */}
      {groupMenu ? (
        <div
          className="fixed z-50 min-w-48 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: groupMenu.x, top: groupMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => {
              window.dispatchEvent(
                new CustomEvent(OPEN_GROUP_PROPERTIES_EVENT, { detail: { show: groupMenu.show, group: groupMenu.group } }),
              );
              setGroupMenu(null);
            }}
          >
            Group Properties...
          </button>
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => {
              window.dispatchEvent(
                new CustomEvent(OPEN_CREATE_GROUP_EVENT, { detail: { show: groupMenu.show, parent: groupMenu.group } }),
              );
              setGroupMenu(null);
            }}
          >
            Create Group...
          </button>
          <div className="my-1 h-px bg-border" />
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => {
              setDeleteGroupTarget(groupMenu.group);
              setGroupMenu(null);
            }}
          >
            Delete Group
          </button>
        </div>
      ) : null}

      <ConfirmDialog
        open={deleteGroupTarget !== null}
        onOpenChange={(o) => !o && setDeleteGroupTarget(null)}
        title="Delete group?"
        description={deleteGroupTarget ? `Delete the group "${deleteGroupTarget.name}"? Its jobs move to the parent group.` : ""}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={async () => {
          if (deleteGroupTarget && (await deleteGroup(deleteGroupTarget))) {
            window.dispatchEvent(new CustomEvent(GROUPS_CHANGED_EVENT, { detail: {} }));
          }
          setDeleteGroupTarget(null);
        }}
      />

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
