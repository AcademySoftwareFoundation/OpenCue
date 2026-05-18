"use client";
import { useEffect, useState, useCallback } from "react";
import {
  SubscriptionStore,
  addSubscription,
  getSubscriptions,
  removeSubscription,
  subscribeToChanges,
} from "./subscription_utils";

// React hook exposing the subscription store + subscribe/unsubscribe actions.
// Listens for change events from subscription_utils so updates from any source
// are reflected across all hook instances without manual coordination.
export function useJobSubscriptions() {
  const [store, setStore] = useState<SubscriptionStore>(getSubscriptions);

  useEffect(() => {
    return subscribeToChanges(() => setStore(getSubscriptions()));
  }, []);

  const subscribe = useCallback((jobId: string, jobName: string) => {
    addSubscription(jobId, jobName);
  }, []);

  const unsubscribe = useCallback((jobId: string) => {
    removeSubscription(jobId);
  }, []);

  return { store, subscribe, unsubscribe };
}
