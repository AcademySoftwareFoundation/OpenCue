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
  ColumnFiltersState,
  Table,
  VisibilityState,
} from "@tanstack/react-table";
import { Check, Eye, Pencil, Plus, RotateCcw, Save, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/**
 * Web-native replacement for CueGUI's "Save Window Settings"
 * (cuegui/cuegui/MainWindow.py). Each major table gets a "Views" dropdown so
 * users can save the current column order/visibility, sort, filters and page
 * size as a named preset, then re-apply / rename / delete it later.
 *
 * Presets live in localStorage under `cueweb.views.<page>` (an array of
 * {@link View}) and the active preset name under `cueweb.views.<page>.active`.
 * Both keys broadcast to other open tabs via the native `storage` event so a
 * preset saved in one tab shows up in the others without a reload.
 *
 * The built-in "Default" preset is synthesized from the table's documented
 * defaults (column-def natural order + caller-supplied default visibility /
 * page size). It can't be renamed or deleted; selecting it restores the table.
 *
 * The component is deliberately table-agnostic: it reads and writes everything
 * through the TanStack `table` instance, which both the Jobs `data-table.tsx`
 * and the shared `SimpleDataTable` already expose. Applying a view routes
 * through the table's own onChange handlers, so each table's existing
 * localStorage persistence (columnVisibility/columnOrder/page-size) keeps
 * working unchanged.
 */

/** One column's saved order + visibility. `order` is the 0-based slot. */
export interface ViewColumn {
  id: string;
  visible: boolean;
  order: number;
}

/** One sort directive. `dir` mirrors TanStack's `desc` boolean. */
export interface ViewSort {
  id: string;
  dir: "asc" | "desc";
}

/** Serializable snapshot of a table's user-tunable layout. */
export interface View {
  name: string;
  columns: ViewColumn[];
  sort: ViewSort[];
  filters: ColumnFiltersState;
  pageSize: number;
}

/** Reserved name for the built-in preset; can't be saved/renamed/deleted. */
export const DEFAULT_VIEW_NAME = "Default";

const viewsStorageKey = (page: string) => `cueweb.views.${page}`;
const activeStorageKey = (page: string) => `cueweb.views.${page}.active`;

/** Read the saved preset list for a page. Returns [] on any parse error. */
export function loadViews(page: string): View[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(viewsStorageKey(page));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as View[]) : [];
  } catch {
    return [];
  }
}

/** Persist the preset list for a page (fires `storage` in other tabs). */
export function saveViews(page: string, views: View[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(viewsStorageKey(page), JSON.stringify(views));
  } catch {
    // Quota / private mode; ignore - presets just won't persist.
  }
}

/**
 * Snapshot the table's current layout into a {@link View}. Column order
 * follows the live `columnOrder` when set, otherwise the natural column-def
 * order; any columns missing from `columnOrder` are appended in natural order
 * so a partial order never drops columns.
 */
export function captureView(table: Table<any>, name: string): View {
  const leafColumns = table.getAllLeafColumns();
  const naturalIds = leafColumns.map((c) => c.id);
  const naturalSet = new Set(naturalIds);
  const currentOrder = table.getState().columnOrder ?? [];
  const seen = new Set<string>();
  const orderedIds: string[] = [];
  for (const id of currentOrder) {
    if (naturalSet.has(id) && !seen.has(id)) {
      seen.add(id);
      orderedIds.push(id);
    }
  }
  for (const id of naturalIds) {
    if (!seen.has(id)) orderedIds.push(id);
  }

  const columns: ViewColumn[] = orderedIds.map((id, index) => {
    const column = table.getColumn(id);
    return {
      id,
      visible: column ? column.getIsVisible() : true,
      order: index,
    };
  });

  const sort: ViewSort[] = table
    .getState()
    .sorting.map((s) => ({ id: s.id, dir: s.desc ? "desc" : "asc" }));

  return {
    name,
    columns,
    sort,
    filters: table.getState().columnFilters ?? [],
    pageSize: table.getState().pagination.pageSize,
  };
}

