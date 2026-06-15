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
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

// One detection filter (CueGUI StuckFrameBar). service === "" is the catch-all
// ("All" when it's the only filter, "All Other Types" when service filters
// exist). The four thresholds mirror CueGUI's spinboxes.
export type StuckFilter = {
  service: string;
  regex: string; // exclude keywords, comma-separated
  percentStuck: number; // % of runtime since last log update
  minLlu: number; // minutes
  avgComp: number; // % of average completion time
  runtime: number; // minutes
  enabled: boolean;
};

// CueGUI defaults: [percentStuck, minLlu, avgComp, runtime].
export const SERVICE_DEFAULTS: Record<string, [number, number, number, number]> = {
  preprocess: [1, 1, 115, 10],
  nuke: [50, 5, 115, 10],
  arnold: [50, 60, 115, 120],
};

export const DEFAULT_FILTER: StuckFilter = {
  service: "",
  regex: "",
  percentStuck: 50,
  minLlu: 30,
  avgComp: 115,
  runtime: 60,
  enabled: true,
};

export function makeServiceFilter(service: string): StuckFilter {
  const d = SERVICE_DEFAULTS[service];
  return d
    ? { service, regex: "", percentStuck: d[0], minLlu: d[1], avgComp: d[2], runtime: d[3], enabled: true }
    : { ...DEFAULT_FILTER, service };
}

const NUM = "h-8 w-20 text-right";

function NumberField({
  label,
  suffix,
  value,
  disabled,
  onChange,
}: {
  label: string;
  suffix: string;
  value: number;
  disabled: boolean;
  onChange: (n: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted-foreground">
      {label}
      <span className="flex items-center gap-1">
        <Input
          type="number"
          min={1}
          value={value}
          disabled={disabled}
          onChange={(e) => {
            // Ignore transient/invalid input (empty field, partial entry) so a
            // NaN can't poison the filter comparisons or persisted state.
            const n = e.currentTarget.valueAsNumber;
            if (Number.isFinite(n)) onChange(n);
          }}
          className={NUM}
          aria-label={label}
        />
        <span>{suffix}</span>
      </span>
    </label>
  );
}

export function StuckFrameFilters({
  filters,
  onChange,
  availableServices,
}: {
  filters: StuckFilter[];
  onChange: (filters: StuckFilter[]) => void;
  availableServices: string[];
}) {
  function update(index: number, patch: Partial<StuckFilter>) {
    onChange(filters.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  }
  function addFilter() {
    // Default the new filter to the first available service not already used.
    // Bail out if every service is taken, rather than adding an empty row.
    const used = new Set(filters.map((f) => f.service).filter(Boolean));
    const next = availableServices.find((s) => !used.has(s));
    if (!next) return;
    onChange([...filters, makeServiceFilter(next)]);
  }
  function removeFilter(index: number) {
    onChange(filters.filter((_, i) => i !== index));
  }

  const hasServiceFilters = filters.some((f, i) => i > 0);
  const usedServices = new Set(filters.map((f) => f.service).filter(Boolean));
  const canAddFilter = availableServices.some((s) => !usedServices.has(s));

  return (
    <div className="space-y-2">
      {filters.map((f, i) => {
        const isCatchAll = i === 0;
        const disabled = !f.enabled;
        return (
          <div key={i} className="flex flex-wrap items-end gap-3 rounded-md border p-3">
            <div className="flex flex-col gap-1 text-xs text-muted-foreground">
              Layer Service
              {isCatchAll ? (
                <span className="flex h-8 items-center text-sm text-foreground">
                  {hasServiceFilters ? "All Other Types" : "All"}
                </span>
              ) : (
                <select
                  value={f.service}
                  disabled={disabled}
                  onChange={(e) => update(i, makeServiceFilter(e.target.value))}
                  className="h-8 w-40 rounded-md border border-input bg-background px-2 text-sm disabled:opacity-50"
                  aria-label="Service"
                >
                  {f.service && !availableServices.includes(f.service) ? (
                    <option value={f.service}>{f.service}</option>
                  ) : null}
                  {availableServices
                    .filter((s) => s === f.service || !usedServices.has(s))
                    .map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                </select>
              )}
            </div>

            <NumberField label="% of Run Since LLU" suffix="%" value={f.percentStuck} disabled={disabled} onChange={(n) => update(i, { percentStuck: n })} />
            <NumberField label="Min LLU" suffix="min" value={f.minLlu} disabled={disabled} onChange={(n) => update(i, { minLlu: n })} />
            <NumberField label="% Avg Completion" suffix="%" value={f.avgComp} disabled={disabled} onChange={(n) => update(i, { avgComp: n })} />
            <NumberField label="Total Runtime" suffix="min" value={f.runtime} disabled={disabled} onChange={(n) => update(i, { runtime: n })} />

            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Exclude Keywords
              <Input
                value={f.regex}
                disabled={disabled}
                onChange={(e) => update(i, { regex: e.target.value })}
                placeholder="comma-separated"
                className="h-8 w-44"
                aria-label="Exclude Keywords"
              />
            </label>

            <label className="flex flex-col items-center gap-1 text-xs text-muted-foreground">
              Enable
              <span className="flex h-8 items-center">
                <Checkbox checked={f.enabled} onCheckedChange={(c) => update(i, { enabled: !!c })} aria-label="Enable" />
              </span>
            </label>

            {isCatchAll ? (
              <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={addFilter} disabled={!canAddFilter} title={canAddFilter ? "Add a service-specific filter" : "All services already have a filter"} aria-label="Add service filter">
                <Plus className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={() => removeFilter(i)} title="Remove this filter" aria-label="Remove service filter">
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
