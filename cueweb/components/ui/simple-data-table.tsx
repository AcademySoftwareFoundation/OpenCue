"use client";

import * as React from "react";

import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { DataTablePagination } from "@/components/ui/pagination";
import { Status } from "./status";
import Link from "next/link";
import { Job } from "../../app/jobs/columns";
import { getFrameLogDir } from "../../app/utils/utils";
import { Frame } from "@/app/frames/frame-columns";

interface SimpleDataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  showPagination?: boolean;
  job?: Job;
  isFramesTable?: boolean;
}

export function SimpleDataTable<TData, TValue>({
  columns,
  data,
  showPagination = true,
  job,
  isFramesTable = false,
}: SimpleDataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);

  // column IDs of columns that look better when their data is left-aligned (the default)
  const leftAlignedColumns = ["dispatchOrder", "name", "services", "lastResource"];

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),

    state: {
      sorting,
    },
  });

  return (
    <>
      <div className="rounded-md border">
        <Table className="border">
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
                <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {cell.column.id === "state" ? (
                        <Status status={(row.original as Frame).state} />
                      ) : // only include link for the frame's logs page if this table is used to display the frames in
                      // the pop-up window
                      isFramesTable && cell.column.id === "layerName" ? (
                        <Link
                          href={{
                            pathname: `frames/${(row.original as Frame).name}`,
                            query: {
                              frameId: (row.original as Frame).id,
                              frameLogDir: getFrameLogDir(job as Job, row.original as Frame),
                            },
                          }}
                        >
                          <div className="text-blue-600  dark:text-blue-400 dark:font-bold">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </div>
                        </Link>
                      ) : (
                        <>
                          {leftAlignedColumns.includes(cell.column.id) ? (
                            flexRender(cell.column.columnDef.cell, cell.getContext())
                          ) : (
                            <div className="text-center">
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </div>
                          )}
                        </>
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
      </div>

      {/* Pagination */}
      {showPagination ? (
        <div className="space-x-2 py-4">
          <DataTablePagination table={table} pageSizes={[10, 20, 30, 40, 50]} />
        </div>
      ) : (
        <div />
      )}
    </>
  );
}
