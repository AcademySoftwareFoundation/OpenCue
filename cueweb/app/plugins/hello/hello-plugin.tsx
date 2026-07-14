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

import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  openPluginSettings,
  usePluginSetting,
} from "@/components/ui/settings-dialog";
import { registerSetting, type PluginComponentProps } from "@/lib/plugins";

// Register this plugin's settings at module load. Because the module is loaded
// lazily when /plugins/hello is visited, the settings appear in the shared
// settings dialog as soon as the plugin is opened. Each call is idempotent and
// returns the definition, which we reuse with `usePluginSetting` below.
const GREETING_SETTING = registerSetting({
  key: "hello.greeting",
  plugin: "hello",
  label: "Greeting",
  kind: "string",
  default: "Hello",
  description: "Word the plugin greets you with.",
});

const SHOUT_SETTING = registerSetting({
  key: "hello.shout",
  plugin: "hello",
  label: "Shout it",
  kind: "boolean",
  default: false,
  description: "Render the greeting in uppercase.",
});

const EMOJI_SETTING = registerSetting({
  key: "hello.emoji",
  plugin: "hello",
  label: "Emoji",
  kind: "select",
  default: "👋",
  description: "Emoji shown after the greeting.",
  // Note: Radix Select disallows empty-string option values, so each emoji is
  // a non-empty value.
  options: [
    { label: "Wave 👋", value: "👋" },
    { label: "Rocket 🚀", value: "🚀" },
    { label: "Sparkles ✨", value: "✨" },
  ],
});

/**
 * Sample "hello world" plugin. Demonstrates the plugin contract (a lazily
 * loaded component mounted on its route) and the generic settings registry:
 * its greeting is driven by persisted plugin settings, so edits made in the
 * settings dialog survive a reload.
 */
export default function HelloPlugin({ manifest }: PluginComponentProps) {
  const greeting = usePluginSetting(GREETING_SETTING) as string;
  const shout = usePluginSetting(SHOUT_SETTING) as boolean;
  const emoji = usePluginSetting(EMOJI_SETTING) as string;

  const text = shout ? greeting.toUpperCase() : greeting;

  return (
    <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <h2 className="text-xl font-semibold">
        {text} from the {manifest.title} plugin{emoji ? ` ${emoji}` : ""}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        This greeting is driven by plugin settings persisted in{" "}
        <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">localStorage</code>. Open
        the settings, change them, then reload — your changes stick.
      </p>

      <div className="mt-4">
        <Button type="button" variant="outline" onClick={() => openPluginSettings(manifest.name)}>
          Open plugin settings
        </Button>
      </div>

      <dl className="mt-6 grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="font-medium text-muted-foreground">Greeting</dt>
        <dd className="font-mono">{greeting}</dd>
        <dt className="font-medium text-muted-foreground">Shout</dt>
        <dd className="font-mono">{String(shout)}</dd>
        <dt className="font-medium text-muted-foreground">Emoji</dt>
        <dd className="font-mono">{emoji || "(none)"}</dd>
        <dt className="font-medium text-muted-foreground">Version</dt>
        <dd className="font-mono">{manifest.version}</dd>
        <dt className="font-medium text-muted-foreground">Route</dt>
        <dd className="font-mono">{manifest.route}</dd>
      </dl>
    </div>
  );
}
