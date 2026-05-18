"use client";
import { useEffect, useRef } from "react";
import { getJob } from "@/app/utils/get_utils";
import {
  getSubscription,
  getSubscriptions,
  markNotified,
  pickEntriesToNotify,
  removeSubscription,
} from "@/app/utils/subscription_utils";
import { toastSuccess } from "@/app/utils/notify_utils";

const POLL_INTERVAL_MS = 15000;

// Serialize the notify decision across same-origin tabs via the Web Locks API
// so only one tab toasts when several poll the same FINISHED job concurrently.
// Falls back to a direct call when navigator.locks is unavailable.
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
          // Hold a per-job cross-tab lock around the re-read + toast + mark so
          // sibling tabs can't both pass the notifiedAt check before either persists.
          await withJobNotifyLock(entry.jobId, () => {
            const fresh = getSubscription(entry.jobId);
            if (!fresh || fresh.notifiedAt !== null) return;
            toastSuccess(`Job finished: ${entry.jobName}`);
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
