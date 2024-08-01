"use client";

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
  VisibilityState,
} from "@tanstack/react-table";
import * as React from "react";
import "./index.css";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TbEyeOff, TbPacman, TbPlayerPause, TbPlayerPlay, TbReload } from "react-icons/tb";
import { MdOutlineCancel } from "react-icons/md";
import { ChevronDown } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@radix-ui/react-label";
import { DataTablePagination } from "@/components/ui/pagination";
import { getState, Job } from "./columns";
import { FramesLayersPopup } from "@/components/ui/frames-layers-popup";
import { JobProgressBar } from "@/components/ui/job-progress-bar";
import JobSearchbox from "@/components/ui/jobs-searchbox";
import SearchDropdown from "@/components/ui/search-dropdown";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import debounce from "lodash/debounce";
import { Session } from "next-auth";
import { signOut } from "next-auth/react";
import { useTheme } from "next-themes";
import { useEffect } from "react";
import CueWebIcon from "../../components/ui/cuewebicon";
import { Frame } from "../frames/frame-columns";
import { getJobsForRegex, getJobsForShow, getJobsForUser, handleError } from "../utils/utils";

export const getItemFromLocalStorage = (itemKey: string, initialItemValue: string) => {
  const itemFromStorage = JSON.parse(localStorage.getItem(itemKey) || initialItemValue);
  return itemFromStorage;
};

const setItemInLocalStorage = (itemKey: string, item: string) => {
  localStorage.setItem(itemKey, item);
};

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<any, any>[];
  data: Job[];
  session: Session;
}

