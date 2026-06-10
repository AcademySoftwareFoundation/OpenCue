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

import { use, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { findShowByName, Show } from "@/app/utils/get_utils";
import { GroupTree } from "@/components/group-tree/group-tree";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type LoadState = "loading" | "not-found" | Show;

export default function ShowPage({
  params,
}: {
  params: Promise<{ showName: string }>;
}) {
  const { showName } = use(params);
  const decodedName = decodeURIComponent(showName);
  const [show, setShow] = useState<LoadState>("loading");
  // Bumping this remounts GroupTree to reload its groups + jobs (expand state
  // survives via the URL).
  const [reloadNonce, setReloadNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    findShowByName(decodedName).then(result => {
      if (cancelled) return;
      setShow(result ?? "not-found");
    });
    return () => { cancelled = true; };
  }, [decodedName]);

  // Use the URL name while loading so the chrome renders immediately (no collapse).
  const title = typeof show === "string" ? decodedName : show.name;
  const subtitle =
    show === "loading"
      ? "Loading…"
      : show === "not-found"
        ? "Not found"
        : show.active
          ? "Active show"
          : "Inactive show";

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <Breadcrumbs
        items={[{ label: "Shows", href: "/shows" }, { label: title }]}
        className="mb-4"
      />
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {typeof show !== "string" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setReloadNonce(n => n + 1)}
            aria-label="Refresh"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </header>

      {show === "loading" ? (
        <div className="text-sm border rounded-md divide-y">
          {[0, 1, 2, 3, 4].map(i => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-4 w-48" />
            </div>
          ))}
        </div>
      ) : show === "not-found" ? (
        <p className="text-sm text-destructive">
          Show <span className="font-mono">{decodedName}</span> not found.
        </p>
      ) : (
        <GroupTree key={reloadNonce} showId={show.id} />
      )}
    </div>
  );
}
