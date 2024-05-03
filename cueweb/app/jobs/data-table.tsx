"use client";

import "./index.css";
import * as React from "react";
import {
  Row,
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";

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

import { TbPacman, TbPlayerPause, TbPlayerPlay, TbReload, TbEyeOff } from "react-icons/tb";

import { MdOutlineCancel } from "react-icons/md";

import { ChevronDown } from "lucide-react";

import { Switch } from "@/components/ui/switch";
import { Label } from "@radix-ui/react-label";

import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";

import { Job, getState, getShowShotUser, getRestOfJobName } from "./columns";
import { DataTablePagination } from "@/components/ui/pagination";

import { Input } from "../../components/ui/input";

import { getJobs, getLayers, getFrames } from "../utils/utils"
import { useEffect } from "react"
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useTheme } from "next-themes";
import { getJobsForShow, getJobsForUser } from "../utils/utils";
import CueWebIcon from "../../components/ui/cuewebicon";
import { JobProgressBar } from "@/components/ui/job-progress-bar";
import { FramesLayersPopup } from "@/components/ui/frames-layers-popup";
import { signOut } from "next-auth/react"
import { Session } from 'next-auth'
import { OktaSignInButton } from "@/components/ui/auth-button";
import SearchDropdown from "@/components/ui/search-dropdown";
import { Frame } from "../frames/frame-columns";


export const getItemFromLocalStorage = (itemKey: string, initialItemValue: string) => {
  const itemFromStorage = JSON.parse(localStorage.getItem(itemKey) || initialItemValue);
  return itemFromStorage;
  };
  
const setItemInLocalStorage = (itemKey: string, item: string) => {
  localStorage.setItem(itemKey, item);
};
  
interface DataTableProps<TData, TValue> {
  columns: ColumnDef<any, any>[]
  data: Job[],
  session: Session
}

export function DataTable<TData, TValue>({
  columns,
  data,
  session
}: DataTableProps<TData, TValue>) {

  const { theme, setTheme } = useTheme()

  const [tableData, setTableData] = React.useState(getItemFromLocalStorage("tableData", JSON.stringify(data)));
  setItemInLocalStorage("tableData", JSON.stringify(tableData))
  
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

  const [commandSuggestionHidden, setCommandSuggestionHidden] = React.useState<boolean>(true);
  const [inputValue, setInputValue] = React.useState<string>("");

  const [usernameInput, setUsernameInput] = React.useState<string>(session && session.user && session.user.email ?
    session.user.email.split('@')[0] : "monitor")
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [jobs, setJobs] = React.useState<Promise<Job[]>>();

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
    setJobs(await getJobsForUser(usernameInput));
  };

  const handleGetJobs = async (show: string) => {
    setJobs(getJobsForShow(show));
  };

  const handleInputChange = (input: string) => {
    setInputValue(input);
    // only start to show suggestions after the first '-' (after user has typed in a show name),
    // since a job name begins with show-shot-user..
    if (input.includes("-")) {
      setCommandSuggestionHidden(false);
      let show = input.split("-")[0];
      handleGetJobs(show);
    }
    if (input === "") {
      setCommandSuggestionHidden(true);
    }
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
            <Button onClick={()=>{
              localStorage.removeItem("tableData")
              localStorage.removeItem("tableDataUnfiltered")
                // @ts-ignore
                signOut("okta");
              }}>Signout ({usernameInput})
            </Button>
            <ThemeToggle></ThemeToggle>
        </div>
      </div>

      {/* Searching, Menubar, Autoload toggle, & Dropdown for column visibility*/}
      <div className="flex flex-row w-full items-center justify-between py-4 space-x-3">
        {/* Searching */}
        <div id="filtering section" className="flex flex-row space-x-2">
          <Command className="h-10 rounded-md border">
            <CommandInput
              placeholder="Search job name..."
              value={inputValue}
              onValueChange={(strInput: string) => handleInputChange(strInput)}
              onXClick={() => handleInputChange("")}
            />
            <React.Suspense fallback={<p className="text-center text-5xl">Loading...</p>}>
              <SearchDropdown
                promise={jobs}
                hidden={commandSuggestionHidden}
                handleJobSearchSelect={handleJobSearchSelect}
              />
            </React.Suspense>
          </Command>
        </div>

        {/* Menu Bar */}
        <div id="menu bar" className="flex flex-row px-6 py-2 space-x-3 border border-gray-400 rounded-xl">
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
