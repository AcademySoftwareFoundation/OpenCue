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

import { Shrink } from "lucide-react";
import * as React from "react";

import { useImmersiveMode } from "@/app/utils/use_immersive_mode";
import { AppHeader } from "@/components/ui/app-header";
import { AppSidebar } from "@/components/ui/app-sidebar";
import { ReadOnlyBanner } from "@/components/ui/read-only-banner";
import { StatusBar } from "@/components/ui/status-bar";

/**
 * Structural shell for the authenticated app. Owns the header / sidebar /
 * status-bar chrome so the "Immersive" toggle (CueGUI's Toggle Full-Screen,
 * `cuegui/cuegui/MainWindow.py`) can hide all of it from one place.
 *
 * When immersive mode is on:
 *   - the global header (A1), sidebar (A2) and status bar (A4) are unmounted,
 *     so the page content (`children`) gets the full viewport height;
 *   - a small floating "Exit immersive" button is shown so mouse-only users
 *     aren't trapped once the header/menu are gone (the `F` shortcut and the
 *     Other ▸ Immersive menu item also toggle it back).
 *
 * The read-only banner is intentionally kept visible in immersive mode - it's
 * a safety affordance, not chrome. The keyboard-shortcut handler, attributes
 * panel, mobile nav and toast host stay mounted at the layout root (outside
 * this component) so the `F` shortcut keeps working while immersed.
 *
 * Immersive state is hydrated from localStorage after mount (SSR-safe), so the
 * first paint shows the chrome and then hides it if the user left immersive
 * mode on - matching every other persisted UI pref in CueWeb.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { immersive, setImmersive } = useImmersiveMode();

  // Detect when a CueWeb page is rendered inside an iframe (a split-view pane).
  // Such panes show page content only - no nested header/sidebar/status bar.
  // Computed after mount (SSR-safe); a cross-origin parent throws on access,
  // which we treat as embedded. See `components/ui/split-view.tsx`.
  const [embedded, setEmbedded] = React.useState(false);
  React.useEffect(() => {
    try {
      setEmbedded(window.self !== window.top);
    } catch {
      setEmbedded(true);
    }
  }, []);

  // Hide the chrome for immersive mode OR when embedded as a split pane.
  const hideChrome = immersive || embedded;

  return (
    <>
      {/* The sidebar sits in its own full-height column on the left; the
          AppHeader, ReadOnlyBanner and main content render in the right column
          so the header never overlaps the sidebar area. */}
      <div className="flex min-h-screen">
        {hideChrome ? null : <AppSidebar />}
        <div className="flex min-w-0 flex-1 flex-col">
          {hideChrome ? null : <AppHeader />}
          <ReadOnlyBanner />
          <main className="flex-1 pb-6">{children}</main>
        </div>
      </div>
      {hideChrome ? null : <StatusBar />}
      {/* The Exit-immersive button is for the top-level window only; inside a
          split pane the chrome is hidden because it's embedded, not immersive. */}
      {immersive && !embedded ? (
        <button
          type="button"
          onClick={() => setImmersive(false)}
          aria-label="Exit immersive mode"
          title="Exit immersive (F)"
          className="fixed right-3 top-3 z-50 inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background/90 px-2.5 text-xs font-medium text-foreground/80 shadow-sm backdrop-blur transition-colors hover:bg-accent hover:text-foreground"
        >
          <Shrink className="h-4 w-4" aria-hidden="true" />
          Exit immersive
        </button>
      ) : null}
    </>
  );
}

export default AppShell;
