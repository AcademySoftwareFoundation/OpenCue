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

import { Service, getDefaultServices } from "@/app/utils/get_utils";
import { deleteService } from "@/app/utils/action_utils";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ServiceDefaultsForm } from "@/components/ui/service-defaults-form";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export default function FacilityServiceDefaultsPage() {
  const [services, setServices] = React.useState<Service[] | null>(null);
  const [selectedName, setSelectedName] = React.useState<string | null>(null);
  const [isNew, setIsNew] = React.useState(false);
  const [deleteOpen, setDeleteOpen] = React.useState(false);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getDefaultServices();
      if (isCancelled?.()) return;
      setServices(data);
    } catch (err) {
      if (isCancelled?.()) return;
      handleError(err, "Could not load services");
      setServices((prev) => prev ?? []);
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    load(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load]);

  const sorted = React.useMemo(
    () => (services ? [...services].sort((a, b) => a.name.localeCompare(b.name)) : null),
    [services],
  );
  const selectedService = React.useMemo(
    () => services?.find((s) => s.name === selectedName) ?? null,
    [services, selectedName],
  );

  function selectService(name: string) {
    setIsNew(false);
    setSelectedName(name);
  }

  function startNew() {
    setSelectedName(null);
    setIsNew(true);
  }

  async function handleSaved(name: string) {
    await load();
    setIsNew(false);
    setSelectedName(name);
  }

  async function handleDeleteConfirm() {
    if (!selectedService) return;
    const ok = await deleteService(selectedService);
    if (!ok) {
      // deleteService already surfaced an error toast; throw so the
      // ConfirmDialog keeps the modal open for retry instead of dismissing as
      // if the delete had succeeded.
      throw new Error(`Failed to delete service ${selectedService.name}`);
    }
    toastSuccess(`Deleted service ${selectedService.name}`);
    setSelectedName(null);
    setIsNew(false);
    await load();
  }

  const showForm = isNew || selectedService !== null;

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Facility Service Defaults</h1>

      <div className="grid grid-cols-[18rem_1fr] gap-6">
        {/* Left pane: service list + New/Del. */}
        <div className="flex flex-col">
          <div className="min-h-[20rem] flex-1 rounded-md border">
            {sorted === null ? (
              <div className="space-y-2 p-2">
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-full" />
              </div>
            ) : sorted.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">No services defined.</p>
            ) : (
              <ul className="py-1">
                {sorted.map((s) => (
                  <li key={s.id || s.name}>
                    <button
                      type="button"
                      onClick={() => selectService(s.name)}
                      className={cn(
                        "w-full px-3 py-1 text-left text-sm hover:bg-muted/60",
                        !isNew && selectedName === s.name && "bg-muted",
                      )}
                    >
                      {s.name}
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
              disabled={!selectedService}
            >
              Del
            </Button>
          </div>
        </div>

        {/* Right pane: edit form. Keyed so it re-initializes on selection. */}
        <div>
          {showForm ? (
            <ServiceDefaultsForm
              key={isNew ? "__new__" : selectedName ?? "__none__"}
              service={isNew ? null : selectedService}
              onSaved={handleSaved}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Select a service to edit, or click New to create one.
            </p>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete service?"
        description={
          selectedService ? `Delete the facility default service "${selectedService.name}"?` : ""
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={handleDeleteConfirm}
      />
    </div>
  );
}
