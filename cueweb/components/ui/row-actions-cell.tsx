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
import { MoreVertical } from "lucide-react";
import type { Row, Table } from "@tanstack/react-table";

// Shared "open the row's context menu" button used as the first column of
// each data table (Jobs / Layers / Frames). Right-click already opens the
// same menu, but right-click isn't available on touch devices and is
// non-discoverable for new users. This button surfaces the same menu via
// a tap, anchored to the button's bounding rect so the menu renders next
// to the trigger instead of at the click coordinate.
//
// The cell reaches the row-level `contextMenuHandleOpen` through the
// table's `meta.openContextMenu` slot, threaded in by each table's
// `useReactTable({ meta })` call.

interface RowActionsCellProps<TData> {
  row: Row<TData>;
  table: Table<TData>;
  label?: string;
}

interface TableMetaWithContextMenu {
  openContextMenu?: (event: React.MouseEvent, row: Row<any>) => void;
}

export function RowActionsCell<TData>({
  row,
  table,
  label = "Open actions menu",
}: RowActionsCellProps<TData>) {
  const meta = table.options.meta as TableMetaWithContextMenu | undefined;
  const open = meta?.openContextMenu;

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (!open) return;
    open(e, row as unknown as Row<any>);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={label}
      title={label}
      className="inline-flex h-7 w-7 items-center justify-center rounded text-foreground/60 transition-colors hover:bg-foreground/10 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
    >
      <MoreVertical className="h-4 w-4" aria-hidden="true" />
    </button>
  );
}
