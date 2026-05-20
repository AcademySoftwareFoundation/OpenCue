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

/** Shape of a single row in the shortcuts cheat-sheet. */
interface ShortcutEntry {
  keys: string[];
  label: string;
  context?: string;
}

/**
 * The cheat-sheet rendered inside the overlay. Keep this in sync with the
 * actual key handler below - and with the table in `cueweb/README.md`.
 */
const SHORTCUTS: ShortcutEntry[] = [
  { keys: ["?"], label: "Show this shortcuts overlay" },
  { keys: ["Esc"], label: "Close this overlay" },
  {
    keys: ["/"],
    label: "Focus the jobs search box",
    context: "On the jobs page",
  },
  {
    keys: ["r"],
    label: "Refresh the jobs table",
    context: "On the jobs page",
  },
  { keys: ["t"], label: "Toggle light / dark theme" },
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

  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      // Never compete with browser / OS shortcuts.
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      // Suppress single-letter shortcuts inside editable elements so the
      // user can still type these characters into a text field.
      if (isEditableTarget(event.target)) return;

      switch (event.key) {
        case "?":
          event.preventDefault();
          setOpen(true);
          break;
        case "/":
          event.preventDefault();
          window.dispatchEvent(new CustomEvent(CUEWEB_FOCUS_SEARCH_EVENT));
          break;
        case "r":
        case "R":
          event.preventDefault();
          window.dispatchEvent(new CustomEvent(CUEWEB_REFRESH_NOW_EVENT));
          break;
        case "t":
        case "T":
          event.preventDefault();
          setTheme(themeRef.current === "dark" ? "light" : "dark");
          break;
        default:
          // No-op for every other key.
          break;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setTheme]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Press <Kbd>?</Kbd> anywhere to open this overlay. Press <Kbd>Esc</Kbd>{" "}
            to close it.
          </DialogDescription>
        </DialogHeader>

        <ul className="mt-2 divide-y divide-border rounded-md border border-border">
          {SHORTCUTS.map((entry) => (
            <li
              key={`${entry.keys.join("+")}-${entry.label}`}
              className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
            >
              <div className="min-w-0">
                <p className="text-foreground">{entry.label}</p>
                {entry.context && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {entry.context}
                  </p>
                )}
              </div>
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
                    <Kbd>{key}</Kbd>
                  </React.Fragment>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Visual representation of a keyboard key. Kept inline (not exported) so the
 * styling stays scoped to the overlay - we may want a global `<Kbd>` element
 * later, but this lives here until there's a second consumer.
 */
function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-md border border-border bg-muted px-1.5 font-mono text-xs font-medium text-foreground shadow-sm">
      {children}
    </kbd>
  );
}
