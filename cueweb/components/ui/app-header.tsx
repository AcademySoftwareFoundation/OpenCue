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

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import * as React from "react";
import { Check, ChevronDown, Columns, Keyboard, LayoutDashboard, Layers3, LogOut, Menu, Search, X } from "lucide-react";

import { useAttributesPanel } from "@/app/utils/use_attributes_panel";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { useImmersiveMode } from "@/app/utils/use_immersive_mode";
import { useShortcutNotifications } from "@/app/utils/use_shortcut_notifications";
import { useShowDependencyGraph } from "@/app/utils/use_show_dependency_graph";
import { useEnabledPlugins } from "@/app/utils/use_plugin_menu";
import { NAV_MENUS, type NavMenu } from "@/app/utils/menus";
import { getPlugins } from "@/lib/plugins";
import {
  buildSplitUrl,
  DEFAULT_LEFT,
  DEFAULT_RIGHT,
} from "@/app/utils/split_view_utils";
import {
  filterMenuCommands,
  useMenuRegistry,
} from "@/app/utils/use_menu_registry";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CUEWEB_OPEN_SHORTCUTS_EVENT } from "@/components/ui/shortcuts-overlay";
import { CUEWEB_OPEN_MOBILE_NAV_EVENT } from "@/components/ui/mobile-nav-sheet";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils";
import opencueLogoBlack from "../../public/opencue-icon-black.png";
import opencueLogoWhite from "../../public/opencue-icon-white.png";

// NAV_MENUS is sourced from `@/app/utils/menus` so the header, sidebar and
// menu registry share one source of truth.

// Default split workspace: Monitor Jobs (left) + Monitor Hosts (right).
const SPLIT_VIEW_HREF = buildSplitUrl(DEFAULT_LEFT, DEFAULT_RIGHT);

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function isMenuActive(pathname: string | null, menu: NavMenu): boolean {
  return menu.items.some((item) => isActive(pathname, item.href));
}

