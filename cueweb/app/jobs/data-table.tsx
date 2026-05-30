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


import {
  eatJobsDeadFramesFromSelectedRows,
  getItemFromLocalStorage,
  killJobFromSelectedRows,
  pauseJobsFromSelectedRows,
  retryJobsDeadFramesFromSelectedRows,
  setItemInLocalStorage,
  unpauseJobsFromSelectedRows
} from "@/app/utils/action_utils";
import {
  getJobsForRegex,
  getJobsForUser
} from "@/app/utils/get_utils";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { setAttributeSelection } from "@/app/utils/use_attribute_selection";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { JobContextMenu } from "@/components/ui/context_menus/action-context-menu";
import { useContextMenu } from "@/components/ui/context_menus/useContextMenu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { JobDetailsInline } from "@/components/ui/job-details-inline";
import { JobProgressBar } from "@/components/ui/job-progress-bar";
import JobSearchbox from "@/components/ui/jobs-searchbox";
import { DataTablePagination } from "@/components/ui/pagination";
import SearchDropdown from "@/components/ui/search-dropdown";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import { Label } from "@radix-ui/react-label";
import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  ColumnOrderState,
  getPaginationRowModel,
  getSortedRowModel,
  Row,
  useReactTable,
  VisibilityState
} from "@tanstack/react-table";
import debounce from "lodash/debounce";
import { ChevronDown, ChevronLeft, ChevronRight, Inbox, Search, SearchX, X } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useTheme } from "next-themes";
import * as React from "react";
import { useEffect, useReducer } from "react";
import { MdOutlineCancel } from "react-icons/md";
import { TbEyeOff, TbPacman, TbPlayerPause, TbPlayerPlay, TbReload } from "react-icons/tb";
import { UNKNOWN_USER } from "@/app/utils/constants";
import { getState, Job } from "./columns";
import "./index.css";

interface DataTableProps {
  columns: ColumnDef<Job>[];
  username: string;
}

// Define the actions for useReducer
type Action =
  | { type: "SET_AUTOLOAD_MINE"; payload: boolean }
  | { type: "SET_TABLE_DATA"; payload: Job[] }
  | { type: "SET_TABLE_DATA_UNFILTERED"; payload: Job[] }
  | { type: "SET_SORTING"; payload: any[] }
  | { type: "SET_COLUMN_FILTERS"; payload: any[] }
  | { type: "SET_STATE_SELECT_VALUE"; payload: string }
  | { type: "SET_JOB_SEARCH_RESULTS"; payload: Job[] }
  | { type: "SET_FILTERED_JOB_SEARCH_RESULTS"; payload: Job[] }
  | { type: "SET_SEARCH_QUERY"; payload: string }
  | { type: "SET_API_QUERY"; payload: string }
  | { type: "SET_ROW_SELECTION"; payload: { [key: string]: boolean } }
  | { type: "SET_COLUMN_VISIBILITY"; payload: VisibilityState }
  | { type: "SET_COLUMN_ORDER"; payload: ColumnOrderState }
  | { type: "SET_ERROR"; payload: string | null } // New action for setting errors
  | { type: "SET_USERNAME"; payload: string }
  | { type: "SET_LOAD_FINISHED"; payload: boolean }
  | { type: "SET_GROUP_BY"; payload: State["groupBy"] }
  | { type: "SET_PICK_FROM_LIST"; payload: boolean }
  | { type: "RESET_COLUMN_VISIBILITY" }
  | { type: "RESET_STATE" };

// tableDataUnfiltered starts off containing the same exact data as tableData (which is used to populate the table)
// The difference is tableDataUnfiltered will be used to keep track of the table data without any 'state' filters
// This is so that when we update the tableData based on the 'state' the user is filtering on,
// tableDataUnfiltered remains the same, so that the user can later access the unfiltered table data

// For example, let's say the user filters tableData on state 'In Progress'
// When they later filter on state 'Finished', we search the unfiltered table data for jobs with state 'Finished'
// If we didn't keep track of the unfiltered table data, the user would get no results because we would be searching
// tableData for state 'Finished' and tableData currently only contains jobs with state 'In Progress'
interface State {
  autoloadMine: boolean;
  tableData: Job[];
  tableDataUnfiltered: Job[];
  sorting: any[];
  columnFilters: ColumnFiltersState;
  stateSelectValue: string;
  jobSearchResults: Job[];
  filteredJobSearchResults: Job[];
  searchQuery: string;
  apiQuery: string;
  rowSelection: { [key: string]: boolean };
  columnVisibility: VisibilityState;
  // Full column order (every column id, in display order). Empty array means
  // "use the natural order from the column defs" (TanStack convention).
  columnOrder: ColumnOrderState;
  error: string | null;
  username: string;
  // CueGUI parity: include finished jobs in autoload-mine + saved-job
  // refreshes when the user opts in via the "Load Finished" checkbox.
  loadFinished: boolean;
  // CueGUI parity: Group By mode for the Monitor Jobs table. Rows are
  // sorted by the computed group key and interleaved with collapsible
  // header rows in the TableBody. See getJobGroupKey() below.
  groupBy: "Clear" | "Dependent" | "Show" | "Show-Shot" | "Show-Shot-Username";
  // Two search modes, persisted across reloads:
  //   - false (default, CueGUI parity): type + Enter loads every match
  //     directly into the table.
  //   - true: each keystroke fires a live regex query; results appear in
  //     the dropdown and the user clicks individual jobs to add them
  //     (the original CueWeb behavior).
  pickFromList: boolean;
}

// Default column visibility for the jobs table: everything visible.
// Users can still hide individual columns via the Columns dropdown, and
// "Reset to Default" puts them all back.
const initialColumnVisibility = {}

// The initial state of the data table on remount using local storage to preserve states
function getInitialState(): State {
  return {
    autoloadMine: getItemFromLocalStorage("autoloadMine", "true"),
    tableData: getItemFromLocalStorage("tableData", "[]"),
    tableDataUnfiltered: getItemFromLocalStorage("tableDataUnfiltered", "[]"),
    sorting: getItemFromLocalStorage("sorting", "[]"),
    columnFilters: getItemFromLocalStorage("columnFilters", "[]"),
    stateSelectValue: getItemFromLocalStorage("stateSelectValue", JSON.stringify("All States")),
    jobSearchResults: [],
    filteredJobSearchResults: [],
    searchQuery: "",
    apiQuery: "",
    rowSelection: {},
    columnVisibility: getItemFromLocalStorage("columnVisibility", JSON.stringify(initialColumnVisibility)),
    columnOrder: getItemFromLocalStorage("columnOrder", "[]"),
    error: null,
    username: UNKNOWN_USER,
    loadFinished: getItemFromLocalStorage("loadFinished", "false"),
    groupBy: getItemFromLocalStorage("groupBy", JSON.stringify("Clear")),
    pickFromList: getItemFromLocalStorage("pickFromList", "false"),
  }
};

