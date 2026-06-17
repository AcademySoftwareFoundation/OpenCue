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

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Group, Show, getShowRootGroup } from "@/app/utils/get_utils";
import { updateGroup } from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { GROUPS_CHANGED_EVENT } from "@/components/ui/create-group-dialog";
import {
  GroupFormFields,
  GroupFormState,
  computeGroupChanges,
  initGroupForm,
} from "@/components/ui/group-form";

/**
 * "Group Properties..." dialog (CueGUI ModifyGroupDialog parity). Edits the
 * show's root group via the shared Group form; only the fields that changed are
 * sent, each mapping to one GroupInterface setter via /api/group/action/update.
 * Mounted once at the page level and opened via a CustomEvent carrying the Show.
 */
export const OPEN_GROUP_PROPERTIES_EVENT = "cueweb:open-group-properties";

export type OpenGroupPropertiesDetail = { show: Show };

export function GroupPropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [group, setGroup] = React.useState<Group | null>(null);
  const [state, setState] = React.useState<GroupFormState | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenGroupPropertiesDetail>).detail;
      if (!detail?.show) return;
      setShow(detail.show);
      setGroup(null);
      setState(null);
      setOpen(true);
      getShowRootGroup(detail.show.id)
        .then((root) => {
          if (!root) {
            handleError(new Error("No root group"), "Could not load group");
            setOpen(false);
            return;
          }
          setGroup(root);
          setState(initGroupForm(root));
        })
        .catch((err) => {
          handleError(err, "Could not load group");
          setOpen(false);
        });
    }
    window.addEventListener(OPEN_GROUP_PROPERTIES_EVENT, handler);
    return () => window.removeEventListener(OPEN_GROUP_PROPERTIES_EVENT, handler);
  }, []);

  async function handleSave() {
    if (!group || !show || !state) return;
    const changes = computeGroupChanges(state, group);
    if (Object.keys(changes).length === 0) {
      // Give feedback rather than closing silently: nothing changed (or the
      // edited fields were left unchecked, which keeps them unset).
      toastWarning("No changes to save.");
      setOpen(false);
      return;
    }
    setSubmitting(true);
    try {
      const ok = await updateGroup(group, changes);
      if (!ok) return; // updateGroup already surfaced an error toast
      toastSuccess(`Saved group ${changes.name ?? group.name}`);
      window.dispatchEvent(new CustomEvent(GROUPS_CHANGED_EVENT, { detail: { show } }));
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Group Properties</DialogTitle>
          <DialogDescription>
            {show ? (
              <>Edit the root group of <span className="font-mono">{show.name}</span>. Check a row to set its value; leave it unchecked to keep the field unset.</>
            ) : (
              "Edit group defaults."
            )}
          </DialogDescription>
        </DialogHeader>

        {state === null ? (
          <div className="space-y-2 py-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <GroupFormFields state={state} setState={setState as React.Dispatch<React.SetStateAction<GroupFormState>>} disabled={submitting} />
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={submitting || state === null}>
            {submitting ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
