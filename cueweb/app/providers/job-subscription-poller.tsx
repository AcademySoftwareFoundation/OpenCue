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
          // Re-read just before firing so a sibling tab that already marked
          // this entry notified doesn't cause a duplicate toast.
          const fresh = getSubscription(entry.jobId);
          if (!fresh || fresh.notifiedAt !== null) continue;
          toastSuccess(`Job finished: ${entry.jobName}`);
          markNotified(entry.jobId);
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
