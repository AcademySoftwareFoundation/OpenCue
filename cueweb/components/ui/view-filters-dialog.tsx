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
import { X } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Filter,
  FilterAction,
  Group,
  Matcher,
  Show,
  getFilterActions,
  getFilterMatchers,
  getShowFilters,
  getShowGroups,
} from "@/app/utils/get_utils";
import { filterMutate } from "@/app/utils/action_utils";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";

/**
 * "View Filters..." dialog (CueGUI FilterDialog parity). A three-panel editor
 * for a show's dispatcher filters: the filter list (left), and for the selected
 * filter its matchers (top-right) and actions (bottom-right). Mounted once at
 * the page level and opened via a CustomEvent carrying the Show.
 */
export const OPEN_VIEW_FILTERS_EVENT = "cueweb:open-view-filters";

export type OpenViewFiltersDetail = { show: Show };

const FILTER_TYPES = ["MATCH_ANY", "MATCH_ALL"];
const MATCH_SUBJECTS = ["JOB_NAME", "SHOW", "SHOT", "USER", "SERVICE_NAME", "PRIORITY", "FACILITY", "LAYER_NAME"];
const MATCH_TYPES = ["CONTAINS", "DOES_NOT_CONTAIN", "IS", "IS_NOT", "REGEX", "BEGINS_WITH", "ENDS_WITH"];

const KB_PER_GB = 1048576;

// Action type -> value handling (CueGUI FilterDialog). `kind` selects the value
// editor; memory is GB in the UI but value*1048576 in the proto integer field.
type ActionKind = "group" | "boolean" | "integer" | "float" | "memory" | "string" | "none";
const ACTION_META: Record<string, { valueType: string; kind: ActionKind; boolLabels?: [string, string] }> = {
  MOVE_JOB_TO_GROUP: { valueType: "GROUP_TYPE", kind: "group" },
  PAUSE_JOB: { valueType: "BOOLEAN_TYPE", kind: "boolean", boolLabels: ["Pause", "Unpause"] },
  SET_JOB_MIN_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_JOB_MAX_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  STOP_PROCESSING: { valueType: "NONE_TYPE", kind: "none" },
  SET_JOB_PRIORITY: { valueType: "INTEGER_TYPE", kind: "integer" },
  SET_ALL_RENDER_LAYER_TAGS: { valueType: "STRING_TYPE", kind: "string" },
  SET_ALL_RENDER_LAYER_MEMORY: { valueType: "INTEGER_TYPE", kind: "memory" },
  SET_MEMORY_OPTIMIZER: { valueType: "BOOLEAN_TYPE", kind: "boolean", boolLabels: ["Enabled", "Disabled"] },
  SET_ALL_RENDER_LAYER_MIN_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_ALL_RENDER_LAYER_MAX_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_ALL_UTIL_LAYER_TAGS: { valueType: "STRING_TYPE", kind: "string" },
  SET_ALL_UTIL_LAYER_MEMORY: { valueType: "INTEGER_TYPE", kind: "memory" },
  SET_ALL_UTIL_LAYER_MIN_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_ALL_UTIL_LAYER_MAX_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_ALL_PRE_LAYER_TAGS: { valueType: "STRING_TYPE", kind: "string" },
  SET_ALL_PRE_LAYER_MEMORY: { valueType: "INTEGER_TYPE", kind: "memory" },
  SET_ALL_PRE_LAYER_MIN_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
  SET_ALL_PRE_LAYER_MAX_CORES: { valueType: "FLOAT_TYPE", kind: "float" },
};
const ACTION_TYPES = Object.keys(ACTION_META);

const SELECT_CLASS =
  "h-8 w-full rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring";

// Build a new Action object of `type` with a sensible default value.
function newActionOf(type: string, groups: Group[]): FilterAction {
  const meta = ACTION_META[type];
  const a: FilterAction = { id: "", type, valueType: meta.valueType };
  switch (meta.kind) {
    case "group":
      a.groupValue = groups[0]?.id ?? "";
      break;
    case "boolean":
      a.booleanValue = true;
      break;
    case "integer":
      a.integerValue = 0;
      break;
    case "memory":
      a.integerValue = 4 * KB_PER_GB; // 4 GB
      break;
    case "float":
      a.floatValue = 1;
      break;
    case "string":
      a.stringValue = "";
      break;
  }
  return a;
}

