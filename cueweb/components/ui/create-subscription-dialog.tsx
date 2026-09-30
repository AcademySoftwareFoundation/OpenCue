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

import type { Allocation, Show } from "@/app/utils/get_utils";
import { getAllocations, getShows } from "@/app/utils/get_utils";
import { createShowSubscription } from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  OPEN_CREATE_SUBSCRIPTION_EVENT,
  SHOWS_CHANGED_EVENT,
  type OpenCreateSubscriptionDetail,
} from "@/components/ui/show-action-events";

/**
 * Create Subscription dialog (CueGUI SubscriptionCreator parity). Mounted once
 * on the Shows page and opened by a `cueweb:open-create-subscription` event.
 * Fields: Show (dropdown), Alloc (dropdown), Size (default 100), Burst
 * (default 110). On create it calls CreateSubscription then fires
 * `cueweb:shows-changed`.
 */

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[5rem_1fr] items-center gap-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

export function CreateSubscriptionDialog() {
  const [open, setOpen] = React.useState(false);
  const [shows, setShows] = React.useState<Show[]>([]);
  const [allocs, setAllocs] = React.useState<Allocation[]>([]);
  const [showName, setShowName] = React.useState("");
  const [allocId, setAllocId] = React.useState("");
  const [size, setSize] = React.useState("100");
  const [burst, setBurst] = React.useState("110");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenCreateSubscriptionDetail>).detail;
      setSize("100");
      setBurst("110");
      setOpen(true);
      // Load the show + allocation lists for the dropdowns.
      Promise.all([getShows(), getAllocations()])
        .then(([s, a]) => {
          setShows(s);
          setAllocs(a);
          setShowName(detail?.show?.name ?? s[0]?.name ?? "");
          setAllocId(a[0]?.id ?? "");
        })
        .catch((err) => handleError(err, "Could not load shows / allocations"));
    }
    window.addEventListener(OPEN_CREATE_SUBSCRIPTION_EVENT, handler);
    return () => window.removeEventListener(OPEN_CREATE_SUBSCRIPTION_EVENT, handler);
  }, []);

  async function handleCreate() {
    const show = shows.find((s) => s.name === showName);
    if (!show || !allocId) return;

    // Block submit on invalid input rather than coercing it to 0, which would
    // silently create a subscription with a value the user didn't intend.
    // Empty / whitespace is rejected explicitly because Number("") is 0.
    if (size.trim() === "" || burst.trim() === "") {
      toastWarning("Size and Burst must be non-negative numbers.");
      return;
    }
    const parsedSize = Number(size);
    const parsedBurst = Number(burst);
    if (
      !Number.isFinite(parsedSize) || parsedSize < 0 ||
      !Number.isFinite(parsedBurst) || parsedBurst < 0
    ) {
      toastWarning("Size and Burst must be non-negative numbers.");
      return;
    }

    setSubmitting(true);
    try {
      const ok = await createShowSubscription(show, allocId, parsedSize, parsedBurst);
      if (ok) {
        const allocName = allocs.find((a) => a.id === allocId)?.name ?? "allocation";
        toastSuccess(`Subscribed ${show.name} to ${allocName}`);
        window.dispatchEvent(new CustomEvent(SHOWS_CHANGED_EVENT));
        setOpen(false);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Subscription</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <Field label="Show">
            <select
              value={showName}
              onChange={(e) => setShowName(e.target.value)}
              disabled={submitting}
              className={SELECT_CLASS}
              aria-label="Show"
            >
              {shows.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Alloc">
            <select
              value={allocId}
              onChange={(e) => setAllocId(e.target.value)}
              disabled={submitting}
              className={SELECT_CLASS}
              aria-label="Allocation"
            >
              {allocs.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Size">
            <Input
              type="number"
              min={0}
              value={size}
              onChange={(e) => setSize(e.target.value)}
              disabled={submitting}
              aria-label="Size"
            />
          </Field>
          <Field label="Burst">
            <Input
              type="number"
              min={0}
              value={burst}
              onChange={(e) => setBurst(e.target.value)}
              disabled={submitting}
              aria-label="Burst"
            />
          </Field>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleCreate} disabled={submitting || !showName || !allocId}>
            {submitting ? "Creating…" : "OK"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
