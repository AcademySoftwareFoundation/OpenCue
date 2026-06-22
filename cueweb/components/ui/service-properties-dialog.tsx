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
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ServiceDefaultsForm } from "@/components/ui/service-defaults-form";
import { Skeleton } from "@/components/ui/skeleton";
import { Service, ServiceOverride, Show, getShowServiceOverrides } from "@/app/utils/get_utils";
import {
  createServiceOverride,
  deleteServiceOverride,
  updateServiceOverride,
} from "@/app/utils/action_utils";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";
import { cn } from "@/lib/utils";

/**
 * "Service Properties..." dialog (CueGUI ServiceDialog, show-scoped mode). The
 * left pane lists a show's service *overrides* (New / Del); the right pane is
 * the shared service form, scoped to overrides: Save creates a new override
 * (CreateServiceOverride) or updates the selected one
 * (ServiceOverrideInterface.Update), with no facility-wide confirmation.
 * Mounted once at the page level and opened via a CustomEvent carrying the Show.
 */
export const OPEN_SERVICE_PROPERTIES_EVENT = "cueweb:open-service-properties";

export type OpenServicePropertiesDetail = { show: Show };

export function ServicePropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [overrides, setOverrides] = React.useState<ServiceOverride[] | null>(null);
  const [selectedName, setSelectedName] = React.useState<string | null>(null);
  const [isNew, setIsNew] = React.useState(false);
  const [deleteOpen, setDeleteOpen] = React.useState(false);

  const selected = React.useMemo(
    () => overrides?.find((o) => o.data.name === selectedName) ?? null,
    [overrides, selectedName],
  );

  const load = React.useCallback(async (showId: string) => {
    const list = await getShowServiceOverrides(showId);
    list.sort((a, b) => a.data.name.localeCompare(b.data.name));
    setOverrides(list);
    return list;
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenServicePropertiesDetail>).detail;
      if (!detail?.show) return;
      setShow(detail.show);
      setOverrides(null);
      setSelectedName(null);
      setIsNew(false);
      setOpen(true);
      load(detail.show.id)
        .then((list) => setSelectedName(list[0]?.data.name ?? null))
        .catch((err) => handleError(err, "Could not load service overrides"));
    }
    window.addEventListener(OPEN_SERVICE_PROPERTIES_EVENT, handler);
    return () => window.removeEventListener(OPEN_SERVICE_PROPERTIES_EVENT, handler);
  }, [load]);

  function selectOverride(name: string) {
    setIsNew(false);
    setSelectedName(name);
  }

  function startNew() {
    setSelectedName(null);
    setIsNew(true);
  }

  async function handleSaved(name: string) {
    if (!show) return;
    await load(show.id);
    setIsNew(false);
    setSelectedName(name);
  }

  async function handleDeleteConfirm() {
    if (!show || !selected) return;
    const ok = await deleteServiceOverride(selected.data);
    if (!ok) throw new Error(`Failed to delete override ${selected.data.name}`);
    toastSuccess(`Deleted override ${selected.data.name}`);
    setSelectedName(null);
    setIsNew(false);
    await load(show.id);
  }

  const showForm = isNew || selected !== null;
  const sorted = overrides;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Service Properties: {show?.name ?? ""}</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-[16rem_1fr] gap-6">
          {/* Left: override list + New/Del. */}
          <div className="flex flex-col">
            <div className="min-h-[20rem] flex-1 overflow-y-auto rounded-md border">
              {sorted === null ? (
                <div className="space-y-2 p-2">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
              ) : sorted.length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">No service overrides for this show.</p>
              ) : (
                <ul className="py-1">
                  {sorted.map((o) => (
                    <li key={o.id || o.data.name}>
                      <button
                        type="button"
                        onClick={() => selectOverride(o.data.name)}
                        className={cn(
                          "w-full px-3 py-1 text-left text-sm hover:bg-muted/60",
                          !isNew && selectedName === o.data.name && "bg-muted",
                        )}
                      >
                        {o.data.name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="mt-2 flex gap-2">
              <Button type="button" variant="outline" size="sm" onClick={startNew}>
                New
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDeleteOpen(true)}
                disabled={!selected}
              >
                Del
              </Button>
            </div>
          </div>

          {/* Right: the shared service form, scoped to overrides. */}
          <div className="max-h-[70vh] overflow-y-auto pr-1">
            {showForm ? (
              <ServiceDefaultsForm
                key={isNew ? "__new__" : selectedName ?? "__none__"}
                service={isNew ? null : selected?.data ?? null}
                confirm={null}
                onPersist={(payload: Service, fresh: boolean) =>
                  fresh
                    ? show
                      ? createServiceOverride(show, payload)
                      : Promise.resolve(false)
                    : updateServiceOverride(payload)
                }
                onSaved={handleSaved}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                Select an override to edit, or click New to add one.
              </p>
            )}
          </div>
        </div>

        <ConfirmDialog
          open={deleteOpen}
          onOpenChange={setDeleteOpen}
          title="Delete service override?"
          description={selected ? `Delete the override "${selected.data.name}" for this show?` : ""}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          variant="destructive"
          onConfirm={handleDeleteConfirm}
        />
      </DialogContent>
    </Dialog>
  );
}
