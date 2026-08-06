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

import { Show, getShows } from "@/app/utils/get_utils";
import {
  WidgetCard,
  WidgetCardError,
  WidgetCardSkeleton,
} from "@/components/dashboard/widget-card";
import { Film } from "lucide-react";
import * as React from "react";

const REFRESH_MS = 60000;

export function ShowsWidget() {
  const [shows, setShows] = React.useState<Show[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getShows();
        if (!cancelled) {
          setShows(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (shows === null && !error) {
    return <WidgetCardSkeleton title="Shows" />;
  }
  if (shows === null && error) {
    return (
      <WidgetCardError
        title="Shows"
        href="/shows"
        message="Could not load shows from Cuebot."
      />
    );
  }

  const list = shows ?? [];
  const active = list.filter((s) => s.active).length;
  const totalPendingJobs = list.reduce(
    (acc, s) => acc + (s.showStats?.pendingJobs ?? 0),
    0,
  );

  // Top 3 shows by running frames - mirrors the "busiest shows" feel of the
  // ShowMonitor plugin in CueGUI.
  const top = [...list]
    .sort(
      (a, b) =>
        (b.showStats?.runningFrames ?? 0) - (a.showStats?.runningFrames ?? 0),
    )
    .slice(0, 3)
    .filter((s) => (s.showStats?.runningFrames ?? 0) > 0);

  return (
    <WidgetCard
      title="Shows"
      icon={<Film className="h-4 w-4" />}
      value={`${active} / ${list.length}`}
      subLabel={`${active} active - ${totalPendingJobs} pending jobs`}
      footer={
        top.length === 0 ? (
          list.length === 0 ? (
            "No shows configured."
          ) : (
            "No running frames across all shows."
          )
        ) : (
          <ul className="space-y-1">
            {top.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-2">
                <span className="truncate" title={s.name}>
                  {s.name}
                </span>
                <span className="tabular-nums">
                  {s.showStats?.runningFrames ?? 0}
                </span>
              </li>
            ))}
          </ul>
        )
      }
      href="/shows"
      ctaLabel="View shows"
    />
  );
}