export function ViewFiltersDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [filters, setFilters] = React.useState<Filter[] | null>(null);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [matchers, setMatchers] = React.useState<Matcher[]>([]);
  const [actions, setActions] = React.useState<FilterAction[]>([]);
  const [groups, setGroups] = React.useState<Group[]>([]);
  const [menu, setMenu] = React.useState<{ x: number; y: number; filter: Filter } | null>(null);
  const [confirm, setConfirm] = React.useState<{ title: string; description: string; onConfirm: () => Promise<void> } | null>(null);

  const selected = React.useMemo(
    () => (filters ?? []).find((f) => f.id === selectedId) ?? null,
    [filters, selectedId],
  );

  const loadFilters = React.useCallback(async (showId: string, keepSelection?: string) => {
    const list = await getShowFilters(showId);
    list.sort((a, b) => a.order - b.order);
    setFilters(list);
    const next = keepSelection && list.some((f) => f.id === keepSelection) ? keepSelection : list[0]?.id ?? null;
    setSelectedId(next);
    return list;
  }, []);

  const loadMatchersActions = React.useCallback(async (filter: Filter | null) => {
    if (!filter) {
      setMatchers([]);
      setActions([]);
      return;
    }
    const [ms, as] = await Promise.all([getFilterMatchers(filter), getFilterActions(filter)]);
    setMatchers(ms);
    setActions(as);
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenViewFiltersDetail>).detail;
      if (!detail?.show) return;
      setShow(detail.show);
      setFilters(null);
      setSelectedId(null);
      setMatchers([]);
      setActions([]);
      setOpen(true);
      Promise.all([loadFilters(detail.show.id), getShowGroups(detail.show.id)])
        .then(([, gs]) => setGroups(gs))
        .catch((err) => handleError(err, "Could not load filters"));
    }
    window.addEventListener(OPEN_VIEW_FILTERS_EVENT, handler);
    return () => window.removeEventListener(OPEN_VIEW_FILTERS_EVENT, handler);
  }, [loadFilters]);

  // Load the selected filter's matchers + actions when the selection changes.
  React.useEffect(() => {
    loadMatchersActions(selected);
  }, [selected, loadMatchersActions]);

  // Close the filter context menu on any outside interaction.
  React.useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [menu]);

  const refresh = React.useCallback(async () => {
    if (!show) return;
    await loadFilters(show.id, selectedId ?? undefined);
  }, [show, selectedId, loadFilters]);

  // --- Filter operations -----------------------------------------------------
  async function addFilter() {
    if (!show) return;
    const name = window.prompt("Filter name?");
    if (!name || !name.trim()) return;
    if (await filterMutate("show.createfilter", { show, name: name.trim() })) {
      const list = await loadFilters(show.id);
      const created = list.find((f) => f.name === name.trim());
      if (created) setSelectedId(created.id);
      toastSuccess(`Created filter ${name.trim()}`);
    }
  }

  async function setFilterField(filter: Filter, op: string, payload: object, optimistic?: Partial<Filter>) {
    if (optimistic) {
      setFilters((prev) => (prev ?? []).map((f) => (f.id === filter.id ? { ...f, ...optimistic } : f)));
    }
    if (!(await filterMutate(op, { filter, ...payload }))) await refresh();
  }

  async function filterOrderOp(filter: Filter, op: string) {
    if (await filterMutate(op, { filter })) await refresh();
  }

  async function renameFilter(filter: Filter) {
    const name = window.prompt("What is the new name for the filter?", filter.name);
    if (!name || !name.trim() || name.trim() === filter.name) return;
    if (await filterMutate("filter.setname", { filter, name: name.trim() })) await refresh();
  }

  async function setFilterOrder(filter: Filter) {
    const raw = window.prompt("Please enter the new filter order:", String(Math.round(filter.order)));
    if (raw === null) return;
    const order = parseInt(raw, 10);
    if (!Number.isFinite(order)) return;
    if (await filterMutate("filter.setorder", { filter, order })) await refresh();
  }

  function deleteFilter(filter: Filter) {
    setConfirm({
      title: "Delete selected filters?",
      description: filter.name,
      onConfirm: async () => {
        if (await filterMutate("filter.delete", { filter })) {
          setSelectedId(null);
          await refresh();
        }
      },
    });
  }

  // --- Matcher operations ----------------------------------------------------
  async function addMatcher() {
    if (!selected) return;
    const data: Matcher = { id: "", subject: "SHOT", type: "IS", input: "" };
    if (await filterMutate("filter.creatematcher", { filter: selected, data })) {
      await loadMatchersActions(selected);
    }
  }

  async function addMultipleMatchers(replace: boolean) {
    if (!selected) return;
    const subject = window.prompt(`Subject (${MATCH_SUBJECTS.join(", ")})`, "SHOT");
    if (!subject || !MATCH_SUBJECTS.includes(subject)) return;
    const type = window.prompt(`Match type (${MATCH_TYPES.join(", ")})`, "IS");
    if (!type || !MATCH_TYPES.includes(type)) return;
    const list = window.prompt("Paste a list (space- or comma-separated):", "");
    if (list === null) return;
    const inputs = list.split(/[\s,]+/).filter(Boolean);
    if (inputs.length === 0) return;
    if (replace) {
      for (const m of matchers) await filterMutate("matcher.delete", { matcher: m });
    }
    for (const input of inputs) {
      await filterMutate("filter.creatematcher", { filter: selected, data: { id: "", subject, type, input } });
    }
    await loadMatchersActions(selected);
  }

  async function commitMatcher(matcher: Matcher, changes: Partial<Matcher>) {
    const updated = { ...matcher, ...changes };
    setMatchers((prev) => prev.map((m) => (m.id === matcher.id ? updated : m)));
    if (!(await filterMutate("matcher.commit", { matcher: updated }))) await loadMatchersActions(selected);
  }

  async function deleteMatcher(matcher: Matcher) {
    if (await filterMutate("matcher.delete", { matcher })) await loadMatchersActions(selected);
  }

  function deleteAllMatchers() {
    if (!selected || matchers.length === 0) return;
    setConfirm({
      title: "Delete all matchers?",
      description: "Are you sure you want to delete all matchers?",
      onConfirm: async () => {
        for (const m of matchers) await filterMutate("matcher.delete", { matcher: m });
        await loadMatchersActions(selected);
      },
    });
  }

  // --- Action operations -----------------------------------------------------
  async function addAction(type: string) {
    if (!selected) return;
    const data = newActionOf(type, groups);
    if (await filterMutate("filter.createaction", { filter: selected, data })) {
      await loadMatchersActions(selected);
    }
  }

  async function commitAction(action: FilterAction, changes: Partial<FilterAction>) {
    const updated = { ...action, ...changes };
    setActions((prev) => prev.map((a) => (a.id === action.id ? updated : a)));
    if (!(await filterMutate("action.commit", { action: updated }))) await loadMatchersActions(selected);
  }

  async function deleteAction(action: FilterAction) {
    if (await filterMutate("action.delete", { action })) await loadMatchersActions(selected);
  }

  function deleteAllActions() {
    if (!selected || actions.length === 0) return;
    setConfirm({
      title: "Delete all actions?",
      description: "Are you sure you want to delete all actions?",
      onConfirm: async () => {
        for (const a of actions) await filterMutate("action.delete", { action: a });
        await loadMatchersActions(selected);
      },
    });
  }

  const groupName = (id: string | undefined) => groups.find((g) => g.id === id)?.name ?? id ?? "";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-6xl">
        <DialogHeader>
          <DialogTitle>Filters for: {show?.name ?? ""}</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4">
          {/* Left: filter list */}
          <div className="flex flex-col rounded-md border">
            <div className="grid grid-cols-[3rem_1fr_7rem] gap-2 border-b bg-muted/40 px-2 py-1 text-xs font-medium">
              <span>Enabled</span>
              <span>Filter Name</span>
              <span>Type</span>
            </div>
            <div className="min-h-[20rem] flex-1 overflow-y-auto">
              {filters === null ? (
                <p className="p-3 text-sm text-muted-foreground">Loading…</p>
              ) : filters.length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">No filters.</p>
              ) : (
                filters.map((f) => (
                  <div
                    key={f.id}
                    onClick={() => setSelectedId(f.id)}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      setSelectedId(f.id);
                      setMenu({ x: e.clientX, y: e.clientY, filter: f });
                    }}
                    className={`grid cursor-pointer grid-cols-[3rem_1fr_7rem] items-center gap-2 px-2 py-1 text-xs ${
                      selectedId === f.id ? "bg-muted" : "hover:bg-muted/40"
                    }`}
                  >
                    <Checkbox
                      checked={f.enabled}
                      onClick={(e) => e.stopPropagation()}
                      onCheckedChange={(c) => setFilterField(f, "filter.setenabled", { enabled: !!c }, { enabled: !!c })}
                      aria-label="Enabled"
                    />
                    <span className="truncate" title={f.name}>{f.name}</span>
                    <select
                      value={f.type}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => setFilterField(f, "filter.settype", { type: e.target.value }, { type: e.target.value })}
                      className={SELECT_CLASS}
                      aria-label="Filter type"
                    >
                      {FILTER_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                ))
              )}
            </div>
            <div className="flex justify-between gap-2 border-t p-2">
              <Button type="button" variant="outline" size="sm" onClick={refresh}>Refresh</Button>
              <Button type="button" variant="outline" size="sm" onClick={addFilter}>Add Filter</Button>
            </div>
          </div>

          {/* Right: matchers (top) + actions (bottom) */}
          <div className="flex flex-col gap-4">
            {/* Matchers */}
            <div className="flex flex-col rounded-md border">
              <div className="grid grid-cols-[1fr_1fr_1.4fr_2rem] gap-2 border-b bg-muted/40 px-2 py-1 text-xs font-medium">
                <span>Matcher Subject</span>
                <span>Type</span>
                <span>Input</span>
                <span />
              </div>
              <div className="h-40 overflow-y-auto">
                {!selected ? (
                  <p className="p-3 text-sm text-muted-foreground">Select a filter.</p>
                ) : matchers.length === 0 ? (
                  <p className="p-3 text-sm text-muted-foreground">No matchers.</p>
                ) : (
                  matchers.map((m) => (
                    <div key={m.id} className="grid grid-cols-[1fr_1fr_1.4fr_2rem] items-center gap-2 px-2 py-1">
                      <select value={m.subject} onChange={(e) => commitMatcher(m, { subject: e.target.value })} className={SELECT_CLASS} aria-label="Subject">
                        {MATCH_SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                      <select value={m.type} onChange={(e) => commitMatcher(m, { type: e.target.value })} className={SELECT_CLASS} aria-label="Match type">
                        {MATCH_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <Input
                        defaultValue={m.input}
                        onBlur={(e) => e.target.value !== m.input && commitMatcher(m, { input: e.target.value })}
                        onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
                        className="h-8 text-xs"
                        aria-label="Input"
                      />
                      <button type="button" onClick={() => deleteMatcher(m)} aria-label="Delete matcher" title="Delete matcher" className="text-red-500 hover:text-red-400">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
              <div className="flex flex-wrap justify-end gap-2 border-t p-2">
                <Button type="button" variant="outline" size="sm" onClick={() => addMultipleMatchers(false)} disabled={!selected}>Add Multiple Matchers</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => addMultipleMatchers(true)} disabled={!selected}>Replace All Matchers</Button>
                <Button type="button" variant="outline" size="sm" onClick={deleteAllMatchers} disabled={!selected}>Delete All Matchers</Button>
                <Button type="button" variant="outline" size="sm" onClick={addMatcher} disabled={!selected}>Add Matcher</Button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col rounded-md border">
              <div className="grid grid-cols-[1.4fr_1.6fr_2rem] gap-2 border-b bg-muted/40 px-2 py-1 text-xs font-medium">
                <span>Action Type</span>
                <span>Value</span>
                <span />
              </div>
              <div className="h-40 overflow-y-auto">
                {!selected ? (
                  <p className="p-3 text-sm text-muted-foreground">Select a filter.</p>
                ) : actions.length === 0 ? (
                  <p className="p-3 text-sm text-muted-foreground">No actions.</p>
                ) : (
                  actions.map((a) => (
                    <div key={a.id} className="grid grid-cols-[1.4fr_1.6fr_2rem] items-center gap-2 px-2 py-1 text-xs">
                      <span className="truncate" title={a.type}>{a.type}</span>
                      <ActionValueEditor action={a} groups={groups} onCommit={(changes) => commitAction(a, changes)} groupName={groupName} />
                      <button type="button" onClick={() => deleteAction(a)} aria-label="Delete action" title="Delete action" className="text-red-500 hover:text-red-400">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
              <div className="flex justify-end gap-2 border-t p-2">
                <Button type="button" variant="outline" size="sm" onClick={deleteAllActions} disabled={!selected}>Delete All Actions</Button>
                <AddActionButton onAdd={addAction} disabled={!selected} />
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button type="button" onClick={() => setOpen(false)}>Done</Button>
        </div>
      </DialogContent>

      {/* Filter right-click menu */}
      {menu ? (
        <div
          className="fixed z-[60] min-w-44 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {[
            ["Raise Order", () => filterOrderOp(menu.filter, "filter.raiseorder")],
            ["Lower Order", () => filterOrderOp(menu.filter, "filter.lowerorder")],
            ["Order First", () => filterOrderOp(menu.filter, "filter.orderfirst")],
            ["Order Last", () => filterOrderOp(menu.filter, "filter.orderlast")],
            ["sep", null],
            ["Rename...", () => renameFilter(menu.filter)],
            ["Set Order...", () => setFilterOrder(menu.filter)],
            ["sep", null],
            ["Delete", () => deleteFilter(menu.filter)],
          ].map(([label, fn], i) =>
            label === "sep" ? (
              <div key={i} className="my-1 h-px bg-border" />
            ) : (
              <button
                key={i}
                className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
                onClick={() => { (fn as () => void)(); setMenu(null); }}
              >
                {label as string}
              </button>
            ),
          )}
        </div>
      ) : null}

      {confirm ? (
        <ConfirmDialog
          open={!!confirm}
          onOpenChange={(o) => !o && setConfirm(null)}
          title={confirm.title}
          description={confirm.description}
          confirmLabel="OK"
          cancelLabel="Cancel"
          variant="destructive"
          onConfirm={async () => { await confirm.onConfirm(); setConfirm(null); }}
        />
      ) : null}
    </Dialog>
  );
}

// Per-action value editor; the control depends on the action type.
function ActionValueEditor({
  action,
  groups,
  onCommit,
  groupName,
}: {
  action: FilterAction;
  groups: Group[];
  onCommit: (changes: Partial<FilterAction>) => void;
  groupName: (id: string | undefined) => string;
}) {
  const meta = ACTION_META[action.type];
  if (!meta) return <span className="text-muted-foreground">{groupName(action.groupValue)}</span>;

  switch (meta.kind) {
    case "none":
      return <span className="text-muted-foreground">(no value)</span>;
    case "group":
      return (
        <select value={action.groupValue ?? ""} onChange={(e) => onCommit({ groupValue: e.target.value })} className={SELECT_CLASS} aria-label="Group">
          {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
      );
    case "boolean": {
      const [tLabel, fLabel] = meta.boolLabels ?? ["True", "False"];
      return (
        <select
          value={action.booleanValue ? "true" : "false"}
          onChange={(e) => onCommit({ booleanValue: e.target.value === "true" })}
          className={SELECT_CLASS}
          aria-label="Value"
        >
          <option value="true">{tLabel}</option>
          <option value="false">{fLabel}</option>
        </select>
      );
    }
    case "string":
      return (
        <Input
          defaultValue={action.stringValue ?? ""}
          onBlur={(e) => e.target.value !== (action.stringValue ?? "") && onCommit({ stringValue: e.target.value })}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
          className="h-8 text-xs"
          aria-label="Value"
        />
      );
    case "integer":
      return (
        <Input
          type="number"
          defaultValue={action.integerValue ?? 0}
          onBlur={(e) => onCommit({ integerValue: Math.round(Number(e.target.value)) })}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
          className="h-8 text-xs"
          aria-label="Value"
        />
      );
    case "float":
      return (
        <Input
          type="number"
          step={0.01}
          defaultValue={action.floatValue ?? 0}
          onBlur={(e) => onCommit({ floatValue: Number(e.target.value) })}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
          className="h-8 text-xs"
          aria-label="Value"
        />
      );
    case "memory":
      return (
        <Input
          type="number"
          step={0.01}
          defaultValue={(action.integerValue ?? 0) / KB_PER_GB}
          onBlur={(e) => onCommit({ integerValue: Math.round(Number(e.target.value) * KB_PER_GB) })}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
          className="h-8 text-xs"
          aria-label="Value (GB)"
          title="GB"
        />
      );
  }
}

// "Add Action" with an inline action-type picker (CueGUI prompts for the type).
function AddActionButton({ onAdd, disabled }: { onAdd: (type: string) => void; disabled?: boolean }) {
  const [openPicker, setOpenPicker] = React.useState(false);
  const [type, setType] = React.useState(ACTION_TYPES[0]);
  return (
    <>
      <Button type="button" variant="outline" size="sm" onClick={() => setOpenPicker(true)} disabled={disabled}>Add Action</Button>
      <Dialog open={openPicker} onOpenChange={setOpenPicker}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Create Action</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">Please select the type of action to add:</p>
          <select value={type} onChange={(e) => setType(e.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm" aria-label="Action type">
            {ACTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpenPicker(false)}>Cancel</Button>
            <Button type="button" onClick={() => { onAdd(type); setOpenPicker(false); }}>OK</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
