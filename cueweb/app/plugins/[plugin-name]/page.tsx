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
import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { getPlugin, getPlugins } from "@/lib/plugins";
import { PluginHost } from "./plugin-host";

// The `[plugin-name]` segment is named with a hyphen, so the resolved param
// key is the literal string "plugin-name".
type PluginRouteParams = { "plugin-name": string };

/**
 * Pre-render a static page per registered plugin. New plugins added to the
 * registry are picked up automatically.
 */
export function generateStaticParams(): PluginRouteParams[] {
  return getPlugins().map((plugin) => ({ "plugin-name": plugin.manifest.name }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<PluginRouteParams>;
}): Promise<Metadata> {
  const { "plugin-name": name } = await params;
  const plugin = getPlugin(name);
  return {
    title: plugin ? `${plugin.manifest.title} · CueWeb Plugins` : "Plugin not found · CueWeb",
  };
}

export default async function PluginPage({ params }: { params: Promise<PluginRouteParams> }) {
  // Next.js 15 passes route params as a Promise that must be awaited.
  const { "plugin-name": name } = await params;
  const plugin = getPlugin(name);

  if (!plugin) notFound();

  return (
    <div className="container mx-auto py-6 max-w-5xl">
      <Breadcrumbs
        items={[{ label: "Plugins", href: "/plugins" }, { label: plugin.manifest.title }]}
        className="mb-4"
      />

      <header className="mb-6">
        <h1 className="text-2xl font-semibold">{plugin.manifest.title}</h1>
        {plugin.manifest.description && (
          <p className="mt-1 text-sm text-muted-foreground">{plugin.manifest.description}</p>
        )}
      </header>

      <PluginHost name={name} />
    </div>
  );
}
