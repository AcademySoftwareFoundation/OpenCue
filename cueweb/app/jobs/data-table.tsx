"use client";

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
  getJobsForShowShot,
  getJobsForUser
} from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { JobContextMenu } from "@/components/ui/context_menus/action-context-menu";
import { useContextMenu } from "@/components/ui/context_menus/useContextMenu";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { FramesLayersPopup } from "@/components/ui/frames-layers-popup";
import { JobProgressBar } from "@/components/ui/job-progress-bar";
import JobSearchbox from "@/components/ui/jobs-searchbox";
import { DataTablePagination } from "@/components/ui/pagination";
import SearchDropdown from "@/components/ui/search-dropdown";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ThemeToggle } from "@/components/ui/theme-toggle";
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
  getPaginationRowModel,
  getSortedRowModel,
  Row,
  useReactTable,
  VisibilityState
} from "@tanstack/react-table";
import debounce from "lodash/debounce";
import { ChevronDown } from "lucide-react";
import { signOut } from "next-auth/react";
import { useTheme } from "next-themes";
import * as React from "react";
import { useEffect, useReducer } from "react";
import { MdOutlineCancel } from "react-icons/md";
import { TbEyeOff, TbPacman, TbPlayerPause, TbPlayerPlay, TbReload } from "react-icons/tb";
import CueWebIcon from "../../components/ui/cuewebicon";
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
  | { type: "SET_ERROR"; payload: string | null } // New action for setting errors
  | { type: "SET_USERNAME"; payload: string }
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
  error: string | null;
  username: string;
}

const initialColumnVisibility = {
  running: false,
  dead: false,
  wait: false,
  eaten: false,
  age: false,
  maxRss: false,
}

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
    error: null,
    username: UNKNOWN_USER,
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
    case "SET_ERROR":
      return { ...state, error: action.payload }; // Set the error message
    case "SET_USERNAME":
      return { ...state, username: action.payload };
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

// Reusable Job Action Button component to reduce redundancy
const JobActionButton = ({
  icon: Icon,
  label,
  onClick,
  color,
  last=false,
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  color: string;
  last?: boolean;
}) => (
  last ? (
    <button className="flex flex-row justify-center items-center" onClick={onClick}>
      <Icon className="mr-1" size={18} color={color} />
      {label}
    </button>
  ) : (
    <button className="flex flex-row justify-center items-center border-r border-gray-300 pr-2" onClick={onClick}>
      <Icon className="mr-1" size={18} color={color} />
      {label}
    </button>
  )
  
);

