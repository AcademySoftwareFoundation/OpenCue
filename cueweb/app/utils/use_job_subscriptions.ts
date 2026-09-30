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