// Reducer function
function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_AUTOLOAD_MINE":
      return { ...state, autoloadMine: action.payload };
    case "SET_TABLE_DATA":
      return { ...state, tableData: action.payload };
    case "SET_TABLE_DATA_UNFILTERED":
      return { ...state, tableDataUnfiltered: action.payload };
    case "SET_SORTING":
      return { ...state, sorting: action.payload };
    case "SET_COLUMN_FILTERS":
      return { ...state, columnFilters: action.payload };
    case "SET_STATE_SELECT_VALUE":
      return { ...state, stateSelectValue: action.payload };
    case "SET_JOB_SEARCH_RESULTS":
      return { ...state, jobSearchResults: action.payload };
    case "SET_FILTERED_JOB_SEARCH_RESULTS":
      return { ...state, filteredJobSearchResults: action.payload };
    case "SET_SEARCH_QUERY":
      return { ...state, searchQuery: action.payload };
    case "SET_API_QUERY":
      return { ...state, apiQuery: action.payload };
    case "SET_ROW_SELECTION":
      return { ...state, rowSelection: action.payload };
    case "SET_COLUMN_VISIBILITY":
      return { ...state, columnVisibility: action.payload };
    case "SET_COLUMN_ORDER":
      return { ...state, columnOrder: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload }; // Set the error message
    case "SET_USERNAME":
      return { ...state, username: action.payload };
    case "SET_LOAD_FINISHED":
      setItemInLocalStorage("loadFinished", JSON.stringify(action.payload));
      return { ...state, loadFinished: action.payload };
    case "SET_GROUP_BY":
      setItemInLocalStorage("groupBy", JSON.stringify(action.payload));
      return { ...state, groupBy: action.payload };
    case "SET_PICK_FROM_LIST":
      setItemInLocalStorage("pickFromList", JSON.stringify(action.payload));
      return { ...state, pickFromList: action.payload };
    case "RESET_COLUMN_VISIBILITY":
      return {
        ...state,
        columnVisibility: initialColumnVisibility,
      };
    case "RESET_STATE":
      return getInitialState();
    default:
      return state;
  }
}

// Reusable compact action button used in the Monitor Jobs toolbar.
// Mirrors the CueGUI Monitor Jobs dock buttons: small icon + short label,
// auto-disabled when the "Disable Job Interaction" safety flag is on.
// Resolves the group-by key for a single job. The key is also the label
// rendered on the group-header row in the table body. Matches CueGUI's
// MonitorJobsPlugin grouping modes; the "Dependent" mode is the
// approximate (job-local) variant - it splits jobs into "Has pending
// dependencies" vs "Independent jobs" based on jobStats.dependFrames.
// Full dependency-graph grouping would require fetching each job's
// depends from Cuebot and is tracked as a follow-up.
function getJobGroupKey(job: Job, mode: State["groupBy"]): string {
  switch (mode) {
    case "Show":
      return job.show || "(no show)";
    case "Show-Shot":
      return `${job.show || "(no show)"} - ${job.shot || "(no shot)"}`;
    case "Show-Shot-Username":
      return `${job.show || "(no show)"} - ${job.shot || "(no shot)"} - ${job.user || "(no user)"}`;
    case "Dependent":
      return (job.jobStats?.dependFrames ?? 0) > 0
        ? "Has pending dependencies"
        : "Independent jobs";
    case "Clear":
    default:
      return "";
  }
}

const JobActionButton = ({
  icon: Icon,
  label,
  onClick,
  color,
  variant = "default",
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  color?: string;
  variant?: "default" | "destructive";
}) => {
  const { disabled } = useDisableJobInteraction();
  const tint = disabled
    ? "text-muted-foreground"
    : variant === "destructive"
      ? "text-destructive hover:text-destructive"
      : "text-foreground/80 hover:text-foreground";
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      aria-disabled={disabled}
      title={
        disabled
          ? "Disabled - File -> Disable Job Interaction is on"
          : label
      }
      className={`inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md border border-border bg-background px-3 text-xs font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50 ${tint}`}
    >
      <Icon size={14} color={disabled ? undefined : color} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
};