function NavMenuButton({
  menu,
  pathname,
}: {
  menu: NavMenu;
  pathname: string | null;
}) {
  const active = isMenuActive(pathname, menu);
  // The Cuetopia menu gets an extra checkable "View Job Graph" entry
  // that toggles the inline Dependency Graph panel in JobDetailsInline
  // (mirrors CueGUI's `Cuetopia > Job Graph` toggle dock).
  const isCuetopia = menu.label === "Cuetopia";
  const { show: showGraph, toggle: toggleGraph } = useShowDependencyGraph();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-current={active ? "page" : undefined}
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            active
              ? "bg-foreground/10 text-foreground"
              : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
          )}
        >
          {menu.label}
          <ChevronDown className="h-3.5 w-3.5 opacity-70" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-[12rem]">
        {menu.items.map((item) => {
          const itemActive = isActive(pathname, item.href);
          return (
            <DropdownMenuItem
              key={item.href}
              asChild
              className={cn(itemActive && "bg-foreground/10 text-foreground")}
            >
              <Link
                href={item.href}
                aria-current={itemActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            </DropdownMenuItem>
          );
        })}
        {isCuetopia ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={(e) => {
                // Keep the menu open so the user can see the check
                // appear before it dismisses on the next click outside.
                e.preventDefault();
                toggleGraph();
              }}
              className="cursor-pointer"
              aria-checked={showGraph}
              role="menuitemcheckbox"
            >
              <span className="mr-2 flex h-4 w-4 items-center justify-center">
                {showGraph && <Check className="h-4 w-4" aria-hidden="true" />}
              </span>
              View Job Graph
            </DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * Help dropdown - CueGUI parity (Help menu in `cuegui/cuegui/MainWindow.py`).
 * The search box at the top searches across **every** menu command in
 * CueWeb (File, Cuebot Facility, Cuetopia, CueCommander, Other, Help),
 * mirroring CueGUI's Help-menu search behavior. With an empty query it
 * shows the three canonical Help items.
 */
function HelpDropdownMenu() {
  const [query, setQuery] = React.useState<string>("");
  const commands = useMenuRegistry();

  // Empty query -> show only the canonical Help items so the menu still
  // behaves like a plain "Help" menu when not searching.
  const helpOnly = React.useMemo(
    () => commands.filter((c) => c.group === "Help"),
    [commands],
  );

  const results = React.useMemo(() => {
    if (!query.trim()) return helpOnly;
    return filterMenuCommands(commands, query);
  }, [commands, helpOnly, query]);

  return (
    <DropdownMenu
      onOpenChange={(open) => {
        if (!open) setQuery("");
      }}
    >
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
        >
          Help
          <ChevronDown className="h-3.5 w-3.5 opacity-70" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="max-h-[60vh] min-w-[22rem] overflow-y-auto p-1"
      >
        {/* Search filter. stopPropagation defeats Radix's built-in
            typeahead so the input captures every keystroke. */}
        <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-popover px-2 py-1.5">
          <Search className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              // Defeat Radix's built-in typeahead for text-editing keys so
              // every keystroke reaches this input. Navigation keys
              // (Esc, arrows, Tab, Enter, Home/End/PageUp/PageDown) are
              // left to bubble so the dropdown's own keyboard controls
              // (close, item focus, etc.) keep working.
              if (
                e.key.length === 1 ||
                e.key === "Backspace" ||
                e.key === "Delete"
              ) {
                e.stopPropagation();
              }
            }}
            placeholder="Search menus"
            aria-label="Search menus"
            className="h-7 w-full bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
              className="rounded p-0.5 text-muted-foreground hover:bg-foreground/5 hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          )}
        </div>

        {results.length === 0 ? (
          <div className="px-3 py-2 text-xs text-muted-foreground">
            No matches.
          </div>
        ) : (
          results.map((cmd) => (
            <DropdownMenuItem
              key={cmd.id}
              onSelect={() => cmd.run()}
              className="cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Layers3
                  className="h-3.5 w-3.5 text-muted-foreground"
                  aria-hidden="true"
                />
                {/* Show "Group > Label" so the user always knows where the
                    command lives - except for Help entries, where the
                    group prefix is redundant in the unfiltered view. */}
                {!query && cmd.group === "Help" ? (
                  <span>{cmd.label}</span>
                ) : (
                  <span>
                    <span className="text-muted-foreground">
                      {cmd.group}
                      {" > "}
                    </span>
                    <span>{cmd.label}</span>
                  </span>
                )}
              </span>
              {cmd.hint && (
                <span className="ml-auto text-[10px] uppercase tracking-wide text-muted-foreground">
                  {cmd.hint}
                </span>
              )}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppHeader() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { disabled: jobInteractionDisabled, toggle: toggleJobInteraction } =
    useDisableJobInteraction();
  const { facility, facilities, setFacility } = useCuebotFacility();
  const {
    isOpen: attributesOpen,
    toggle: toggleAttributes,
  } = useAttributesPanel();
  const {
    enabled: shortcutNotificationsEnabled,
    toggle: toggleShortcutNotifications,
  } = useShortcutNotifications();
  const { immersive, toggle: toggleImmersive } = useImmersiveMode();

  // The Plugins menu lists only the user-enabled plugins (plugins page
  // checkboxes); inject them after the static "All Plugins" entry.
  const { enabled: enabledPlugins } = useEnabledPlugins();
  const navMenus = React.useMemo<NavMenu[]>(
    () =>
      NAV_MENUS.map((menu) => {
        if (menu.label !== "Plugins") return menu;
        const pluginItems = getPlugins()
          .map((plugin) => plugin.manifest)
          .filter((manifest) => enabledPlugins.has(manifest.name))
          .map((manifest) => ({ label: manifest.title, href: manifest.route }));
        return { ...menu, items: [...menu.items, ...pluginItems] };
      }),
    [enabledPlugins],
  );

  // Trigger the shortcuts overlay programmatically. Used by the
  // "Show Shortcuts" item below so users who never press `?` can still
  // surface the cheat sheet.
  const openShortcutsOverlay = React.useCallback(() => {
    window.dispatchEvent(new CustomEvent(CUEWEB_OPEN_SHORTCUTS_EVENT));
  }, []);

  if (pathname?.startsWith("/login")) return null;

  const userName = session?.user?.name ?? null;
  const userEmail = session?.user?.email ?? null;
  const userLabel = userName || userEmail;

  /**
   * Always routes back to /login.
   * - With a session: NextAuth clears it, then redirects.
   * - Without a session: NextAuth is a no-op, then redirects.
   * - The /login page itself handles both auth configurations
   *   (no providers → "CueWeb Home" button; providers configured → buttons per provider).
   */
  const handleSignOut = () => {
    try {
      localStorage.removeItem("tableData");
      localStorage.removeItem("tableDataUnfiltered");
    } catch {
      // localStorage may be unavailable; ignore
    }
    signOut({ callbackUrl: "/login" });
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 dark:border-zinc-800 dark:bg-zinc-900/95 dark:shadow-md dark:shadow-black/30 dark:supports-[backdrop-filter]:bg-zinc-900/80">
      <div className="flex h-14 items-center gap-3 px-4">
        {/* Hamburger: only on mobile, opens the MobileNavSheet drawer. The
            desktop sidebar (md+) is always visible to the left of the
            header, so no trigger is needed at desktop sizes. */}
        <button
          type="button"
          aria-label="Open navigation menu"
          onClick={() =>
            window.dispatchEvent(new CustomEvent(CUEWEB_OPEN_MOBILE_NAV_EVENT))
          }
          className="-ml-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground md:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>

        {/* Logo + product name */}
        <Link
          href="/"
          aria-label="CueWeb home"
          className="flex shrink-0 items-center gap-2 text-foreground"
        >
          <Image
            src={opencueLogoBlack}
            alt=""
            height={28}
            width={28}
            className="block h-7 w-7 dark:hidden"
            priority
          />
          <Image
            src={opencueLogoWhite}
            alt=""
            height={28}
            width={28}
            className="hidden h-7 w-7 dark:block"
            priority
          />
          <span className="hidden text-sm font-semibold sm:inline">CueWeb</span>
        </Link>

        {/* Primary nav (desktop) */}
        <nav
          aria-label="Primary"
          className="ml-2 hidden items-center gap-1 md:flex"
        >
          {/* Dashboard - landing page with at-a-glance widgets. Top-level link
              rather than a CueGUI-parity menu entry since CueGUI has no
              equivalent grouping. */}
          <Link
            href="/dashboard"
            aria-current={isActive(pathname, "/dashboard") ? "page" : undefined}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              isActive(pathname, "/dashboard")
                ? "bg-foreground/10 text-foreground"
                : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
            )}
          >
            <LayoutDashboard className="h-3.5 w-3.5" aria-hidden="true" />
            Dashboard
          </Link>

          {/* File menu — CueGUI parity */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className={cn(
                  "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  jobInteractionDisabled
                    ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                    : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                )}
              >
                File
                <ChevronDown
                  className="h-3.5 w-3.5 opacity-70"
                  aria-hidden="true"
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[14rem]">
              <DropdownMenuItem
                onSelect={() => toggleJobInteraction()}
                className="cursor-pointer"
              >
                <span className="mr-2 flex h-4 w-4 items-center justify-center">
                  {jobInteractionDisabled && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </span>
                Disable Job Interaction
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Cuebot Facility menu — CueGUI parity */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
              >
                <span>Cuebot Facility</span>
                <span className="rounded bg-foreground/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
                  {facility}
                </span>
                <ChevronDown
                  className="h-3.5 w-3.5 opacity-70"
                  aria-hidden="true"
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[12rem]">
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

          {navMenus.map((menu) => (
            <NavMenuButton key={menu.label} menu={menu} pathname={pathname} />
          ))}

          {/* Other menu — CueGUI parity (Views/Plugins > Other). */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className={cn(
                  "inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  attributesOpen
                    ? "bg-foreground/10 text-foreground"
                    : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
                )}
              >
                Other
                <ChevronDown
                  className="h-3.5 w-3.5 opacity-70"
                  aria-hidden="true"
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[12rem]">
              <DropdownMenuItem
                onSelect={() => toggleAttributes()}
                className="cursor-pointer"
              >
                <span className="mr-2 flex h-4 w-4 items-center justify-center">
                  {attributesOpen && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </span>
                Attributes
              </DropdownMenuItem>

              {/* CueGUI parity: Toggle Full-Screen. Hides the header, sidebar
                  and status bar so the active table gets the full viewport.
                  Also bound to `F` / Cmd-Ctrl+Shift+F. */}
              <DropdownMenuItem
                onSelect={() => toggleImmersive()}
                className="cursor-pointer"
              >
                <span className="mr-2 flex h-4 w-4 items-center justify-center">
                  {immersive && <Check className="h-4 w-4" aria-hidden="true" />}
                </span>
                Immersive (full-screen)
              </DropdownMenuItem>

              {/* CueGUI parity: Window ▸ "Add new window" - open two pages
                  side-by-side in a resizable split workspace. */}
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link href={SPLIT_VIEW_HREF}>
                  <Columns className="mr-2 h-4 w-4" aria-hidden="true" />
                  Split view
                </Link>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {/* CueGUI parity: surfaces the same overlay as `?`, for users
                  who prefer menus to keyboard shortcuts. */}
              <DropdownMenuItem
                onSelect={openShortcutsOverlay}
                className="cursor-pointer"
              >
                <Keyboard className="mr-2 h-4 w-4" aria-hidden="true" />
                Show Shortcuts
              </DropdownMenuItem>

              {/* Per-user opt-out for the toast that fires after every
                  triggered shortcut. Default ON so new users discover the
                  shortcuts; flip OFF once they're internalized. */}
              <DropdownMenuItem
                onSelect={() => toggleShortcutNotifications()}
                className="cursor-pointer"
              >
                <span className="mr-2 flex h-4 w-4 items-center justify-center">
                  {shortcutNotificationsEnabled && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </span>
                Notify on Shortcut
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Help menu — CueGUI parity (Help > Search / User Guide / Suggestion / Bug). */}
          <HelpDropdownMenu />
        </nav>

        {/* Right cluster: theme + user menu */}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <ThemeToggle />

          {userLabel && (
            <span
              className="hidden max-w-[180px] truncate text-sm text-foreground/70 sm:inline-block"
              title={userLabel}
            >
              {userLabel}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleSignOut}
            aria-label="Sign out"
          >
            <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </div>

      {/* Mobile nav lives in the hamburger-triggered MobileNavSheet drawer
          rendered at the layout root; no in-header mobile row needed. */}
    </header>
  );
}
