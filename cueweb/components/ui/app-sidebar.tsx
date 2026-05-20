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

import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRightLeft,
  BarChart3,
  Boxes,
  Briefcase,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Cloud,
  Film,
  FolderCog,
  Gauge,
  HelpCircle,
  Layers3,
  LayoutGrid,
  Lock,
  Monitor,
  PieChart,
  Receipt,
  Server,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  getItemFromLocalStorage,
  setItemInLocalStorage,
} from "@/app/utils/action_utils";
import { HELP_ITEMS } from "@/app/utils/help_menu";
import { useAttributesPanel } from "@/app/utils/use_attributes_panel";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { cn } from "@/lib/utils";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

type NavGroup = {
  label: string;
  icon: LucideIcon;
  items: NavItem[];
};

/**
 * Sidebar nav mirrors the CueGUI Views/Plugins menu (and the header):
 *   - Cuetopia    -> Monitor Jobs
 *   - CueCommander -> Allocations, Limits, Monitor Cue, Monitor Hosts,
 *                    Redirect, Services, Shows, Stuck Frame,
 *                    Subscription Graphs, Subscriptions
 */
const NAV_GROUPS: NavGroup[] = [
  {
    label: "Cuetopia",
    icon: LayoutGrid,
    items: [
      { label: "Monitor Jobs", href: "/", icon: Briefcase },
    ],
  },
  {
    label: "CueCommander",
    icon: Monitor,
    items: [
      { label: "Allocations", href: "/allocations", icon: PieChart },
      { label: "Limits", href: "/limits", icon: Gauge },
      { label: "Monitor Cue", href: "/monitor-cue", icon: Activity },
      { label: "Monitor Hosts", href: "/hosts", icon: Server },
      { label: "Redirect", href: "/redirect", icon: ArrowRightLeft },
      { label: "Services", href: "/services", icon: Wrench },
      { label: "Shows", href: "/shows", icon: Film },
      { label: "Stuck Frame", href: "/stuck-frames", icon: AlertTriangle },
      { label: "Subscription Graphs", href: "/subscription-graphs", icon: BarChart3 },
      { label: "Subscriptions", href: "/subscriptions", icon: Receipt },
    ],
  },
];

const COLLAPSED_KEY = "cueweb.sidebar.collapsed";
const OPEN_GROUPS_KEY = "cueweb.sidebar.openGroups";

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function groupContainsActive(pathname: string | null, group: NavGroup): boolean {
  return group.items.some((item) => isActive(pathname, item.href));
}

const FILE_GROUP_LABEL = "File";
const FACILITY_GROUP_LABEL = "Cuebot Facility";
const OTHER_GROUP_LABEL = "Other";
const HELP_GROUP_LABEL = "Help";

