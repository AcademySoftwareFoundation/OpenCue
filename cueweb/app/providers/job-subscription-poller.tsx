"use client";
import { useEffect, useRef } from "react";
import { getJob } from "@/app/utils/get_utils";
import {
  getSubscriptions,
  markNotified,
  pickEntriesToNotify,
  removeSubscription,
} from "@/app/utils/subscription_utils";

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
            const job = await getJob(entry.jobId);
            if (job === null) {
              removeSubscription(entry.jobId);
            } else {
              fetchedStates[entry.jobId] = job.state;
            }
          }),
        );

        const toNotify = pickEntriesToNotify(getSubscriptions(), fetchedStates);
        for (const entry of toNotify) {
          if (cancelled) break;
          new Notification(entry.jobName, { body: "Job finished" });
          markNotified(entry.jobId);
        }
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
