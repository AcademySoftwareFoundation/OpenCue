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

import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { getPlugins } from "@/lib/plugins";
import { PluginsBrowser } from "./plugins-browser";

export const metadata: Metadata = {
  title: "Plugins · CueWeb",
  description: "Plugins registered with CueWeb.",
};

export default function PluginsIndexPage() {
  // Pass only the (serializable) manifests to the client browser — PluginModule
  // also holds a `load` function, which cannot cross the server/client boundary.
  const manifests = getPlugins().map((plugin) => plugin.manifest);

  return (
    <div className="container mx-auto py-6 max-w-5xl">
      <Breadcrumbs items={[{ label: "Plugins" }]} className="mb-4" />

      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Plugins</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Each plugin declares a manifest and a lazily-loaded React component, and mounts on its own
          route. Search and select one to load it.
        </p>
      </header>

      {manifests.length === 0 ? (
        <p className="text-sm text-muted-foreground">No plugins are registered.</p>
      ) : (
        <PluginsBrowser plugins={manifests} />
      )}
    </div>
  );
}
