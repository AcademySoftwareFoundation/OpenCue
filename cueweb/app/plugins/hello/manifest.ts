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

import type { PluginModule } from "@/lib/plugins";

/**
 * Manifest for the sample "hello world" plugin. `load` is a deferred
 * `import()` so the component lands in its own chunk and is only fetched
 * when `/plugins/hello` is visited.
 */
export const helloPlugin: PluginModule = {
  manifest: {
    name: "hello",
    title: "Hello OpenCue",
    version: "1.0.0",
    route: "/plugins/hello",
    description: "A minimal example plugin that proves the CueWeb plugin contract.",
    // Not shown in the Plugins menu by default; users can enable it on the
    // plugins page.
    defaultEnabled: false,
  },
  load: () => import("./hello-plugin"),
};
