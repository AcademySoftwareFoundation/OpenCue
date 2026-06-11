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

import { createShow, findShow, isValidShowName } from "@/app/utils/show_utils";
import { createShowSubscription } from "@/app/utils/action_utils";
import { getAllocations, type Allocation } from "@/app/utils/get_utils";
import { toastSuccess } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import * as React from "react";

interface CreateShowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (showName: string) => void;
}

type SubRow = { enabled: boolean; size: string; burst: string };

export function CreateShowDialog({ open, onOpenChange, onSuccess }: CreateShowDialogProps) {
  const [showName, setShowName] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [allocs, setAllocs] = React.useState<Allocation[]>([]);
  const [subs, setSubs] = React.useState<Record<string, SubRow>>({});

  // Load the allocations for the Subscriptions section when the dialog opens
  // (mirrors CueGUI's CreateShowDialog, which lists every allocation).
  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    getAllocations()
      .then((list) => {
        if (cancelled) return;
        setAllocs(list);
        setSubs((prev) => {
          const next = { ...prev };
          for (const a of list) {
            if (!next[a.id]) next[a.id] = { enabled: false, size: "100", burst: "100" };
          }
          return next;
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setShowName("");
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  const updateSub = (id: string, patch: Partial<SubRow>) =>
    setSubs((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmed = showName.trim();
    if (!trimmed) {
      setError("Please enter a valid show name.");
      return;
    }

    if (!isValidShowName(trimmed)) {
      setError("Show names must be alphanumeric only (no spaces, dashes, or punctuation).");
      return;
    }

    setIsSubmitting(true);
    try {
      const existing = await findShow(trimmed);
      if (existing) {
        setError("A show with that name already exists, please enter a unique show name.");
        return;
      }

      const created = await createShow(trimmed);

      // Create a subscription on each checked allocation (CueGUI parity).
      for (const a of allocs) {
        const row = subs[a.id];
        if (row?.enabled) {
          await createShowSubscription(
            created,
            a.id,
            Number.parseFloat(row.size) || 0,
            Number.parseFloat(row.burst) || 0,
          );
        }
      }

      toastSuccess(`Show "${trimmed}" created successfully.`);
      handleOpenChange(false);
      onSuccess?.(trimmed);
    } catch (err) {
      setError((err as Error).message || "Failed to create show.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create New Show</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col space-y-4 py-4">
            <div className="grid grid-cols-[6rem_1fr] items-center gap-3">
              <label htmlFor="show-name" className="text-sm font-medium">
                Show name
              </label>
              <input
                id="show-name"
                type="text"
                value={showName}
                onChange={(e) => setShowName(e.target.value)}
                placeholder="Enter show name here"
                className="rounded border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={isSubmitting}
                autoFocus
              />
            </div>

            {allocs.length > 0 && (
              <fieldset className="rounded-md border p-3">
                <legend className="px-1 text-sm font-medium">Subscriptions</legend>
                <div className="grid grid-cols-[1fr_5rem_5rem] items-center gap-x-3 gap-y-2">
                  <span className="text-xs text-muted-foreground">Allocation</span>
                  <span className="text-xs text-muted-foreground">Size</span>
                  <span className="text-xs text-muted-foreground">Burst</span>
                  {allocs.map((a) => {
                    const row = subs[a.id] ?? { enabled: false, size: "100", burst: "100" };
                    return (
                      <React.Fragment key={a.id}>
                        <label className="flex items-center gap-2 text-sm">
                          <Checkbox
                            checked={row.enabled}
                            onCheckedChange={(v) => updateSub(a.id, { enabled: !!v })}
                            disabled={isSubmitting}
                          />
                          <span className="truncate">{a.name}</span>
                        </label>
                        <Input
                          type="number"
                          min={0}
                          value={row.size}
                          onChange={(e) => updateSub(a.id, { size: e.target.value })}
                          disabled={isSubmitting || !row.enabled}
                          className="h-8"
                          aria-label={`${a.name} size`}
                        />
                        <Input
                          type="number"
                          min={0}
                          value={row.burst}
                          onChange={(e) => updateSub(a.id, { burst: e.target.value })}
                          disabled={isSubmitting || !row.enabled}
                          className="h-8"
                          aria-label={`${a.name} burst`}
                        />
                      </React.Fragment>
                    );
                  })}
                </div>
              </fieldset>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
              Close
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
