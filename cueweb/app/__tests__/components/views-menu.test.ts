/**
 * @jest-environment jsdom
 */

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
  applyView,
  captureView,
  loadViews,
  saveViews,
  View,
} from "@/components/ui/views-menu";

// Minimal stand-in for the slice of the TanStack table API that captureView /
// applyView touch. Lets us exercise the pure capture/apply logic without
// mounting a real React table.
function makeMockTable(opts: {
  columnIds: string[];
  visibility?: Record<string, boolean>;
  columnOrder?: string[];
  sorting?: { id: string; desc: boolean }[];
  columnFilters?: { id: string; value: unknown }[];
  pageSize?: number;
}) {
  const state = {
    columnOrder: opts.columnOrder ?? [],
    sorting: opts.sorting ?? [],
    columnFilters: opts.columnFilters ?? [],
    pagination: { pageIndex: 0, pageSize: opts.pageSize ?? 10 },
  };
  const visibility: Record<string, boolean> = { ...(opts.visibility ?? {}) };

  return {
    state,
    visibility,
    getAllLeafColumns: () => opts.columnIds.map((id) => ({ id })),
    getColumn: (id: string) => ({
      id,
      getIsVisible: () => visibility[id] !== false,
    }),
    getState: () => state,
    setColumnOrder: (order: string[]) => {
      state.columnOrder = order;
    },
    setColumnVisibility: (v: Record<string, boolean>) => {
      Object.keys(visibility).forEach((k) => delete visibility[k]);
      Object.assign(visibility, v);
    },
    setSorting: (s: { id: string; desc: boolean }[]) => {
      state.sorting = s;
    },
    setColumnFilters: (f: { id: string; value: unknown }[]) => {
      state.columnFilters = f;
    },
    setPageSize: (n: number) => {
      state.pagination.pageSize = n;
    },
  };
}

describe("views-menu storage helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("loadViews returns [] when nothing is stored", () => {
    expect(loadViews("jobs")).toEqual([]);
  });

  it("loadViews returns [] for malformed JSON", () => {
    localStorage.setItem("cueweb.views.jobs", "{not json");
    expect(loadViews("jobs")).toEqual([]);
  });

  it("loadViews returns [] when the stored value is not an array", () => {
    localStorage.setItem("cueweb.views.jobs", JSON.stringify({ a: 1 }));
    expect(loadViews("jobs")).toEqual([]);
  });

  it("saveViews + loadViews round-trips a preset list", () => {
    const views: View[] = [
      {
        name: "Mine",
        columns: [{ id: "name", visible: true, order: 0 }],
        sort: [{ id: "name", dir: "asc" }],
        filters: [],
        pageSize: 25,
      },
    ];
    saveViews("jobs", views);
    expect(localStorage.getItem("cueweb.views.jobs")).toBe(
      JSON.stringify(views),
    );
    expect(loadViews("jobs")).toEqual(views);
  });

  it("namespaces presets per page", () => {
    saveViews("hosts", [
      { name: "H", columns: [], sort: [], filters: [], pageSize: 10 },
    ]);
    expect(loadViews("hosts")).toHaveLength(1);
    expect(loadViews("jobs")).toEqual([]);
  });
});

describe("captureView", () => {
  it("captures column order, visibility, sort, filters and page size", () => {
    const table = makeMockTable({
      columnIds: ["select", "name", "state", "cores"],
      visibility: { cores: false },
      columnOrder: ["select", "state", "name", "cores"],
      sorting: [{ id: "name", desc: true }],
      columnFilters: [{ id: "state", value: "RUNNING" }],
      pageSize: 50,
    });

    const view = captureView(table as any, "snap");

    expect(view.name).toBe("snap");
    expect(view.columns.map((c) => c.id)).toEqual([
      "select",
      "state",
      "name",
      "cores",
    ]);
    expect(view.columns.map((c) => c.order)).toEqual([0, 1, 2, 3]);
    expect(view.columns.find((c) => c.id === "cores")?.visible).toBe(false);
    expect(view.columns.find((c) => c.id === "name")?.visible).toBe(true);
    expect(view.sort).toEqual([{ id: "name", dir: "desc" }]);
    expect(view.filters).toEqual([{ id: "state", value: "RUNNING" }]);
    expect(view.pageSize).toBe(50);
  });

  it("falls back to natural order and appends columns missing from columnOrder", () => {
    const table = makeMockTable({
      columnIds: ["a", "b", "c"],
      // Partial / stale order: only "c" listed, plus a bogus id to ignore.
      columnOrder: ["c", "ghost"],
    });

    const view = captureView(table as any, "v");
    expect(view.columns.map((c) => c.id)).toEqual(["c", "a", "b"]);
  });
});

describe("applyView", () => {
  it("writes order, visibility, sort, filters and page size back to the table", () => {
    const table = makeMockTable({ columnIds: ["a", "b", "c"] });
    const view: View = {
      name: "v",
      columns: [
        { id: "b", visible: true, order: 0 },
        { id: "a", visible: false, order: 1 },
        { id: "c", visible: true, order: 2 },
      ],
      sort: [{ id: "b", dir: "desc" }],
      filters: [{ id: "a", value: "x" }],
      pageSize: 100,
    };

    applyView(table as any, view);

    expect(table.state.columnOrder).toEqual(["b", "a", "c"]);
    expect(table.visibility).toEqual({ b: true, a: false, c: true });
    expect(table.state.sorting).toEqual([{ id: "b", desc: true }]);
    expect(table.state.columnFilters).toEqual([{ id: "a", value: "x" }]);
    expect(table.state.pagination.pageSize).toBe(100);
  });

  it("sorts columns by their saved order before applying", () => {
    const table = makeMockTable({ columnIds: ["a", "b", "c"] });
    const view: View = {
      name: "v",
      columns: [
        { id: "c", visible: true, order: 2 },
        { id: "a", visible: true, order: 0 },
        { id: "b", visible: true, order: 1 },
      ],
      sort: [],
      filters: [],
      pageSize: 10,
    };

    applyView(table as any, view);
    expect(table.state.columnOrder).toEqual(["a", "b", "c"]);
  });

  it("ignores a non-positive page size", () => {
    const table = makeMockTable({ columnIds: ["a"], pageSize: 20 });
    applyView(table as any, {
      name: "v",
      columns: [{ id: "a", visible: true, order: 0 }],
      sort: [],
      filters: [],
      pageSize: 0,
    });
    expect(table.state.pagination.pageSize).toBe(20);
  });

  it("round-trips through capture then apply", () => {
    const source = makeMockTable({
      columnIds: ["select", "name", "state"],
      visibility: { state: false },
      columnOrder: ["name", "select", "state"],
      sorting: [{ id: "name", desc: false }],
      pageSize: 15,
    });
    const view = captureView(source as any, "roundtrip");

    const target = makeMockTable({ columnIds: ["select", "name", "state"] });
    applyView(target as any, view);

    expect(target.state.columnOrder).toEqual(["name", "select", "state"]);
    expect(target.visibility).toEqual({
      name: true,
      select: true,
      state: false,
    });
    expect(target.state.sorting).toEqual([{ id: "name", desc: false }]);
    expect(target.state.pagination.pageSize).toBe(15);
  });
});
