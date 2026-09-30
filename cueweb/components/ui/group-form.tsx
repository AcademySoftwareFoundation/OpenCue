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

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Group, getDepartmentNames } from "@/app/utils/get_utils";
import type { GroupChanges } from "@/app/utils/action_utils";

/**
 * Shared Group form (CueGUI GroupDialog parity), used by both the "Group
 * Properties..." (modify) and "Create Group..." (new) dialogs - in CueGUI both
 * are the same GroupDialog. Name + Department plus the toggleable numeric
 * fields.
 *
 * Each numeric field mirrors CueGUI's toggle spin box: Cuebot stores an
 * "unset" sentinel (-1, or 0 for the group minimums) which is shown as a
 * friendly default (the field minimum) with the checkbox off. Checking the box
 * enables the value; unchecking it leaves the field unset. `newDefault` is the
 * create-mode starting value (CueGUI NewGroupDialog defaults).
 */

export type GroupFieldKey = keyof GroupChanges;

export const GROUP_NUMERIC_FIELDS: {
  key: Exclude<GroupFieldKey, "name" | "department">;
  label: string;
  min: number;
  disable: number;
  int: boolean;
  newDefault: number;
}[] = [
  { key: "defaultJobPriority", label: "Job Default Priority", min: 0, disable: -1, int: true, newDefault: 0 },
  { key: "defaultJobMinCores", label: "Job Default Min Cores", min: 1, disable: -1, int: false, newDefault: 1 },
  { key: "defaultJobMaxCores", label: "Job Default Max Cores", min: 1, disable: -1, int: false, newDefault: 1 },
  { key: "minCores", label: "Group Min Cores", min: 0, disable: 0, int: false, newDefault: 0 },
  { key: "maxCores", label: "Group Max Cores", min: 1, disable: -1, int: false, newDefault: 1 },
  { key: "defaultJobMinGpus", label: "Job Default Min Gpus", min: 1, disable: -1, int: true, newDefault: 0 },
  { key: "defaultJobMaxGpus", label: "Job Default Max Gpus", min: 1, disable: -1, int: true, newDefault: 0 },
  { key: "minGpus", label: "Group Min Gpus", min: 0, disable: 0, int: true, newDefault: 0 },
  { key: "maxGpus", label: "Group Max Gpus", min: 1, disable: -1, int: true, newDefault: 0 },
];

const numOf = (g: Group, k: GroupFieldKey): number => Number((g as Record<string, unknown>)[k] ?? 0);

export type GroupFormState = {
  name: string;
  department: string;
  values: Record<string, string>;
  enabled: Record<string, boolean>;
};

/** Initialize form state from a group (modify) or with create-mode defaults (group=null). */
export function initGroupForm(group: Group | null): GroupFormState {
  const values: Record<string, string> = {};
  const enabled: Record<string, boolean> = {};
  for (const f of GROUP_NUMERIC_FIELDS) {
    const cur = group ? numOf(group, f.key) : f.newDefault;
    const display = Math.max(cur, f.min); // sentinel clamps to the field minimum
    // Cores use 2 decimals (CueGUI QDoubleSpinBox); priority/gpus are integers.
    values[f.key] = f.int ? String(Math.round(display)) : display.toFixed(2);
    // Modify: check a field only when a real value is set. New: all off.
    enabled[f.key] = group ? cur !== f.disable : false;
  }
  return {
    name: group?.name ?? "",
    department: group?.department ?? "Unknown",
    values,
    enabled,
  };
}

/**
 * Compute the GroupInterface changes to send. For modify, `baseline` is the
 * group's current data and a field is included only when its effective value
 * differs (checked => the value; unchecked => the sentinel). For create
 * (baseline=null), only checked fields are sent (a new group already starts at
 * the sentinels), plus name/department.
 */
export function computeGroupChanges(state: GroupFormState, baseline: Group | null): GroupChanges {
  const changes: GroupChanges = {};
  const name = state.name.trim();
  if (name && name !== (baseline?.name ?? "")) changes.name = name;
  const dept = state.department.trim();
  if (dept && dept !== (baseline?.department ?? "")) changes.department = dept;

  for (const f of GROUP_NUMERIC_FIELDS) {
    const cur = baseline ? numOf(baseline, f.key) : null;
    if (state.enabled[f.key]) {
      const raw = f.int ? parseInt(state.values[f.key], 10) : Number(state.values[f.key]);
      if (state.values[f.key] === "" || !Number.isFinite(raw)) continue;
      const result = Math.max(raw, f.min);
      if (cur === null || result !== cur) (changes[f.key] as number) = result;
    } else if (cur !== null && cur !== f.disable) {
      // Modify only: unchecking a previously-set field resets it to the sentinel.
      (changes[f.key] as number) = f.disable;
    }
  }
  return changes;
}

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

export function GroupFormFields({
  state,
  setState,
  disabled,
}: {
  state: GroupFormState;
  setState: React.Dispatch<React.SetStateAction<GroupFormState>>;
  disabled?: boolean;
}) {
  // Department options come from Cuebot (CueGUI getDepartmentNames). Always
  // include the current value so a modify dialog shows it even if the list
  // hasn't loaded or no longer contains it.
  const [departments, setDepartments] = React.useState<string[]>([]);
  React.useEffect(() => {
    let cancelled = false;
    getDepartmentNames()
      .then((names) => {
        if (!cancelled) setDepartments(names);
      })
      .catch(() => {
        /* fall back to just the current value */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const departmentOptions = React.useMemo(() => {
    const set = new Set<string>(departments);
    if (state.department) set.add(state.department);
    if (set.size === 0) set.add("Unknown");
    return Array.from(set);
  }, [departments, state.department]);

  return (
    <div className="space-y-2 py-2">
      <div className="grid grid-cols-[1.5rem_12rem_1fr] items-center gap-3">
        <span aria-hidden />
        <label className="text-sm text-muted-foreground">Name</label>
        <Input
          value={state.name}
          onChange={(e) => setState((s) => ({ ...s, name: e.target.value }))}
          aria-label="Name"
          disabled={disabled}
          autoFocus
        />
      </div>
      <div className="grid grid-cols-[1.5rem_12rem_1fr] items-center gap-3">
        <span aria-hidden />
        <label className="text-sm text-muted-foreground">Department</label>
        <select
          value={state.department}
          onChange={(e) => setState((s) => ({ ...s, department: e.target.value }))}
          aria-label="Department"
          disabled={disabled}
          className={SELECT_CLASS}
        >
          {departmentOptions.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>
      {GROUP_NUMERIC_FIELDS.map((f) => {
        const on = !!state.enabled[f.key];
        return (
          <div key={f.key} className="grid grid-cols-[1.5rem_12rem_1fr] items-center gap-3">
            <Checkbox
              checked={on}
              onCheckedChange={(c) =>
                setState((s) => ({ ...s, enabled: { ...s.enabled, [f.key]: !!c } }))
              }
              aria-label={`Enable ${f.label}`}
              disabled={disabled}
            />
            <label className={`text-sm ${on ? "text-foreground" : "text-muted-foreground"}`}>{f.label}</label>
            <Input
              type="number"
              min={f.min}
              step={f.int ? 1 : 0.01}
              value={state.values[f.key] ?? ""}
              onChange={(e) =>
                setState((s) => ({ ...s, values: { ...s.values, [f.key]: e.target.value } }))
              }
              aria-label={f.label}
              disabled={disabled || !on}
            />
          </div>
        );
      })}
    </div>
  );
}
