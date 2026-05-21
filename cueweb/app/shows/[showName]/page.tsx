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
import { findShowByName, Show } from "@/app/utils/get_utils";
import { GroupTree } from "@/components/group-tree/group-tree";

type LoadState = "loading" | "not-found" | Show;

export default function ShowPage({
  params,
}: {
  params: Promise<{ showName: string }>;
}) {
  const { showName } = use(params);
  const decodedName = decodeURIComponent(showName);
  const [show, setShow] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    findShowByName(decodedName).then(result => {
      if (cancelled) return;
      setShow(result ?? "not-found");
    });
    return () => { cancelled = true; };
  }, [decodedName]);

  if (show === "loading") {
    return <p className="p-6 text-sm text-muted-foreground">Loading show…</p>;
  }

  if (show === "not-found") {
    return (
      <p className="p-6 text-sm text-destructive">
        Show <span className="font-mono">{decodedName}</span> not found.
      </p>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold">{show.name}</h1>
        <p className="text-sm text-muted-foreground">
          {show.active ? "Active show" : "Inactive show"}
        </p>
      </header>
      <GroupTree showId={show.id} />
    </div>
  );
}
