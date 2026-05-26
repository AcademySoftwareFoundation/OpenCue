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

/**
 * Shared navigation menu definitions used by the AppHeader, the AppSidebar
 * and the global menu registry (`use_menu_registry.ts`). Mirrors the
 * CueGUI Views/Plugins menu:
 *
 *   - Cuetopia    -> Monitor Jobs
 *   - CueCommander -> Allocations, Limits, Monitor Cue, Monitor Hosts,
 *                    Redirect, Services, Shows, Stuck Frame,
 *                    Subscription Graphs, Subscriptions
 *
 */

export type NavItem = {
  label: string;
  href: string;
};

export type NavMenu = {
  label: string;
  items: NavItem[];
};

export const NAV_MENUS: NavMenu[] = [
  {
    label: "Cuetopia",
    items: [{ label: "Monitor Jobs", href: "/" }],
  },
  {
    label: "CueCommander",
    items: [
      { label: "Allocations", href: "/allocations" },
      { label: "Limits", href: "/limits" },
      { label: "Monitor Cue", href: "/monitor-cue" },
      { label: "Monitor Hosts", href: "/hosts" },
      { label: "Redirect", href: "/redirect" },
      { label: "Services", href: "/services" },
      { label: "Shows", href: "/shows" },
      { label: "Stuck Frame", href: "/stuck-frames" },
      { label: "Subscription Graphs", href: "/subscription-graphs" },
      { label: "Subscriptions", href: "/subscriptions" },
    ],
  },
];
