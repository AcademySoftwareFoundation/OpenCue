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
import { useSession } from "next-auth/react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Job } from "@/app/jobs/columns";
import { addJobSubscriber } from "@/app/utils/action_utils";
import { toastWarning } from "@/app/utils/notify_utils";

/**
 * "Subscribe to Job" dialog. Mounted once at the page level and opened
 * in response to a `cueweb:open-subscribe-to-job` CustomEvent dispatched
 * from the row context menu. Decoupled this way so the menu's free-
 * function handlers can stay free of component refs.
 *
 * UI mirrors CueGUI's SubscribeToJobDialog:
 *
 *   Subscribe to jobs <jobName>
 *
 *   Job name
 *     <jobName>
 *
 *   From: <noreply address>
 *   To:   <user>@<domain>
 *
 *   [ Save ] [ Cancel ]
 *
 * Save calls the Cuebot AddSubscriber RPC via /api/job/action/addsubscriber;
 * Cuebot emails the subscriber when the job finishes. The From address is
 * informational - the actual sender is whatever Cuebot is configured with.
 *
 * Defaults are configurable at build time:
 *
 *   NEXT_PUBLIC_EMAIL_DOMAIN          - domain part of the default "To"
 *                                       address. Defaults to
 *                                       "your.domain.com".
 *   NEXT_PUBLIC_SUBSCRIBE_FROM_EMAIL  - the informational From label.
 *                                       Defaults to
 *                                       "opencue-noreply@<EMAIL_DOMAIN>".
 */

export const OPEN_SUBSCRIBE_TO_JOB_EVENT = "cueweb:open-subscribe-to-job";

export type OpenSubscribeToJobDetail = {
  job: Job;
};

const EMAIL_DOMAIN = (
  process.env.NEXT_PUBLIC_EMAIL_DOMAIN ?? "your.domain.com"
).trim();
const FROM_EMAIL = (
  process.env.NEXT_PUBLIC_SUBSCRIBE_FROM_EMAIL ??
  `opencue-noreply@${EMAIL_DOMAIN}`
).trim();

function defaultToFor(user: string): string {
  const safeUser = user?.trim() || "you";
  return `${safeUser}@${EMAIL_DOMAIN}`;
}

// RFC 5322-ish: just enough to reject obvious typos before hitting the
// backend. Cuebot does its own validation server-side.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SubscribeToJobDialog() {
  const { data: session } = useSession();
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [to, setTo] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenSubscribeToJobDetail>).detail;
      if (!detail?.job) return;
      const j = detail.job;
      // Prefer the signed-in user's email when available; otherwise fall
      // back to <sessionName-or-jobUser>@<EMAIL_DOMAIN>, matching the
      // CueGUI default of getpass.getuser()+EMAIL_DOMAIN.
      const sessionEmail = session?.user?.email?.trim();
      const userFallback = session?.user?.name?.trim() || j.user;
      setJob(j);
      setTo(sessionEmail || defaultToFor(userFallback));
      setOpen(true);
    }
    window.addEventListener(OPEN_SUBSCRIBE_TO_JOB_EVENT, handler);
    return () =>
      window.removeEventListener(OPEN_SUBSCRIBE_TO_JOB_EVENT, handler);
  }, [session?.user?.email, session?.user?.name]);

  async function handleSave() {
    if (!job) return;
    const subscriber = to.trim();
    if (!EMAIL_RE.test(subscriber)) {
      toastWarning("Enter a valid email address before saving.");
      return;
    }
    setBusy(true);
    try {
      await addJobSubscriber(job, subscriber);
      setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && setOpen(o)}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            <span className="font-mono break-all">
              Subscribe to jobs {job?.name ?? "Job"}
            </span>
          </DialogTitle>
          <DialogDescription>
            On Save the address is registered as a subscriber on Cuebot;
            you&apos;ll receive an email from Cuebot when the job finishes. The
            <span className="font-mono"> From:</span> address shown is
            informational - the real sender is whatever Cuebot is
            configured with.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-2 text-sm">
          <div>
            <div className="text-foreground/70">Job name</div>
            <div className="mt-1 rounded-md border border-input bg-foreground/[0.04] px-3 py-2 font-mono text-xs break-all">
              {job?.name ?? ""}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label
              htmlFor="subscribe-to-job-from"
              className="w-16 shrink-0 text-right text-foreground/70"
            >
              From:
            </label>
            <span
              id="subscribe-to-job-from"
              className="flex-1 rounded-md border border-input bg-foreground/[0.04] px-3 py-1.5 font-mono text-xs"
            >
              {FROM_EMAIL}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <label
              htmlFor="subscribe-to-job-to"
              className="w-16 shrink-0 text-right text-foreground/70"
            >
              To:
            </label>
            <input
              id="subscribe-to-job-to"
              type="email"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              autoFocus
              className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={busy || !to.trim()}
          >
            {busy ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
