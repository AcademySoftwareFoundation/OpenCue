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

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Film, RefreshCw } from "lucide-react";
import { getShows, Show } from "@/app/utils/get_utils";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { sortShows } from "./sort-shows";

export default function ShowsPage() {
  const [shows, setShows] = useState<Show[] | null>(null);
  const [loading, setLoading] = useState(false);
  const cancelledRef = useRef(false);

  const loadShows = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getShows();
      if (!cancelledRef.current) setShows(sortShows(result));
    } finally {
      if (!cancelledRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    loadShows();
    return () => { cancelledRef.current = true; };
  }, [loadShows]);

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <Breadcrumbs items={[{ label: "Shows" }]} className="mb-4" />
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Shows</h1>
          <p className="text-sm text-muted-foreground">
            Select a show to browse its groups and jobs.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadShows}
          disabled={loading}
          aria-label="Refresh"
        >
          <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
          Refresh
        </Button>
      </header>

      {shows === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map(i => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : shows.length === 0 ? (
        <EmptyState
          icon={<Film className="h-6 w-6" />}
          title="No shows"
          description="No shows are registered in this OpenCue deployment yet."
        />
      ) : (
        <ul className="text-sm border rounded-md overflow-hidden divide-y">
          {shows.map(show => (
            <li key={show.id}>
              <Link
                href={`/shows/${encodeURIComponent(show.name)}`}
                className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors"
              >
                <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="font-medium truncate">{show.name}</span>
                <span
                  className={`text-xs rounded px-1.5 py-0.5 ${
                    show.active
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {show.active ? "active" : "inactive"}
                </span>
                {show.showStats && (
                  <span className="ml-auto flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    {show.showStats.runningFrames > 0 && (
                      <span>{show.showStats.runningFrames} running</span>
                    )}
                    {show.showStats.pendingJobs > 0 && (
                      <span>{show.showStats.pendingJobs} pending</span>
                    )}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
