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
import { ChevronDown } from "lucide-react";

import {
  Show,
  Subscription,
  getActiveShows,
  getAllocations,
  getShowSubscriptions,
} from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { CreateSubscriptionDialog } from "@/components/ui/create-subscription-dialog";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  OPEN_CREATE_SUBSCRIPTION_EVENT,
  SHOWS_CHANGED_EVENT,
} from "@/components/ui/show-action-events";
import {
  OPEN_DELETE_SUBSCRIPTION_EVENT,
  OPEN_EDIT_SUBSCRIPTION_BURST_EVENT,
  OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT,
  SUBSCRIPTIONS_CHANGED_EVENT,
} from "@/components/ui/subscription-action-events";
import { ShowSubscriptionGraph } from "@/components/ui/subscription-graph";
import { SubscriptionDialogs } from "@/components/ui/subscription-dialogs";

const REFRESH_MS = 15000;
const SELECTED_SHOWS_KEY = "cueweb.subscription-graphs.shows";

// A subscription-row right-click carries the sub; an empty-area / empty-show
// right-click has no sub and only offers "Add new subscription".
type MenuState = { x: number; y: number; sub: Subscription | null; showName: string };

export default function SubscriptionGraphsPage() {
  const [shows, setShows] = React.useState<Show[] | null>(null);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [subs, setSubs] = React.useState<Record<string, Subscription[] | null>>({});
  const [allocCores, setAllocCores] = React.useState<Record<string, number>>({});
  const [menu, setMenu] = React.useState<MenuState | null>(null);

  // Allocation core totals (allocationName -> cores) back the bar scaling: each
  // subscription bar is drawn relative to its allocation's full capacity, like
  // CueGUI. Allocations are global, so poll them independently of the shows.
  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const allocs = await getAllocations();
        if (cancelled) return;
        const map: Record<string, number> = {};
        for (const a of allocs) map[a.name] = a.stats?.cores ?? 0;
        setAllocCores(map);
      } catch {
        // Non-fatal: bars fall back to size/burst scaling without alloc totals.
      }
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Load the active-show list for the dropdown, then restore any previously
  // selected shows that are still active.
  React.useEffect(() => {
    let cancelled = false;
    getActiveShows()
      .then((data) => {
        if (cancelled) return;
        setShows(data);
        const stored = typeof window !== "undefined" ? window.localStorage.getItem(SELECTED_SHOWS_KEY) : null;
        if (stored) {
          try {
            const names: string[] = JSON.parse(stored);
            setSelected(names.filter((n) => data.some((s) => s.name === n)));
          } catch {
            // Ignore a corrupt stored value.
          }
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

  const persistSelected = React.useCallback((names: string[]) => {
    setSelected(names);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SELECTED_SHOWS_KEY, JSON.stringify(names));
    }
  }, []);

  const loadSubs = React.useCallback(
    async (showNames: string[], showList: Show[], isCancelled?: () => boolean) => {
      const results = await Promise.all(
        showNames.map(async (name) => {
          const show = showList.find((s) => s.name === name);
          if (!show) return [name, [] as Subscription[]] as const;
          try {
            return [name, await getShowSubscriptions(show)] as const;
          } catch {
            // getShowSubscriptions already toasts; treat as empty for this show.
            return [name, [] as Subscription[]] as const;
          }
        }),
      );
      if (isCancelled?.()) return;
      setSubs((prev) => {
        const next: Record<string, Subscription[] | null> = {};
        for (const name of showNames) next[name] = prev[name] ?? null;
        for (const [name, list] of results) next[name] = list;
        return next;
      });
    },
    [],
  );

  // Fetch the selected shows' subscriptions, polling on an interval and
  // re-fetching when a subscription or show changes elsewhere.
  React.useEffect(() => {
    if (!shows) return;
    let cancelled = false;
    const isCancelled = () => cancelled;
    // Seed loading skeletons for newly-selected shows; drop deselected ones.
    setSubs((prev) => {
      const next: Record<string, Subscription[] | null> = {};
      for (const name of selected) next[name] = name in prev ? prev[name] : null;
      return next;
    });
    loadSubs(selected, shows, isCancelled);
    const interval = setInterval(() => loadSubs(selected, shows, isCancelled), REFRESH_MS);
    // A subscription change only affects the rows for the shows already loaded.
    const refreshSubscriptions = () => loadSubs(selected, shows, isCancelled);
    // A show change can add/remove/rename shows, so re-fetch the active-show
    // list, drop any selected show that no longer exists, and reload against
    // the fresh snapshot (otherwise the dropdown and per-show lookups go stale).
    const refreshShows = async () => {
      try {
        const nextShows = await getActiveShows();
        if (isCancelled()) return;
        setShows(nextShows);
        const activeNames = new Set(nextShows.map((s) => s.name));
        const nextSelected = selected.filter((name) => activeNames.has(name));
        if (nextSelected.length !== selected.length) persistSelected(nextSelected);
        await loadSubs(nextSelected, nextShows, isCancelled);
      } catch (err) {
        if (!isCancelled()) handleError(err, "Could not load shows");
      }
    };
    window.addEventListener(SUBSCRIPTIONS_CHANGED_EVENT, refreshSubscriptions);
    window.addEventListener(SHOWS_CHANGED_EVENT, refreshShows);
    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener(SUBSCRIPTIONS_CHANGED_EVENT, refreshSubscriptions);
      window.removeEventListener(SHOWS_CHANGED_EVENT, refreshShows);
    };
  }, [selected, shows, loadSubs, persistSelected]);

  // Close the right-click menu on any outside interaction.
  React.useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  function toggleShow(name: string, checked: boolean) {
    persistSelected(checked ? [...selected, name] : selected.filter((n) => n !== name));
  }

  function onSubContextMenu(e: React.MouseEvent, sub: Subscription) {
    e.preventDefault();
    // Stop the show-section handler from also firing and overwriting with a
    // show-level (sub-less) menu.
    e.stopPropagation();
    setMenu({ x: e.clientX, y: e.clientY, sub, showName: sub.showName });
  }

  // Right-clicking a show's area (including an empty "no subscriptions" show)
  // opens a menu offering only "Add new subscription", matching CueGUI.
  function onShowContextMenu(e: React.MouseEvent, showName: string) {
    e.preventDefault();
    setMenu({ x: e.clientX, y: e.clientY, sub: null, showName });
  }

  function dispatch(name: string, detail: object) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
    setMenu(null);
  }

  const sortedShowNames = React.useMemo(
    () => (shows ?? []).map((s) => s.name).sort((a, b) => a.localeCompare(b)),
    [shows],
  );
  const selectedSorted = React.useMemo(
    () => [...selected].sort((a, b) => a.localeCompare(b)),
    [selected],
  );

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center gap-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={shows === null}>
              Shows
              <ChevronDown className="ml-1 h-4 w-4 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-96 overflow-y-auto">
            <DropdownMenuItem onSelect={() => persistSelected(sortedShowNames)}>
              All Shows
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => persistSelected([])}>Clear</DropdownMenuItem>
            <DropdownMenuSeparator />
            {sortedShowNames.map((name) => (
              <DropdownMenuCheckboxItem
                key={name}
                checked={selected.includes(name)}
                onCheckedChange={(checked) => toggleShow(name, !!checked)}
                onSelect={(e) => e.preventDefault()}
              >
                {name}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Legend (CueGUI uses the same color coding). */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: "#87cfeb" }} />
            Allocation
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: "#c8c837" }} />
            In use
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3.5 w-[3px]" style={{ backgroundColor: "#58a3d1" }} />
            Size
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3.5 w-[3px]" style={{ backgroundColor: "#e03434" }} />
            Burst
          </span>
        </div>
      </div>

      {selectedSorted.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Select one or more shows from the Shows menu to graph their subscriptions.
        </p>
      ) : (
        selectedSorted.map((name) => (
          <ShowSubscriptionGraph
            key={name}
            showName={name}
            subscriptions={subs[name] ?? null}
            allocCores={allocCores}
            onSubContextMenu={onSubContextMenu}
            onShowContextMenu={onShowContextMenu}
          />
        ))
      )}

      {/* Right-click context menu (CueGUI parity): Edit Size / Edit Burst /
          Delete / Add new subscription. */}
      {menu ? (
        <div
          className="fixed z-50 min-w-52 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Edit/Delete only apply to an actual subscription row; an empty
              show's right-click offers just "Add new subscription". */}
          {menu.sub ? (
            <>
              <button
                className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
                onClick={() => dispatch(OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT, { subscription: menu.sub })}
              >
                Edit Subscription Size...
              </button>
              <button
                className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
                onClick={() => dispatch(OPEN_EDIT_SUBSCRIPTION_BURST_EVENT, { subscription: menu.sub })}
              >
                Edit Subscription Burst...
              </button>
              <div className="my-1 h-px bg-border" />
              <button
                className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
                onClick={() => dispatch(OPEN_DELETE_SUBSCRIPTION_EVENT, { subscription: menu.sub })}
              >
                Delete Subscription
              </button>
              <div className="my-1 h-px bg-border" />
            </>
          ) : null}
          <button
            className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
            onClick={() => {
              const show = shows?.find((s) => s.name === menu.showName);
              if (show) dispatch(OPEN_CREATE_SUBSCRIPTION_EVENT, { show });
              else setMenu(null);
            }}
          >
            Add new subscription
          </button>
        </div>
      ) : null}

      {/* Shared dialogs opened via CustomEvents (reused from the Subscriptions
          page and the Shows window). */}
      <SubscriptionDialogs />
      <CreateSubscriptionDialog />
    </div>
  );
}
