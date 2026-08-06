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

import type { Subscription } from "@/app/utils/get_utils";
import {
  deleteSubscription,
  setSubscriptionBurst,
  setSubscriptionSize,
} from "@/app/utils/action_utils";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";
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
  OPEN_DELETE_SUBSCRIPTION_EVENT,
  OPEN_EDIT_SUBSCRIPTION_BURST_EVENT,
  OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT,
  SUBSCRIPTIONS_CHANGED_EVENT,
  type OpenSubscriptionDetail,
} from "@/components/ui/subscription-action-events";

/**
 * Subscription dialogs (CueGUI SubscriptionActions parity). Mounted once on the
 * Subscriptions page and opened by the `cueweb:open-edit-subscription-size`,
 * `cueweb:open-edit-subscription-burst`, and `cueweb:open-delete-subscription`
 * events from the row context menu. Each fires `cueweb:subscriptions-changed`
 * on success so the page re-fetches.
 *
 * Size / burst are stored as centcores (cores * 100): the table divides by 100
 * for display, so these dialogs show cores and multiply back by 100 before
 * sending, matching CueGUI's int(value * 100.0).
 */

function notifyChanged() {
  window.dispatchEvent(new CustomEvent(SUBSCRIPTIONS_CHANGED_EVENT));
}

// Parse a cores value from a text input. Returns null on empty / invalid /
// negative so callers can reject rather than silently coerce to 0.
function parseCores(text: string): number | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  if (!Number.isFinite(n) || n < 0) return null;
  return n;
}

// Edit Subscription Size - mirrors CueGUI editSize: an input prefilled with the
// current size (cores), the administrator advisory, then a billing
// confirmation step before the value is committed.
function EditSizeDialog() {
  const [open, setOpen] = React.useState(false);
  const [sub, setSub] = React.useState<Subscription | null>(null);
  const [value, setValue] = React.useState("");
  const [confirming, setConfirming] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const { subscription } = (e as CustomEvent<OpenSubscriptionDetail>).detail;
      setSub(subscription);
      setValue(String(subscription.size / 100));
      setConfirming(false);
      setOpen(true);
    }
    window.addEventListener(OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT, handler);
    return () => window.removeEventListener(OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT, handler);
  }, []);

  function handleProceed() {
    if (parseCores(value) === null) {
      toastWarning("Size must be a non-negative number.");
      return;
    }
    setConfirming(true);
  }

  async function handleConfirm() {
    if (!sub) return;
    const cores = parseCores(value);
    if (cores === null) return;
    setSubmitting(true);
    try {
      const ok = await setSubscriptionSize(sub, Math.round(cores * 100));
      if (ok) {
        toastSuccess(`Set size on ${sub.name} to ${cores}`);
        notifyChanged();
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
          <DialogTitle>Edit Subscription Size</DialogTitle>
        </DialogHeader>

        {confirming ? (
          <p className="py-2 text-sm">
            You are about to modify a number that can affect a show&apos;s billing. Are you sure you
            want to do this?
          </p>
        ) : (
          <div className="space-y-3 py-2">
            <p className="whitespace-pre-line text-sm text-muted-foreground">
              {"Please enter the new subscription size value:\nThis should only be changed by administrators.\nPlease contact the resource department."}
            </p>
            <Input
              type="number"
              min={0}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              aria-label="Size"
              autoFocus
            />
          </div>
        )}

        <DialogFooter>
          {confirming ? (
            <>
              <Button type="button" variant="outline" onClick={() => setConfirming(false)} disabled={submitting}>
                No
              </Button>
              <Button type="button" onClick={handleConfirm} disabled={submitting}>
                {submitting ? "Saving…" : "Yes"}
              </Button>
            </>
          ) : (
            <>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="button" onClick={handleProceed}>
                OK
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Edit Subscription Burst - mirrors CueGUI editBurst: a single input prefilled
// with the current burst (cores), no billing confirmation.
function EditBurstDialog() {
  const [open, setOpen] = React.useState(false);
  const [sub, setSub] = React.useState<Subscription | null>(null);
  const [value, setValue] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const { subscription } = (e as CustomEvent<OpenSubscriptionDetail>).detail;
      setSub(subscription);
      setValue(String(subscription.burst / 100));
      setOpen(true);
    }
    window.addEventListener(OPEN_EDIT_SUBSCRIPTION_BURST_EVENT, handler);
    return () => window.removeEventListener(OPEN_EDIT_SUBSCRIPTION_BURST_EVENT, handler);
  }, []);

  async function handleSave() {
    if (!sub) return;
    const cores = parseCores(value);
    if (cores === null) {
      toastWarning("Burst must be a non-negative number.");
      return;
    }
    setSubmitting(true);
    try {
      const ok = await setSubscriptionBurst(sub, Math.round(cores * 100));
      if (ok) {
        toastSuccess(`Set burst on ${sub.name} to ${cores}`);
        notifyChanged();
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
          <DialogTitle>Edit Subscription Burst</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <p className="text-sm text-muted-foreground">
            Please enter the maximum number of cores that this subscription should be allowed to
            reach:
          </p>
          <Input
            type="number"
            min={0}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={submitting}
            aria-label="Burst"
            autoFocus
          />
        </div>

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

// Delete Subscription - mirrors CueGUI delete: a confirmation listing the
// subscription name.
function DeleteSubscriptionDialog() {
  const [open, setOpen] = React.useState(false);
  const [sub, setSub] = React.useState<Subscription | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const { subscription } = (e as CustomEvent<OpenSubscriptionDetail>).detail;
      setSub(subscription);
      setOpen(true);
    }
    window.addEventListener(OPEN_DELETE_SUBSCRIPTION_EVENT, handler);
    return () => window.removeEventListener(OPEN_DELETE_SUBSCRIPTION_EVENT, handler);
  }, []);

  async function handleDelete() {
    if (!sub) return;
    setSubmitting(true);
    try {
      const ok = await deleteSubscription(sub);
      if (ok) {
        toastSuccess(`Deleted subscription ${sub.name}`);
        notifyChanged();
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
          <DialogTitle>Delete Subscriptions?</DialogTitle>
        </DialogHeader>

        <div className="space-y-2 py-2">
          <p className="text-sm">Are you sure you want to delete these subscriptions?</p>
          {sub ? (
            <p className="rounded-md border bg-muted/40 px-3 py-2 font-mono text-sm">{sub.name}</p>
          ) : null}
        </div>

        <DialogFooter>
          <Button type="button" onClick={handleDelete} disabled={submitting}>
            {submitting ? "Deleting…" : "Ok"}
          </Button>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mounts all three subscription dialogs. Place once on the Subscriptions page.
export function SubscriptionDialogs() {
  return (
    <>
      <EditSizeDialog />
      <EditBurstDialog />
      <DeleteSubscriptionDialog />
    </>
  );
}
