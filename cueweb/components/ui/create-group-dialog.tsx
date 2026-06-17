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
import { Show, getShowGroups, getShowRootGroup } from "@/app/utils/get_utils";
import { createSubGroup, updateGroup } from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import {
  GroupFormFields,
  GroupFormState,
  computeGroupChanges,
  initGroupForm,
} from "@/components/ui/group-form";

/**
 * "Create Group..." dialog (CueGUI NewGroupDialog parity). Same form as Group
 * Properties, in create mode: creates a sub-group under the show's root group,
 * then applies any toggled defaults/department to the new group. Mounted once
 * at the page level and opened via a CustomEvent carrying the Show.
 */
export const OPEN_CREATE_GROUP_EVENT = "cueweb:open-create-group";
// Fired after a group is created/changed so a tree view can re-fetch.
export const GROUPS_CHANGED_EVENT = "cueweb:groups-changed";

export type OpenCreateGroupDetail = { show: Show };

export function CreateGroupDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [state, setState] = React.useState<GroupFormState>(() => initGroupForm(null));
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenCreateGroupDetail>).detail;
      if (!detail?.show) return;
      setShow(detail.show);
      setState(initGroupForm(null));
      setOpen(true);
    }
    window.addEventListener(OPEN_CREATE_GROUP_EVENT, handler);
    return () => window.removeEventListener(OPEN_CREATE_GROUP_EVENT, handler);
  }, []);

  async function handleCreate() {
    if (!show) return;
    const name = state.name.trim();
    if (name.length === 0) {
      toastWarning("Enter a group name.");
      return;
    }
    setSubmitting(true);
    try {
      const root = await getShowRootGroup(show.id);
      if (!root) {
        toastWarning("Could not resolve the show's root group.");
        return;
      }
      const ok = await createSubGroup(root, name);
      if (!ok) return; // createSubGroup already surfaced an error toast

      // Apply the department / toggled defaults to the just-created group. The
      // name is already set by CreateSubGroup, so drop it from the changes.
      const changes = computeGroupChanges(state, null);
      delete changes.name;
      if (Object.keys(changes).length > 0) {
        const created = (await getShowGroups(show.id)).find(
          (g) => g.parentId === root.id && g.name === name,
        );
        if (created) await updateGroup(created, changes);
      }

      toastSuccess(`Created group ${name}`);
      window.dispatchEvent(new CustomEvent(GROUPS_CHANGED_EVENT, { detail: { show } }));
      setOpen(false);
    } catch (err) {
      handleError(err, "Could not create group");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Group</DialogTitle>
          <DialogDescription>
            {show ? (
              <>Create a new group as a child of <span className="font-mono">{show.name}</span>. Check a row to set its value.</>
            ) : (
              "Create a new group."
            )}
          </DialogDescription>
        </DialogHeader>

        <GroupFormFields state={state} setState={setState} disabled={submitting} />

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleCreate} disabled={submitting}>
            {submitting ? "Creating…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
