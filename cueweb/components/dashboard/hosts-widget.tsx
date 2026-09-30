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

import { Host, getHosts } from "@/app/utils/get_utils";
import {
  WidgetCard,
  WidgetCardError,
  WidgetCardSkeleton,
} from "@/components/dashboard/widget-card";
import { Server } from "lucide-react";
import * as React from "react";

const REFRESH_MS = 30000;

// Mirrors cuegui's host-state semantics: hardware.HardwareState UP/DOWN/REBOOTING/REPAIR.
const UP_STATE = "UP";

export function HostsWidget() {
  const [hosts, setHosts] = React.useState<Host[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getHosts();
        if (!cancelled) {
          setHosts(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (hosts === null && !error) {
    return <WidgetCardSkeleton title="Hosts" />;
  }
  if (hosts === null && error) {
    return (
      <WidgetCardError
        title="Hosts"
        href="/hosts"
        message="Could not load hosts from Cuebot."
      />
    );
  }

  const list = hosts ?? [];
  const up = list.filter((h) => h.state === UP_STATE).length;
  const down = list.length - up;
  const locked = list.filter((h) => h.lockState && h.lockState !== "OPEN").length;

  return (
    <WidgetCard
      title="Hosts"
      icon={<Server className="h-4 w-4" />}
      value={`${up} / ${list.length}`}
      subLabel={`${up} up - ${down} not up`}
      footer={
        list.length === 0
          ? "No hosts reporting yet."
          : `${locked} locked (NLE / DISABLED) - ${list.length - locked} open`
      }
      href="/hosts"
      ctaLabel="View hosts"
    />
  );
}