/** Apply a saved {@link View} back onto the table instance. */
export function applyView(table: Table<any>, view: View): void {
  const ordered = [...view.columns].sort((a, b) => a.order - b.order);
  table.setColumnOrder(ordered.map((c) => c.id));

  const visibility: VisibilityState = {};
  for (const c of view.columns) visibility[c.id] = c.visible;
  table.setColumnVisibility(visibility);

  table.setSorting(view.sort.map((s) => ({ id: s.id, desc: s.dir === "desc" })));
  table.setColumnFilters(view.filters ?? []);
  if (typeof view.pageSize === "number" && view.pageSize > 0) {
    table.setPageSize(view.pageSize);
  }
}

interface ViewsMenuProps {
  /** Storage namespace, e.g. "jobs" | "hosts" | "frames". */
  page: string;
  /** The TanStack table instance to capture from / apply to. */
  table: Table<any>;
  /**
   * Visibility map the "Default" preset restores (hidden-by-default columns).
   * Should match the table's own `defaultColumnVisibility`.
   */
  defaultColumnVisibility?: VisibilityState;
  /** Page size the "Default" preset restores. */
  defaultPageSize?: number;
  className?: string;
}

type PresetDialog =
  | { mode: "save" }
  | { mode: "rename"; target: string }
  | null;

