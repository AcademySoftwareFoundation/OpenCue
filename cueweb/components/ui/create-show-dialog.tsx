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
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toastSuccess } from "@/app/utils/notify_utils";
import * as React from "react";

interface CreateShowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (showName: string) => void;
}

export function CreateShowDialog({ open, onOpenChange, onSuccess }: CreateShowDialogProps) {
  const [showName, setShowName] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setShowName("");
      setError(null);
    }
    onOpenChange(nextOpen);
  };

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

      await createShow(trimmed);
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
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create New Show</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col space-y-3 py-4">
            <label htmlFor="show-name" className="text-sm font-medium">
              Show name
            </label>
            <input
              id="show-name"
              type="text"
              value={showName}
              onChange={(e) => setShowName(e.target.value)}
              placeholder="Enter show name here"
              className="border rounded px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={isSubmitting}
              autoFocus
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
              Cancel
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
