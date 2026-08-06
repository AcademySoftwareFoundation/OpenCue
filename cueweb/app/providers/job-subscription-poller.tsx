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

import { useEffect, useRef } from "react";
import { getJob } from "@/app/utils/get_utils";
import { toastSuccess } from "@/app/utils/notify_utils";
import {
  getSubscription,
  getSubscriptions,
  JobSubscription,
  markNotified,
  pickEntriesToNotify,
  removeSubscription,
} from "@/app/utils/subscription_utils";

const POLL_INTERVAL_MS = 15000;

// True when the page can fire a desktop / OS-level notification right
// now. Checked at fire-time (not module load) so users who flip the
// site permission in browser settings start receiving system popups on
// the next poll without a reload.
function canFireDesktopNotification(): boolean {
  return (
    typeof window !== "undefined"
    && typeof Notification !== "undefined"
    && Notification.permission === "granted"
  );
}

// Single fire path so the in-app toast always runs, with the desktop
// popup layered on top when the user has granted permission. `new
// Notification(...)` can throw in some browsers when permission is not
// granted, so the desktop attempt is wrapped in try/catch and never
// suppresses the in-app toast.
function fireCompletionNotice(entry: JobSubscription): void {
  toastSuccess(`Job finished: ${entry.jobName}`);
  if (canFireDesktopNotification()) {
    try {
      new Notification(entry.jobName, { body: "Job finished" });
    } catch {
      // Desktop popup failed (permission revoked between check and
      // fire, browser quota, etc.); the in-app toast already ran.
    }
  }
}

// Serialize the notify decision across same-origin tabs via the Web Locks
// API so only one tab fires the toast / desktop popup when several poll the
// same FINISHED job concurrently. Falls back to a direct call when
// navigator.locks is unavailable.
async function withJobNotifyLock(jobId: string, fn: () => void): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    await navigator.locks.request(`cueweb:notify-${jobId}`, { mode: "exclusive" }, async () => {
      fn();
    });
    return;
  }
  fn();
}

export function JobSubscriptionPoller() {
  const inFlight = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      if (inFlight.current) return;
      inFlight.current = true;
      try {
        const unnotified = Object.values(getSubscriptions()).filter((entry) => entry.notifiedAt === null);
        if (unnotified.length === 0) return;

        const fetchedStates: Record<string, string> = {};
        await Promise.all(
          unnotified.map(async (entry) => {
            try {
              const job = await getJob(entry.jobId);
              if (job === null) {
                removeSubscription(entry.jobId);
              } else {
                fetchedStates[entry.jobId] = job.state;
              }
            } catch (err) {
              console.error(`JobSubscriptionPoller: getJob(${entry.jobId}) failed`, err);
            }
          }),
        );

        const toNotify = pickEntriesToNotify(getSubscriptions(), fetchedStates);
        for (const entry of toNotify) {
          if (cancelled) break;
          // Hold a per-job cross-tab lock around the re-read + fire + mark
          // so sibling tabs can't both pass the notifiedAt check before
          // either persists. fireCompletionNotice runs the in-app toast
          // and (when permission was granted) the desktop popup.
          await withJobNotifyLock(entry.jobId, () => {
            const fresh = getSubscription(entry.jobId);
            if (!fresh || fresh.notifiedAt !== null) return;
            fireCompletionNotice(fresh);
            markNotified(entry.jobId);
          });
        }
      } catch (err) {
        console.error("JobSubscriptionPoller: tick failed", err);
      } finally {
        inFlight.current = false;
      }
    }

    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return null;
}