export function AppSidebar() {
  const pathname = usePathname();
  const { disabled: jobInteractionDisabled, toggle: toggleJobInteraction } =
    useDisableJobInteraction();
  const { facility, facilities, setFacility } = useCuebotFacility();
  const {
    isOpen: attributesOpen,
    toggle: toggleAttributes,
  } = useAttributesPanel();

  // SSR can't read localStorage, so we start with sensible defaults and
  // reconcile on mount. The initial server-rendered DOM therefore matches
  // the initial client render (no hydration mismatch); we hide the sidebar
  // for one paint with `invisible` to avoid a width/state flash.
  const [collapsed, setCollapsed] = React.useState<boolean>(false);
  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>(
    () => Object.fromEntries(NAV_GROUPS.map((g) => [g.label, true])),
  );
  const [hydrated, setHydrated] = React.useState<boolean>(false);

  React.useEffect(() => {
    try {
      const rawCollapsed = getItemFromLocalStorage(COLLAPSED_KEY, '"false"');
      setCollapsed(rawCollapsed === true || rawCollapsed === "true");
    } catch {
      // ignore
    }
    try {
      const rawGroups = getItemFromLocalStorage(OPEN_GROUPS_KEY, '"{}"');
      if (rawGroups && typeof rawGroups === "object" && !Array.isArray(rawGroups)) {
        setOpenGroups((prev) => ({ ...prev, ...(rawGroups as Record<string, boolean>) }));
      }
    } catch {
      // ignore
    }
    setHydrated(true);
  }, []);

  // Auto-expand the group containing the active route so it's never hidden
  // behind a collapsed accordion on first load.
  React.useEffect(() => {
    if (!hydrated) return;
    setOpenGroups((prev) => {
      let next = prev;
      for (const group of NAV_GROUPS) {
        if (groupContainsActive(pathname, group) && !prev[group.label]) {
          next = { ...next, [group.label]: true };
        }
      }
      return next;
    });
  }, [pathname, hydrated]);

  const toggleCollapsed = React.useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        setItemInLocalStorage(COLLAPSED_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const setGroupOpen = React.useCallback(
    (label: string, open: boolean) => {
      setOpenGroups((prev) => {
        const next = { ...prev, [label]: open };
        try {
          setItemInLocalStorage(OPEN_GROUPS_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    },
    [],
  );

  if (pathname?.startsWith("/login")) return null;

  return (
    <aside
      aria-label="Sidebar"
      data-collapsed={collapsed ? "true" : "false"}
      className={cn(
        // Sticky below the 14-unit (h-14 = 56px) AppHeader; full remaining
        // viewport height so the sidebar scrolls independently of content.
        "sticky top-14 hidden h-[calc(100vh-3.5rem)] shrink-0 overflow-y-auto border-r border-border bg-background transition-[width] duration-200 ease-out md:flex md:flex-col",
        // Match the AppHeader's dark surface for visual continuity.
        "dark:border-zinc-800 dark:bg-zinc-900",
        collapsed ? "w-16" : "w-60",
        // Avoid a flash of expanded width / closed groups before the
        // localStorage read completes.
        !hydrated && "invisible",
      )}
    >
      <nav aria-label="Primary navigation" className="flex-1 px-2 py-4">
        {/* File group - CueGUI parity (Disable Job Interaction). */}
        {collapsed ? (
          <ul
            className="mb-2 space-y-1 border-b border-border pb-2 dark:border-zinc-800"
            aria-label={FILE_GROUP_LABEL}
          >
            <li>
              <button
                type="button"
                onClick={toggleJobInteraction}
                title={`File - Disable Job Interaction${jobInteractionDisabled ? " (on)" : ""}`}
                aria-pressed={jobInteractionDisabled}
                className={cn(
                  "flex w-full items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  jobInteractionDisabled
                    ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                    : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                )}
              >
                <Lock className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="sr-only">Disable Job Interaction</span>
              </button>
            </li>
          </ul>
        ) : (
          <Collapsible
            open={openGroups[FILE_GROUP_LABEL] ?? true}
            onOpenChange={(next) => setGroupOpen(FILE_GROUP_LABEL, next)}
            className="mb-2"
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground">
              <FolderCog className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-left">{FILE_GROUP_LABEL}</span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform",
                  !(openGroups[FILE_GROUP_LABEL] ?? true) && "-rotate-90",
                )}
                aria-hidden="true"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className="ml-2 mt-1 space-y-1 border-l border-border pl-2 dark:border-zinc-800">
                <li>
                  <button
                    type="button"
                    onClick={toggleJobInteraction}
                    aria-pressed={jobInteractionDisabled}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                      jobInteractionDisabled
                        ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                        : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                    )}
                  >
                    <Lock className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="flex-1 truncate text-left">
                      Disable Job Interaction
                    </span>
                    <span className="ml-2 flex h-4 w-4 items-center justify-center">
                      {jobInteractionDisabled && (
                        <Check className="h-4 w-4" aria-hidden="true" />
                      )}
                    </span>
                  </button>
                </li>
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Cuebot Facility group - CueGUI parity (local / dev / cloud / external). */}
        {collapsed ? (
          <ul
            className="mb-2 space-y-1 border-b border-border pb-2 dark:border-zinc-800"
            aria-label={FACILITY_GROUP_LABEL}
          >
            <li>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    title={`Cuebot Facility - ${facility}`}
                    className="flex w-full items-center justify-center rounded-md px-3 py-2 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
                  >
                    <Cloud className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="sr-only">
                      Cuebot Facility - {facility}
                    </span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" side="right" className="min-w-[10rem]">
                  {facilities.map((f) => (
                    <DropdownMenuItem
                      key={f}
                      onSelect={() => setFacility(f)}
                      className="cursor-pointer"
                    >
                      <span className="mr-2 flex h-4 w-4 items-center justify-center">
                        {f === facility && (
                          <Check className="h-4 w-4" aria-hidden="true" />
                        )}
                      </span>
                      {f}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </li>
          </ul>
        ) : (
          <Collapsible
            open={openGroups[FACILITY_GROUP_LABEL] ?? true}
            onOpenChange={(next) => setGroupOpen(FACILITY_GROUP_LABEL, next)}
            className="mb-2"
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground">
              <Cloud className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-left">{FACILITY_GROUP_LABEL}</span>
              <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] font-semibold normal-case tracking-normal text-foreground">
                {facility}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform",
                  !(openGroups[FACILITY_GROUP_LABEL] ?? true) && "-rotate-90",
                )}
                aria-hidden="true"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul
                role="radiogroup"
                aria-label="Cuebot Facility"
                className="ml-2 mt-1 space-y-1 border-l border-border pl-2 dark:border-zinc-800"
              >
                {facilities.map((f) => {
                  const active = f === facility;
                  return (
                    <li key={f}>
                      <button
                        type="button"
                        role="radio"
                        aria-checked={active}
                        onClick={() => setFacility(f)}
                        className={cn(
                          "flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                          active
                            ? "bg-foreground/10 text-foreground"
                            : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                        )}
                      >
                        <span className="flex h-4 w-4 items-center justify-center">
                          {active && (
                            <Check className="h-4 w-4" aria-hidden="true" />
                          )}
                        </span>
                        <span className="truncate">{f}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}

        {collapsed
          ? // Icon-only view: flatten every group's items into a single column
            // of icon links. Group labels are dropped (the section dividers
            // below keep them visually separated).
            NAV_GROUPS.map((group, groupIndex) => (
              <ul
                key={group.label}
                className={cn(
                  "space-y-1",
                  groupIndex > 0 && "mt-2 border-t border-border pt-2 dark:border-zinc-800",
                )}
                aria-label={group.label}
              >
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(pathname, item.href);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        title={`${group.label} - ${item.label}`}
                        className={cn(
                          "flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                          active
                            ? "bg-foreground/10 text-foreground"
                            : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <span className="sr-only">{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            ))
          : // Expanded view: render each group as a Radix Collapsible
            // accordion whose open/closed state is persisted.
            NAV_GROUPS.map((group) => {
              const GroupIcon = group.icon;
              const open = openGroups[group.label] ?? true;
              const hasActive = groupContainsActive(pathname, group);
              return (
                <Collapsible
                  key={group.label}
                  open={open}
                  onOpenChange={(next) => setGroupOpen(group.label, next)}
                  className="mb-2 last:mb-0"
                >
                  <CollapsibleTrigger
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground",
                      hasActive && "text-foreground",
                    )}
                  >
                    <GroupIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="flex-1 text-left">{group.label}</span>
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 shrink-0 transition-transform",
                        !open && "-rotate-90",
                      )}
                      aria-hidden="true"
                    />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <ul className="ml-2 mt-1 space-y-1 border-l border-border pl-2 dark:border-zinc-800">
                      {group.items.map((item) => {
                        const Icon = item.icon;
                        const active = isActive(pathname, item.href);
                        return (
                          <li key={item.href}>
                            <Link
                              href={item.href}
                              aria-current={active ? "page" : undefined}
                              className={cn(
                                "flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                                active
                                  ? "bg-foreground/10 text-foreground"
                                  : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                              )}
                            >
                              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                              <span className="truncate">{item.label}</span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </CollapsibleContent>
                </Collapsible>
              );
            })}

        {/* Other group - CueGUI parity (Views/Plugins > Other > Attributes). */}
        {collapsed ? (
          <ul
            className="mt-2 space-y-1 border-t border-border pt-2 dark:border-zinc-800"
            aria-label={OTHER_GROUP_LABEL}
          >
            <li>
              <button
                type="button"
                onClick={toggleAttributes}
                aria-pressed={attributesOpen}
                title={`Other - Attributes${attributesOpen ? " (open)" : ""}`}
                className={cn(
                  "flex w-full items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  attributesOpen
                    ? "bg-foreground/10 text-foreground"
                    : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                )}
              >
                <Layers3 className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="sr-only">Attributes</span>
              </button>
            </li>
          </ul>
        ) : (
          <Collapsible
            open={openGroups[OTHER_GROUP_LABEL] ?? true}
            onOpenChange={(next) => setGroupOpen(OTHER_GROUP_LABEL, next)}
            className="mb-2"
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground">
              <Boxes className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-left">{OTHER_GROUP_LABEL}</span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform",
                  !(openGroups[OTHER_GROUP_LABEL] ?? true) && "-rotate-90",
                )}
                aria-hidden="true"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className="ml-2 mt-1 space-y-1 border-l border-border pl-2 dark:border-zinc-800">
                <li>
                  <button
                    type="button"
                    onClick={toggleAttributes}
                    aria-pressed={attributesOpen}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                      attributesOpen
                        ? "bg-foreground/10 text-foreground"
                        : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                    )}
                  >
                    <Layers3 className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="flex-1 truncate text-left">Attributes</span>
                    <span className="ml-2 flex h-4 w-4 items-center justify-center">
                      {attributesOpen && (
                        <Check className="h-4 w-4" aria-hidden="true" />
                      )}
                    </span>
                  </button>
                </li>
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Help group - CueGUI parity (Help menu). */}
        {collapsed ? (
          <ul
            className="mt-2 space-y-1 border-t border-border pt-2 dark:border-zinc-800"
            aria-label={HELP_GROUP_LABEL}
          >
            {HELP_ITEMS.map((item) => (
              <li key={item.label}>
                <a
                  href={item.href}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={`Help - ${item.label}`}
                  className="flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
                >
                  <HelpCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="sr-only">{item.label}</span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <Collapsible
            open={openGroups[HELP_GROUP_LABEL] ?? true}
            onOpenChange={(next) => setGroupOpen(HELP_GROUP_LABEL, next)}
            className="mb-2"
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground">
              <HelpCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-left">{HELP_GROUP_LABEL}</span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform",
                  !(openGroups[HELP_GROUP_LABEL] ?? true) && "-rotate-90",
                )}
                aria-hidden="true"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className="ml-2 mt-1 space-y-1 border-l border-border pl-2 dark:border-zinc-800">
                {HELP_ITEMS.map((item) => (
                  <li key={item.label}>
                    <a
                      href={item.href}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
                    >
                      <span className="truncate">{item.label}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}
      </nav>

      {/* Collapse toggle pinned to the bottom of the sidebar. */}
      <div className="border-t border-border p-2 dark:border-zinc-800">
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          className={cn(
            "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground",
            collapsed && "justify-center",
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
