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
import { useTheme } from "next-themes";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getShortcutNotificationsEnabled } from "@/app/utils/use_shortcut_notifications";
import { toastSuccess } from "@/app/utils/notify_utils";

/**
 * Event name dispatched on `window` when the user presses `r` to ask for an
 * immediate table refresh. Pages that show live data (e.g. the jobs table)
 * subscribe to this and rerun their fetch.
 */
export const CUEWEB_REFRESH_NOW_EVENT = "cueweb:refresh-now";

/**
 * Event name dispatched on `window` when the user presses `/` to focus the
 * primary search box. Search components subscribe to this and focus their
 * underlying input element.
 */
export const CUEWEB_FOCUS_SEARCH_EVENT = "cueweb:focus-search";

/**
 * Event name dispatched on `window` to programmatically open the shortcuts
 * overlay (e.g. from the "Show Shortcuts" menu item in the Other menu /
 * sidebar). Allows non-keyboard users to reach the same affordance as `?`.
 */
export const CUEWEB_OPEN_SHORTCUTS_EVENT = "cueweb:open-shortcuts";

/** Identifies the action a row (and its kbd chip) triggers when clicked.
 * Each maps to a handler built inside `KeyboardShortcuts` below. */
type ShortcutAction = "show" | "close" | "focusSearch" | "refresh" | "toggleTheme";

/** Shape of a single row in the shortcuts cheat-sheet. */
interface ShortcutEntry {
  keys: string[];
  label: string;
  context?: string;
  action: ShortcutAction;
}

/**
 * The cheat-sheet rendered inside the overlay. Keep this in sync with the
 * actual key handler below - and with the table in `cueweb/README.md`.
 */
const SHORTCUTS: ShortcutEntry[] = [
  { keys: ["?"], label: "Show this shortcuts overlay", action: "show" },
  { keys: ["Esc"], label: "Close this overlay", action: "close" },
  {
    keys: ["/"],
    label: "Focus the jobs search box",
    context: "On the jobs page",
    action: "focusSearch",
  },
  {
    keys: ["r"],
    label: "Refresh the jobs table",
    context: "On the jobs page",
    action: "refresh",
  },
  { keys: ["t"], label: "Toggle light / dark theme", action: "toggleTheme" },
];

/**
 * Returns true if the keyboard event originated from an editable target -
 * <input>, <textarea>, or any element with `contenteditable`. We use this
 * to suppress single-letter shortcuts (`r`, `t`, `/`) while typing so the
 * user can still type those characters into a search field.
 *
 * `?` is treated the same way: typing `?` into a search box should produce
 * a literal `?`, not pop the cheat sheet.
 */
