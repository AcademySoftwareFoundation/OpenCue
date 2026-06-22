<!--
Copyright Contributors to the OpenCue Project

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# CueWeb plugins

A plugin is a manifest plus a lazily-loaded React component that mounts on its
own route under `/plugins/<name>`. This is the browser equivalent of the CueGUI
plugin system (`cuegui/cuegui/Plugins.py`,
`cuegui/cuegui/cueguiplugin/loader.py`), where each plugin declares metadata
(`PLUGIN_NAME`, `PLUGIN_DESCRIPTION`, `PLUGIN_PROVIDES`, ...) and exposes a class
the host instantiates.

## The contract

The contract types live in [`lib/plugins.ts`](../../lib/plugins.ts):

- **`PluginManifest`** — `name` (URL-safe id and route segment), `title`,
  `version`, `route`, optional `description`.
- **`PluginModule`** — the `manifest` plus a `load` thunk that returns a dynamic
  `import()` of the component module (`() => import("./my-plugin")`). Keeping
  `load` a static `import()` expression lets the bundler split the plugin into
  its own chunk, fetched only when its route is visited.
- **`PluginComponentProps`** — every plugin component receives the `manifest`
  that resolved to it.

## How it loads

- `app/plugins/[plugin-name]/page.tsx` (server component) resolves the manifest
  by name, sets metadata, and calls `notFound()` for unknown plugins.
- `app/plugins/[plugin-name]/plugin-host.tsx` (client component) loads the
  component with `next/dynamic({ ssr: false })`. Plugin UIs are client
  components, and Next.js 15 disallows `ssr: false` in server components, so the
  dynamic import lives here.
- `app/plugins/page.tsx` lists every registered plugin.

## Adding a plugin

1. Create `app/plugins/<name>/<name>-plugin.tsx` — a default-exported React
   component accepting `PluginComponentProps`.
2. Add `app/plugins/<name>/manifest.ts` exporting a `PluginModule` whose `load`
   is `() => import("./<name>-plugin")`.
3. Register it in `PLUGIN_REGISTRY` in `lib/plugins.ts`.

See [`hello/`](./hello) for a working example, served at `/plugins/hello`.