export function ViewsMenu({
  page,
  table,
  defaultColumnVisibility,
  defaultPageSize,
  className,
}: ViewsMenuProps) {
  // Hydrate from localStorage on mount (not in the initializer) so SSR and the
  // first client render agree - matches the hydration model used elsewhere in
  // the table components.
  const [views, setViews] = React.useState<View[]>([]);
  const [activeName, setActiveName] = React.useState<string>(DEFAULT_VIEW_NAME);
  const [dialog, setDialog] = React.useState<PresetDialog>(null);
  const [nameInput, setNameInput] = React.useState("");
  const [nameError, setNameError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setViews(loadViews(page));
    const storedActive = window.localStorage.getItem(activeStorageKey(page));
    if (storedActive) setActiveName(storedActive);
  }, [page]);

  // Cross-tab sync: another tab saving a preset (or switching the active one)
  // writes our storage keys; the native `storage` event lets us pick that up
  // without a reload. We don't re-apply the layout on a remote active-change
  // (that would yank the layout out from under the user); we only mirror the
  // list + active label so the menu stays consistent.
  React.useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === viewsStorageKey(page)) {
        setViews(loadViews(page));
      } else if (e.key === activeStorageKey(page)) {
        setActiveName(e.newValue || DEFAULT_VIEW_NAME);
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [page]);

  const persistViews = React.useCallback(
    (next: View[]) => {
      setViews(next);
      saveViews(page, next);
    },
    [page],
  );

  const markActive = React.useCallback(
    (name: string) => {
      setActiveName(name);
      try {
        window.localStorage.setItem(activeStorageKey(page), name);
      } catch {
        // ignore persistence failure; in-memory state still updates.
      }
    },
    [page],
  );

  const handleApply = React.useCallback(
    (view: View) => {
      applyView(table, view);
      markActive(view.name);
    },
    [table, markActive],
  );

  const handleRestoreDefault = React.useCallback(() => {
    table.setColumnOrder([]);
    table.setColumnVisibility(defaultColumnVisibility ?? {});
    table.setSorting([]);
    table.setColumnFilters([]);
    if (typeof defaultPageSize === "number" && defaultPageSize > 0) {
      table.setPageSize(defaultPageSize);
    }
    markActive(DEFAULT_VIEW_NAME);
  }, [table, defaultColumnVisibility, defaultPageSize, markActive]);

  // Overwrite the active user preset in place with the current layout.
  const handleUpdateActive = React.useCallback(() => {
    const captured = captureView(table, activeName);
    persistViews(views.map((v) => (v.name === activeName ? captured : v)));
  }, [table, activeName, views, persistViews]);

  const openSaveDialog = React.useCallback(() => {
    setNameInput("");
    setNameError(null);
    setDialog({ mode: "save" });
  }, []);

  const openRenameDialog = React.useCallback((target: string) => {
    setNameInput(target);
    setNameError(null);
    setDialog({ mode: "rename", target });
  }, []);

  const handleDelete = React.useCallback(
    (name: string) => {
      persistViews(views.filter((v) => v.name !== name));
      if (activeName === name) markActive(DEFAULT_VIEW_NAME);
    },
    [views, activeName, persistViews, markActive],
  );

  const validateName = (raw: string, currentTarget?: string): string | null => {
    const name = raw.trim();
    if (!name) return "Name can't be empty.";
    if (name === DEFAULT_VIEW_NAME) return `"${DEFAULT_VIEW_NAME}" is reserved.`;
    const clash = views.some((v) => v.name === name && v.name !== currentTarget);
    if (clash) return "A view with that name already exists.";
    return null;
  };

  const handleDialogConfirm = () => {
    if (!dialog) return;
    const name = nameInput.trim();
    const target = dialog.mode === "rename" ? dialog.target : undefined;
    const error = validateName(nameInput, target);
    if (error) {
      setNameError(error);
      return;
    }
    if (dialog.mode === "save") {
      const captured = captureView(table, name);
      persistViews([...views, captured]);
      markActive(name);
    } else {
      persistViews(
        views.map((v) => (v.name === dialog.target ? { ...v, name } : v)),
      );
      if (activeName === dialog.target) markActive(name);
    }
    setDialog(null);
  };

  const activeIsUserView = views.some((v) => v.name === activeName);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={cn("h-8 max-w-[12rem]", className)}
            aria-label="Saved views"
          >
            <Eye className="mr-1 h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">
              {activeName === DEFAULT_VIEW_NAME ? "Views" : activeName}
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          className="max-h-[60vh] w-64 overflow-y-auto"
        >
          <DropdownMenuLabel>Views</DropdownMenuLabel>

          {/* Built-in Default preset: restores the table to its documented
              defaults. Can't be renamed or deleted. */}
          <DropdownMenuItem
            onSelect={handleRestoreDefault}
            className="flex items-center gap-2"
          >
            <span className="flex w-4 shrink-0 justify-center">
              {activeName === DEFAULT_VIEW_NAME ? (
                <Check className="h-4 w-4" aria-hidden="true" />
              ) : null}
            </span>
            <RotateCcw className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="flex-1 truncate">{DEFAULT_VIEW_NAME}</span>
          </DropdownMenuItem>

          {views.length > 0 ? <DropdownMenuSeparator /> : null}

          {/* Each saved view is a submenu so Apply / Rename / Delete are
              first-class, keyboard-navigable menu items (Radix arrow-key focus
              only reaches menuitems, not buttons nested inside a row). */}
          {views.map((view) => (
            <DropdownMenuSub key={view.name}>
              <DropdownMenuSubTrigger className="gap-2">
                <span className="flex w-4 shrink-0 justify-center">
                  {activeName === view.name ? (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  ) : null}
                </span>
                <span className="flex-1 truncate">{view.name}</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem onSelect={() => handleApply(view)}>
                  <Eye className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                  Apply
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(e) => {
                    // Mirror the "Save as…" item: keep the menu open while the
                    // rename dialog takes focus.
                    e.preventDefault();
                    openRenameDialog(view.name);
                  }}
                >
                  <Pencil className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                  Rename&hellip;
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() => handleDelete(view.name)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          ))}

          <DropdownMenuSeparator />

          {/* Update the active user preset in place. Hidden when Default (or no
              user preset) is active - there's nothing to overwrite. */}
          {activeIsUserView ? (
            <DropdownMenuItem onSelect={handleUpdateActive}>
              <Save className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
              {`Update "${activeName}"`}
            </DropdownMenuItem>
          ) : null}

          <DropdownMenuItem
            onSelect={(e) => {
              // Keep the dropdown from stealing focus back from the dialog.
              e.preventDefault();
              openSaveDialog();
            }}
          >
            <Plus className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Save as&hellip;
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {dialog?.mode === "rename" ? "Rename view" : "Save view"}
            </DialogTitle>
            <DialogDescription>
              {dialog?.mode === "rename"
                ? "Give this saved view a new name."
                : "Save the current columns, sort, filters and page size as a named view."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="view-name">Name</Label>
            <Input
              id="view-name"
              autoFocus
              value={nameInput}
              onChange={(e) => {
                setNameInput(e.target.value);
                if (nameError) setNameError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleDialogConfirm();
                }
              }}
              placeholder="My view"
              aria-invalid={nameError ? true : undefined}
            />
            {nameError ? (
              <p className="text-xs text-destructive">{nameError}</p>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button onClick={handleDialogConfirm}>
              {dialog?.mode === "rename" ? "Rename" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default ViewsMenu;
