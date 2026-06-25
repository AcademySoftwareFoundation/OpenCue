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

import type { Show } from "@/app/utils/get_utils";
import {
  enableShowBooking,
  enableShowDispatching,
  setShowCommentEmail,
  setShowDefaultMaxCores,
  setShowDefaultMinCores,
} from "@/app/utils/action_utils";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  OPEN_SHOW_PROPERTIES_EVENT,
  SHOWS_CHANGED_EVENT,
  type OpenShowPropertiesDetail,
} from "@/components/ui/show-action-events";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

/**
 * Show Properties dialog (CueGUI ShowDialog parity). Mounted once on the Shows
 * page and opened by a `cueweb:open-show-properties` CustomEvent from the row
 * context menu. Four tabs:
 *   - Settings: default max/min cores, comment notification email.
 *   - Booking: enable booking, enable dispatch.
 *   - Statistics: read-only show_stats counts.
 *   - Raw Show Data: read-only dump of the show object.
 * Save calls only the setters whose value changed (mirroring CueGUI), then
 * fires `cueweb:shows-changed` so the table refreshes.
 */

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums">{value ?? "-"}</span>
    </div>
  );
}

export function ShowPropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [show, setShow] = React.useState<Show | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  // Editable form state, hydrated from the show when the dialog opens.
  const [maxCores, setMaxCores] = React.useState("0");
  const [minCores, setMinCores] = React.useState("0");
  const [email, setEmail] = React.useState("");
  const [booking, setBooking] = React.useState(true);
  const [dispatch, setDispatch] = React.useState(true);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenShowPropertiesDetail>).detail;
      if (!detail?.show) return;
      const s = detail.show;
      setShow(s);
      setMaxCores(String(s.defaultMaxCores ?? 0));
      setMinCores(String(s.defaultMinCores ?? 0));
      setEmail(s.commentEmail ?? "");
      setBooking(s.bookingEnabled ?? true);
      setDispatch(s.dispatchEnabled ?? true);
      setOpen(true);
    }
    window.addEventListener(OPEN_SHOW_PROPERTIES_EVENT, handler);
    return () => window.removeEventListener(OPEN_SHOW_PROPERTIES_EVENT, handler);
  }, []);

  async function handleSave() {
    if (!show) return;

    // Validate the core inputs before saving anything. Reject invalid input
    // explicitly rather than silently skipping those fields, which would apply
    // a partial save while the user believes everything was saved.
    // Reject blank input explicitly: Number("") and Number("  ") are 0, which
    // would otherwise pass the finite/non-negative checks below as a valid 0.
    if (maxCores.trim() === "" || minCores.trim() === "") {
      toastWarning("Default cores must be non-negative numbers.");
      return;
    }
    const nextMax = Number(maxCores);
    const nextMin = Number(minCores);
    if (!Number.isFinite(nextMax) || nextMax < 0 || !Number.isFinite(nextMin) || nextMin < 0) {
      toastWarning("Default cores must be non-negative numbers.");
      return;
    }
    if (nextMin > nextMax) {
      toastWarning("Default minimum cores cannot exceed default maximum cores.");
      return;
    }

    setSubmitting(true);
    try {
      const tasks: Promise<boolean>[] = [];

      if (nextMax !== (show.defaultMaxCores ?? 0)) {
        tasks.push(setShowDefaultMaxCores(show, nextMax));
      }
      if (nextMin !== (show.defaultMinCores ?? 0)) {
        tasks.push(setShowDefaultMinCores(show, nextMin));
      }
      if (email !== (show.commentEmail ?? "")) {
        tasks.push(setShowCommentEmail(show, email));
      }
      if (booking !== (show.bookingEnabled ?? true)) {
        tasks.push(enableShowBooking(show, booking));
      }
      if (dispatch !== (show.dispatchEnabled ?? true)) {
        tasks.push(enableShowDispatching(show, dispatch));
      }

      if (tasks.length === 0) {
        toastWarning("No changes to save.");
        setOpen(false);
        return;
      }

      const results = await Promise.all(tasks);
      if (results.every(Boolean)) {
        toastSuccess(`Saved ${show.name} properties`);
        window.dispatchEvent(new CustomEvent(SHOWS_CHANGED_EVENT));
        setOpen(false);
      }
      // On partial failure accessActionApi has already toasted the error(s);
      // the dialog stays open so the user can retry.
    } finally {
      setSubmitting(false);
    }
  }

  const stats = show?.showStats;

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{show ? `${show.name} Properties` : "Show Properties"}</DialogTitle>
          <DialogDescription className="sr-only">
            Edit show settings, booking, and view statistics.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="settings">
          <TabsList className="grid grid-cols-4">
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="booking">Booking</TabsTrigger>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="raw">Raw Show Data</TabsTrigger>
          </TabsList>

          <TabsContent value="settings" className="space-y-4 py-3">
            <div className="grid grid-cols-[1fr_auto] items-center gap-3">
              <Input
                type="number"
                min={0}
                step="1"
                value={maxCores}
                onChange={(e) => setMaxCores(e.target.value)}
                disabled={submitting}
                aria-label="Default maximum cores"
              />
              <Label className="text-sm font-normal">Default maximum cores</Label>
              <Input
                type="number"
                min={0}
                step="1"
                value={minCores}
                onChange={(e) => setMinCores(e.target.value)}
                disabled={submitting}
                aria-label="Default minimum cores"
              />
              <Label className="text-sm font-normal">Default minimum cores</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
                placeholder="comments@example.com"
                aria-label="Comment Notification Email"
              />
              <Label className="text-sm font-normal">Comment Notification Email</Label>
            </div>
          </TabsContent>

          <TabsContent value="booking" className="space-y-3 py-3">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={booking}
                onCheckedChange={(v) => setBooking(!!v)}
                disabled={submitting}
              />
              Enable booking
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={dispatch}
                onCheckedChange={(v) => setDispatch(!!v)}
                disabled={submitting}
              />
              Enable dispatch
            </label>
          </TabsContent>

          <TabsContent value="statistics" className="py-3">
            <div className="rounded-md border p-3">
              <StatRow label="Running frames" value={stats?.runningFrames} />
              <StatRow label="Pending frames" value={stats?.pendingFrames} />
              <StatRow label="Dead frames" value={stats?.deadFrames} />
              <StatRow label="Pending jobs" value={stats?.pendingJobs} />
              <StatRow label="Reserved cores" value={stats?.reservedCores?.toFixed(2)} />
              <StatRow label="Reserved GPUs" value={stats?.reservedGpus?.toFixed(2)} />
              <StatRow label="Created jobs" value={stats?.createdJobCount} />
              <StatRow label="Created frames" value={stats?.createdFrameCount} />
              <StatRow label="Rendered frames" value={stats?.renderedFrameCount} />
              <StatRow label="Failed frames" value={stats?.failedFrameCount} />
            </div>
          </TabsContent>

          <TabsContent value="raw" className="py-3">
            <pre className="max-h-64 overflow-auto rounded-md border bg-muted/30 p-3 text-xs">
              {show ? JSON.stringify(show, null, 2) : ""}
            </pre>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Close
          </Button>
          <Button type="button" onClick={handleSave} disabled={submitting}>
            {submitting ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
