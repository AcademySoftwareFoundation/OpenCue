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

import dynamic from "next/dynamic";
import * as React from "react";

import { getPlugin, type PluginManifest } from "@/lib/plugins";

/**
 * Client-side host that resolves a plugin by name and renders its component.
 *
 * The component is loaded with `next/dynamic({ ssr: false })`: plugin UIs are
 * client components (they own state / browser APIs), and Next.js 15 disallows
 * `ssr: false` in Server Components — so the dynamic import has to live here.
 * `useMemo` keys the loaded component on the plugin name so it is created once
 * per route rather than on every render.
 */
export function PluginHost({ name }: { name: string }) {
  const plugin = getPlugin(name);

  const Component = React.useMemo(() => {
    if (!plugin) return null;
    return dynamic(() => plugin.load(), {
      ssr: false,
      loading: () => <p className="text-sm text-muted-foreground">Loading plugin…</p>,
    });
  }, [plugin]);

  if (!plugin || !Component) {
    // The server page already calls notFound() for unknown plugins; this is a
    // defensive fallback in case the host is rendered without a match.
    return <p className="text-sm text-muted-foreground">Plugin &quot;{name}&quot; was not found.</p>;
  }

  return <Component manifest={plugin.manifest as PluginManifest} />;
}
