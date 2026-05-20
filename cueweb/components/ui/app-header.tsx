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
import { ChevronDown, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils";
import opencueLogoBlack from "../../public/opencue-icon-black.png";
import opencueLogoWhite from "../../public/opencue-icon-white.png";

type NavItem = {
  label: string;
  href: string;
};

type NavMenu = {
  label: string;
  items: NavItem[];
};

/**
 * Nav structure mirrors the CueGUI Views/Plugins menu:
 *   - Cuetopia    → Monitor Jobs
 *   - CueCommander → Allocations, Limits, Monitor Cue, Monitor Hosts, Redirect,
 *                    Services, Shows, Stuck Frame, Subscription Graphs, Subscriptions
 *
 * Routes for not-yet-built pages 404 gracefully until those Category D–G tasks land.
 */
const NAV_MENUS: NavMenu[] = [
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
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppHeader() {
  const pathname = usePathname();
  const { data: session } = useSession();

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
          {NAV_MENUS.map((menu) => (
            <NavMenuButton key={menu.label} menu={menu} pathname={pathname} />
          ))}
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

      {/* Mobile nav row */}
      <nav
        aria-label="Primary mobile"
        className="flex items-center gap-1 overflow-x-auto border-t border-border px-4 py-2 dark:border-zinc-800 md:hidden"
      >
        {NAV_MENUS.map((menu) => (
          <NavMenuButton key={menu.label} menu={menu} pathname={pathname} />
        ))}
      </nav>
    </header>
  );
}