export function DataTable({ columns, username }: DataTableProps) {
  const { theme, setTheme } = useTheme();

  // useReducer hook to manage state
  const [state, dispatch] = useReducer(reducer, getInitialState());

  // CueGUI parity: clicking a row in the jobs table loads its layers +
  // frames into the inline detail panels below. Tracks the last-clicked
  // job by id so renaming or duplicate name matches stay accurate.
  const [detailJob, setDetailJob] = React.useState<Job | null>(null);

  // Keep the detail panels in sync if the selected job is later removed
  // from the monitor list (unmonitor finished/all/selected, finished-job
  // sweeps, etc.).
  React.useEffect(() => {
    if (!detailJob) return;
    const stillPresent = state.tableDataUnfiltered.some(
      (j: Job) => j.id === detailJob.id,
    );
    if (!stillPresent) setDetailJob(null);
  }, [detailJob, state.tableDataUnfiltered]);

  // Tracks which group headers are currently collapsed (by group key).
  // Toggled via a click on the header row in the TableBody. Reset when
  // the user switches grouping mode so stale keys do not linger.
  const [collapsedGroups, setCollapsedGroups] = React.useState<Set<string>>(new Set());
  React.useEffect(() => {
    setCollapsedGroups(new Set());
  }, [state.groupBy]);
  const toggleGroup = React.useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Skeleton rows are shown only on the very first paint while we wait
  // for the autoload-mine fetch to complete. If localStorage already has
  // cached jobs, no skeletons are needed.
  const [initialLoading, setInitialLoading] = React.useState<boolean>(false);

  useEffect(() => {
    dispatch({ type: "RESET_STATE"});
    const cached = getItemFromLocalStorage("tableData", "[]");
    if (Array.isArray(cached) && cached.length === 0) {
      setInitialLoading(true);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await addUsersJobs();
      setInitialLoading(false);
    })();
    // state.loadFinished is read inside addUsersJobs() (it forwards the
    // flag to getJobsForUser), so it has to be in the dep array - without
    // it, toggling Load Finished doesn't re-run this effect and the
    // Autoload Mine fetch keeps using whatever value loadFinished had on
    // the previous run.
  }, [state.username, state.autoloadMine, state.loadFinished]);
  
  useEffect(() => {
    setItemInLocalStorage("autoloadMine", JSON.stringify(state.autoloadMine));
  }, [state.autoloadMine]);

  useEffect(() => {
    setItemInLocalStorage("tableData", JSON.stringify(state.tableData));
  }, [state.tableData]);

  useEffect(() => {
    setItemInLocalStorage("tableDataUnfiltered", JSON.stringify(state.tableDataUnfiltered));
  }, [state.tableDataUnfiltered]);
  
  useEffect(() => {
    setItemInLocalStorage("sorting", JSON.stringify(state.sorting));
  }, [state.sorting]);

  useEffect(() => {
    setItemInLocalStorage("columnFilters", JSON.stringify(state.columnFilters));
  }, [state.columnFilters]);

  useEffect(() => {
    setItemInLocalStorage("columnVisibility", JSON.stringify(state.columnVisibility));
  }, [state.columnVisibility]);

  useEffect(() => {
    setItemInLocalStorage("columnOrder", JSON.stringify(state.columnOrder));
  }, [state.columnOrder]);

  useEffect(() => {
    setItemInLocalStorage("stateSelectValue", JSON.stringify(state.stateSelectValue));
  }, [state.stateSelectValue]);

  useEffect(() => {
    dispatch({ type: "SET_USERNAME", payload: username });
  }, []);

  function setAutoloadMine(
    dispatch: React.Dispatch<Action>,
    autoloadMine: boolean): React.Dispatch<React.SetStateAction<boolean>> {
    return (update) => {
      const newAutoload = typeof update === "function" ? update(autoloadMine) : update;
      dispatch({ type: "SET_AUTOLOAD_MINE", payload: newAutoload });
    };
  }

  function setTableData(
    dispatch: React.Dispatch<Action>,
    tableData: Job[]): React.Dispatch<React.SetStateAction<Job[]>> {
    return (update) => {
      const newTableData = typeof update === "function" ? update(tableData) : update;
      dispatch({ type: "SET_TABLE_DATA", payload: newTableData });
    };
  }

  function setTableDataUnfiltered(
    dispatch: React.Dispatch<Action>,
    tableData: Job[]): React.Dispatch<React.SetStateAction<Job[]>> {
    return (update) => {
      const newTableData = typeof update === "function" ? update(tableData) : update;
      dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: newTableData });
    };
  }

  function setRowSelection(
    dispatch: React.Dispatch<Action>,
    rowSelection: { [key: string]: boolean }
  ): React.Dispatch<React.SetStateAction<{ [key: string]: boolean }>> {
    return (update) => {
      const newRowSelection = typeof update === "function" ? update(rowSelection) : update;
      dispatch({ type: "SET_ROW_SELECTION", payload: newRowSelection });
    };
  }
  
  function setSorting(
    dispatch: React.Dispatch<Action>,
    sorting: any[]
  ): React.Dispatch<React.SetStateAction<any[]>> {
    return (update) => {
      const newSorting = typeof update === "function" ? update(sorting) : update;
      dispatch({ type: "SET_SORTING", payload: newSorting });
    };
  }
  
  function setColumnFilters(
    dispatch: React.Dispatch<Action>,
    columnFilters: ColumnFiltersState
  ): React.Dispatch<React.SetStateAction<ColumnFiltersState>> {
    return (update) => {
      const newColumnFilters = typeof update === "function" ? update(columnFilters) : update;
      dispatch({ type: "SET_COLUMN_FILTERS", payload: newColumnFilters });
    };
  }
  
  function setColumnVisibility(
    dispatch: React.Dispatch<Action>,
    columnVisibility: VisibilityState
  ): React.Dispatch<React.SetStateAction<VisibilityState>> {
    return (update) => {
      const newColumnVisibility = typeof update === "function" ? update(columnVisibility) : update;
      dispatch({ type: "SET_COLUMN_VISIBILITY", payload: newColumnVisibility });
    };
  }

  // Search/dropdown variables:
  const [hideSearchDropdown, setHideSearchDropdown] = React.useState<boolean>(true);
  // The amount of delay in milliseconds after typing stops that is required before calling handleGetJobs
  const searchDelay = 300;
  // Current api query to keep track if it changes during search
  const [jobSearchLoading, setJobSearchLoading] = React.useState<boolean>(false);
  const [waitingForFiltering, setWaitingForFiltering] = React.useState<boolean>(false);
  const [searchDropdownWidth, setSearchDropdownWidth] = React.useState<number>(1000);
  const filterWorkerRef = React.useRef<Worker | null>(null);
  const searchDropdownRef = React.useRef<HTMLDivElement | null>(null);
  // Used to track when searching (API and Filtering) is finished
  // Without this, the loading component would render right as '-' was typed
  const searchFinishedRef = React.useRef<boolean>(false);
  const SEARCH_BY_REGEX = "search_by_regex";
  const TOOLTIP_TITLE = `
  Search by any substring or regex pattern against the job name.<br>
  Use .* to match any string<br>
  Example searches:<br>
  &nbsp;&nbsp;&nbsp;&nbsp;testing<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2.*comp<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2-(madkisson|chung).*comp<br>
  Jobs finished for 3 days will not be shown.`;
  // column IDs of columns that look better when their data is center-aligned, rather than to the left (the default)
  // Every body cell is centered now via the TableCell className below;
  // the legacy `centeredColumns` allowlist is no longer needed.
  
  // Regularly update the data-table data to see if jobs have changed attributes
  useEffect(() => {
    let interval: NodeJS.Timeout | undefined;
    let worker: Worker | undefined;
    let refreshHandler: (() => void) | undefined;
    try{
      // Worker to update table data on a separate thread every 5 seconds
      worker = new Worker(new URL('/public/workers/updateJobsTableDataWorker.tsx', import.meta.url));
      const updateData = () => {
        if (worker) {
          worker.postMessage({ jobs: state.tableDataUnfiltered });
        } else {
          throw new Error("Error creating worker in data-table.tsx");
        } 
      };

      worker.onmessage = (e) => {
        if (e.data.error || typeof e.data.updatedJobs === undefined) {
          throw new Error(e.data.error);
        }
        const newData = e.data.updatedJobs;
        if (JSON.stringify(newData) !== JSON.stringify(state.tableDataUnfiltered)) {
          // Update the old data based on the new data retrieved from the web worker
          let updatedTableDataUnfiltered = state.tableDataUnfiltered.map((oldJob: Job) => {
            const updatedJob = newData.find((newJob: Job) => newJob.id === oldJob.id);
            return updatedJob ? updatedJob : oldJob;
          });
          let updatedTableData = state.tableData.map((oldJob: Job) => {
            const updatedJob = newData.find((newJob: Job) => newJob.id === oldJob.id);
            return updatedJob ? updatedJob : oldJob;
          });
          
          // Filter out any of the old data in the data table which no longer exists (has been finished for over 48 hours)
          updatedTableDataUnfiltered = updatedTableDataUnfiltered.filter((oldJob: Job) => newData.some((newJob: Job) => oldJob.id === newJob.id));
          updatedTableData = updatedTableData.filter((oldJob: Job) => newData.some((newJob: Job) => oldJob.id === newJob.id));
          // Update table data as both a variable and in local storage
          dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: updatedTableDataUnfiltered });
          dispatch({ type: "SET_TABLE_DATA", payload: updatedTableData });
        }
      };

      // Helper used by both the 5s interval and the on-demand `r` shortcut.
      // Refreshing dispatches the same `cueweb:jobs-refreshed` event the
      // status bar already listens for, so manual refreshes update the
      // "Last refresh" timestamp identically to scheduled ones.
      const refreshOnce = async () => {
        updateData();
        await addUsersJobs();
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("cueweb:jobs-refreshed", {
              detail: { at: new Date().toISOString() },
            }),
          );
        }
      };

      interval = setInterval(refreshOnce, 5000);

      // Wire the global `r` keyboard shortcut (dispatched by
      // KeyboardShortcuts) to an immediate refresh of this table.
      if (typeof window !== "undefined") {
        refreshHandler = () => {
          void refreshOnce();
        };
        window.addEventListener("cueweb:refresh-now", refreshHandler);
      }
    } catch (error) {
      handleError(error, "Error updating table");
    }

    return () => {
      // Clean up interval on component unmount
      if (interval) clearInterval(interval);
      if (refreshHandler && typeof window !== "undefined") {
        window.removeEventListener("cueweb:refresh-now", refreshHandler);
      }
      // Terminate the worker when the component unmounts
      worker?.terminate();
    };
    // state.loadFinished feeds addUsersJobs() inside this effect's polling
    // tick; without it in the dep array, toggling Load Finished doesn't
    // rebuild the interval and the 5s refresh keeps the stale value.
  }, [state.tableDataUnfiltered, state.tableData, state.autoloadMine, state.loadFinished]);

  // Automatically remove jobs in selectedRows if they've been removed from the table.
  // Cases where jobs are removed include:
  // - deselecting jobs that have been added from the dropdown
  // - automatically removed jobs by a web worker because the jobs been finished for 48 hours 
  useEffect(() => {
    const updatedRowSelection = { ...state.rowSelection };
    const validJobIds = new Set(state.tableDataUnfiltered.map((job: Job) => job.id));
    Object.keys(updatedRowSelection).forEach((jobId: string) => {
      if (!validJobIds.has(jobId)) {
        delete updatedRowSelection[jobId];
      }
    });
    dispatch({ type: "SET_ROW_SELECTION", payload: updatedRowSelection });
  }, [state.tableDataUnfiltered]);

  // Uses debouncing and memoization (useCallback) to cache the function and only run after delay of no typing.
  // Single path now: regex match against job name (CueGUI parity).
  // `includeFinished` is passed through so the live-search results respect
  // the "Load Finished" toggle. The debounced function is created once
  // with an empty deps array, so we pass `includeFinished` as a call-time
  // arg instead of closing over it (otherwise the stale snapshot would
  // win after a toggle change).
  const handleGetJobs = React.useCallback(
    debounce(async (query: string, searchType: string, includeFinished: boolean) => {
      if (searchType !== SEARCH_BY_REGEX) return;
      dispatch({ type: "SET_API_QUERY", payload: SEARCH_BY_REGEX });
      setJobSearchLoading(true);
      try {
        const newJobs = await getJobsForRegex(query, includeFinished);
        dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: newJobs });
        dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: newJobs });
        searchFinishedRef.current = true;
      } catch (error) {
        handleError(error, "Error searching for jobs");
      } finally {
        // Always clear the spinner, even when getJobsForRegex throws -
        // otherwise the search input stays stuck in the loading state.
        setJobSearchLoading(false);
      }
    }, searchDelay),
    [],
  );

  // Use a worker thread to filter and return the filtered jobs based on the query
  useEffect(() => {
    filterWorkerRef.current = new Worker(new URL("/public/workers/searchFilterWorker.tsx", import.meta.url));

    if (filterWorkerRef.current) {
      filterWorkerRef.current.onmessage = (e: MessageEvent<any>) => {
        // If there is an error in the web worker, set filtered jobs to empty and show errors
        // Otherise, set filtered jobs to filtering results
        if (e.data.error) {
          handleError(e.data.error, "Issue with filtering");
          dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
        } else {
          dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: e.data });
        }
        setWaitingForFiltering(false);
      };
    }

    return () => {
      filterWorkerRef.current?.terminate();
    };
  }, []);

  // Calls the worker thread when jobs, input, or API status changes
  useEffect(() => {
    const handleFiltering = (query: string) => {
      if (filterWorkerRef.current) {
        setWaitingForFiltering(true);
        filterWorkerRef.current.postMessage({ allJobs: state.jobSearchResults, query });
      }
    };

    if (state.apiQuery !== SEARCH_BY_REGEX && !jobSearchLoading) {
      handleFiltering(state.searchQuery);
      searchFinishedRef.current = true;
    }
  }, [state.jobSearchResults, state.searchQuery, jobSearchLoading]);

  // Opens/closes search dropdown based on where the user clicks
  const handleClickOutsideDropdown = (event: MouseEvent) => {
    if (searchDropdownRef && searchDropdownRef.current) {
      if (!searchDropdownRef.current.contains(event.target as Node)) {
        setHideSearchDropdown(true);
      } else if (searchDropdownRef.current.contains(event.target as Node)) {
        setHideSearchDropdown(false);
      }
    }
  };

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutsideDropdown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutsideDropdown);
    };
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    searchFinishedRef.current = false;
    setHideSearchDropdown(true);

    const query = e.target.value;
    dispatch({ type: "SET_SEARCH_QUERY", payload: query });

    // Two modes (the user picks one via the "Pick from list" toggle):
    //   - default / unchecked: CueGUI parity. Typing only updates the
    //     local search-query state; no API hit. The user presses Enter
    //     to load every match into the table at once.
    //   - checked: live dropdown. Each keystroke fires a debounced regex
    //     query and the dropdown surfaces individual jobs the user can
    //     click to add. This was the original CueWeb behavior.
    if (!state.pickFromList) {
      // Always keep the results panel clean in default mode so it never
      // pops up between keystrokes; the Enter handler will populate it.
      dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_API_QUERY", payload: "" });
      return;
    }

    if (query.trim().length === 0) {
      dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_API_QUERY", payload: "" });
      return;
    }

    // CueGUI parity for the regex grammar: `!` suffix accepted but
    // stripped, otherwise any text is the pattern.
    const regexQuery = query.endsWith("!") ? query.slice(0, -1) : query;
    handleGetJobs(regexQuery, SEARCH_BY_REGEX, state.loadFinished);
    setHideSearchDropdown(false);

    // Cancel handleGetJobs if the input changes before the timeout completes
    return () => {
      handleGetJobs.cancel();
    };
  };

  // Clears the search box and any open dropdown / loaded suggestions.
  // Mirrors the CueGUI "Clr" button next to the Load text input.
  const handleClearSearch = () => {
    handleGetJobs.cancel?.();
    dispatch({ type: "SET_SEARCH_QUERY", payload: "" });
    dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: [] });
    dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
    dispatch({ type: "SET_API_QUERY", payload: "" });
    setHideSearchDropdown(true);
    setJobSearchLoading(false);
    searchFinishedRef.current = false;
  };

  // Submit handler for the explicit "Load" button next to the search
  // input (CueGUI's <Load:> button). Also wired to the Enter key in
  // both modes - so users in Pick-from-list can still bulk-load if
  // they don't want to click each match individually. Hits the regex
  // endpoint, de-duplicates against jobs already in the table, then
  // adds the rest in one batch. Clears the input on success so the
  // user can immediately type the next query.
  const handleSearchSubmit = async (rawQuery: string) => {
    const query = rawQuery.trim();
    if (query.length === 0) return;

    setHideSearchDropdown(true);
    setJobSearchLoading(true);
    try {
      const regexQuery = query.endsWith("!") ? query.slice(0, -1) : query;
      const matches = await getJobsForRegex(regexQuery, state.loadFinished);

      if (matches.length === 0) {
        toastWarning(`No jobs match "${query}"`);
        return;
      }

      const existingNames = new Set(
        state.tableDataUnfiltered.map((j: Job) => j.name),
      );
      const fresh = matches.filter((j: Job) => !existingNames.has(j.name));

      if (fresh.length === 0) {
        toastWarning(
          `All ${matches.length} match${matches.length === 1 ? "" : "es"} for "${query}" are already loaded.`,
        );
        return;
      }

      dispatch({
        type: "SET_TABLE_DATA",
        payload: [...state.tableData, ...fresh],
      });
      dispatch({
        type: "SET_TABLE_DATA_UNFILTERED",
        payload: [...state.tableDataUnfiltered, ...fresh],
      });
      toastSuccess(
        `Loaded ${fresh.length} job${fresh.length === 1 ? "" : "s"} matching "${query}".`,
      );
      dispatch({ type: "SET_SEARCH_QUERY", payload: "" });
    } catch (err) {
      handleError(err, "Error loading jobs from search");
    } finally {
      setJobSearchLoading(false);
    }
  };

  // Deep-link: `/?search=<jobname>` from elsewhere in the app
  // (the job detail page's "View in Monitor Jobs" button) auto-loads
  // the matching job into the Cuetopia table on mount. Regex special
  // characters in the URL param are escaped so the value behaves as a
  // literal substring instead of accidentally matching unrelated jobs.
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const autoLoadedRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    const q = searchParams?.get("search") ?? "";
    if (!q) return;
    if (autoLoadedRef.current === q) return; // already handled this query
    autoLoadedRef.current = q;
    const escaped = q.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
    handleSearchSubmit(escaped).finally(() => {
      // Drop the param so reloads do not keep re-firing the search.
      try {
        const next = new URLSearchParams(searchParams?.toString() ?? "");
        next.delete("search");
        const qs = next.toString();
        router.replace(qs ? `${pathname}?${qs}` : (pathname ?? "/"), {
          scroll: false,
        });
      } catch {
        /* ignore */
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleUnmonitorSelected = () => {
    const selectedRows = table.getSelectedRowModel().rows;
    let jobsToUnmonitorSet = new Set(selectedRows.map((row: Row<Job>) => JSON.stringify(row.original)));

    const updatedTableDataUnfiltered = state.tableDataUnfiltered.filter(
      (job: Job) => !jobsToUnmonitorSet.has(JSON.stringify(job)),
    );
    dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: updatedTableDataUnfiltered });

    const updatedTableData = state.tableData.filter((job: Job) => !jobsToUnmonitorSet.has(JSON.stringify(job)));
    dispatch({ type: "SET_TABLE_DATA", payload: updatedTableData });

    dispatch({ type: "SET_ROW_SELECTION", payload: {} });
  };

  const handleUnmonitorPaused = () => {
    const pausedJobs = state.tableData.filter((job: Job) => getState(job) === "Paused");

    // Update unfiltered table data
    const updatedTableDataUnfiltered = state.tableDataUnfiltered.filter(
      (job: Job) => !pausedJobs.some((pausedJob: Job) => pausedJob === job),
    );
    dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: updatedTableDataUnfiltered });
    
    // Update table data
    const updatedTableData = state.tableData.filter((job: Job) => !pausedJobs.some((pausedJob: Job) => pausedJob === job));
    dispatch({ type: "SET_TABLE_DATA", payload: updatedTableData });
    
    // Update row selection data
    const updatedRowSelection = { ...state.rowSelection };
    pausedJobs.forEach((pausedJob: Job) => {
      delete updatedRowSelection[pausedJob.id];
    });
    dispatch({ type: "SET_ROW_SELECTION", payload: updatedRowSelection });
  };

  const handleUnmonitorFinished = () => {
    const finishedJobs = state.tableDataUnfiltered.filter((job: Job) => getState(job) === "Finished");

    // Update unfiltered table data
    const updatedTableDataUnfiltered = state.tableDataUnfiltered.filter(
      (job: Job) => !finishedJobs.some((finishedJob: Job) => finishedJob === job),
    );
    dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: updatedTableDataUnfiltered });
    
    // Update table data
    const updatedTableData = state.tableData.filter(
      (job: Job) => !finishedJobs.some((finishedJob: Job) => finishedJob === job),
    );
    dispatch({ type: "SET_TABLE_DATA", payload: updatedTableData });
    
    // Update row selection data
    const updatedRowSelection = { ...state.rowSelection };
    finishedJobs.forEach((pausedJob: Job) => {
      delete updatedRowSelection[pausedJob.id];
    });
    dispatch({ type: "SET_ROW_SELECTION", payload: updatedRowSelection });
  };
  
  const handleUnmonitorAll = () => {
    dispatch({ type: "SET_TABLE_DATA", payload: [] });
    dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: [] });
    dispatch({ type: "SET_ROW_SELECTION", payload: {} });
  };

  const handleJobSearchSelect = (job: Job) => {
    // we check if the job is already in tableDataUnfiltered so we don't add it twice
    const isJobAlreadyAdded = state.tableDataUnfiltered.some((existingJob: Job) => (existingJob as Job).name === job.name);

    if (!isJobAlreadyAdded) {
      // if job not already in the table data, add it (to both tableData & tableDataUnfiltered)
      dispatch({ type: "SET_TABLE_DATA", payload: [...state.tableData, job] });
      dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: [...state.tableDataUnfiltered, job] });
    } else {
      const newTableData = state.tableData.filter(oldJob => oldJob.name !== job.name);
      dispatch({ type: "SET_TABLE_DATA", payload: newTableData });

      const newTableDataUnfiltered = state.tableDataUnfiltered.filter(oldJob => oldJob.name !== job.name);
      dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: newTableDataUnfiltered });
    }
  };

  async function addUsersJobs() {
    if (!state.autoloadMine || state.username === UNKNOWN_USER) return;

    const userJobs = await getJobsForUser(state.username, state.loadFinished);

    const jobsToAddUnfiltered = userJobs.filter(userJob => {
      return !state.tableDataUnfiltered.some(existingJob => existingJob.name === userJob.name)
    });

    const jobsToAdd = userJobs.filter(userJob => {
      return !state.tableData.some(existingJob => existingJob.name === userJob.name)
    });

    if (jobsToAddUnfiltered.length > 0) {
      dispatch({ type: "SET_TABLE_DATA", payload: [...state.tableDataUnfiltered, ...jobsToAddUnfiltered] });
    }

    if (jobsToAdd.length > 0) {
      dispatch({ type: "SET_TABLE_DATA_UNFILTERED", payload: [...state.tableData, ...jobsToAdd] });
    }
  };

  const handleStateFiltering = (stateFilter: string) => {
    dispatch({ type: "SET_STATE_SELECT_VALUE", payload: stateFilter });
    if (stateFilter === "All States") {
      dispatch({ type: "SET_TABLE_DATA", payload: state.tableDataUnfiltered });
    } else {
      const newTableData = state.tableDataUnfiltered.filter((job: Job) => getState(job) === stateFilter);
      dispatch({ type: "SET_TABLE_DATA", payload: newTableData });
    }
  };

  useEffect(() => {
    handleStateFiltering(state.stateSelectValue);
  }, [state.tableDataUnfiltered]);

  const resetColumnsToDefault = () => {
    // Reset both visibility AND order so the table fully returns to the
    // natural defaults defined in columns.tsx.
    dispatch({ type: "SET_COLUMN_VISIBILITY", payload: initialColumnVisibility });
    dispatch({ type: "SET_COLUMN_ORDER", payload: [] });
  };

  // Hoisted above useReactTable so its `meta` block can pass
  // `contextMenuHandleOpen` to the Actions column cell. The cell forwards
  // its tap to the same handler the row-level right-click already uses,
  // so touch users get the same menu without needing a real contextmenu
  // event.
  const jobTableRef = React.useRef<HTMLDivElement>(null);
  const {
    contextMenuState,
    contextMenuHandleOpen,
    contextMenuHandleClose,
    contextMenuRef,
    contextMenuTargetAreaRef,
  } = useContextMenu(jobTableRef);

  const setColumnOrderDispatch = React.useCallback(
    (update: React.SetStateAction<ColumnOrderState>) => {
      const next = typeof update === "function" ? update(state.columnOrder) : update;
      dispatch({ type: "SET_COLUMN_ORDER", payload: next });
    },
    [state.columnOrder],
  );

  // Client-side substring filter that narrows the rows currently loaded
  // in the Jobs table (distinct from the server-side "Load" / "Pick from
  // list" searches at the top of the page).
  const [jobLocalFilter, setJobLocalFilter] = React.useState<string>("");

  const table = useReactTable({
    data: state.tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting(dispatch, state.sorting),
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters(dispatch, state.columnFilters),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility(dispatch, state.columnVisibility),
    onColumnOrderChange: setColumnOrderDispatch,
    onGlobalFilterChange: setJobLocalFilter,
    onRowSelectionChange: setRowSelection(dispatch, state.rowSelection),
    getRowId: (job: Job) => job.id,
    autoResetPageIndex: false,

    // Column resizing: TanStack handles the drag math; we render the
    // resize handle below in each TableHead and apply the live size as
    // an inline width style on the header/cell.
    enableColumnResizing: true,
    columnResizeMode: "onChange",

    state: {
      sorting: state.sorting,
      columnFilters: state.columnFilters,
      columnVisibility: state.columnVisibility,
      columnOrder: state.columnOrder,
      globalFilter: jobLocalFilter,
      rowSelection: state.rowSelection,
    },

    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: 10,
      },
    },

    meta: {
      // Surface the right-click menu via tap. The Actions column reads
      // this and calls it from a button click; mobile users get the same
      // menu without needing a real contextmenu event.
      openContextMenu: contextMenuHandleOpen,
    },
  });

  // Snap back to page 1 whenever the substring filter changes so the user
  // never lands on an empty page after narrowing the result set.
  useEffect(() => {
    table.setPageIndex(0);
  }, [jobLocalFilter, table]);

  // Move a hideable column one slot left (-1) or right (+1). Non-hideable
  // columns (e.g. row-select) stay anchored in their original positions; we
  // only shuffle hideable IDs among themselves.
  const moveColumn = React.useCallback((columnId: string, direction: -1 | 1) => {
    const allColumns = table.getAllColumns();
    const currentOrder = table.getState().columnOrder.length
      ? [...table.getState().columnOrder]
      : allColumns.map((c) => c.id);
    const hideableIds = new Set(
      allColumns.filter((c) => c.getCanHide()).map((c) => c.id),
    );
    const hideable = currentOrder.filter((id) => hideableIds.has(id));
    const idx = hideable.indexOf(columnId);
    if (idx < 0) return;
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= hideable.length) return;
    [hideable[idx], hideable[targetIdx]] = [hideable[targetIdx], hideable[idx]];
    let cursor = 0;
    const next = currentOrder.map((id) => (hideableIds.has(id) ? hideable[cursor++] : id));
    dispatch({ type: "SET_COLUMN_ORDER", payload: next });
  }, [table]);

  // Compute the list of items to render in the TableBody. In "Clear"
  // mode this is the raw row list (1:1 with the table's row model). In
  // every other mode the rows are re-sorted by their group key and a
  // header item is interleaved before each group. The header row owns
  // the expand/collapse toggle for that group; row items carry their
  // group key so the renderer can skip them when the group is collapsed.
  type DisplayItem =
    | { kind: "row"; row: Row<Job>; groupKey: string }
    | { kind: "header"; key: string; count: number };
  const tableRows = table.getRowModel().rows;
  const displayItems = React.useMemo<DisplayItem[]>(() => {
    if (state.groupBy === "Clear") {
      return tableRows.map((row) => ({ kind: "row" as const, row, groupKey: "" }));
    }

    // Annotate + stable sort by group key (preserves the table's own
    // sort within each group via the original index as tiebreaker).
    const annotated = tableRows.map((row, idx) => ({
      row,
      idx,
      key: getJobGroupKey(row.original as Job, state.groupBy),
    }));
    annotated.sort((a, b) => {
      const k = a.key.localeCompare(b.key);
      return k !== 0 ? k : a.idx - b.idx;
    });

    const counts = new Map<string, number>();
    for (const { key } of annotated) {
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }

    const out: DisplayItem[] = [];
    let currentKey: string | null = null;
    for (const { row, key } of annotated) {
      if (key !== currentKey) {
        currentKey = key;
        out.push({ kind: "header", key, count: counts.get(key) ?? 0 });
      }
      out.push({ kind: "row", row, groupKey: key });
    }
    return out;
  }, [tableRows, state.groupBy]);

  return (
    <>
      {/* Searching, Menubar, Autoload toggle, & Dropdown for column visibility*/}
      {/* On mobile the search column stacks above the action toolbar so the
          page doesn't force horizontal scroll. On lg+ it sits beside the
          toolbar as a fixed ~35% column. */}
      <div className="flex w-full flex-col items-stretch justify-between gap-3 py-4 lg:flex-row lg:items-center lg:gap-0 lg:space-x-3">
        <div
          id="filtering section"
          ref={searchDropdownRef}
          className="relative flex w-full flex-row justify-start space-y-2 lg:w-[35%] lg:min-w-[360px]"
        >
          <Box
            sx={{
              width: "100%",
              textAlign: "left",
              mt: 4,
              position: "relative",
            }}
          >
            {/* Search input + CueGUI-parity "Load" and "Clear" buttons.
                Enter and the Load button trigger the same bulk-load
                regardless of mode, so users always have an explicit
                submit affordance. Clear resets the box and any open
                dropdown. */}
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <JobSearchbox
                  searchQuery={state.searchQuery}
                  handleInputChange={handleInputChange}
                  tooltipTitle={TOOLTIP_TITLE}
                  hidden={!hideSearchDropdown}
                  onSubmit={handleSearchSubmit}
                  placeholder={
                    state.pickFromList
                      ? "Search jobs - live results"
                      : "Search jobs - Enter to load"
                  }
                />
              </div>
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={() => handleSearchSubmit(state.searchQuery)}
                disabled={state.searchQuery.trim().length === 0}
                // Dark-mode contrast: pinned to an explicit light
                // surface + dark text so the button is clearly readable
                // against the dark page background. Disabled state
                // keeps the same surface (opacity:1) and uses the
                // cursor-not-allowed pointer to convey the inactive
                // state instead of fading the color into illegibility.
                className="h-10 disabled:!opacity-100 disabled:cursor-not-allowed dark:bg-zinc-200 dark:text-zinc-900 dark:hover:bg-zinc-300 dark:disabled:bg-zinc-400 dark:disabled:text-zinc-800"
                title="Load every job matching the search pattern (Enter also works)"
              >
                Load
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleClearSearch}
                disabled={state.searchQuery.length === 0}
                // The default `border-input` is the same color as
                // `--background` in dark mode, so an outline button
                // visually vanishes. Force a brighter zinc border + a
                // slightly lighter surface so the button reads on top
                // of the page in both states.
                className="h-10 disabled:!opacity-100 disabled:cursor-not-allowed dark:border-zinc-500 dark:bg-zinc-700 dark:text-zinc-100 dark:hover:bg-zinc-600 dark:disabled:border-zinc-700 dark:disabled:bg-zinc-800 dark:disabled:text-zinc-400"
                title="Clear the search box and any open results"
              >
                Clear
              </Button>
            </div>

            {/* Two search modes (CueGUI parity vs original CueWeb live
                search). Persisted across reloads via the reducer. */}
            <div className="flex items-center gap-2 pt-1">
              <Switch
                id="pick-from-list"
                checked={state.pickFromList}
                onCheckedChange={(value: boolean) =>
                  dispatch({ type: "SET_PICK_FROM_LIST", payload: value })
                }
              />
              <Label htmlFor="pick-from-list" className="text-xs text-muted-foreground">
                Pick from list
                <span className="ml-1 text-muted-foreground/70">
                  ({state.pickFromList ? "live results, click to add" : "press Enter to load every match"})
                </span>
              </Label>
            </div>
            {jobSearchLoading || waitingForFiltering ? (
              <Box style={{ position: "absolute", top: "100%", left: 0, width: "100%", zIndex: 1000 }}>
                <LinearProgress />
              </Box>
            ) : (
              <>
                {state.filteredJobSearchResults.length > 0 && (
                  <SearchDropdown
                    jobs={state.filteredJobSearchResults}
                    hidden={hideSearchDropdown}
                    handleJobSearchSelect={handleJobSearchSelect}
                    maxListWidth={searchDropdownWidth}
                    setMaxListWidth={setSearchDropdownWidth}
                    tableData={state.tableDataUnfiltered}
                  />
                )}
                {state.filteredJobSearchResults.length === 0 &&
                  state.apiQuery !== "" &&
                  !hideSearchDropdown &&
                  searchFinishedRef.current && (
                    <Box style={{ position: "absolute", top: "100%", left: 0, width: "100%", zIndex: 1000 }}>
                      <div className="rounded-md border border-border bg-popover text-popover-foreground shadow-md">
                        <EmptyState
                          icon={<SearchX className="h-6 w-6" aria-hidden="true" />}
                          title="No matching jobs"
                          description={`Nothing matches "${state.searchQuery}". Try a different pattern (e.g. .* to match any substring).`}
                          className="py-6"
                        />
                      </div>
                    </Box>
                  )}
              </>
            )}
          </Box>
        </div>

        {/* Toolbar - CueGUI Monitor Jobs parity (compact group layout).
            Each group is its OWN flex-wrap container so the label and
            buttons can wrap together as a unit (instead of the label
            standing alone on one line while the buttons fall to the next
            line on narrow viewports). The divider hides on mobile because
            the two groups are already on separate lines there. */}
        <div
          id="monitor-jobs-toolbar"
          role="toolbar"
          aria-label="Monitor Jobs actions"
          className="flex flex-1 flex-col items-stretch gap-3 px-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6 sm:gap-y-2"
        >
          {/* Unmonitor group */}
          <div className="flex flex-wrap items-center gap-1">
            <span className="w-full px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground sm:w-auto">
              Unmonitor
            </span>
            <JobActionButton icon={TbEyeOff} label="Finished" onClick={handleUnmonitorFinished} />
            <JobActionButton icon={TbEyeOff} label="All" onClick={handleUnmonitorAll} />
            <JobActionButton icon={TbEyeOff} label="Selected" onClick={handleUnmonitorSelected} />
          </div>

          <div className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />

          {/* Job actions group */}
          <div className="flex flex-wrap items-center gap-1">
            <span className="w-full px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground sm:w-auto">
              Job Actions
            </span>
            <JobActionButton icon={TbPacman} label="Eat Dead Frames" onClick={() => eatJobsDeadFramesFromSelectedRows(table)} color="#f59e0b" />
            <JobActionButton icon={TbReload} label="Retry Dead Frames" onClick={() => retryJobsDeadFramesFromSelectedRows(table)} color="#3b82f6" />
            <JobActionButton icon={MdOutlineCancel} label="Kill Jobs" onClick={() => killJobFromSelectedRows(table, state.username)} color="#ef4444" variant="destructive" />
            <JobActionButton icon={TbPlayerPause} label="Pause Jobs" onClick={() => pauseJobsFromSelectedRows(table)} color="#3b82f6" />
            <JobActionButton icon={TbPlayerPlay} label="Unpause Jobs" onClick={() => unpauseJobsFromSelectedRows(table)} color="#10b981" />
          </div>
        </div>

      </div>

      {/* State filter, Autoload Mine, Load Finished, Group By
          (CueGUI Monitor Jobs parity). */}
      <div className="m-2 mx-0 flex flex-row flex-wrap items-center gap-3">
        <Select defaultValue={state.stateSelectValue} onValueChange={(val: string) => handleStateFiltering(val)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="All States" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All States">All States</SelectItem>
            <SelectItem value="Finished">Finished</SelectItem>
            <SelectItem value="Failing">Failing</SelectItem>
            <SelectItem value="Dependency">Dependency</SelectItem>
            <SelectItem value="In Progress">In Progress</SelectItem>
            <SelectItem value="Paused">Paused</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex items-center gap-2">
          <Switch
            id="autoload-mine"
            checked={state.autoloadMine}
            onCheckedChange={setAutoloadMine(dispatch, state.autoloadMine)}
          />
          <Label htmlFor="autoload-mine" className="text-sm">Autoload Mine</Label>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id="load-finished"
            checked={state.loadFinished}
            onCheckedChange={(value: boolean) =>
              dispatch({ type: "SET_LOAD_FINISHED", payload: value })
            }
          />
          <Label htmlFor="load-finished" className="text-sm">Load Finished</Label>
        </div>

        <div className="flex items-center gap-2">
          <Label htmlFor="group-by" className="text-sm">Group By</Label>
          <Select
            value={state.groupBy}
            onValueChange={(val: string) =>
              dispatch({ type: "SET_GROUP_BY", payload: val as State["groupBy"] })
            }
          >
            <SelectTrigger id="group-by" className="w-[200px]">
              <SelectValue placeholder="Clear" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Clear">Clear</SelectItem>
              <SelectItem value="Dependent">Dependent</SelectItem>
              <SelectItem value="Show">Show</SelectItem>
              <SelectItem value="Show-Shot">Show-Shot</SelectItem>
              <SelectItem value="Show-Shot-Username">Show-Shot-Username</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Per-table toolbar: CueGUI-parity total-count label on the
          left, Columns dropdown on the right above the jobs table.
          The count tracks the unfiltered table data so state-filter
          changes don't lie about how many jobs are actually loaded.
          Layers + Frames tables below get their own Columns dropdowns
          via SimpleDataTable. */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-medium text-muted-foreground">
          Jobs [Total Count:{" "}
          <span className="font-semibold text-foreground tabular-nums">
            {state.tableDataUnfiltered.length}
          </span>
          ]
        </div>
        <div className="flex items-center gap-2">
          {/* Client-side substring filter that narrows the rows already
              loaded in the table - separate from the server-side load
              search at the top of the page. */}
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              value={jobLocalFilter}
              onChange={(e) => setJobLocalFilter(e.target.value)}
              placeholder="Filter jobs..."
              aria-label="Filter loaded jobs"
              className="h-8 w-44 pl-7 pr-7 text-xs"
            />
            {jobLocalFilter ? (
              <button
                type="button"
                aria-label="Clear filter"
                title="Clear filter"
                onClick={() => setJobLocalFilter("")}
                className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            ) : null}
          </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              Columns
              <ChevronDown className="ml-1 h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="max-h-[60vh] w-64 overflow-y-auto">
            <div className="sticky top-0 z-10 mb-1 border-b border-border bg-popover pb-1">
              <Button
                className="w-full justify-start px-2 py-1.5"
                variant="secondary"
                size="sm"
                onClick={resetColumnsToDefault}
              >
                Reset to Default
              </Button>
            </div>
            {(() => {
              const hideable = table.getAllColumns().filter((c) => c.getCanHide());
              return hideable.map((column, idx) => (
                <DropdownMenuItem
                  key={column.id}
                  // Keep the menu open after every interaction so the user
                  // can toggle visibility and bump the column around
                  // without having to reopen the dropdown each time.
                  onSelect={(e) => e.preventDefault()}
                  className="flex cursor-default items-center justify-between gap-2 px-2 py-1 capitalize focus:bg-accent/40"
                >
                  <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                    <Checkbox
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) => column.toggleVisibility(!!value)}
                      aria-label={`Toggle ${column.id}`}
                    />
                    <span className="truncate">{column.id}</span>
                  </label>
                  <span className="inline-flex shrink-0 items-center gap-0.5">
                    <button
                      type="button"
                      aria-label={`Move ${column.id} left`}
                      title="Move left"
                      disabled={idx === 0}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        moveColumn(column.id, -1);
                      }}
                      className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      aria-label={`Move ${column.id} right`}
                      title="Move right"
                      disabled={idx === hideable.length - 1}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        moveColumn(column.id, 1);
                      }}
                      className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                    >
                      <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </span>
                </DropdownMenuItem>
              ));
            })()}
          </DropdownMenuContent>
        </DropdownMenu>
        </div>
      </div>

      {/* Table */}
      {/* overflow-x-auto so the wide Jobs grid is horizontally swipeable on
          phones without breaking the rest of the layout. */}
      <div className="overflow-x-auto rounded-md border" ref={jobTableRef}>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      className="group relative h-8 px-1.5 text-[11px]"
                      style={{ width: header.getSize() }}
                    >
                      {header.isPlaceholder ? null : (
                        <div className="flex items-center justify-center">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </div>
                      )}
                      {header.column.getCanResize() && (
                        <div
                          // Resize grip: a 6px-wide drag strip pinned to
                          // the column's right edge. Invisible until the
                          // user hovers the header (group-hover) or is
                          // actively dragging (data-state=resizing).
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          onClick={(e) => e.stopPropagation()}
                          data-state={header.column.getIsResizing() ? "resizing" : undefined}
                          className="absolute right-0 top-0 z-10 h-full w-1.5 cursor-col-resize touch-none select-none bg-border opacity-0 transition-opacity hover:bg-foreground/40 group-hover:opacity-60 data-[state=resizing]:bg-primary data-[state=resizing]:opacity-100"
                          aria-hidden="true"
                        />
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {tableRows.length ? (
              displayItems.map((item) => {
                if (item.kind === "header") {
                  const collapsed = collapsedGroups.has(item.key);
                  return (
                    <TableRow
                      key={`group-header-${item.key}`}
                      className="cursor-pointer bg-muted/50 hover:bg-muted"
                      onClick={() => toggleGroup(item.key)}
                    >
                      <TableCell colSpan={columns.length} className="py-1.5">
                        <div className="flex items-center gap-2 px-2 text-xs font-semibold uppercase tracking-wide">
                          {collapsed ? (
                            <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                          )}
                          <span className="truncate">{item.key}</span>
                          <span className="text-muted-foreground">
                            ({item.count})
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                }

                // Row item - skip when its group is collapsed.
                if (item.groupKey && collapsedGroups.has(item.groupKey)) {
                  return null;
                }
                const row = item.row;
                return (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                    onContextMenu={(e: React.MouseEvent) => contextMenuHandleOpen(e, row)}
                    onClick={() => {
                      const job = row.original as Job;
                      setAttributeSelection({
                        type: "job",
                        id: job.id,
                        name: job.name,
                        data: job as unknown as Record<string, unknown>,
                      });
                      // CueGUI parity: clicking a job row loads its layers +
                      // frames into the inline detail panels below.
                      setDetailJob(job);
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className="px-1.5 py-1 text-xs"
                        style={{ width: cell.column.getSize() }}
                      >
                        {/* Wrap every cell's content in a centered flex
                            container so the rendered output (badge,
                            progress bar, plain text, etc.) sits in the
                            middle of the cell horizontally regardless of
                            its own display type. */}
                        <div className="flex items-center justify-center">
                          {cell.column.id === "progress" ? (
                            <JobProgressBar job={row.original as Job} />
                          ) : (
                            flexRender(cell.column.columnDef.cell, cell.getContext())
                          )}
                        </div>
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : initialLoading ? (
              // Render 10 skeleton rows that mirror the final layout so
              // the first paint reserves the same vertical space the real
              // rows will occupy (avoids cumulative layout shift).
              Array.from({ length: 10 }).map((_, rowIdx) => (
                <TableRow key={`skeleton-row-${rowIdx}`}>
                  {table.getAllLeafColumns().filter((c) => c.getIsVisible()).map((col) => (
                    <TableCell
                      key={`skeleton-cell-${rowIdx}-${col.id}`}
                      className="px-1.5 py-1"
                    >
                      <Skeleton className="h-4 w-3/4" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 p-0">
                  <EmptyState
                    icon={<Inbox className="h-6 w-6" aria-hidden="true" />}
                    title="No jobs monitored"
                    description="Search for a job above and click a result to add it here. Toggle Autoload Mine to also load your jobs automatically."
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        {/* Context menu for the jobs table */}
        <JobContextMenu
          username={state.username}
          contextMenuState={contextMenuState}
          contextMenuHandleClose={contextMenuHandleClose}
          contextMenuRef={contextMenuRef}
          contextMenuTargetAreaRef={contextMenuTargetAreaRef}
          // Unmonitor jobs props
          tableData={state.tableData}
          tableDataUnfiltered={state.tableDataUnfiltered}
          rowSelection={state.rowSelection}
          setTableData={setTableData(dispatch, state.tableData)}
          setTableDataUnfiltered={setTableDataUnfiltered(dispatch, state.tableDataUnfiltered)}
          setRowSelection={setRowSelection(dispatch, state.rowSelection)}
          tableStorageName={"tableData"}
          unfilteredTableStorageName={"tableDataUnfiltered"}
        />
      </div>

      {/* Pagination */}
      <div className="space-x-2 py-4">
        <DataTablePagination
          table={table}
          pageSizes={[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 100, 150, 200, 250, 300]}
        />
      </div>

      {/* Inline Monitor Job Details (CueGUI parity): replaces the legacy
          per-row popup with stacked Layers + Frames panels for the row
          the user last clicked above. */}
      <JobDetailsInline job={detailJob} username={state.username} />
    </>
  );
}
export default DataTable;
