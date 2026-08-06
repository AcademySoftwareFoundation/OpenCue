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

import { createLimit } from "@/app/utils/action_utils";
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
import { LIMITS_CHANGED_EVENT } from "@/components/ui/limit-action-events";

interface LimitAddDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Add Limit" dialog (CueGUI LimitsWidget parity). Opened from the Limits page
 * header button. Asks for a name; the new limit is created with max value 0
 * (matching CueGUI, which then lets you Edit Max Value). Fires
 * `cueweb:limits-changed` on success.
 */
export function LimitAddDialog({ open, onOpenChange }: LimitAddDialogProps) {
  const [name, setName] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const handleOpenChange = (next: boolean) => {
    if (!next) setName("");
    onOpenChange(next);
  };

  async function handleCreate() {
    const trimmed = name.trim();
    if (trimmed.length === 0) {
      toastWarning("Enter a name for the new limit.");
      return;
    }
    setSubmitting(true);
    try {
      const ok = await createLimit(trimmed, 0);
      if (ok) {
        toastSuccess(`Created limit ${trimmed}`);
        window.dispatchEvent(new CustomEvent(LIMITS_CHANGED_EVENT));
        handleOpenChange(false);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : handleOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Add Limit</DialogTitle>
          <DialogDescription>Enter a name for the new limit.</DialogDescription>
        </DialogHeader>

        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={submitting}
          autoFocus
          aria-label="Limit name"
        />

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleCreate} disabled={submitting}>
            {submitting ? "Creating…" : "OK"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
