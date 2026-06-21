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
import { deleteLimit } from "@/app/utils/action_utils";
import { toastSuccess } from "@/app/utils/notify_utils";
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
  LIMITS_CHANGED_EVENT,
  OPEN_LIMIT_DELETE_EVENT,
  type OpenLimitDetail,
} from "@/components/ui/limit-action-events";

/**
 * "Delete selected limits?" confirmation (CueGUI LimitsWidget parity). Mounted
 * once on the Limits page and opened by a `cueweb:open-limit-delete` event from
 * the row context menu. On confirm it calls Delete (by name) and fires
 * `cueweb:limits-changed`.
 */
export function LimitDeleteDialog() {
  const [open, setOpen] = React.useState(false);
  const [limit, setLimit] = React.useState<Limit | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenLimitDetail>).detail;
      if (!detail?.limit) return;
      setLimit(detail.limit);
      setOpen(true);
    }
    window.addEventListener(OPEN_LIMIT_DELETE_EVENT, handler);
    return () => window.removeEventListener(OPEN_LIMIT_DELETE_EVENT, handler);
  }, []);

  async function handleConfirm() {
    if (!limit) return;
    setSubmitting(true);
    try {
      const ok = await deleteLimit(limit.name);
      if (ok) {
        toastSuccess(`Deleted limit ${limit.name}`);
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
          <DialogTitle>Delete selected limit?</DialogTitle>
          <DialogDescription>This cannot be undone.</DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-muted/30 p-2 font-mono text-sm break-all">
          {limit?.name}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
