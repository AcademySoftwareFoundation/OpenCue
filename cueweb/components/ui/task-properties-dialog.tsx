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

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Department,
  Show,
  Task,
  getDepartmentTasks,
  getShowDepartments,
} from "@/app/utils/get_utils";
import { taskMutate } from "@/app/utils/action_utils";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";

/**
 * "Task Properties..." dialog (CueGUI TasksDialog parity). Displays/modifies a
 * show's department-managed tasks: a department selector, the department's
 * "managed" toggle + minimum (managed) cores, and the task list (Shot /
 * Department / Minimum Cores / Adjust Cores) with per-task actions. Mounted
 * once at the page level and opened via a CustomEvent carrying the Show.
 */
export const OPEN_TASK_PROPERTIES_EVENT = "cueweb:open-task-properties";

export type OpenTaskPropertiesDetail = { show: Show };

const SELECT_CLASS =
  "h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// window.prompt for a double in [min,max]; returns null on cancel/invalid.
function promptDouble(message: string, def: number, min = 0, max = 50000): number | null {
  const raw = window.prompt(message, String(def));
  if (raw === null) return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n < min || n > max) return null;
  return n;
}

export function TaskPropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [departments, setDepartments] = React.useState<Department[]>([]);
  const [deptName, setDeptName] = React.useState<string>("");
  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [menu, setMenu] = React.useState<{ x: number; y: number; task: Task } | null>(null);
  const [confirm, setConfirm] = React.useState<{ title: string; description: string; onConfirm: () => Promise<void> } | null>(null);

  const department = React.useMemo(
    () => departments.find((d) => d.name === deptName) ?? null,
    [departments, deptName],
  );

  const loadDepartments = React.useCallback(async (showId: string, keepName?: string) => {
    const list = await getShowDepartments(showId);
    list.sort((a, b) => a.name.localeCompare(b.name));
    setDepartments(list);
    const next = keepName && list.some((d) => d.name === keepName) ? keepName : list[0]?.name ?? "";
    setDeptName(next);
    return list;
  }, []);

  const loadTasks = React.useCallback(async (dept: Department | null) => {
    if (!dept) {
      setTasks([]);
      return;
    }
    setTasks(await getDepartmentTasks(dept));
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenTaskPropertiesDetail>).detail;
      if (!detail?.show) return;
      setShow(detail.show);
      setDepartments([]);
      setDeptName("");
      setTasks([]);
      setOpen(true);
      loadDepartments(detail.show.id).catch((err) => handleError(err, "Could not load departments"));
    }
    window.addEventListener(OPEN_TASK_PROPERTIES_EVENT, handler);
    return () => window.removeEventListener(OPEN_TASK_PROPERTIES_EVENT, handler);
  }, [loadDepartments]);

  // Reload the task list when the selected department changes.
  React.useEffect(() => {
    loadTasks(department);
  }, [department, loadTasks]);

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

  async function reloadDepartment() {
    if (!show) return;
    await loadDepartments(show.id, deptName);
  }

  // --- Department operations --------------------------------------------------
  async function setManagedCores() {
    if (!department) return;
    const managed = promptDouble("Please enter the new managed cores value:", department.minCores);
    if (managed === null) return;
    if (await taskMutate("dept.setmanagedcores", { department, managed_cores: managed })) {
      await reloadDepartment();
    }
  }

  async function toggleManaged(checked: boolean) {
    if (!department) return;
    if (!department.tiManaged && checked) {
      const tiTask = window.prompt(
        `What tiTask should be used to manage the ${department.name} department?`,
        department.tiTask,
      );
      if (tiTask === null) return;
      const managed = promptDouble("Please enter the new managed cores value:", department.minCores);
      if (managed === null) return;
      if (await taskMutate("dept.enabletimanaged", { department, ti_task: tiTask, managed_cores: managed })) {
        toastSuccess(`Enabled management of ${department.name}`);
        await reloadDepartment();
      }
    } else if (department.tiManaged && !checked) {
      setConfirm({
        title: "Confirm",
        description: `Disable management of the ${department.name} department?`,
        onConfirm: async () => {
          if (await taskMutate("dept.disabletimanaged", { department })) {
            toastSuccess(`Disabled management of ${department.name}`);
            await reloadDepartment();
          }
        },
      });
    }
  }

  async function addTask() {
    if (!department) return;
    const shot = window.prompt("What shot is this task for?", "");
    if (!shot || !shot.trim()) return;
    const minCores = promptDouble("Please enter the new minimum cores value:", 1);
    if (minCores === null) return;
    if (await taskMutate("dept.addtask", { department, shot: shot.trim(), min_cores: minCores })) {
      toastSuccess(`Added task ${shot.trim()}`);
      await loadTasks(department);
    }
  }

  // --- Task operations --------------------------------------------------------
  async function setTaskMinCores(task: Task) {
    const minCores = promptDouble("Please enter the new minimum cores value:", task.minCores);
    if (minCores === null) return;
    if (await taskMutate("task.setmincores", { task, new_min_cores: minCores })) await loadTasks(department);
  }

  async function clearTaskAdjustment(task: Task) {
    if (await taskMutate("task.clearadjustments", { task })) await loadTasks(department);
  }

  function deleteTask(task: Task) {
    setConfirm({
      title: "Delete Task",
      description: `Delete the task for shot "${task.shot}"?`,
      onConfirm: async () => {
        if (await taskMutate("task.delete", { task })) await loadTasks(department);
      },
    });
  }

  const managed = department?.tiManaged ?? false;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Tasks for: {show?.name ?? ""}</DialogTitle>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={deptName}
            onChange={(e) => setDeptName(e.target.value)}
            className={SELECT_CLASS}
            aria-label="Department"
            disabled={departments.length === 0}
          >
            {departments.length === 0 ? <option value="">No departments</option> : null}
            {departments.map((d) => (
              <option key={d.id || d.name} value={d.name}>{d.name}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={managed}
              onCheckedChange={(c) => toggleManaged(!!c)}
              disabled={!department}
              aria-label="Managed"
            />
            Managed
          </label>
          <Button type="button" variant="outline" size="sm" onClick={setManagedCores} disabled={!department}>
            Minimum Cores: {(department?.minCores ?? 0).toFixed(2)}
          </Button>
        </div>

        <div className="rounded-md border">
          <div className="grid grid-cols-4 gap-2 border-b bg-muted/40 px-3 py-1 text-xs font-medium">
            <span>Shot</span>
            <span>Department</span>
            <span className="text-right">Minimum Cores</span>
            <span className="text-right">Adjust Cores</span>
          </div>
          <div className="max-h-80 min-h-[16rem] overflow-y-auto">
            {!department ? (
              <p className="p-3 text-sm text-muted-foreground">Select a department.</p>
            ) : tasks.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">No tasks.</p>
            ) : (
              [...tasks]
                .sort((a, b) => a.shot.localeCompare(b.shot))
                .map((t) => (
                  <div
                    key={t.id}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      setMenu({ x: e.clientX, y: e.clientY, task: t });
                    }}
                    className="grid cursor-default grid-cols-4 gap-2 px-3 py-1 text-sm hover:bg-muted/40"
                  >
                    <span className="truncate" title={t.shot}>{t.shot}</span>
                    <span className="truncate">{t.dept}</span>
                    <span className="text-right tabular-nums">{t.minCores.toFixed(2)}</span>
                    <span className="text-right tabular-nums">{t.adjustCores.toFixed(2)}</span>
                  </div>
                ))
            )}
          </div>
        </div>

        <div className="flex justify-between gap-2 pt-1">
          <Button type="button" variant="outline" size="sm" onClick={addTask} disabled={!department || managed}>
            Add Task
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => loadTasks(department)} disabled={!department}>
            Refresh
          </Button>
          <Button type="button" size="sm" onClick={() => setOpen(false)}>Done</Button>
        </div>
      </DialogContent>

      {/* Task right-click menu (CueGUI parity). Delete only when not managed. */}
      {menu ? (
        <div
          className="fixed z-[60] min-w-56 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => { setTaskMinCores(menu.task); setMenu(null); }}
          >
            Set Minimum Cores...
          </button>
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => { clearTaskAdjustment(menu.task); setMenu(null); }}
          >
            Clear Minimum Core Adjustment
          </button>
          {!managed ? (
            <>
              <div className="my-1 h-px bg-border" />
              <button
                className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
                onClick={() => { deleteTask(menu.task); setMenu(null); }}
              >
                Delete Task
              </button>
            </>
          ) : null}
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
          onConfirm={async () => { await confirm.onConfirm(); setConfirm(null); }}
        />
      ) : null}
    </Dialog>
  );
}
