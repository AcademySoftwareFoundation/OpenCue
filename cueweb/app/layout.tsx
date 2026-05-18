import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { JobSubscriptionPoller } from "@/app/providers/job-subscription-poller";

export const metadata: Metadata = {
  title: "CueWeb",
  description: "CueWeb System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
          {children}
        </ThemeProvider>
        <JobSubscriptionPoller />
      </body>
    </html>
  );
}
