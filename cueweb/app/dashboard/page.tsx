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

import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { ActiveJobsWidget } from "@/components/dashboard/active-jobs-widget";
import { FrameStateChart } from "@/components/dashboard/frame-state-chart";
import { HostsStateChart } from "@/components/dashboard/hosts-state-chart";
import { HostsWidget } from "@/components/dashboard/hosts-widget";
import { JobAgeChart } from "@/components/dashboard/job-age-chart";
import { JobsPerShowChart } from "@/components/dashboard/jobs-per-show-chart";
import { RecentFailuresWidget } from "@/components/dashboard/recent-failures-widget";
import { ShowsWidget } from "@/components/dashboard/shows-widget";
import { TopJobsChart } from "@/components/dashboard/top-jobs-chart";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function DashboardPage() {
  return (
    <div className="container mx-auto py-6 max-w-7xl">
      <ToastContainer />

      <Breadcrumbs items={[{ label: "Dashboard" }]} className="mb-4" />

      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          At-a-glance health of the render farm. Each card refreshes on its own
          schedule; click any card to jump to its detail page.
        </p>
      </header>

      <section
        aria-label="Dashboard widgets"
        className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4"
      >
        <ActiveJobsWidget />
        <HostsWidget />
        <RecentFailuresWidget />
        <ShowsWidget />
      </section>

      <section
        aria-label="Dashboard charts"
        className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2"
      >
        <FrameStateChart />
        <TopJobsChart />
        <HostsStateChart />
        <JobsPerShowChart />
        <JobAgeChart />
      </section>
    </div>
  );
}
