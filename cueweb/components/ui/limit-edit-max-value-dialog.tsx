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

import type { Limit } from "@/app/utils/get_utils";
import { setLimitMaxValue } from "@/app/utils/action_utils";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  LIMITS_CHANGED_EVENT,
  OPEN_LIMIT_EDIT_MAX_VALUE_EVENT,
  type OpenLimitDetail,
} from "@/components/ui/limit-action-events";

/**
 * "Edit Max Value" dialog (CueGUI LimitsWidget parity). Mounted once on the
 * Limits page and opened by a `cueweb:open-limit-edit-max-value` event from the
 * row context menu. Validates a non-negative integer before calling
 * SetMaxValue, then fires `cueweb:limits-changed` so the table refreshes.
 */
export function LimitEditMaxValueDialog() {
  const [open, setOpen] = React.useState(false);
  const [limit, setLimit] = React.useState<Limit | null>(null);
  const [value, setValue] = React.useState("0");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenLimitDetail>).detail;
      if (!detail?.limit) return;
      setLimit(detail.limit);
      setValue(String(detail.limit.maxValue ?? 0));
      setOpen(true);
    }
    window.addEventListener(OPEN_LIMIT_EDIT_MAX_VALUE_EVENT, handler);
    return () => window.removeEventListener(OPEN_LIMIT_EDIT_MAX_VALUE_EVENT, handler);
  }, []);

  async function handleSave() {
    if (!limit) return;
    if (value.trim() === "") {
      toastWarning("Max value must be a non-negative integer.");
      return;
    }
    const n = Number(value);
    if (!Number.isInteger(n) || n < 0) {
      toastWarning("Max value must be a non-negative integer.");
      return;
    }
    setSubmitting(true);
    try {
      const ok = await setLimitMaxValue(limit.name, n);
      if (ok) {
        toastSuccess(`Set max value ${n} on ${limit.name}`);
        window.dispatchEvent(new CustomEvent(LIMITS_CHANGED_EVENT));
        setOpen(false);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Edit Max Value</DialogTitle>
          <DialogDescription>
            {limit ? (
              <>Please enter the new max value for <span className="font-mono">{limit.name}</span>:</>
            ) : (
              "Please enter the new limit max value:"
            )}
          </DialogDescription>
        </DialogHeader>

        <Input
          type="number"
          min={0}
          step={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={submitting}
          autoFocus
          aria-label="Max value"
        />

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={submitting}>
            {submitting ? "Saving…" : "OK"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
