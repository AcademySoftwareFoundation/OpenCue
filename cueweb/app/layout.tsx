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
import { AppHeader } from "@/components/ui/app-header";
import { AppSidebar } from "@/components/ui/app-sidebar";
import { AttributesPanel } from "@/components/ui/attributes-panel";
import { KeyboardShortcuts } from "@/components/ui/shortcuts-overlay";
import { ReadOnlyBanner } from "@/components/ui/read-only-banner";
import { StatusBar } from "@/components/ui/status-bar";
import { ToastHost } from "@/components/ui/toast-host";

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
            <AppHeader />
            <ReadOnlyBanner />
            <div className="flex pb-6">
              <AppSidebar />
              <main className="min-w-0 flex-1">{children}</main>
            </div>
            <AttributesPanel />
            <StatusBar />
            <KeyboardShortcuts />
            <ToastHost />
          </AppSessionProvider>
        </ThemeProvider>
        <JobSubscriptionPoller />
      </body>
    </html>
  );
}
