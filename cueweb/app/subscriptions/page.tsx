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

import { Show, Subscription, getActiveShows, getShowSubscriptions } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { subscriptionColumns } from "@/app/subscriptions/subscription-columns";
import { Button } from "@/components/ui/button";
import { CreateSubscriptionDialog } from "@/components/ui/create-subscription-dialog";
import {
  OPEN_CREATE_SUBSCRIPTION_EVENT,
  OPEN_SHOW_PROPERTIES_EVENT,
  SHOWS_CHANGED_EVENT,
} from "@/components/ui/show-action-events";
import { ShowPropertiesDialog } from "@/components/ui/show-properties-dialog";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Skeleton } from "@/components/ui/skeleton";
import { SUBSCRIPTIONS_CHANGED_EVENT } from "@/components/ui/subscription-action-events";
import { SubscriptionDialogs } from "@/components/ui/subscription-dialogs";

const REFRESH_MS = 30000;
const SELECTED_SHOW_KEY = "cueweb.subscriptions.show";

const SELECT_CLASS =
  "h-9 w-72 max-w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

export default function SubscriptionsPage() {
  const [shows, setShows] = React.useState<Show[] | null>(null);
  const [showName, setShowName] = React.useState<string>("");
  const [subs, setSubs] = React.useState<Subscription[] | null>(null);

  // The full Show object backing the current selection (needed by the Show
  // Properties / Add Subscription dialogs).
  const selectedShow = React.useMemo(
    () => shows?.find((s) => s.name === showName) ?? null,
    [shows, showName],
  );

  // Load the active-show list for the dropdown (CueGUI uses getActiveShows).
  // Restore the last-selected show from localStorage if it is still active.
  React.useEffect(() => {
    let cancelled = false;
    getActiveShows()
      .then((data) => {
        if (cancelled) return;
        setShows(data);
        const stored =
          typeof window !== "undefined" ? window.localStorage.getItem(SELECTED_SHOW_KEY) : null;
        if (stored && data.some((s) => s.name === stored)) {
          setShowName(stored);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        handleError(err, "Could not load shows");
        setShows([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSubs = React.useCallback(
    async (show: Show | null, isCancelled?: () => boolean) => {
      if (!show) {
        setSubs(null);
        return;
      }
      try {
        const data = await getShowSubscriptions(show);
        if (isCancelled?.()) return;
        setSubs(data);
      } catch (err) {
        if (isCancelled?.()) return;
        handleError(err, "Could not load subscriptions");
        setSubs((prev) => prev ?? []);
      }
    },
    [],
  );

  // (Re)load the selected show's subscriptions, polling on an interval. Also
  // re-fetch when a subscription or show changes (size/burst edited, deleted,
  // or a new subscription created).
  React.useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;
    // Reset to the skeleton state on show change so we don't flash the prior
    // show's rows while the new show's subscriptions load.
    setSubs(null);
    loadSubs(selectedShow, isCancelled);
    const interval = setInterval(() => loadSubs(selectedShow, isCancelled), REFRESH_MS);
    const handler = () => loadSubs(selectedShow);
    window.addEventListener(SUBSCRIPTIONS_CHANGED_EVENT, handler);
    window.addEventListener(SHOWS_CHANGED_EVENT, handler);
    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener(SUBSCRIPTIONS_CHANGED_EVENT, handler);
      window.removeEventListener(SHOWS_CHANGED_EVENT, handler);
    };
  }, [selectedShow, loadSubs]);

  function handleSelectShow(name: string) {
    setShowName(name);
    if (typeof window !== "undefined") {
      if (name) window.localStorage.setItem(SELECTED_SHOW_KEY, name);
      else window.localStorage.removeItem(SELECTED_SHOW_KEY);
    }
  }

  function openShowProperties() {
    if (!selectedShow) return;
    window.dispatchEvent(
      new CustomEvent(OPEN_SHOW_PROPERTIES_EVENT, { detail: { show: selectedShow } }),
    );
  }

  function openAddSubscription() {
    if (!selectedShow) return;
    window.dispatchEvent(
      new CustomEvent(OPEN_CREATE_SUBSCRIPTION_EVENT, { detail: { show: selectedShow } }),
    );
  }

  const sortedShowNames = React.useMemo(
    () => (shows ?? []).map((s) => s.name).sort((a, b) => a.localeCompare(b)),
    [shows],
  );

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Subscriptions</h1>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <select
          value={showName}
          onChange={(e) => handleSelectShow(e.target.value)}
          disabled={shows === null}
          className={SELECT_CLASS}
          aria-label="Select Show"
        >
          <option value="">Select Show:</option>
          {sortedShowNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={openShowProperties} disabled={!selectedShow}>
            Show Properties
          </Button>
          <Button onClick={openAddSubscription} disabled={!selectedShow}>
            Add Subscription
          </Button>
        </div>
      </div>

      {!selectedShow ? (
        <p className="text-sm text-muted-foreground">
          Select a show to view its subscriptions.
        </p>
      ) : subs === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <SimpleDataTable
          columns={subscriptionColumns}
          data={subs}
          username=""
          isSubscriptionsTable
          columnVisibilityStorageKey="cueweb.subscriptions.columnVisibility"
        />
      )}

      {/* Dialogs opened via CustomEvents (Show Properties + Add Subscription are
          reused from the Shows window; the edit/delete dialogs are
          subscription-specific). */}
      <ShowPropertiesDialog />
      <CreateSubscriptionDialog />
      <SubscriptionDialogs />
    </div>
  );
}