export function DataTable<TData, TValue>({ columns, data, session }: DataTableProps<TData, TValue>) {
  const { theme, setTheme } = useTheme();

  const [tableData, setTableData] = React.useState(getItemFromLocalStorage("tableData", JSON.stringify(data)));
  setItemInLocalStorage("tableData", JSON.stringify(tableData));

  const [sorting, setSorting] = React.useState(getItemFromLocalStorage("sorting", "[]"));
  setItemInLocalStorage("sorting", JSON.stringify(sorting));

  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    getItemFromLocalStorage("columnFilters", "[]"),
  );
  setItemInLocalStorage("columnFilters", JSON.stringify(columnFilters));

  // by default, certain columns are hidden
  const initialColumnVisibility = {
    running: false,
    dead: false,
    wait: false,
    eaten: false,
    age: false,
    maxRss: false,
  };
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>(
    getItemFromLocalStorage("columnVisibility", JSON.stringify(initialColumnVisibility)),
  );
  setItemInLocalStorage("columnVisibility", JSON.stringify(columnVisibility));

  const [rowSelection, setRowSelection] = React.useState({});

  const [usernameInput, setUsernameInput] = React.useState<string>(
    session && session.user && session.user.email ? session.user.email.split("@")[0] : "monitor",
  );
  const [frames, setFrames] = React.useState<Frame[]>([]);

  // Search/dropdown variables:
  const [hideSearchDropdown, setHideSearchDropdown] = React.useState<boolean>(true);
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  // The amount of delay in milliseconds after typing stops that is required before calling handleGetJobs
  const searchDelay = 300;
  const [allJobs, setAllJobs] = React.useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = React.useState<Job[]>([]);
  // Current api query to keep track if it changes during search
  const [curAPIQuery, setCurAPIQuery] = React.useState<string>("");
  const [waitingForAPI, setWaitingForAPI] = React.useState<boolean>(false);
  const [waitingForFiltering, setWaitingForFiltering] = React.useState<boolean>(false);
  const [searchDropdownWidth, setSearchDropdownWidth] = React.useState<number>(1000);
  const filterWorkerRef = React.useRef<Worker | null>(null);
  const searchDropdownRef = React.useRef<HTMLDivElement | null>(null);
  // Used to track when searching (API and Filtering) is finished
  // Without this, the loading component would render right as '-' was typed
  const searchFinishedRef = React.useRef<boolean>(false);
  const SEARCH_BY_SHOW = "search_by_show";
  const SEARCH_BY_REGEX = "search_by_regex";
  const TOOLTIP_TITLE = `
  Add '!' after searches for regular expressions.<br>
  Use .* to match any string<br>
  Example searches:<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2.*comp!<br>
  &nbsp;&nbsp;&nbsp;&nbsp;sm2-(madkisson|chung).*comp!<br>
  Jobs finished for 3 days will not be shown.<br>
  Load your finished jobs with: show-shot-username_`;

  // tableDataUnfiltered starts off containing the same exact data as tableData (which is used to populate the table)
  // The difference is tableDataUnfiltered will be used to keep track of the table data without any 'state' filters
  // This is so that when we update the tableData based on the 'state' the user is filtering on,
  // tableDataUnfiltered remains the same, so that the user can later access the unfiltered table data

  // For example, let's say the user filters tableData on state 'In Progress'
  // When they later filter on state 'Finished', we search the unfiltered table data for jobs with state 'Finished'
  // If we didn't keep track of the unfiltered table data, the user would get no results because we would be searching
  // tableData for state 'Finished' and tableData currently only contains jobs with state 'In Progress'
  const [tableDataUnfiltered, setTableDataUnfiltered] = React.useState(
    getItemFromLocalStorage("tableDataUnfiltered", JSON.stringify(data)),
  );
  setItemInLocalStorage("tableDataUnfiltered", JSON.stringify(tableDataUnfiltered));

  const [stateSelectValue, setStateSelectValue] = React.useState(
    getItemFromLocalStorage("stateSelectValue", JSON.stringify("All States")),
  );
  setItemInLocalStorage("stateSelectValue", JSON.stringify(stateSelectValue));

  // column IDs of columns that look better when their data is center-aligned, rather than to the left (the default)
  const centeredColumns = ["done / total", "running", "dead", "eaten", "wait", "maxRss"];

  const handleSetUserAndGetJobs = async () => {
    const userJobs = await getJobsForUser(usernameInput);
    setAllJobs(userJobs);
  };

  // Uses debouncing and memoization (useCallback) to cache the function and only run after delay of no typing
  const handleGetJobs = React.useCallback(
    debounce(async (query: string, searchType: string) => {
      if (searchType === SEARCH_BY_SHOW) {
        setCurAPIQuery(query);
        setWaitingForAPI(true);
        const newJobs = await getJobsForShow(query);
        setWaitingForAPI(false);
        setAllJobs(newJobs);
        if (newJobs.length === 0) {
          setFilteredJobs([]);
        }
      } else if (searchType === SEARCH_BY_REGEX) {
        setCurAPIQuery(SEARCH_BY_REGEX);
        setWaitingForAPI(true);
        const newJobs = await getJobsForRegex(query);
        setWaitingForAPI(false);
        setAllJobs(newJobs);
        setFilteredJobs(newJobs);
        searchFinishedRef.current = true;
      }
    }, searchDelay),
    [],
  );

  // Use a worker thread to filter and return the filtered jobs based on the query
  useEffect(() => {
    filterWorkerRef.current = new Worker(new URL("../workers/searchFilterWorker.tsx", import.meta.url));

    if (filterWorkerRef.current) {
      filterWorkerRef.current.onmessage = (e: MessageEvent<any>) => {
        // If there is an error in the web worker, set filtered jobs to empty and show errors
        // Otherise, set filtered jobs to filtering results
        if (e.data.error) {
          handleError("Issue with filtering", e.data.error);
          setFilteredJobs([]);
        } else {
          setFilteredJobs(e.data);
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
        filterWorkerRef.current.postMessage({ allJobs, query });
      }
    };

    if (curAPIQuery !== SEARCH_BY_REGEX && !waitingForAPI) {
      handleFiltering(searchQuery);
      searchFinishedRef.current = true;
    }
  }, [allJobs, searchQuery, waitingForAPI]);

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
    setSearchQuery(query);

    // Query the API after the first '-' typed since a job name begins with 'show-shot-user'
    // We also Query the API for show name if it doesn't include '!' or for regex if it includes '!' at the end
    if (query.slice(-1) === "!") {
      const regexQuery = query.slice(0, -1);
      handleGetJobs(regexQuery, SEARCH_BY_REGEX);
      setHideSearchDropdown(false);
    } else if (query.includes("-")) {
      const nextShow = query.split("-")[0];
      if (nextShow !== curAPIQuery) {
        handleGetJobs(nextShow, SEARCH_BY_SHOW);
      }
      setHideSearchDropdown(false);
    } else {
      setAllJobs([]);
      setFilteredJobs([]);
      setCurAPIQuery("");
    }

    // Cancel handleGetJobs if the input changes before the timeout completes
    return () => {
      handleGetJobs.cancel();
    };
  };

  const handleUnmonitorSelected = () => {
    const selectedRows = table.getSelectedRowModel().rows;
    let jobsToUnmonitorSet = new Set(selectedRows.map((row: Row<TData>) => JSON.stringify(row.original)));

    const updatedUnfilteredTableData = tableDataUnfiltered.filter(
      (job: Job) => !jobsToUnmonitorSet.has(JSON.stringify(job)),
    );
    setTableDataUnfiltered(updatedUnfilteredTableData);

    const updatedTableData = tableData.filter((job: Job) => !jobsToUnmonitorSet.has(JSON.stringify(job)));
    setTableData(updatedTableData);

    setRowSelection({});
  };

  const handleUnmonitorPaused = () => {
    const pausedJobs = tableData.filter((job: Job) => getState(job) === "Paused");

    const updatedUnfilteredTableData = tableDataUnfiltered.filter(
      (job: Job) => !pausedJobs.some((pausedJob: Job) => pausedJob === job),
    );
    setTableDataUnfiltered(updatedUnfilteredTableData);

    const updatedTableData = tableData.filter((job: Job) => !pausedJobs.some((pausedJob: Job) => pausedJob === job));
    setTableData(updatedTableData);
  };

  const handleUnmonitorFinished = () => {
    const finishedJobs = tableDataUnfiltered.filter((job: Job) => getState(job) === "Finished");

    const updatedUnfilteredTableData = tableDataUnfiltered.filter(
      (job: Job) => !finishedJobs.some((finishedJob: Job) => finishedJob === job),
    );
    setTableDataUnfiltered(updatedUnfilteredTableData);

    const updatedTableData = tableData.filter(
      (job: Job) => !finishedJobs.some((finishedJob: Job) => finishedJob === job),
    );
    setTableData(updatedTableData);
  };

  const handleUnmonitorAll = () => {
    setTableDataUnfiltered([]);
    setTableData([]);
  };

  const handleJobSearchSelect = (job: Job) => {
    // we check if the job is already in tableDataUnfiltered so we don't add it twice
    const isJobAlreadyAdded = tableDataUnfiltered.some((existingJob: Job) => (existingJob as Job).name === job.name);

    if (!isJobAlreadyAdded) {
      // if job not already in the table data, add it (to both tableData & tableDataUnfiltered)
      setTableData((prevData: TData[]) => [...prevData, job] as TData[]);
      setTableDataUnfiltered((prevData: TData[]) => [...prevData, job] as TData[]);
    } else {
      setTableData((prevData: Job[]) => prevData.filter((existingJob) => existingJob.name !== job.name));
      setTableDataUnfiltered((prevData: Job[]) => prevData.filter((existingJob) => existingJob.name !== job.name));
    }
  };

  const handleStateFiltering = (state: string) => {
    setStateSelectValue(state);
    if (state === "All States") {
      setTableData(tableDataUnfiltered);
      return;
    }
    const filteredData = tableDataUnfiltered.filter((job: Job) => getState(job) === state);
    setTableData(filteredData);
  };

  const resetColumnVisibilityToDefault = () => {
    setColumnVisibility(initialColumnVisibility);
  };

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,

    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },

    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: 50,
      },
    },
  });

  return (
    <>
      {/* Cueweb icon, Mode Toggle */}
      <div className="flex items-center justify-between px-1 py-4">
        <CueWebIcon />
        <div className="flex flex-row space-x-2">
          <Button
            onClick={() => {
              localStorage.removeItem("tableData");
              localStorage.removeItem("tableDataUnfiltered");
              // @ts-ignore
              signOut("okta");
            }}
          >
            Signout ({usernameInput})
          </Button>
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
              searchQuery={searchQuery}
              handleInputChange={handleInputChange}
              tooltipTitle={TOOLTIP_TITLE}
              hidden={!hideSearchDropdown}
            />
            {waitingForAPI || waitingForFiltering ? (
              <Box style={{ position: "absolute", top: "100%", left: 0, width: "100%", zIndex: 1000 }}>
                <LinearProgress />
              </Box>
            ) : (
              <>
                {filteredJobs.length > 0 && (
                  <SearchDropdown
                    jobs={filteredJobs}
                    hidden={hideSearchDropdown}
                    handleJobSearchSelect={handleJobSearchSelect}
                    maxListWidth={searchDropdownWidth}
                    setMaxListWidth={setSearchDropdownWidth}
                    tableData={tableData}
                  />
                )}
                {filteredJobs.length === 0 &&
                  curAPIQuery !== "" &&
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
          <button className="flex flex-row justify-center items-center border-r border-gray-300 pr-2">
            <MdOutlineCancel className="mr-1" size={18} color="red" />
            Kill
          </button>
          <button className="flex flex-row justify-center items-center border-r border-gray-300 pr-2">
            <TbPacman className="mr-1" size={18} color="orange" />
            Eat Dead Frame
          </button>
          <button className="flex flex-row justify-center items-center border-r border-gray-300 pr-2">
            <TbReload className="mr-1" size={18} color="black" />
            Retry Dead Frames
          </button>
          <button className="flex flex-row justify-center items-center border-r border-gray-300 pr-2">
            <TbPlayerPause className="mr-1" size={20} color="blue" />
            Pause
          </button>
          <button className="flex flex-row justify-center items-center">
            <TbPlayerPlay className="mr-1" size={18} color="green" />
            Unpause
          </button>
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
        <Select defaultValue={stateSelectValue} onValueChange={(val: string) => handleStateFiltering(val)}>
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
            onCheckedChange={(checked) => {
              checked === true;
            }}
          />
          <Label htmlFor="autoload-mine">Autoload Mine</Label>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
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
                <React.Fragment key={row.id}>
                  <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                    {row.getVisibleCells().map((cell) => (
                      // if the column for this cell is the pop-up button column, make it a "sticky" column so that
                      // it hovers over all other columns when table overflow occurs and the table becomes scrollable
                      <TableCell key={cell.id} className={cell.column.id == "pop-up" ? `sticky ${theme}` : ""}>
                        {cell.column.id === "progress" ? (
                          <JobProgressBar job={row.original as Job} />
                        ) : cell.column.id === "pop-up" ? (
                          <FramesLayersPopup job={row.original as Job} />
                        ) : centeredColumns.includes(cell.column.id) ? (
                          <div className="text-center">{flexRender(cell.column.columnDef.cell, cell.getContext())}</div>
                        ) : (
                          flexRender(cell.column.columnDef.cell, cell.getContext())
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                </React.Fragment>
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
      </div>

      {/* Pagination */}
      <div className="space-x-2 py-4">
        <DataTablePagination table={table} pageSizes={[50, 100, 150, 200, 250, 300]} />
      </div>
    </>
  );
}
export default DataTable;
