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

import * as React from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useEnabledPlugins } from "@/app/utils/use_plugin_menu";
import { cn } from "@/lib/utils";
import type { PluginManifest } from "@/lib/plugins";

/** Plugins shown per page. */
const PAGE_SIZE = 6;

/**
 * Searchable, paginated grid of registered plugins. The registry is static and
 * small, so filtering and paging happen client-side over the manifests passed
 * in by the server page.
 */
export function PluginsBrowser({ plugins }: { plugins: PluginManifest[] }) {
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(0);
  const { enabled, setEnabled } = useEnabledPlugins();

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return plugins;
    return plugins.filter((plugin) =>
      [plugin.title, plugin.name, plugin.route, plugin.description ?? ""].some((field) =>
        field.toLowerCase().includes(q),
      ),
    );
  }, [plugins, query]);

  // Reset to the first page whenever the search narrows/changes the results.
  React.useEffect(() => {
    setPage(0);
  }, [query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const start = currentPage * PAGE_SIZE;
  const visible = filtered.slice(start, start + PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search plugins…"
          aria-label="Search plugins"
          className="pl-9 pr-9"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No plugins match <span className="font-medium">&ldquo;{query}&rdquo;</span>.
        </p>
      ) : (
        <>
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {visible.map((manifest) => (
              <li
                key={manifest.name}
                className="flex h-full flex-col rounded-lg border bg-card p-4 text-card-foreground shadow-sm"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <Link
                    href={manifest.route}
                    className="rounded font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {manifest.title}
                  </Link>
                  <span className="font-mono text-xs text-muted-foreground">
                    v{manifest.version}
                  </span>
                </div>
                {manifest.description && (
                  <p className="mt-1 text-sm text-muted-foreground">{manifest.description}</p>
                )}
                <Link
                  href={manifest.route}
                  className="mt-2 block w-fit rounded font-mono text-xs text-muted-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {manifest.route}
                </Link>
                <label className="mt-3 flex cursor-pointer items-center gap-2 border-t pt-3 text-sm">
                  <Checkbox
                    checked={enabled.has(manifest.name)}
                    onCheckedChange={(checked) => setEnabled(manifest.name, checked === true)}
                    aria-label={`Show ${manifest.title} in the Plugins menu`}
                  />
                  <span className="text-muted-foreground">Show in Plugins menu</span>
                </label>
              </li>
            ))}
          </ul>

          <div className="flex items-center justify-between gap-4 pt-1">
            <p className="text-xs text-muted-foreground">
              {filtered.length === plugins.length
                ? `${filtered.length} plugin${filtered.length === 1 ? "" : "s"}`
                : `${filtered.length} of ${plugins.length} plugins`}
            </p>

            {pageCount > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={currentPage === 0}
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                </Button>
                <span className={cn("text-xs tabular-nums text-muted-foreground")}>
                  Page {currentPage + 1} of {pageCount}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={currentPage >= pageCount - 1}
                  aria-label="Next page"
                >
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
