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

// Mobile drawer that mirrors the AppSidebar's navigation groups inside a
// Sheet. The desktop sidebar stays untouched (it's `hidden md:flex`); this
// component fills the same role on viewports below the `md` breakpoint.
//
// Opens via the `cueweb:open-mobile-nav` window event dispatched by the
// hamburger button in AppHeader, so the trigger and the drawer are
// decoupled and the same event can be reused from anywhere later (e.g. a
// gesture handler).

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Check, Keyboard, LayoutDashboard } from "lucide-react";

import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { NAV_MENUS } from "@/app/utils/menus";
import { HELP_ITEMS } from "@/app/utils/help_menu";
import { useAttributesPanel } from "@/app/utils/use_attributes_panel";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { useShortcutNotifications } from "@/app/utils/use_shortcut_notifications";
import { CUEWEB_OPEN_SHORTCUTS_EVENT } from "@/components/ui/shortcuts-overlay";
import { cn } from "@/lib/utils";

/** Dispatched by the hamburger button in AppHeader. */
export const CUEWEB_OPEN_MOBILE_NAV_EVENT = "cueweb:open-mobile-nav";

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function MobileNavSheet() {
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);
  const { disabled: jobInteractionDisabled, toggle: toggleJobInteraction } =
    useDisableJobInteraction();
  const { facility, facilities, setFacility } = useCuebotFacility();
  const { isOpen: attributesOpen, toggle: toggleAttributes } = useAttributesPanel();
  const { enabled: shortcutNotificationsEnabled, toggle: toggleShortcutNotifications } =
    useShortcutNotifications();

  React.useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener(CUEWEB_OPEN_MOBILE_NAV_EVENT, handler);
    return () => window.removeEventListener(CUEWEB_OPEN_MOBILE_NAV_EVENT, handler);
  }, []);

  // Close the drawer whenever the user navigates so a Link tap doesn't
  // leave the overlay sitting open over the new page.
  React.useEffect(() => {
    setOpen(false);
  }, [pathname]);

  if (pathname?.startsWith("/login")) return null;

  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent
        side="left"
        // Flex column so the title bar takes its natural height and the
        // <nav> below it claims the remaining space + owns the scroll.
        // Putting overflow on the SheetContent itself didn't work because
        // its height comes from `inset-y-0` (fixed viewport edges) rather
        // than from layout, so an inner flex container is the reliable
        // way to give the menu a real scrollable region.
        className="flex w-80 max-w-[85vw] flex-col p-0 md:hidden"
      >
        <div className="shrink-0 border-b border-border px-4 py-3 dark:border-zinc-800">
          <SheetTitle>Menu</SheetTitle>
        </div>

        <nav className="flex-1 space-y-4 overflow-y-auto overscroll-contain px-3 py-3 text-sm">
          {/* Dashboard - standalone link (no CueGUI grouping). */}
          <MobileLink
            href="/dashboard"
            label="Dashboard"
            icon={<LayoutDashboard className="h-4 w-4 shrink-0" aria-hidden="true" />}
            active={isActive(pathname, "/dashboard")}
            onSelect={close}
          />

          {/* File */}
          <Group label="File">
            <MobileToggle
              label="Disable Job Interaction"
              checked={jobInteractionDisabled}
              onToggle={toggleJobInteraction}
            />
          </Group>

          {/* Cuebot Facility */}
          <Group label="Cuebot Facility">
            {facilities.map((f) => (
              <MobileToggle
                key={f}
                label={f}
                checked={f === facility}
                onToggle={() => setFacility(f)}
              />
            ))}
          </Group>

          {/* Cuetopia / CueCommander - the NAV_MENUS groups */}
          {NAV_MENUS.map((menu) => (
            <Group key={menu.label} label={menu.label}>
              {menu.items.map((item) => (
                <MobileLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  active={isActive(pathname, item.href)}
                  onSelect={close}
                />
              ))}
            </Group>
          ))}

          {/* Other */}
          <Group label="Other">
            <MobileToggle
              label="Attributes"
              checked={attributesOpen}
              onToggle={toggleAttributes}
            />
            <MobileAction
              label="Show Shortcuts"
              icon={<Keyboard className="h-4 w-4 shrink-0" aria-hidden="true" />}
              onClick={() => {
                close();
                // Defer so the Sheet's close animation can clear focus
                // before the overlay grabs it.
                requestAnimationFrame(() => {
                  window.dispatchEvent(new CustomEvent(CUEWEB_OPEN_SHORTCUTS_EVENT));
                });
              }}
            />
            <MobileToggle
              label="Notify on Shortcut"
              checked={shortcutNotificationsEnabled}
              onToggle={toggleShortcutNotifications}
            />
          </Group>

          {/* Help */}
          <Group label="Help">
            {HELP_ITEMS.map((item) => (
              <a
                key={item.label}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={close}
                className="flex items-center justify-between rounded-md px-3 py-2 text-sm text-foreground/70 hover:bg-foreground/5 hover:text-foreground"
              >
                {item.label}
              </a>
            ))}
          </Group>
        </nav>
      </SheetContent>
    </Sheet>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section aria-label={label} className="space-y-1">
      <p className="px-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="space-y-0.5">{children}</div>
    </section>
  );
}

function MobileLink({
  href,
  label,
  icon,
  active,
  onSelect,
}: {
  href: string;
  label: string;
  icon?: React.ReactNode;
  active?: boolean;
  onSelect?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onSelect}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-foreground/10 text-foreground"
          : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
    </Link>
  );
}

function MobileToggle({
  label,
  checked,
  onToggle,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={checked}
      className={cn(
        "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
        checked
          ? "bg-foreground/10 text-foreground"
          : "text-foreground/70 hover:bg-foreground/5 hover:text-foreground",
      )}
    >
      <span className="truncate">{label}</span>
      <span className="ml-2 flex h-4 w-4 items-center justify-center">
        {checked && <Check className="h-4 w-4" aria-hidden="true" />}
      </span>
    </button>
  );
}

function MobileAction({
  label,
  icon,
  onClick,
}: {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  );
}
