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

import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { JobSubscriptionPoller } from "@/app/providers/job-subscription-poller";
import { AppSessionProvider } from "@/app/providers/session-provider";
// AppShell (workspace-layout) owns the header / sidebar / status-bar /
// read-only-banner chrome. AboutDialog and PluginSettingsDialog are global
// event-driven dialogs rendered here (not part of AppShell).
import { AppShell } from "@/components/ui/app-shell";
import { AttributesPanel } from "@/components/ui/attributes-panel";
import { MobileNavSheet } from "@/components/ui/mobile-nav-sheet";
import { KeyboardShortcuts } from "@/components/ui/shortcuts-overlay";
import { AboutDialog } from "@/components/ui/about-dialog";
import { PluginSettingsDialog } from "@/components/ui/settings-dialog";
import { ToastHost } from "@/components/ui/toast-host";
import { UsageTracker } from "@/components/ui/usage-tracker";

export const metadata: Metadata = {
  title: "CueWeb",
  description: "CueWeb System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
          <AppSessionProvider>
            {/* AppShell owns the header / sidebar / status-bar chrome so the
                Immersive (full-screen) toggle can hide it all from one place.
                The keyboard-shortcut handler, attributes panel, mobile nav and
                toast host stay mounted here so the `F` shortcut still works
                while immersed. */}
            <AppShell>{children}</AppShell>
            <AttributesPanel />
            <AboutDialog />
            <KeyboardShortcuts />
            <MobileNavSheet />
            <PluginSettingsDialog />
            <ToastHost />
            <UsageTracker />
          </AppSessionProvider>
        </ThemeProvider>
        <JobSubscriptionPoller />
      </body>
    </html>
  );
}