function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Global keyboard-shortcut handler + cheat-sheet overlay.
 *
 * Mount once near the top of the app (we do it from `app/layout.tsx`).
 * Listens for `keydown` on `window` and:
 *   - `?`  opens the overlay (mirrors GitHub's `?` cheat sheet)
 *   - `/`  dispatches CUEWEB_FOCUS_SEARCH_EVENT
 *   - `r`  dispatches CUEWEB_REFRESH_NOW_EVENT
 *   - `t`  toggles the next-themes theme between light and dark
 *
 * Esc is handled by the Dialog primitive itself (Radix wires that), so no
 * extra key handler is needed to close the overlay.
 *
 * All single-letter shortcuts are skipped when the focused element is
 * editable (INPUT / TEXTAREA / SELECT / contenteditable) so they do not
 * interfere with typing. They are also skipped when a modifier key (Ctrl,
 * Cmd, Alt) is held so they do not collide with browser shortcuts like
 * Ctrl+R / Cmd+R (full page reload).
 */
export function KeyboardShortcuts() {
  const [open, setOpen] = React.useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  // resolvedTheme is more reliable than `theme` when the user is on the
  // "system" preference - it gives us the actual rendered theme so the
  // toggle always flips to the opposite side.
  const themeRef = React.useRef<string | undefined>(resolvedTheme);
  React.useEffect(() => {
    themeRef.current = resolvedTheme;
  }, [resolvedTheme]);

  // Fires a small toast naming the shortcut that was just triggered, but
  // only when the user hasn't opted out via the Other menu. Reads the pref
  // imperatively so flipping the toggle takes effect on the very next
  // keypress without remounting the listener.
  const notify = React.useCallback((label: string) => {
    if (!getShortcutNotificationsEnabled()) return;
    toastSuccess(label);
  }, []);

  // Single source of truth for what each shortcut actually does, so the
  // keydown handler and the clickable kbd chips in the dialog (used on
  // touch devices that can't fire real key events) call the same code.
  // `closeOverlay` is true when the action's effect makes the overlay
  // irrelevant - e.g. focusing the search box should also dismiss the
  // dialog so the user can see / type into the input.
  const runAction = React.useCallback((action: ShortcutAction) => {
    switch (action) {
      case "show":
        setOpen(true);
        notify("Shortcut: ? → Show shortcuts");
        return;
      case "close":
        setOpen(false);
        return;
      case "focusSearch":
        setOpen(false);
        window.dispatchEvent(new CustomEvent(CUEWEB_FOCUS_SEARCH_EVENT));
        notify("Shortcut: / → Focus search");
        return;
      case "refresh":
        setOpen(false);
        window.dispatchEvent(new CustomEvent(CUEWEB_REFRESH_NOW_EVENT));
        notify("Shortcut: r → Refresh table");
        return;
      case "toggleTheme":
        setTheme(themeRef.current === "dark" ? "light" : "dark");
        notify("Shortcut: t → Toggle theme");
        return;
    }
  }, [setTheme, notify]);

  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      // Never compete with browser / OS shortcuts.
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      // Suppress single-letter shortcuts inside editable elements so the
      // user can still type these characters into a text field.
      if (isEditableTarget(event.target)) return;

      let action: ShortcutAction | null = null;
      switch (event.key) {
        case "?": action = "show"; break;
        case "/": action = "focusSearch"; break;
        case "r": case "R": action = "refresh"; break;
        case "t": case "T": action = "toggleTheme"; break;
      }
      if (!action) return;
      event.preventDefault();
      runAction(action);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [runAction]);

  // Allow non-keyboard callers (menu items) to open the overlay too.
  React.useEffect(() => {
    const openHandler = () => setOpen(true);
    window.addEventListener(CUEWEB_OPEN_SHORTCUTS_EVENT, openHandler);
    return () => window.removeEventListener(CUEWEB_OPEN_SHORTCUTS_EVENT, openHandler);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {/* Mobile-friendly sizing:
           - `max-w-[calc(100vw-2rem)]` leaves a 1rem gutter on either
             side of the viewport so the dialog (and the Radix `X` close
             button) never bleed past the edge on phones.
           - `max-h-[calc(100vh-3rem)]` plus `overflow-y-auto` lets the
             content scroll instead of overflowing on short viewports.
           - `p-4 sm:p-6` shrinks the padding on small screens so each
             row's text + kbd chip can fit on one line. */}
      <DialogContent className="max-h-[calc(100vh-3rem)] w-full max-w-[calc(100vw-2rem)] overflow-y-auto p-4 sm:max-w-lg sm:p-6">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Press <Kbd>?</Kbd> anywhere to open this overlay. Press{" "}
            <Kbd ariaLabel="Close overlay" onClick={() => runAction("close")}>
              Esc
            </Kbd>{" "}
            to close it. Tap any key below to trigger its action.
          </DialogDescription>
        </DialogHeader>

        <ul className="mt-2 divide-y divide-border rounded-md border border-border">
          {SHORTCUTS.map((entry) => {
            // Each row's chips dispatch the same action the keyboard
            // shortcut would. Critical on touch devices where the
            // physical keys aren't reachable, but also a nicer
            // discoverability path on desktop.
            const onClick = () => runAction(entry.action);
            return (
              <li
                key={`${entry.keys.join("+")}-${entry.label}`}
                className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <button
                  type="button"
                  onClick={onClick}
                  className="min-w-0 flex-1 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                  aria-label={`${entry.label}${entry.context ? ` (${entry.context})` : ""}`}
                >
                  <p className="break-words text-foreground">{entry.label}</p>
                  {entry.context && (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {entry.context}
                    </p>
                  )}
                </button>
                <div className="flex shrink-0 items-center gap-1">
                  {entry.keys.map((key, i) => (
                    <React.Fragment key={key}>
                      {i > 0 && (
                        <span
                          className="text-xs text-muted-foreground"
                          aria-hidden="true"
                        >
                          +
                        </span>
                      )}
                      <Kbd ariaLabel={`${entry.label}`} onClick={onClick}>
                        {key}
                      </Kbd>
                    </React.Fragment>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Visual representation of a keyboard key. When an `onClick` is supplied,
 * the chip renders as a real button so touch users can fire the action
 * without a physical keyboard; otherwise it renders as a plain decorative
 * `<kbd>`.
 */
function Kbd({
  children,
  onClick,
  ariaLabel,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  ariaLabel?: string;
}) {
  const baseClass =
    "inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-md border border-border bg-muted px-1.5 font-mono text-xs font-medium text-foreground shadow-sm";
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label={ariaLabel}
        className={`${baseClass} cursor-pointer transition-colors hover:bg-foreground/10 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring active:bg-foreground/15`}
      >
        {children}
      </button>
    );
  }
  return <kbd className={baseClass}>{children}</kbd>;
}