export function DataTable({ columns, username }: DataTableProps) {
  const { theme, setTheme } = useTheme();

  // useReducer hook to manage state
  const [state, dispatch] = useReducer(reducer, getInitialState());

  useEffect(() => {
    dispatch({ type: "RESET_STATE"});
  }, []);

  useEffect(() => {
    addUsersJobs();
  },[state.username, state.autoloadMine]);
  
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
  const SEARCH_BY_SHOWSHOT = "search_by_showshot";
  const SEARCH_BY_REGEX = "search_by_regex";
  const TOOLTIP_TITLE = `
  Add '!' after searches for regular expressions.<br>
  Use .* to match any string<br>
  Example searches:<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2.*comp!<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2-(madkisson|chung).*comp!<br>
  Jobs finished for 3 days will not be shown.<br>
  Load your jobs with: show-shot-`;
  // column IDs of columns that look better when their data is center-aligned, rather than to the left (the default)
  const centeredColumns = ["done / total", "running", "dead", "eaten", "wait", "maxRss"];
  
  // Regularly update the data-table data to see if jobs have changed attributes
  useEffect(() => {
    let interval: NodeJS.Timeout | undefined;
    let worker: Worker | undefined;
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

      // Trigger table updates every 5000ms
      interval = setInterval(async () => {
        updateData();
        await addUsersJobs();
      }, 5000);
    } catch (error) {
      handleError(error, "Error updating table");
    }

    return () => {
      // Clean up interval on component unmount
      if (interval) clearInterval(interval);
      // Terminate the worker when the component unmounts
      worker?.terminate();
    };
  }, [state.tableDataUnfiltered, state.tableData, state.autoloadMine]);

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

  // Uses debouncing and memoization (useCallback) to cache the function and only run after delay of no typing
  const handleGetJobs = React.useCallback(
    debounce(async (query: string, searchType: string) => {
      try {
        if (searchType === SEARCH_BY_SHOWSHOT) {
          dispatch({ type: "SET_API_QUERY", payload: query });
          setJobSearchLoading(true);
          const showShot = query.split("-");
          const newJobs = await getJobsForShowShot(showShot[0], showShot[1]);
  
          setJobSearchLoading(false);
          dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: newJobs });
          if (newJobs.length === 0) {
            dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
          }
        } else if (searchType === SEARCH_BY_REGEX) {
          dispatch({ type: "SET_API_QUERY", payload: SEARCH_BY_REGEX });
          setJobSearchLoading(true);
          const newJobs = await getJobsForRegex(query);
          setJobSearchLoading(false);
          dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: newJobs });
          dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: newJobs });
          searchFinishedRef.current = true;
        }
      } catch (error) {
        handleError(error, "Error searching for jobs");
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
    dispatch({ type: "SET_SEARCH_QUERY", payload: query});
    // Regex to match if the query has the format "[at least one character]-[at least one character]-[any or no characters]"
    const showShot = query.match(/^(.+)-(.+)-.*$/)

    // Query the API for show name if it inlcudes the correct 'show-shot-' format or for regex if it includes '!' at the end
    if (query.slice(-1) === "!") {
      const regexQuery = query.slice(0, -1);
      handleGetJobs(regexQuery, SEARCH_BY_REGEX);
      setHideSearchDropdown(false);
    } else if (showShot && showShot.length >= 3) {
      const nextShowShot = `${showShot[1]}-${showShot[2]}`
      if (nextShowShot !== state.apiQuery) {
        handleGetJobs(nextShowShot, SEARCH_BY_SHOWSHOT);
      }
      setHideSearchDropdown(false);
    } else {
      dispatch({ type: "SET_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_FILTERED_JOB_SEARCH_RESULTS", payload: [] });
      dispatch({ type: "SET_API_QUERY", payload: "" });
    }

    // Cancel handleGetJobs if the input changes before the timeout completes
    return () => {
      handleGetJobs.cancel();
    };
  };

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

    const userJobs = await getJobsForUser(state.username);

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

  const resetColumnVisibilityToDefault = () => {
    dispatch({ type: "SET_COLUMN_VISIBILITY", payload: initialColumnVisibility });
  };

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
    onRowSelectionChange: setRowSelection(dispatch, state.rowSelection),
    getRowId: (job: Job) => job.id,
    autoResetPageIndex: false,

    state: {
      sorting: state.sorting,
      columnFilters: state.columnFilters,
      columnVisibility: state.columnVisibility,
      rowSelection: state.rowSelection,
    },

    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: 50,
      },
    },
  });

  const jobTableRef = React.useRef<HTMLDivElement>(null);
  const {
    contextMenuState,
    contextMenuHandleOpen,
    contextMenuHandleClose,
    contextMenuRef,
    contextMenuTargetAreaRef
  } = useContextMenu(jobTableRef);

  return (
    <>
      {/* Cueweb icon, Mode Toggle */}
      <div className="flex items-center justify-between px-1 py-4">
        <CueWebIcon />
        <div className="flex flex-row space-x-2">
          {
            username !== UNKNOWN_USER &&
            <Button
              onClick={() => {
                localStorage.removeItem("tableData");
                localStorage.removeItem("tableDataUnfiltered");
                // @ts-ignore
                signOut("okta");
              }}
            >
              Signout ({state.username})
            </Button>
          }
          <ThemeToggle></ThemeToggle>
        </div>
      </div>

      {/* Searching, Menubar, Autoload toggle, & Dropdown for column visibility*/}
      <div className="flex flex-row w-full items-center justify-between py-4 space-x-3">
        <div id="filtering section" ref={searchDropdownRef} className="relative flex flex-row justify-start space-y-2" style={{ width: "25%" }}>
          <Box
            sx={{
              width: "100%",
              textAlign: "left",
              mt: 4,
              position: "relative",
            }}
          >
            <JobSearchbox
              searchQuery={state.searchQuery}
              handleInputChange={handleInputChange}
              tooltipTitle={TOOLTIP_TITLE}
              hidden={!hideSearchDropdown}
            />
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
                      <Alert severity="info">No results found</Alert>
                    </Box>
                  )}
              </>
            )}
          </Box>
        </div>

        {/* Menu Bar */}
        <div id="menu bar" className="flex flex-row px-6 py-2 space-x-3 border border-gray-400 justify-center rounded-xl">
          <div className="flex justify-center items-center border-r border-gray-300 pr-2">
            <TbEyeOff className="mr-1" size={18} color="gray" />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex justify-center items-center">
                  Unmonitor
                  <ChevronDown className="opacity-50 ml-1" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem>
                  <Button variant="ghost" onClick={handleUnmonitorAll}>
                    Unmonitor All
                  </Button>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Button variant="ghost" onClick={handleUnmonitorSelected}>
                    Unmonitor Selected
                  </Button>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Button variant="ghost" onClick={handleUnmonitorFinished}>
                    Unmonitor Finished
                  </Button>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Button variant="ghost" onClick={handleUnmonitorPaused}>
                    Unmonitor Paused
                  </Button>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <JobActionButton icon={TbPacman} label="Eat Dead Frames" onClick={() => eatJobsDeadFramesFromSelectedRows(table)} color="orange" />
          <JobActionButton icon={TbReload} label="Retry Dead Frames" onClick={() => retryJobsDeadFramesFromSelectedRows(table)} color="red" />
          <JobActionButton icon={TbPlayerPause} label="Pause" onClick={() => pauseJobsFromSelectedRows(table)} color="blue" />
          <JobActionButton icon={TbPlayerPlay} label="Unpause" onClick={() => unpauseJobsFromSelectedRows(table)} color="green" />
          <JobActionButton icon={MdOutlineCancel} label="Kill" onClick={() => killJobFromSelectedRows(table, state.username)} color="red" last={true} />
        </div>

        {/* Dropdown Column Visibility */}
        <div className="relative flex flex-row justify-end" style={{ width: "25%" }}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="ml-auto">
                Columns
                <ChevronDown />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <Button className="px-2 py-1.5" variant={"ghost"} onClick={resetColumnVisibilityToDefault}>
                Reset to Default
              </Button>
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) => column.toggleVisibility(!!value)}
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  );
                })}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Filtering for state & the 'Autoload Mine' toggle*/}
      <div className="flex flex-row space-x-2 m-2 mx-0">
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
        <div className="flex items-center space-x-2" align-items="flex-end">
          {/* to do later: add functionality for autoloading artist jobs after checking if checked is true */}
          <Switch
            id="autoload-mine"
            checked={state.autoloadMine}
            onCheckedChange={setAutoloadMine(dispatch, state.autoloadMine)}
          />
          <Label htmlFor="autoload-mine">Autoload Mine</Label>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border" ref={jobTableRef}>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                // React.Fragment is a way to group elements without introducing an extra container in the DOM.
                // the shorthand notation for a Fragment is <>
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  onContextMenu={(e: React.MouseEvent) => contextMenuHandleOpen(e, row)}
                >
                  {row.getVisibleCells().map((cell) => (
                    // if the column for this cell is the pop-up button column, make it a "sticky" column so that
                    // it hovers over all other columns when table overflow occurs and the table becomes scrollable
                    <TableCell key={cell.id} className={cell.column.id == "pop-up" ? `sticky ${theme}` : ""}>
                      {cell.column.id === "progress" ? (
                        <JobProgressBar job={row.original as Job} />
                      ) : cell.column.id === "pop-up" ? (
                        <FramesLayersPopup job={row.original as Job} username={state.username} />
                      ) : centeredColumns.includes(cell.column.id) ? (
                        <div className="text-center">{flexRender(cell.column.columnDef.cell, cell.getContext())}</div>
                      ) : (
                        flexRender(cell.column.columnDef.cell, cell.getContext())
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
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
        <DataTablePagination table={table} pageSizes={[50, 100, 150, 200, 250, 300]} />
      </div>
    </>
  );
}
export default DataTable;
